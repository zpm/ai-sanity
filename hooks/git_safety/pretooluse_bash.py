import os
import shlex
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common import _hook_io


class PreToolUseBashGitSafetyRuleChecks:

    """Git-safety rule checks for the Bash matcher. Each method takes the full PreToolUse payload dict and returns
    either a string deny-reason on violation or None to pass."""

    _DENIED_GIT_SUBCOMMANDS = frozenset({
        "add", "am", "apply", "bisect", "branch", "cherry-pick", "checkout", "clean", "clone",
        "commit", "config", "fetch", "filter-branch", "filter-repo", "gc", "init", "merge",
        "notes", "pack-refs", "prune", "pull", "push", "rebase", "remote", "repack", "reset",
        "restore", "revert", "rm", "stash", "submodule", "switch", "tag", "update-index",
        "update-ref", "worktree",
    })

    @staticmethod
    def check_deny_git_write_commands(pretooluse_payload):

        """Rejects all git write subcommands. Only read-only commands (diff, status, log, ls-files, show) and git mv
        are allowed. Checks the token immediately after 'git' (position 1) against the denied subcommand set, which
        matches the same surface area as the settings.json glob patterns (e.g. Bash(git commit *))."""
        bash_command_string = (pretooluse_payload.get("tool_input") or {}).get("command", "")
        try:
            command_tokens = shlex.split(bash_command_string)
        except ValueError:
            return None
        if not command_tokens or command_tokens[0] != "git":
            return None
        if len(command_tokens) < 2:
            return None
        subcommand = command_tokens[1]
        if subcommand in PreToolUseBashGitSafetyRuleChecks._DENIED_GIT_SUBCOMMANDS:
            return (
                "Git write commands are strictly prohibited. Only read commands"
                " (diff, status, log, ls-files, show) and `git mv` are allowed."
            )
        return None

    @staticmethod
    def check_require_git_mv_for_tracked_file_moves(pretooluse_payload):

        """Rejects Bash `mv` commands when any source argument is a git-tracked file or a directory containing tracked
        files. Runs `git ls-files <path>` against each non-flag source argument in the call's cwd; if the output is
        non-empty, the path has tracked content and `git mv` must be used instead. The rule comes from CLAUDE.md
        ('Always use `git mv` to rename or move tracked files. Only use plain `mv` if the file is not yet under
        version control'). The plain ls-files form (no --error-unmatch) is what catches the tracked-directory case:
        --error-unmatch only matches exact tracked paths, while plain ls-files lists every tracked file at or under
        the path."""
        bash_command_string = (pretooluse_payload.get("tool_input") or {}).get("command", "")
        bash_command_cwd = pretooluse_payload.get("cwd") or "."
        try:
            command_tokens = shlex.split(bash_command_string)
        except ValueError:
            return None
        if not command_tokens or command_tokens[0] != "mv":
            return None
        target_dir_mode = None
        for token in command_tokens[1:]:
            if token == "-t":
                target_dir_mode = "separate"
                break
            if token.startswith("--target-directory="):
                target_dir_mode = "inline"
                break
            if token == "--target-directory":
                target_dir_mode = "separate"
                break
        non_flag_argument_tokens = [t for t in command_tokens[1:] if not t.startswith("-")]
        if target_dir_mode == "separate":
            source_path_argument_tokens = non_flag_argument_tokens[1:]
        elif target_dir_mode == "inline":
            source_path_argument_tokens = non_flag_argument_tokens
        else:
            if len(non_flag_argument_tokens) < 2:
                return None
            source_path_argument_tokens = non_flag_argument_tokens[:-1]
        for source_path_argument in source_path_argument_tokens:
            git_ls_files_result = subprocess.run(
                ["git", "ls-files", "--", source_path_argument],
                cwd = bash_command_cwd,
                capture_output = True,
                text = True
            )
            if git_ls_files_result.stdout.strip():
                return (
                    f"Refused: `{source_path_argument}` is tracked by git (or contains tracked files). CLAUDE.md"
                    f" requires `git mv` instead of `mv` for tracked paths. Re-run with `git mv` for any tracked source."
                )
        return None


class PreToolUseBashGitSafetyHookEntry:

    """Composes git-safety rule checks for Bash tool calls."""

    _rule_check_methods_to_run_in_order = (
        PreToolUseBashGitSafetyRuleChecks.check_deny_git_write_commands,
        PreToolUseBashGitSafetyRuleChecks.check_require_git_mv_for_tracked_file_moves,
    )

    @staticmethod
    def main():

        """Reads the payload, runs every applicable rule check, denies on the first violation, otherwise passes
        through. Any unexpected error falls through to passthrough so a bug in this hook cannot block a command."""
        try:
            pretooluse_payload = _hook_io.PreToolUseHookIo.read_pretooluse_payload_from_stdin()
            for rule_check_method in PreToolUseBashGitSafetyHookEntry._rule_check_methods_to_run_in_order:
                deny_reason_or_none = rule_check_method(pretooluse_payload)
                if deny_reason_or_none is not None:
                    _hook_io.PreToolUseHookIo.emit_deny_decision_and_exit(deny_reason_or_none)
            _hook_io.PreToolUseHookIo.emit_passthrough_and_exit()
        except Exception:
            _hook_io.PreToolUseHookIo.emit_passthrough_and_exit()


if __name__ == "__main__":
    PreToolUseBashGitSafetyHookEntry.main()
