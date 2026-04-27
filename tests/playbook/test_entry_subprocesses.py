########################################################################################################################
# tests/playbook/test_entry_subprocesses.py
#
# integration tests invoking the playbook entry script as a subprocess
########################################################################################################################


import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "hooks"))

import tests._common.fixtures
import tests._common.subprocess_helpers


class TestPreToolUsePlaybookEntryScript(unittest.TestCase):

    def setUp(self):

        self.temp_project_directory = tempfile.mkdtemp()
        self.dot_ai_sanity_directory = os.path.join(self.temp_project_directory, ".ai-sanity")
        os.makedirs(self.dot_ai_sanity_directory)
        self.playbook_abs_path = os.path.join(self.dot_ai_sanity_directory, "playbook.json")
        playbook_entries = [
            {
                "bash": "python -m unittest discover -s tests -t . -v",
                "what": "Runs the full test suite",
                "when": "Run as a final step after all changes have landed"
            },
            {
                "bash": "python -m unittest *",
                "what": "Run targeted tests",
                "when": "After modifying a specific hook"
            }
        ]
        with open(self.playbook_abs_path, "w", encoding = "utf-8") as open_playbook_file_handle:
            json.dump(playbook_entries, open_playbook_file_handle)


    def _invoke(self, command, working_directory = None):

        if working_directory is None:
            working_directory = self.temp_project_directory
        return tests._common.subprocess_helpers.HookEntryScriptInvocationHelper.invoke_entry_script(
            entry_script_relative_path = "playbook/pretooluse_bash.py",
            pretooluse_payload = tests._common.fixtures.PreToolUsePayloadFixtureBuilder.build_bash_payload(
                bash_command_string = command,
                working_directory = working_directory
            )
        )


    def test_exact_matching_command_is_allowed(self):

        exit_code, parsed_stdout = self._invoke("python -m unittest discover -s tests -t . -v")
        tests._common.subprocess_helpers.HookEntryScriptInvocationHelper.assert_allow_decision(
            self, exit_code, parsed_stdout
        )


    def test_prefix_matching_command_is_allowed(self):

        exit_code, parsed_stdout = self._invoke("python -m unittest tests.playbook.test_rule_checks -v")
        tests._common.subprocess_helpers.HookEntryScriptInvocationHelper.assert_allow_decision(
            self, exit_code, parsed_stdout
        )


    def test_pipe_with_safe_target_is_allowed(self):

        exit_code, parsed_stdout = self._invoke(
            "python -m unittest discover -s tests -t . -v 2>&1 | tail -5"
        )
        tests._common.subprocess_helpers.HookEntryScriptInvocationHelper.assert_allow_decision(
            self, exit_code, parsed_stdout
        )


    def test_non_matching_command_passes_through(self):

        exit_code, parsed_stdout = self._invoke("ls -la")
        tests._common.subprocess_helpers.HookEntryScriptInvocationHelper.assert_passthrough(
            self, exit_code, parsed_stdout
        )


    def test_sequential_operator_passes_through(self):

        exit_code, parsed_stdout = self._invoke(
            "python -m unittest discover -s tests -t . -v && rm -rf /"
        )
        tests._common.subprocess_helpers.HookEntryScriptInvocationHelper.assert_passthrough(
            self, exit_code, parsed_stdout
        )


    def test_unsafe_pipe_target_passes_through(self):

        exit_code, parsed_stdout = self._invoke(
            "python -m unittest discover -s tests -t . -v | rm -rf /"
        )
        tests._common.subprocess_helpers.HookEntryScriptInvocationHelper.assert_passthrough(
            self, exit_code, parsed_stdout
        )


    def test_file_redirect_passes_through(self):

        exit_code, parsed_stdout = self._invoke(
            "python -m unittest discover -s tests -t . -v > output.txt"
        )
        tests._common.subprocess_helpers.HookEntryScriptInvocationHelper.assert_passthrough(
            self, exit_code, parsed_stdout
        )


    def test_no_playbook_passes_through(self):

        empty_temp_directory = tempfile.mkdtemp()
        exit_code, parsed_stdout = self._invoke(
            command = "python -m unittest discover -s tests -t . -v",
            working_directory = empty_temp_directory
        )
        tests._common.subprocess_helpers.HookEntryScriptInvocationHelper.assert_passthrough(
            self, exit_code, parsed_stdout
        )


    def test_empty_command_passes_through(self):

        exit_code, parsed_stdout = self._invoke("")
        tests._common.subprocess_helpers.HookEntryScriptInvocationHelper.assert_passthrough(
            self, exit_code, parsed_stdout
        )


if __name__ == "__main__":
    unittest.main()
