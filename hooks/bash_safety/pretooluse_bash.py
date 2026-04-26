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
        "add": ["*"],
        "am": ["*"],
        "apply": ["*"],
        "bisect": ["*"],
        "branch": ["*"],
        "cherry-pick": ["*"],
        "checkout": ["*"],
        "clean": ["*"],
        "clone": ["*"],
        "commit": ["*"],
        "config": ["*"],
        "fetch": ["*"],
        "filter-branch": ["*"],
        "filter-repo": ["*"],
        "gc": ["*"],
        "init": ["*"],
        "merge": ["*"],
        "notes": ["*"],
        "pack-refs": ["*"],
        "prune": ["*"],
        "pull": ["*"],
        "push": ["*"],
        "rebase": ["*"],
        "remote": ["*"],
        "reflog": ["*"],
        "repack": ["*"],
        "reset": ["*"],
        "restore": ["*"],
        "revert": ["*"],
        "rm": ["*"],
        "stash": ["*"],
        "submodule": ["*"],
        "switch": ["*"],
        "tag": ["*"],
        "update-index": ["*"],
        "update-ref": ["*"],
        "worktree": ["*"],
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
    def check(pretooluse_payload):

        """Checks every clause for denied git write subcommands, then checks if a single-clause command is an allowed
        read-only git subcommand. Returns a deny reason string, True to allow, or None to passthrough."""
        bash_command_string = (pretooluse_payload.get("tool_input") or {}).get("command", "")
        clauses = _common._command_parser.BashCommandParser.extract_command_clauses(bash_command_string)
        for clause in clauses:
            if clause[0] != "git" or len(clause) < 2:
                continue
            if clause[1] in GitCommandsCheck._DENIED_GIT_SUBCOMMANDS:
                return GitCommandsCheck._DENY_MESSAGE
        if len(clauses) == 1 and len(clauses[0]) >= 2 and clauses[0][0] == "git":
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


class NoPackageManagersCheck:

    """Rejects package manager install/add commands. Keys are command prefixes (multi-word for nested commands like
    uv pip or python -m pip). Values are lists of denied subcommands, or ["*"] to deny all subcommands."""

    _DENIED_PACKAGE_MANAGERS = {
        "yarn": ["*"],
        "pnpm": ["*"],
        "brew": ["*"],
        "pip": ["install"],
        "pip3": ["install"],
        "npm": ["install"],
        "cargo": ["install", "add"],
        "gem": ["install"],
        "bun": ["install", "add"],
        "poetry": ["add", "install"],
        "uv add": ["*"],
        "uv remove": ["*"],
        "uv pip": ["install", "uninstall", "sync", "compile"],
        "python -m pip": ["install"],
        "python3 -m pip": ["install"],
        "py -m pip": ["install"],
    }

    _DENY_MESSAGE = (
        "Package installation is strictly prohibited."
        " Suggest the command to the user instead of running it."
    )

    @staticmethod
    def check(pretooluse_payload):

        """Returns a deny reason string if any clause contains a package install command, or None."""
        bash_command_string = (pretooluse_payload.get("tool_input") or {}).get("command", "")
        clauses = _common._command_parser.BashCommandParser.extract_command_clauses(bash_command_string)
        checks = NoPackageManagersCheck
        for clause in clauses:
            for prefix_length in range(1, len(clause) + 1):
                prefix_key = " ".join(clause[:prefix_length])
                if prefix_key not in checks._DENIED_PACKAGE_MANAGERS:
                    continue
                denied_subcommands = checks._DENIED_PACKAGE_MANAGERS[prefix_key]
                if denied_subcommands == ["*"]:
                    return checks._DENY_MESSAGE
                if prefix_length < len(clause) and clause[prefix_length] in denied_subcommands:
                    return checks._DENY_MESSAGE
        return None


class NoSystemOperationsCheck:

    """Rejects system operation commands in any clause of the command."""

    _DENIED_COMMANDS = {
        "sudo": ["*"],
        "chmod": ["*"],
        "chown": ["*"],
        "curl": ["*"],
        "wget": ["*"],
        "docker": ["*"],
    }

    _DENY_MESSAGE = (
        "System operations (sudo, chmod, chown, curl, wget, docker) are strictly prohibited."
        " Have the user run the command instead."
    )

    @staticmethod
    def check(pretooluse_payload):

        """Returns a deny reason string if any clause starts with a denied system command, or None."""
        bash_command_string = (pretooluse_payload.get("tool_input") or {}).get("command", "")
        clauses = _common._command_parser.BashCommandParser.extract_command_clauses(bash_command_string)
        for clause in clauses:
            if clause[0] in NoSystemOperationsCheck._DENIED_COMMANDS:
                return NoSystemOperationsCheck._DENY_MESSAGE
        return None


class NoShellSpawningCheck:

    """Rejects sub-shell invocations in any clause of the command."""

    _DENIED_COMMANDS = {
        "bash": ["*"],
        "cmd": ["*"],
        "cmd.exe": ["*"],
        "powershell": ["*"],
    }

    _DENY_MESSAGE = "Spawning sub-shells is strictly prohibited. Run commands directly."

    @staticmethod
    def check(pretooluse_payload):

        """Returns a deny reason string if any clause starts with a denied shell command, or None."""
        bash_command_string = (pretooluse_payload.get("tool_input") or {}).get("command", "")
        clauses = _common._command_parser.BashCommandParser.extract_command_clauses(bash_command_string)
        for clause in clauses:
            if clause[0] in NoShellSpawningCheck._DENIED_COMMANDS:
                return NoShellSpawningCheck._DENY_MESSAGE
        return None


class NoGithubApiCheck:

    """Rejects gh api calls while allowing other gh subcommands (gh pr, gh issue, etc.)."""

    _DENIED_GH_SUBCOMMANDS = {
        "api": ["*"],
    }

    _DENY_MESSAGE = "Direct GitHub API calls via `gh api` are prohibited."

    @staticmethod
    def check(pretooluse_payload):

        """Returns a deny reason string if any clause contains gh api, or None."""
        bash_command_string = (pretooluse_payload.get("tool_input") or {}).get("command", "")
        clauses = _common._command_parser.BashCommandParser.extract_command_clauses(bash_command_string)
        for clause in clauses:
            if clause[0] != "gh" or len(clause) < 2:
                continue
            if clause[1] in NoGithubApiCheck._DENIED_GH_SUBCOMMANDS:
                return NoGithubApiCheck._DENY_MESSAGE
        return None


class NoTextManipulationCheck:

    """Rejects text manipulation commands in any clause of the command."""

    _DENIED_COMMANDS = {
        "sed": ["*"],
        "awk": ["*"],
        "tee": ["*"],
    }

    _DENY_MESSAGE = "Text manipulation via sed/awk/tee is prohibited. Use the Edit tool instead."

    @staticmethod
    def check(pretooluse_payload):

        """Returns a deny reason string if any clause starts with a denied text manipulation command, or None."""
        bash_command_string = (pretooluse_payload.get("tool_input") or {}).get("command", "")
        clauses = _common._command_parser.BashCommandParser.extract_command_clauses(bash_command_string)
        for clause in clauses:
            if clause[0] in NoTextManipulationCheck._DENIED_COMMANDS:
                return NoTextManipulationCheck._DENY_MESSAGE
        return None


class NoTaskkillCheck:

    """Rejects taskkill commands in any clause of the command."""

    _DENIED_COMMANDS = {
        "taskkill": ["*"],
    }

    _DENY_MESSAGE = "Process termination via taskkill is prohibited. Have the user run the command instead."

    @staticmethod
    def check(pretooluse_payload):

        """Returns a deny reason string if any clause starts with taskkill, or None."""
        bash_command_string = (pretooluse_payload.get("tool_input") or {}).get("command", "")
        clauses = _common._command_parser.BashCommandParser.extract_command_clauses(bash_command_string)
        for clause in clauses:
            if clause[0] in NoTaskkillCheck._DENIED_COMMANDS:
                return NoTaskkillCheck._DENY_MESSAGE
        return None


########################################################################################################################


class PreToolUseBashSafetyHookEntry:

    """Composes all bash safety checks. Runs git deny/allow first, then other deny checks, then passthrough."""

    _deny_check_methods_to_run_in_order = (
        RequireGitMvForTrackedMovesCheck.check,
        NoPackageManagersCheck.check,
        NoSystemOperationsCheck.check,
        NoShellSpawningCheck.check,
        NoGithubApiCheck.check,
        NoTextManipulationCheck.check,
        NoTaskkillCheck.check,
    )

    @staticmethod
    def main():

        """Reads the payload, runs all checks, and emits a deny, allow, or passthrough decision."""
        try:
            pretooluse_payload = _common._hook_io.PreToolUseHookIo.read_pretooluse_payload_from_stdin()
            git_check_result = GitCommandsCheck.check(pretooluse_payload)
            if isinstance(git_check_result, str):
                _common._hook_io.PreToolUseHookIo.emit_deny_decision_and_exit(git_check_result)
            for deny_check_method in PreToolUseBashSafetyHookEntry._deny_check_methods_to_run_in_order:
                deny_reason_or_none = deny_check_method(pretooluse_payload)
                if deny_reason_or_none is not None:
                    _common._hook_io.PreToolUseHookIo.emit_deny_decision_and_exit(deny_reason_or_none)
            if git_check_result is True:
                _common._hook_io.PreToolUseHookIo.emit_allow_decision_and_exit()
            _common._hook_io.PreToolUseHookIo.emit_passthrough_and_exit()
        except Exception:
            _common._hook_io.PreToolUseHookIo.emit_passthrough_and_exit()


if __name__ == "__main__":
    PreToolUseBashSafetyHookEntry.main()
