########################################################################################################################
# hooks/pretooluse_bash.py
#
# PreToolUse entry script for the Bash matcher and its rule check methods
########################################################################################################################
import os
import shlex
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import _lib


class PreToolUseBashRuleChecks:

    """Rule checks that apply only to the Bash matcher. Each method takes the full PreToolUse payload dict and returns
    either a string deny-reason on violation or None to pass. Per the enforcement-philosophy section, this file is
    deliberately narrow: install detection and all git write subcommand blocking live entirely in settings.json deny
    rules. The hook only handles cases settings.json globs cannot express: dynamic git ls-files on mv, and per-token
    memory path scan."""

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
        non_flag_argument_tokens = [t for t in command_tokens[1:] if not t.startswith("-")]
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

    @staticmethod
    def check_no_memory_access_for_bash(pretooluse_payload):

        """Bash-side memory check. Tokenises the command and checks each token against the auto-memory directory and
        MEMORY.md path patterns. This is more accurate than scanning the raw command string: `echo "search for
        MEMORY.md term"` shlex-splits into a single token whose start position is not preceded by `/` or `\\`, so the
        regex correctly does not match. Falls back to scanning the raw command string when tokenisation fails
        (malformed quoting), to avoid bypass via crafted broken syntax."""
        bash_command_string = (pretooluse_payload.get("tool_input") or {}).get("command", "")
        try:
            command_tokens = shlex.split(bash_command_string)
            return _lib.MemoryPathChecker.assert_paths_are_not_memory_locations(*command_tokens)
        except ValueError:
            return _lib.MemoryPathChecker.assert_paths_are_not_memory_locations(bash_command_string)


class PreToolUseBashHookEntry:

    """Composes every rule check that applies to Bash tool calls in declaration order."""

    _rule_check_methods_to_run_in_order = (
        PreToolUseBashRuleChecks.check_require_git_mv_for_tracked_file_moves,
        PreToolUseBashRuleChecks.check_no_memory_access_for_bash
    )

    @staticmethod
    def main():

        """Reads the payload, runs every applicable rule check, denies on the first violation, otherwise passes through."""
        pretooluse_payload = _lib.PreToolUseHookIo.read_pretooluse_payload_from_stdin()
        for rule_check_method in PreToolUseBashHookEntry._rule_check_methods_to_run_in_order:
            deny_reason_or_none = rule_check_method(pretooluse_payload)
            if deny_reason_or_none is not None:
                _lib.PreToolUseHookIo.emit_deny_decision_and_exit(deny_reason_or_none)
        _lib.PreToolUseHookIo.emit_passthrough_and_exit()


if __name__ == "__main__":
    PreToolUseBashHookEntry.main()