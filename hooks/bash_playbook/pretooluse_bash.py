########################################################################################################################
# hooks/bash_playbook/pretooluse_bash.py
#
# single entry point for all bash safety deny checks
#
# all command lists (deny, allow, safe) use the same dict format: {"command": ["*"]} to match all uses, or
# {"command": ["sub1", "sub2"]} to match specific subcommands. all lists are matched via CommandMatcher.
########################################################################################################################


import os
import shlex
import subprocess
import sys

# hot patch so that imports work when script is invoked directly (how claude invokes hooks)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json

import _common._command_parser
import _common._hook_io


class PlaybookMatchCheck:

    """Reads the project's .ai-sanity/playbook.json and matches a bash command against its entries. Supports exact and
    prefix (trailing ` *`) matching at the token level. If it's in the playbook, it's allowed."""

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

        """Reads and parses a playbook JSON file. Detects trailing ` *` in the bash field to enable prefix matching.
        Returns a list of dicts with added `_match_tokens` and `_is_prefix_match` keys, or [] on any error."""
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
            enriched_entry = dict(candidate_entry)
            enriched_entry["_match_tokens"] = match_tokens
            enriched_entry["_is_prefix_match"] = is_prefix_match
            valid_playbook_entries.append(enriched_entry)
        return valid_playbook_entries


    @staticmethod
    def check(pretooluse_payload):

        """Returns a matching playbook entry if the command tokens match (exact or prefix). Returns None on no match."""
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
        for candidate_playbook_entry in playbook_entries:
            entry_match_tokens = candidate_playbook_entry["_match_tokens"]
            if candidate_playbook_entry["_is_prefix_match"]:
                if (
                    len(command_tokens) >= len(entry_match_tokens)
                    and command_tokens[:len(entry_match_tokens)] == entry_match_tokens
                ):
                    return candidate_playbook_entry
            else:
                if command_tokens == entry_match_tokens:
                    return candidate_playbook_entry
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
        "powershell": ["*"],
        "powershell.exe": ["*"],
        "pwsh": ["*"],
        "pwsh.exe": ["*"],
        "sed": ["*"],
        "select": ["*"],
        "sh": ["*"],
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


class SafeCommandsCheck:

    """Auto-allows commands that are safe to run without user confirmation. Mirrors Claude Code's own auto-approve
    list. Returns True if every clause starts with a safe command, None otherwise."""

    _SAFE_COMMANDS = {
        "cat": ["*"],
        "cd": ["*"],
        "echo": ["*"],
        "find": ["*"],
        "grep": ["*"],
        "head": ["*"],
        "ls": ["*"],
        "printf": ["*"],
        "pwd": ["*"],
        "tail": ["*"],
        "wc": ["*"],
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
        if PlaybookMatchCheck.check(segment_payload) is not None:
            return "allow"
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
            compound_command_segments = (
                _common._command_parser.BashCommandParser.extract_compound_command_segments(bash_command_string)
            )
            if not compound_command_segments:
                _common._hook_io.PreToolUseHookIo.emit_passthrough_and_exit()
            segment_evaluation_results = []
            for segment_clause_groups in compound_command_segments:
                segment_payload = PreToolUseBashSafetyHookEntry._build_payload_for_command_segment(
                    segment_clause_groups = segment_clause_groups,
                    original_cwd = bash_command_cwd,
                )
                segment_result = PreToolUseBashSafetyHookEntry._evaluate_single_command_segment(
                    segment_payload = segment_payload,
                )
                if isinstance(segment_result, str) and segment_result != "allow":
                    _common._hook_io.PreToolUseHookIo.emit_deny_decision_and_exit(segment_result)
                segment_evaluation_results.append(segment_result)
            if all(result == "allow" for result in segment_evaluation_results):
                _common._hook_io.PreToolUseHookIo.emit_allow_decision_and_exit()
            _common._hook_io.PreToolUseHookIo.emit_passthrough_and_exit()
        except Exception:
            _common._hook_io.PreToolUseHookIo.emit_passthrough_and_exit()


if __name__ == "__main__":
    PreToolUseBashSafetyHookEntry.main()
