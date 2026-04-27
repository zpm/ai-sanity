########################################################################################################################
# hooks/playbook/pretooluse_bash.py
#
# auto-whitelists bash commands listed in a project's .ai-sanity/playbook.json
########################################################################################################################


import json
import os
import shlex
import sys

# hot patch so that imports work when script is invoked directly (how claude invokes hooks)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import _common._command_parser
import _common._hook_io


class PlaybookMatchCheck:

    """Finds the project's .ai-sanity/playbook.json and matches the first clause of a bash command against playbook
    entries. Supports exact and prefix (trailing ` *`) matching. Allows pipe chains to safe output-filtering commands
    and descriptor-to-descriptor redirects (2>&1). Rejects sequential operators (&&, ||, ;), file redirects, and
    pipes to commands not in the safe allowlist."""

    _playbook_relative_path_from_project_root = ".ai-sanity/playbook.json"

    _SAFE_PIPE_TARGET_COMMANDS = _common._command_parser.SAFE_PIPE_TARGET_COMMANDS


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
    def strip_descriptor_merge_tokens_from_clause(clause_tokens):

        """Removes descriptor merges and checks for file redirects. Returns the cleaned list, or None if a file
        redirect operator is detected (signaling the caller should passthrough)."""
        if _common._command_parser.RedirectTokenClassifier.clause_contains_file_redirect(clause_tokens):
            return None
        return _common._command_parser.RedirectTokenClassifier.strip_descriptor_merge_tokens_from_clause(
            clause_tokens = clause_tokens
        )


    @staticmethod
    def check(pretooluse_payload):

        """Returns a matching playbook entry if the first clause matches (exact or prefix) and all pipes target safe
        output-filtering commands. Returns None on no match, unsafe pipes, file redirects, or sequential operators."""
        bash_command_string = (pretooluse_payload.get("tool_input") or {}).get("command", "")
        bash_command_cwd = pretooluse_payload.get("cwd") or "."
        check_class = PlaybookMatchCheck
        playbook_abs_path = check_class.find_playbook_abs_path(
            starting_directory_abs_path = bash_command_cwd
        )
        if playbook_abs_path is None:
            return None
        playbook_entries = check_class.load_playbook_entries(
            playbook_abs_path = playbook_abs_path
        )
        if not playbook_entries:
            return None
        command_clauses, command_separators = (
            _common._command_parser.BashCommandParser.extract_command_clauses_and_separators(bash_command_string)
        )
        if not command_clauses:
            return None
        if any(separator != "|" for separator in command_separators):
            return None
        for downstream_clause in command_clauses[1:]:
            if not downstream_clause or downstream_clause[0] not in check_class._SAFE_PIPE_TARGET_COMMANDS:
                return None
            if check_class.strip_descriptor_merge_tokens_from_clause(downstream_clause) is None:
                return None
        first_clause_tokens = check_class.strip_descriptor_merge_tokens_from_clause(command_clauses[0])
        if first_clause_tokens is None:
            return None
        if not first_clause_tokens:
            return None
        for candidate_playbook_entry in playbook_entries:
            entry_match_tokens = candidate_playbook_entry["_match_tokens"]
            if candidate_playbook_entry["_is_prefix_match"]:
                if (
                    len(first_clause_tokens) >= len(entry_match_tokens)
                    and first_clause_tokens[:len(entry_match_tokens)] == entry_match_tokens
                ):
                    return candidate_playbook_entry
            else:
                if first_clause_tokens == entry_match_tokens:
                    return candidate_playbook_entry
        return None


########################################################################################################################


class PreToolUsePlaybookHookEntry:

    """Entry point. Outcomes: allow (playbook match) bypasses Claude Code's normal permission prompt, passthrough (no
    match) falls back to the normal permission/prompt UI. Errors fall through to passthrough so a bug cannot block."""


    @staticmethod
    def main():

        try:
            pretooluse_payload = _common._hook_io.PreToolUseHookIo.read_pretooluse_payload_from_stdin()
            matched_playbook_entry = PlaybookMatchCheck.check(
                pretooluse_payload = pretooluse_payload
            )
            if matched_playbook_entry is not None:
                _common._hook_io.PreToolUseHookIo.emit_allow_decision_and_exit()
            _common._hook_io.PreToolUseHookIo.emit_passthrough_and_exit()
        except Exception:
            _common._hook_io.PreToolUseHookIo.emit_passthrough_and_exit()


if __name__ == "__main__":
    PreToolUsePlaybookHookEntry.main()
