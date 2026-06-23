########################################################################################################################
# hooks/bash_playbook/pretooluse_bash.py
#
# single entry point for all bash safety deny checks
#
# all command lists (deny, allow, safe) use the same dict format: {"command": ["*"]} to match all uses, or
# {"command": ["sub1", "sub2"]} to match specific subcommands. all lists are matched via CommandMatcher.
########################################################################################################################


import os
import re
import shlex
import subprocess
import sys

# hot patch so that imports work when script is invoked directly (how claude invokes hooks)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json

import _common._command_parser
import _common._hook_io


class PlaybookMatchCheck:

    """Reads the project's .ai-sanity/playbook.json and matches a bash command against its entries. Supports exact,
    prefix (trailing ` *`), and project-root-relative (`*/` prefix) matching at the token level. Returns a dict
    (matched entry) for allow, a string (deny reason) for near-miss detection, or None for no match."""

    _playbook_relative_path_from_project_root = os.path.join(".ai-sanity", "playbook.json")


    @staticmethod
    def find_playbook_abs_path(starting_directory_abs_path):

        """Walks up from starting_directory_abs_path looking for .ai-sanity/playbook.json. Stops at $HOME or filesystem
        root. Returns the absolute path if found, None otherwise."""
        effective_home_abs_path = os.path.expanduser("~")
        current_directory_abs_path = os.path.abspath(starting_directory_abs_path)
        visited_directory_abs_paths = set()
        while True:
            if current_directory_abs_path in visited_directory_abs_paths:
                break
            visited_directory_abs_paths.add(current_directory_abs_path)
            candidate_playbook_abs_path = os.path.join(
                current_directory_abs_path,
                PlaybookMatchCheck._playbook_relative_path_from_project_root
            )
            if os.path.isfile(candidate_playbook_abs_path):
                return candidate_playbook_abs_path
            if current_directory_abs_path == effective_home_abs_path:
                break
            parent_directory_abs_path = os.path.dirname(current_directory_abs_path)
            if parent_directory_abs_path == current_directory_abs_path:
                break
            current_directory_abs_path = parent_directory_abs_path
        return None


    @staticmethod
    def load_playbook_entries(playbook_abs_path):

        """Reads and parses a playbook JSON file. Detects trailing ` *` for prefix matching and leading `*/` for
        project-root-relative path resolution. Returns a list of enriched entry dicts, or [] on any error."""
        try:
            with open(playbook_abs_path, "r", encoding = "utf-8") as open_playbook_file_handle:
                parsed_playbook_object = json.load(open_playbook_file_handle)
        except (OSError, json.JSONDecodeError):
            return []
        if not isinstance(parsed_playbook_object, list):
            return []
        valid_playbook_entries = []
        for candidate_entry in parsed_playbook_object:
            if not isinstance(candidate_entry, dict):
                continue
            bash_command_value = candidate_entry.get("bash")
            if not isinstance(bash_command_value, str) or not bash_command_value.strip():
                continue
            stripped_bash_value = bash_command_value.strip()
            is_prefix_match = stripped_bash_value.endswith(" *")
            command_to_tokenize = stripped_bash_value[:-2] if is_prefix_match else stripped_bash_value
            try:
                match_tokens = shlex.split(command_to_tokenize)
            except ValueError:
                continue
            if not match_tokens:
                continue
            project_root_relative_token_indices = set()
            resolved_match_tokens = []
            has_invalid_project_root_token = False
            for token_index, token_value in enumerate(match_tokens):
                if token_value.startswith("*/"):
                    stripped_token_value = token_value[2:]
                    if not stripped_token_value:
                        has_invalid_project_root_token = True
                        break
                    resolved_match_tokens.append(stripped_token_value)
                    project_root_relative_token_indices.add(token_index)
                else:
                    resolved_match_tokens.append(token_value)
            if has_invalid_project_root_token:
                continue
            enriched_entry = dict(candidate_entry)
            enriched_entry["_match_tokens"] = resolved_match_tokens
            enriched_entry["_is_prefix_match"] = is_prefix_match
            enriched_entry["_project_root_relative_token_indices"] = project_root_relative_token_indices
            valid_playbook_entries.append(enriched_entry)
        return valid_playbook_entries


    @staticmethod
    def _command_path_looks_like_same_playbook_path(entry_path_token, command_path_token):

        """Returns True when the command path appears to reference the same script as the playbook entry, just from a
        different cwd. Compares the normalized path tail (basename plus as many parent components as the shorter path
        has) so that ../../server/scripts/tests/all-fast.sh matches server/scripts/tests/all-fast.sh but
        ./server/scripts/tests/unit-fast.sh does not."""
        normalized_entry_parts = os.path.normpath(entry_path_token).split(os.sep)
        normalized_command_parts = os.path.normpath(command_path_token).split(os.sep)
        if not normalized_entry_parts or not normalized_command_parts:
            return False
        if normalized_entry_parts[-1] != normalized_command_parts[-1]:
            return False
        command_tail_length = min(len(normalized_entry_parts), len(normalized_command_parts))
        return normalized_entry_parts[-command_tail_length:] == normalized_command_parts[-command_tail_length:]


    @staticmethod
    def check(pretooluse_payload):

        """Returns a matching playbook entry if the command tokens match (exact, prefix, or project-root-relative).
        Returns None on no match."""
        bash_command_string = (pretooluse_payload.get("tool_input") or {}).get("command", "")
        bash_command_cwd = pretooluse_payload.get("cwd") or "."
        playbook_abs_path = PlaybookMatchCheck.find_playbook_abs_path(
            starting_directory_abs_path = bash_command_cwd
        )
        if playbook_abs_path is None:
            return None
        playbook_entries = PlaybookMatchCheck.load_playbook_entries(
            playbook_abs_path = playbook_abs_path
        )
        if not playbook_entries:
            return None
        try:
            command_tokens = shlex.split(bash_command_string)
        except ValueError:
            return None
        if not command_tokens:
            return None
        project_root_abs_path = os.path.dirname(os.path.dirname(playbook_abs_path))
        near_miss_deny_reason = None
        for candidate_playbook_entry in playbook_entries:
            entry_match_tokens = candidate_playbook_entry["_match_tokens"]
            project_root_relative_token_indices = candidate_playbook_entry["_project_root_relative_token_indices"]
            if project_root_relative_token_indices:
                if candidate_playbook_entry["_is_prefix_match"]:
                    if len(command_tokens) < len(entry_match_tokens):
                        continue
                else:
                    if len(command_tokens) != len(entry_match_tokens):
                        continue
                all_entry_tokens_match = True
                all_non_path_tokens_matched = True
                candidate_near_miss_command_path_token = None
                for token_index in range(len(entry_match_tokens)):
                    if token_index in project_root_relative_token_indices:
                        entry_token_resolved_abs_path = os.path.realpath(
                            os.path.join(project_root_abs_path, entry_match_tokens[token_index])
                        )
                        command_token_resolved_abs_path = os.path.realpath(
                            os.path.join(bash_command_cwd, command_tokens[token_index])
                        )
                        if entry_token_resolved_abs_path != command_token_resolved_abs_path:
                            all_entry_tokens_match = False
                            if (
                                PlaybookMatchCheck._command_path_looks_like_same_playbook_path(
                                    entry_path_token = entry_match_tokens[token_index],
                                    command_path_token = command_tokens[token_index],
                                )
                                and not os.path.exists(command_token_resolved_abs_path)
                            ):
                                candidate_near_miss_command_path_token = command_tokens[token_index]
                    else:
                        if entry_match_tokens[token_index] != command_tokens[token_index]:
                            all_entry_tokens_match = False
                            all_non_path_tokens_matched = False
                            break
                if all_entry_tokens_match:
                    return candidate_playbook_entry
                nonexistent_command_path_token = (
                    candidate_near_miss_command_path_token if all_non_path_tokens_matched else None
                )
                if nonexistent_command_path_token is not None and near_miss_deny_reason is None:
                    near_miss_deny_reason = (
                        f"Playbook script does not exist at the referenced path:"
                        f" {nonexistent_command_path_token} (check your working directory)"
                    )
            else:
                if candidate_playbook_entry["_is_prefix_match"]:
                    if (
                        len(command_tokens) >= len(entry_match_tokens)
                        and command_tokens[:len(entry_match_tokens)] == entry_match_tokens
                    ):
                        return candidate_playbook_entry
                else:
                    if command_tokens == entry_match_tokens:
                        return candidate_playbook_entry
        if near_miss_deny_reason is not None:
            return near_miss_deny_reason
        return None


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

    _ALLOWED_GIT_READONLY_COMMANDS = {
        "git": [
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
        ],
    }

    _DENY_MESSAGE = (
        "Git write commands are strictly prohibited. Only read commands"
        " (diff, status, log, ls-files, show) and `git mv` are allowed."
        " Commands must be `git <subcommand>` with no flags before the subcommand."
    )

    _DENY_GLOBAL_FLAGS_MESSAGE = (
        "Git global flags (e.g. -C, -c, --git-dir) are not allowed."
        " Rewrite as `git <subcommand>` with no flags between `git` and the subcommand."
    )


    @staticmethod
    def check(clauses):

        """Checks every clause for denied git subcommands or global options, then checks if a single-clause command
        is an allowed read-only git subcommand. Returns a deny reason string, True to allow, or None to passthrough."""
        for clause in clauses:
            if clause[0] != "git" or len(clause) < 2:
                continue
            if clause[1].startswith("-"):
                return GitCommandsCheck._DENY_GLOBAL_FLAGS_MESSAGE
        if CommandMatcher.any_clause_matches(
            clauses,
            GitCommandsCheck._DENIED_GIT_SUBCOMMANDS
        ):
            return GitCommandsCheck._DENY_MESSAGE
        if len(clauses) == 1 and clauses[0][0] == "git":
            if len(clauses[0]) == 1:
                return True
            if CommandMatcher.any_clause_matches(clauses, GitCommandsCheck._ALLOWED_GIT_READONLY_COMMANDS):
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


class CommandMatcher:

    """Shared matching engine for command/subcommand dicts. Keys are command prefixes (single or multi-word), values
    are lists of subcommands or ["*"] to match all uses of the command. Used by deny, allow, and safe checks."""


    @staticmethod
    def any_clause_matches(clauses, command_dict):

        """Returns True if any clause matches an entry in the command dict."""
        for clause in clauses:
            for prefix_length in range(1, len(clause) + 1):
                prefix_key = " ".join(clause[:prefix_length])
                if prefix_key not in command_dict:
                    continue
                matched_subcommands = command_dict[prefix_key]
                if matched_subcommands == ["*"]:
                    return True
                if prefix_length < len(clause) and clause[prefix_length] in matched_subcommands:
                    return True
        return False


    @staticmethod
    def all_clauses_match(clauses, command_dict):

        """Returns True if every clause matches an entry in the command dict."""
        for clause in clauses:
            if not CommandMatcher.any_clause_matches([clause], command_dict):
                return False
        return True


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
        "gh": ["*"],
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
        if CommandMatcher.any_clause_matches(
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
        "case": ["*"],
        "cmd": ["*"],
        "cmd.exe": ["*"],
        "for": ["*"],
        "if": ["*"],
        "perl": ["*"],
        "powershell": ["*"],
        "powershell.exe": ["*"],
        "pwsh": ["*"],
        "pwsh.exe": ["*"],
        "sed": ["*"],
        "select": ["*"],
        "sh": ["*"],
        "source": ["*"],
        "tee": ["*"],
        "until": ["*"],
        "while": ["*"],
        "zsh": ["*"],
    }

    _DENY_MESSAGE = "This command is prohibited. Use the appropriate Claude Code tool instead."


    @staticmethod
    def check(clauses):

        """Returns a deny reason string if any clause matches a denied command, or None."""
        if CommandMatcher.any_clause_matches(
            clauses,
            ProhibitedCommandsCheck._DENIED_COMMANDS
        ):
            return ProhibitedCommandsCheck._DENY_MESSAGE
        return None


class AbsolutePathCommandCheck:

    """Rejects commands whose command word is an absolute path (e.g. /usr/bin/grep, /opt/homebrew/bin/pdftotext). The
    deny and safe lists key on the command name, so a path-qualified binary bypasses both. Tools must be invoked by
    name so PATH resolution applies and the name-based lists govern the command."""

    _DENY_MESSAGE = (
        "Invoke tools by name so PATH resolution applies (e.g. `pdftotext`, not `/opt/homebrew/bin/pdftotext`)."
        " Absolute-path tool invocations are prohibited."
    )


    @staticmethod
    def check(clauses):

        """Returns a deny reason string if any clause's command word is an absolute path, or None."""

        for clause in clauses:
            if clause and clause[0].startswith("/"):
                return AbsolutePathCommandCheck._DENY_MESSAGE
        return None


class PowershellCmdletCheck:

    """Rejects PowerShell cmdlets and aliases inside Bash tool calls. Payload-based because PowerShell is
    case-insensitive and the clause-based CommandMatcher does exact matching."""

    _DENIED_POWERSHELL_TOKENS = frozenset((
        "add-content",
        "add-type",
        "clear-content",
        "clear-host",
        "clear-item",
        "clear-variable",
        "cls",
        "compare-object",
        "convertfrom-json",
        "convertto-json",
        "copy-item",
        "export-csv",
        "foreach-object",
        "format-list",
        "format-table",
        "gci",
        "gcm",
        "get-acl",
        "get-childitem",
        "get-command",
        "get-content",
        "get-date",
        "get-help",
        "get-item",
        "get-itemproperty",
        "get-location",
        "get-member",
        "get-module",
        "get-process",
        "get-service",
        "get-variable",
        "get-wmiobject",
        "gm",
        "iex",
        "import-csv",
        "import-module",
        "invoke-command",
        "invoke-expression",
        "invoke-restmethod",
        "invoke-webrequest",
        "iwr",
        "measure-object",
        "move-item",
        "new-item",
        "new-object",
        "new-variable",
        "ni",
        "out-file",
        "out-null",
        "out-string",
        "read-host",
        "remove-item",
        "remove-variable",
        "rename-item",
        "resolve-path",
        "ri",
        "select-object",
        "select-string",
        "set-content",
        "set-executionpolicy",
        "set-item",
        "set-itemproperty",
        "set-location",
        "set-variable",
        "sls",
        "sort-object",
        "split-path",
        "start-process",
        "start-sleep",
        "stop-process",
        "test-connection",
        "test-path",
        "where-object",
        "write-error",
        "write-host",
        "write-output",
        "write-verbose",
        "write-warning",
    ))

    _DENY_MESSAGE = "You are using bash dude, don't use Powershell commands"


    @staticmethod
    def check(pretooluse_payload):

        """Tokenizes the command and checks each token (case-insensitive) against known PowerShell cmdlets and
        aliases. Returns a deny reason string or None."""
        bash_command_string = (pretooluse_payload.get("tool_input") or {}).get("command", "")
        if not bash_command_string.strip():
            return None
        try:
            command_tokens = shlex.split(bash_command_string)
        except ValueError:
            command_tokens = bash_command_string.split()
        for token in command_tokens:
            token_lower = token.lower().rstrip(";")
            if token_lower in PowershellCmdletCheck._DENIED_POWERSHELL_TOKENS:
                return PowershellCmdletCheck._DENY_MESSAGE
        return None


class WindowsPathCheck:

    """Rejects bash commands containing Windows-style backslash paths. Scans the raw command string (before shlex
    tokenization, which eats backslashes) for drive-letter paths (C:\...) and dot-relative paths (.\..., ..\...)."""

    _WINDOWS_PATH_PATTERN = re.compile(r"(?:\b[A-Za-z]:\\|\.\.?\\)(?![|])")

    _DENY_MESSAGE = "You are using bash dude, use forward slashes for file paths instead of backslashes"


    @staticmethod
    def check(pretooluse_payload):

        """Returns a deny reason string if the raw command contains Windows-style backslash paths, or None."""
        bash_command_string = (pretooluse_payload.get("tool_input") or {}).get("command", "")
        if WindowsPathCheck._WINDOWS_PATH_PATTERN.search(bash_command_string):
            return WindowsPathCheck._DENY_MESSAGE
        return None


class TildePathCheck:

    """Rejects bash commands containing ~ (tilde) paths on Windows. Python's path functions do not expand tilde, so
    playbook path resolution and cd tracking produce bogus paths when the agent writes ~/... in a command."""

    _TILDE_PATH_PATTERN = re.compile(r"(?:^|\s)~/")

    _DENY_MESSAGE = "Try using absolute paths, ~ (tilde) is not supported by the hooks running on Windows"


    @staticmethod
    def check(pretooluse_payload):

        """Returns a deny reason string if the raw command contains tilde paths on Windows, or None."""
        if sys.platform != "win32":
            return None
        bash_command_string = (pretooluse_payload.get("tool_input") or {}).get("command", "")
        if TildePathCheck._TILDE_PATH_PATTERN.search(bash_command_string):
            return TildePathCheck._DENY_MESSAGE
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


class NoSubshellGroupingCheck:

    """Rejects subshell and command-grouping parentheses at command position (start of the command or right after a
    separator). Grouping hides multiple commands behind one approval and breaks the clause parser, which cannot see
    the commands inside the group. A ( inside an argument (e.g. grep -E "(a|b)") is not at command position, so it is
    allowed."""

    # TODO: this matches a command-position ( inside a quoted literal too (e.g. grep -E 'a|(b)').
    # if that becomes a problem, scan with single-quote awareness so 'literal' content is skipped.
    _SUBSHELL_OPEN_PATTERN = re.compile(r"(?:^|[;&|])\s*\(")

    _DENY_MESSAGE = "Subshells and command grouping with ( ) are prohibited. Run each command separately."


    @staticmethod
    def check(pretooluse_payload):

        """Returns a deny reason string if the raw command opens a subshell or group at command position, or None."""

        bash_command_string = (pretooluse_payload.get("tool_input") or {}).get("command", "")
        if NoSubshellGroupingCheck._SUBSHELL_OPEN_PATTERN.search(bash_command_string):
            return NoSubshellGroupingCheck._DENY_MESSAGE
        return None


class NoShellVariableCheck:

    """Rejects commands that assign or expand shell variables. The literal value a variable stands for is invisible to
    the user approving the command and to the clause parser, so claude must inline the literal value instead."""

    # TODO: this denies quoted literals too (e.g. grep '$HOME' or echo 'VAR=x').
    # if that becomes a problem, scan with single-quote awareness so 'literal' content is skipped.
    # assignment matches a NAME= token at the start of the command or after a separator (e.g. FOO=bar, x | BAR=baz);
    # it deliberately ignores NAME= that appears as an argument or --flag=value (no separator precedes the name).
    _ASSIGNMENT_PATTERN = re.compile(r"(?:^|[;&|])\s*[A-Za-z_][A-Za-z0-9_]*=")
    _EXPANSION_PATTERN = re.compile(r"\$\{?[A-Za-z_]")

    _DENY_MESSAGE = "Shell variables ($VAR, VAR=...) are prohibited. Inline the literal value instead."


    @staticmethod
    def command_contains_shell_variable(bash_command_string):

        """Returns True if the raw command assigns or expands a shell variable."""

        if NoShellVariableCheck._ASSIGNMENT_PATTERN.search(bash_command_string):
            return True
        if NoShellVariableCheck._EXPANSION_PATTERN.search(bash_command_string):
            return True
        return False


    @staticmethod
    def check(pretooluse_payload):

        """Returns a deny reason string if the raw command assigns or expands a shell variable, or None."""

        bash_command_string = (pretooluse_payload.get("tool_input") or {}).get("command", "")
        if NoShellVariableCheck.command_contains_shell_variable(bash_command_string):
            return NoShellVariableCheck._DENY_MESSAGE
        return None


class SafeCommandsCheck:

    """Auto-allows commands that are safe to run without user confirmation. Mirrors Claude Code's own auto-approve
    list. Returns True if every clause starts with a safe command, None otherwise."""

    _SAFE_COMMANDS = {
        "cat": ["*"],
        "cd": ["*"],
        "cp": ["*"],
        "echo": ["*"],
        "find": ["*"],
        "grep": ["*"],
        "head": ["*"],
        "ls": ["*"],
        "mdls": ["*"],
        "pdftotext": ["*"],
        "printf": ["*"],
        "pwd": ["*"],
        "tail": ["*"],
        "textutil": ["*"],
        "tr": ["*"],
        "wc": ["*"],
        "which": ["*"],
    }


    @staticmethod
    def check(clauses):

        """Returns True if every clause matches a safe command, or None for passthrough."""
        if not clauses:
            return None
        if CommandMatcher.all_clauses_match(clauses, SafeCommandsCheck._SAFE_COMMANDS):
            return True
        return None


########################################################################################################################


class PreToolUseBashSafetyHookEntry:

    """Composes all bash safety checks. Outcomes: deny (string) blocks the command, allow (True) bypasses permission
    prompting, passthrough (None) falls back to Claude Code's normal permission/prompt UI."""

    _payload_based_deny_check_methods = (
        PowershellCmdletCheck.check,
        NoShellSubstitutionCheck.check,
        NoShellVariableCheck.check,
        RequireGitMvForTrackedMovesCheck.check,
    )

    _clause_based_deny_check_methods = (
        AbsolutePathCommandCheck.check,
        DeferToUserCommandsCheck.check,
        ProhibitedCommandsCheck.check,
    )


    @staticmethod
    def _strip_safe_pipe_tail_from_payload(pretooluse_payload):

        """If the command is a pipe chain where every downstream clause starts with a safe output-filtering command,
        returns a copy of the payload with tool_input.command set to just the first clause (with descriptor merges
        stripped). Otherwise returns the payload unchanged. Bails out if the raw command contains shell substitution
        syntax or a shell variable, since stripping would hide those from downstream checks."""
        bash_command_string = (pretooluse_payload.get("tool_input") or {}).get("command", "")
        for marker in NoShellSubstitutionCheck._SUBSTITUTION_MARKERS:
            if marker in bash_command_string:
                return pretooluse_payload
        if NoShellVariableCheck.command_contains_shell_variable(bash_command_string):
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
        first_clause_cleaned = (
            _common._command_parser.RedirectTokenClassifier.strip_descriptor_merge_tokens_from_clause(
                clause_tokens = clauses[0]
            )
        )
        first_clause_command_string = " ".join(first_clause_cleaned)
        stripped_payload = dict(pretooluse_payload)
        stripped_payload["tool_input"] = dict(pretooluse_payload["tool_input"])
        stripped_payload["tool_input"]["command"] = first_clause_command_string
        return stripped_payload


    @staticmethod
    def _build_payload_for_command_segment(segment_clause_groups, original_cwd):

        """Reconstructs a pretooluse payload for a single command segment. Strips descriptor merge tokens (2>&1 etc.)
        from each clause since they are never relevant to safety checks."""
        cleaned_segment_clause_groups = [
            _common._command_parser.RedirectTokenClassifier.strip_descriptor_merge_tokens_from_clause(
                clause_tokens = clause
            )
            for clause in segment_clause_groups
        ]
        segment_command_string = " | ".join(
            shlex.join(clause) for clause in cleaned_segment_clause_groups if clause
        )
        return {
            "tool_input": {"command": segment_command_string},
            "cwd": original_cwd,
        }


    @staticmethod
    def _evaluate_single_command_segment(segment_payload):

        """Evaluates one command segment through the full check pipeline. Returns the string 'allow', a deny reason
        string, or None for passthrough."""
        segment_payload = PreToolUseBashSafetyHookEntry._strip_safe_pipe_tail_from_payload(segment_payload)
        playbook_check_result = PlaybookMatchCheck.check(segment_payload)
        if isinstance(playbook_check_result, dict):
            return "allow"
        if isinstance(playbook_check_result, str):
            return playbook_check_result
        bash_command_string = (segment_payload.get("tool_input") or {}).get("command", "")
        clauses = _common._command_parser.BashCommandParser.extract_command_clauses(bash_command_string)
        git_check_result = GitCommandsCheck.check(clauses)
        if isinstance(git_check_result, str):
            return git_check_result
        for payload_based_deny_check_method in PreToolUseBashSafetyHookEntry._payload_based_deny_check_methods:
            deny_reason_or_none = payload_based_deny_check_method(segment_payload)
            if deny_reason_or_none is not None:
                return deny_reason_or_none
        for clause_based_deny_check_method in PreToolUseBashSafetyHookEntry._clause_based_deny_check_methods:
            deny_reason_or_none = clause_based_deny_check_method(clauses)
            if deny_reason_or_none is not None:
                return deny_reason_or_none
        if git_check_result is True:
            return "allow"
        if SafeCommandsCheck.check(clauses) is True:
            return "allow"
        return None


    @staticmethod
    def main():

        """Splits the command into compound segments, evaluates each independently, and aggregates: any deny blocks
        the entire command, all-allow auto-approves, mixed allow/passthrough falls through to Claude Code's
        normal permission UI."""
        try:
            pretooluse_payload = _common._hook_io.PreToolUseHookIo.read_pretooluse_payload_from_stdin()
            bash_command_string = (pretooluse_payload.get("tool_input") or {}).get("command", "")
            bash_command_cwd = pretooluse_payload.get("cwd") or "."
            # raw-path checks run first on the raw command string and are absolute: this syntax would corrupt the
            # tokenizer and path matching (including the playbook matcher), so it is denied before the playbook check
            windows_path_deny_reason = WindowsPathCheck.check(pretooluse_payload)
            if windows_path_deny_reason is not None:
                _common._hook_io.PreToolUseHookIo.emit_deny_decision_and_exit(windows_path_deny_reason)
            tilde_path_deny_reason = TildePathCheck.check(pretooluse_payload)
            if tilde_path_deny_reason is not None:
                _common._hook_io.PreToolUseHookIo.emit_deny_decision_and_exit(tilde_path_deny_reason)
            # subshell/group parens break clause parsing (the inner commands are invisible to the matcher), so they
            # are denied on the raw command string before segmentation, the same as the raw-path checks above
            subshell_grouping_deny_reason = NoSubshellGroupingCheck.check(pretooluse_payload)
            if subshell_grouping_deny_reason is not None:
                _common._hook_io.PreToolUseHookIo.emit_deny_decision_and_exit(subshell_grouping_deny_reason)
            compound_command_segments = (
                _common._command_parser.BashCommandParser.extract_compound_command_segments(bash_command_string)
            )
            if not compound_command_segments:
                _common._hook_io.PreToolUseHookIo.emit_passthrough_and_exit()
            segment_evaluation_results = []
            effective_segment_cwd = bash_command_cwd
            for segment_clause_groups in compound_command_segments:
                segment_payload = PreToolUseBashSafetyHookEntry._build_payload_for_command_segment(
                    segment_clause_groups = segment_clause_groups,
                    original_cwd = effective_segment_cwd,
                )
                segment_result = PreToolUseBashSafetyHookEntry._evaluate_single_command_segment(
                    segment_payload = segment_payload,
                )
                if isinstance(segment_result, str) and segment_result != "allow":
                    _common._hook_io.PreToolUseHookIo.emit_deny_decision_and_exit(segment_result)
                segment_evaluation_results.append(segment_result)
                if (
                    len(segment_clause_groups) == 1
                    and len(segment_clause_groups[0]) == 2
                    and segment_clause_groups[0][0] == "cd"
                ):
                    cd_target_path = segment_clause_groups[0][1]
                    if os.path.isabs(cd_target_path):
                        effective_segment_cwd = cd_target_path
                    else:
                        effective_segment_cwd = os.path.normpath(
                            os.path.join(effective_segment_cwd, cd_target_path)
                        )
            if all(result == "allow" for result in segment_evaluation_results):
                _common._hook_io.PreToolUseHookIo.emit_allow_decision_and_exit()
            _common._hook_io.PreToolUseHookIo.emit_passthrough_and_exit()
        except Exception as e:
            _common._hook_io.PreToolUseHookIo.emit_deny_decision_and_exit(f"bash_playbook/pretooluse_bash hook crashed: {e}")


if __name__ == "__main__":
    PreToolUseBashSafetyHookEntry.main()
