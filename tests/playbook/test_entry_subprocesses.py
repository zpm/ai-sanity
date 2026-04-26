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

import tests.fixtures
import tests._subprocess_helpers


class TestPreToolUsePlaybookEntryScript(unittest.TestCase):

    def setUp(self):

        self.temp_project_directory = tempfile.mkdtemp()
        self.dot_ai_sanity_directory = os.path.join(self.temp_project_directory, ".ai-sanity")
        os.makedirs(self.dot_ai_sanity_directory)
        self.playbook_abs_path = os.path.join(self.dot_ai_sanity_directory, "playbook.json")
        playbook_entries = [
            {
                "bash": "./test_hooks.sh",
                "what": "Runs repo tests on mac",
                "when": "Run as a final step after all changes have landed"
            },
            {
                "bash": "pwsh ./test_hooks.ps1",
                "what": "Runs repo tests on Windows",
                "when": "Run as a final step after all changes have landed"
            }
        ]
        with open(self.playbook_abs_path, "w", encoding = "utf-8") as open_playbook_file_handle:
            json.dump(playbook_entries, open_playbook_file_handle)

    def _invoke(self, command, working_directory = None):

        if working_directory is None:
            working_directory = self.temp_project_directory
        return tests._subprocess_helpers.HookEntryScriptInvocationHelper.invoke_entry_script(
            entry_script_relative_path = "playbook/pretooluse_bash.py",
            pretooluse_payload = tests.fixtures.PreToolUsePayloadFixtureBuilder.build_bash_payload(
                bash_command_string = command,
                working_directory = working_directory
            )
        )

    def test_matching_command_is_allowed(self):

        exit_code, parsed_stdout = self._invoke("./test_hooks.sh")
        tests._subprocess_helpers.HookEntryScriptInvocationHelper.assert_allow_decision(
            self, exit_code, parsed_stdout
        )

    def test_second_matching_command_is_allowed(self):

        exit_code, parsed_stdout = self._invoke("pwsh ./test_hooks.ps1")
        tests._subprocess_helpers.HookEntryScriptInvocationHelper.assert_allow_decision(
            self, exit_code, parsed_stdout
        )

    def test_non_matching_command_passes_through(self):

        exit_code, parsed_stdout = self._invoke("ls -la")
        tests._subprocess_helpers.HookEntryScriptInvocationHelper.assert_passthrough(
            self, exit_code, parsed_stdout
        )

    def test_multi_clause_with_match_passes_through(self):

        exit_code, parsed_stdout = self._invoke("./test_hooks.sh && rm -rf /")
        tests._subprocess_helpers.HookEntryScriptInvocationHelper.assert_passthrough(
            self, exit_code, parsed_stdout
        )

    def test_no_playbook_passes_through(self):

        empty_temp_directory = tempfile.mkdtemp()
        exit_code, parsed_stdout = self._invoke(
            command = "./test_hooks.sh",
            working_directory = empty_temp_directory
        )
        tests._subprocess_helpers.HookEntryScriptInvocationHelper.assert_passthrough(
            self, exit_code, parsed_stdout
        )

    def test_empty_command_passes_through(self):

        exit_code, parsed_stdout = self._invoke("")
        tests._subprocess_helpers.HookEntryScriptInvocationHelper.assert_passthrough(
            self, exit_code, parsed_stdout
        )


if __name__ == "__main__":
    unittest.main()
