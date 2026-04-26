########################################################################################################################
# hooks/bash_safety/pretooluse_bash.py
#
# single entry point for all bash safety deny checks
########################################################################################################################


import os
import shlex
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import _common._command_parser
import _common._hook_io


class GitCommandsCheck:

    """Denies git write subcommands and auto-allows known read-only subcommands. Returns a deny reason string, True
    to allow, or None to passthrough."""

    _DENIED_GIT_SUBCOMMANDS = {
        "git": [
            "add",
            "am",
            "apply",
            "bisect",
            "branch",
            "cherry-pick",
            "checkout",
            "clean",
            "clone",
            "commit",
            "config",
            "fetch",
            "filter-branch",
            "filter-repo",
            "gc",
            "init",
            "merge",
            "notes",
            "pack-refs",
            "prune",
            "pull",
            "push",
            "rebase",
            "reflog",
            "remote",
            "repack",
            "reset",
            "restore",
            "revert",
            "rm",
            "stash",
            "submodule",
            "switch",
            "tag",
            "update-index",
            "update-ref",
            "worktree",
        ],
    }

    _ALLOWED_GIT_READONLY_SUBCOMMANDS = {
        "blame",
        "cat-file",
        "describe",
        "diff",
        "for-each-ref",
        "grep",
        "log",
        "ls-files",
        "ls-remote",
        "ls-tree",
        "mv",
        "name-rev",
        "rev-list",
        "rev-parse",
        "shortlog",
        "show",
        "status",
    }

    _DENY_MESSAGE = (
        "Git write commands are strictly prohibited. Only read commands"
        " (diff, status, log, ls-files, show) and `git mv` are allowed."
    )

    @staticmethod
    def check(clauses):

        """Checks every clause for denied git subcommands or global options, then checks if a single-clause command
        is an allowed read-only git subcommand. Returns a deny reason string, True to allow, or None to passthrough."""
        for clause in clauses:
            if clause[0] != "git" or len(clause) < 2:
                continue
            if clause[1].startswith("-"):
                return GitCommandsCheck._DENY_MESSAGE
        if DeniedCommandMatcher.any_clause_matches_denied_commands(
            clauses,
            GitCommandsCheck._DENIED_GIT_SUBCOMMANDS
        ):
            return GitCommandsCheck._DENY_MESSAGE
        if len(clauses) == 1 and clauses[0][0] == "git":
            if len(clauses[0]) == 1:
                return True
            if clauses[0][1] in GitCommandsCheck._ALLOWED_GIT_READONLY_SUBCOMMANDS:
                return True
        return None


class RequireGitMvForTrackedMovesCheck:

    """Rejects Bash mv commands when any source argument is a git-tracked file or a directory containing tracked files.
    Runs git ls-files against each non-flag source argument in the call's cwd."""

    _DENY_MESSAGE = (
        "Refused: `{source_path}` is tracked by git (or contains tracked files). Requires `git mv`"
        " instead of `mv` for tracked paths. Re-run with `git mv` for any tracked source."
    )

    @staticmethod
    def check(pretooluse_payload):

        """Returns a deny reason string if any mv source is tracked, or None."""
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
                return RequireGitMvForTrackedMovesCheck._DENY_MESSAGE.format(
                    source_path = source_path_argument
                )
        return None


class DeniedCommandMatcher:

    """Shared matching engine for command/subcommand deny dicts. Keys are command prefixes (single or multi-word),
    values are lists of denied subcommands or ["*"] to deny all uses of the command."""

    @staticmethod
    def any_clause_matches_denied_commands(clauses, denied_commands):

        """Returns True if any clause matches an entry in the denied commands dict."""
        for clause in clauses:
            for prefix_length in range(1, len(clause) + 1):
                prefix_key = " ".join(clause[:prefix_length])
                if prefix_key not in denied_commands:
                    continue
                denied_subcommands = denied_commands[prefix_key]
                if denied_subcommands == ["*"]:
                    return True
                if prefix_length < len(clause) and clause[prefix_length] in denied_subcommands:
                    return True
        return False


class DeferToUserCommandsCheck:

    """Rejects commands that Claude should not run but the user might need to. Covers package managers, system
    operations, and process management. Deny message tells Claude to suggest the command to the user."""

    _DENIED_COMMANDS = {
        "brew": ["*"],
        "bun": [
            "add",
            "install",
            "remove",
        ],
        "cargo": [
            "add",
            "install",
            "uninstall",
        ],
        "chmod": ["*"],
        "chown": ["*"],
        "curl": ["*"],
        "docker": ["*"],
        "gem": [
            "install",
            "uninstall",
        ],
        "npm": [
            "ci",
            "install",
            "uninstall",
            "update",
        ],
        "pip": [
            "install",
            "uninstall",
        ],
        "pip3": [
            "install",
            "uninstall",
        ],
        "pnpm": ["*"],
        "poetry": [
            "add",
            "install",
            "remove",
        ],
        "py -m pip": [
            "install",
            "uninstall",
        ],
        "python -m pip": [
            "install",
            "uninstall",
        ],
        "python3 -m pip": [
            "install",
            "uninstall",
        ],
        "kill": ["*"],
        "killall": ["*"],
        "pkill": ["*"],
        "sudo": ["*"],
        "taskkill": ["*"],
        "uv add": ["*"],
        "uv lock": ["*"],
        "uv sync": ["*"],
        "uv pip": [
            "compile",
            "install",
            "sync",
            "uninstall",
        ],
        "uv remove": ["*"],
        "wget": ["*"],
        "yarn": ["*"],
    }

    _DENY_MESSAGE = "This command is prohibited. Suggest it to the user instead of running it."

    @staticmethod
    def check(clauses):

        """Returns a deny reason string if any clause matches a denied command, or None."""
        if DeniedCommandMatcher.any_clause_matches_denied_commands(
            clauses,
            DeferToUserCommandsCheck._DENIED_COMMANDS
        ):
            return DeferToUserCommandsCheck._DENY_MESSAGE
        return None


class ProhibitedCommandsCheck:

    """Rejects commands that should never be used. Better alternatives exist within Claude's toolset."""

    _DENIED_COMMANDS = {
        "awk": ["*"],
        "bash": ["*"],
        "cmd": ["*"],
        "cmd.exe": ["*"],
        "powershell": ["*"],
        "pwsh": ["*"],
        "sed": ["*"],
        "sh": ["*"],
        "tee": ["*"],
        "zsh": ["*"],
    }

    _DENY_MESSAGE = "This command is prohibited. Use the appropriate Claude Code tool instead."

    @staticmethod
    def check(clauses):

        """Returns a deny reason string if any clause matches a denied command, or None."""
        if DeniedCommandMatcher.any_clause_matches_denied_commands(
            clauses,
            ProhibitedCommandsCheck._DENIED_COMMANDS
        ):
            return ProhibitedCommandsCheck._DENY_MESSAGE
        return None


class NoShellSubstitutionCheck:

    """Rejects commands containing shell substitution syntax. These hide commands inside arguments where the clause
    parser cannot see them."""

    # TODO: this denies quoted literals too (e.g. rg '$(' or echo '$(').
    # if that becomes a problem, scan with single-quote awareness so 'literal' content is skipped.
    _SUBSTITUTION_MARKERS = ("$(", "`", "<(", ">(")

    _DENY_MESSAGE = (
        "Shell substitution syntax ($(), backticks, <(), >()) is prohibited."
        " Run each command separately instead."
    )

    @staticmethod
    def check(pretooluse_payload):

        """Returns a deny reason string if the raw command contains substitution syntax, or None."""
        bash_command_string = (pretooluse_payload.get("tool_input") or {}).get("command", "")
        for marker in NoShellSubstitutionCheck._SUBSTITUTION_MARKERS:
            if marker in bash_command_string:
                return NoShellSubstitutionCheck._DENY_MESSAGE
        return None


########################################################################################################################


class PreToolUseBashSafetyHookEntry:

    """Composes all bash safety checks. Outcomes: deny (string) blocks the command, allow (True) bypasses permission
    prompting, passthrough (None) falls back to Claude Code's normal permission/prompt UI."""

    _payload_based_deny_check_methods = (
        NoShellSubstitutionCheck.check,
        RequireGitMvForTrackedMovesCheck.check,
    )

    _clause_based_deny_check_methods = (
        DeferToUserCommandsCheck.check,
        ProhibitedCommandsCheck.check,
    )

    @staticmethod
    def _strip_safe_pipe_tail_from_payload(pretooluse_payload):

        """If the command is a pipe chain where every downstream clause starts with a safe output-filtering command,
        returns a copy of the payload with tool_input.command set to just the first clause (with descriptor merges
        stripped). Otherwise returns the payload unchanged. Bails out if the raw command contains shell substitution
        syntax, since stripping would hide those from downstream checks."""
        bash_command_string = (pretooluse_payload.get("tool_input") or {}).get("command", "")
        for marker in NoShellSubstitutionCheck._SUBSTITUTION_MARKERS:
            if marker in bash_command_string:
                return pretooluse_payload
        clauses, separators = (
            _common._command_parser.BashCommandParser.extract_command_clauses_and_separators(bash_command_string)
        )
        if len(clauses) < 2:
            return pretooluse_payload
        if not all(separator == "|" for separator in separators):
            return pretooluse_payload
        for downstream_clause in clauses[1:]:
            cleaned_downstream_clause = (
                _common._command_parser.RedirectTokenClassifier.strip_descriptor_merge_tokens_from_clause(
                    clause_tokens = downstream_clause
                )
            )
            if not cleaned_downstream_clause:
                return pretooluse_payload
            if cleaned_downstream_clause[0] not in _common._command_parser.SAFE_PIPE_TARGET_COMMANDS:
                return pretooluse_payload
        first_clause_cleaned = _common._command_parser.RedirectTokenClassifier.strip_descriptor_merge_tokens_from_clause(
            clause_tokens = clauses[0]
        )
        first_clause_command_string = " ".join(first_clause_cleaned)
        stripped_payload = dict(pretooluse_payload)
        stripped_payload["tool_input"] = dict(pretooluse_payload["tool_input"])
        stripped_payload["tool_input"]["command"] = first_clause_command_string
        return stripped_payload

    @staticmethod
    def main():

        """Reads the payload, runs all checks, and emits a deny, allow, or passthrough decision."""
        try:
            pretooluse_payload = _common._hook_io.PreToolUseHookIo.read_pretooluse_payload_from_stdin()
            pretooluse_payload = PreToolUseBashSafetyHookEntry._strip_safe_pipe_tail_from_payload(pretooluse_payload)
            bash_command_string = (pretooluse_payload.get("tool_input") or {}).get("command", "")
            clauses = _common._command_parser.BashCommandParser.extract_command_clauses(bash_command_string)
            git_check_result = GitCommandsCheck.check(clauses)
            if isinstance(git_check_result, str):
                _common._hook_io.PreToolUseHookIo.emit_deny_decision_and_exit(git_check_result)
            for payload_deny_check_method in PreToolUseBashSafetyHookEntry._payload_based_deny_check_methods:
                deny_reason_or_none = payload_deny_check_method(pretooluse_payload)
                if deny_reason_or_none is not None:
                    _common._hook_io.PreToolUseHookIo.emit_deny_decision_and_exit(deny_reason_or_none)
            for clause_deny_check_method in PreToolUseBashSafetyHookEntry._clause_based_deny_check_methods:
                deny_reason_or_none = clause_deny_check_method(clauses)
                if deny_reason_or_none is not None:
                    _common._hook_io.PreToolUseHookIo.emit_deny_decision_and_exit(deny_reason_or_none)
            if git_check_result is True:
                _common._hook_io.PreToolUseHookIo.emit_allow_decision_and_exit()
            _common._hook_io.PreToolUseHookIo.emit_passthrough_and_exit()
        except Exception:
            _common._hook_io.PreToolUseHookIo.emit_passthrough_and_exit()


if __name__ == "__main__":
    PreToolUseBashSafetyHookEntry.main()
