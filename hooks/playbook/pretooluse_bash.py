########################################################################################################################
# hooks/playbook/pretooluse_bash.py
#
# auto-whitelists bash commands listed in a project's .ai-sanity/playbook.json
########################################################################################################################


import json
import os
import shlex
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import common._command_parser
import common._hook_io


class PlaybookExactMatchCheck:

    """Finds the project's .ai-sanity/playbook.json and returns a matching entry when the bash command exactly matches
    a playbook command (after normalization). Multi-clause commands never match."""

    _playbook_relative_path_from_project_root = ".ai-sanity/playbook.json"

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
                PlaybookExactMatchCheck._playbook_relative_path_from_project_root
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

        """Reads and parses a playbook JSON file. Returns a list of entry dicts, or [] on any error."""
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
            valid_playbook_entries.append(candidate_entry)
        return valid_playbook_entries

    @staticmethod
    def normalize_command_for_matching(command_string):

        """Normalizes a command string by tokenizing via shlex and rejoining, which strips redundant quoting and
        whitespace. Falls back to strip() on malformed quoting so the caller always gets a comparable string."""
        stripped_command_string = command_string.strip()
        if not stripped_command_string:
            return ""
        try:
            tokenized_command_parts = shlex.split(stripped_command_string)
            if not tokenized_command_parts:
                return ""
            return " ".join(tokenized_command_parts)
        except ValueError:
            return stripped_command_string

    @staticmethod
    def check(pretooluse_payload):

        """Returns a matching playbook entry dict if the command exactly matches (after normalization) a single-clause
        playbook command, or None if no match (passthrough signal)."""
        bash_command_string = (pretooluse_payload.get("tool_input") or {}).get("command", "")
        bash_command_cwd = pretooluse_payload.get("cwd") or "."
        playbook_abs_path = PlaybookExactMatchCheck.find_playbook_abs_path(
            starting_directory_abs_path = bash_command_cwd
        )
        if playbook_abs_path is None:
            return None
        playbook_entries = PlaybookExactMatchCheck.load_playbook_entries(
            playbook_abs_path = playbook_abs_path
        )
        if not playbook_entries:
            return None
        command_clauses = common._command_parser.BashCommandParser.extract_command_clauses(bash_command_string)
        if len(command_clauses) != 1:
            return None
        normalized_command_string = PlaybookExactMatchCheck.normalize_command_for_matching(bash_command_string)
        if not normalized_command_string:
            return None
        for candidate_playbook_entry in playbook_entries:
            normalized_playbook_bash_string = PlaybookExactMatchCheck.normalize_command_for_matching(
                candidate_playbook_entry["bash"]
            )
            if normalized_command_string == normalized_playbook_bash_string:
                return candidate_playbook_entry
        return None


########################################################################################################################


class PreToolUsePlaybookHookEntry:

    """Entry point. Allows exact playbook matches, passes through everything else. Errors fall through to passthrough
    so a bug in this hook cannot block a command."""

    @staticmethod
    def main():

        try:
            pretooluse_payload = common._hook_io.PreToolUseHookIo.read_pretooluse_payload_from_stdin()
            matched_playbook_entry = PlaybookExactMatchCheck.check(
                pretooluse_payload = pretooluse_payload
            )
            if matched_playbook_entry is not None:
                common._hook_io.PreToolUseHookIo.emit_allow_decision_and_exit()
            common._hook_io.PreToolUseHookIo.emit_passthrough_and_exit()
        except Exception:
            common._hook_io.PreToolUseHookIo.emit_passthrough_and_exit()


if __name__ == "__main__":
    PreToolUsePlaybookHookEntry.main()
