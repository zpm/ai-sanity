########################################################################################################################
# tests/bash_playbook/test_entry_subprocesses.py
#
# bash safety entry-script filesystem fixture tests
########################################################################################################################


import json
import os
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "hooks"))

import tests._common.fixtures
import tests._common.subprocess_helpers


class TestPreToolUseBashSafetyEntryScriptGitMv(unittest.TestCase):

    def setUp(self):

        self.git_repo_temp_directory = tempfile.mkdtemp()
        subprocess.run(
            ["git", "init", "-q"],
            cwd = self.git_repo_temp_directory,
            check = True
        )
        tracked_file_path = os.path.join(self.git_repo_temp_directory, "tracked-example.txt")
        open(tracked_file_path, "w").close()
        subprocess.run(
            ["git", "add", "tracked-example.txt"],
            cwd = self.git_repo_temp_directory,
            check = True
        )
        subprocess.run(
            ["git", "-c", "user.email=test@test", "-c", "user.name=test", "commit", "-qm", "init"],
            cwd = self.git_repo_temp_directory,
            check = True
        )


    def _invoke(self, command):

        return tests._common.subprocess_helpers.HookEntryScriptInvocationHelper.invoke_entry_script(
            entry_script_relative_path = "bash_playbook/pretooluse_bash.py",
            pretooluse_payload = tests._common.fixtures.PreToolUsePayloadFixtureBuilder.build_bash_payload(
                bash_command_string = command,
                working_directory = self.git_repo_temp_directory
            )
        )


    def test_mv_of_tracked_file_is_denied(self):

        exit_code, parsed_stdout = self._invoke("mv tracked-example.txt renamed.txt")
        tests._common.subprocess_helpers.HookEntryScriptInvocationHelper.assert_deny_decision(
            self, exit_code, parsed_stdout, "tracked"
        )


    def test_non_mv_command_passes_through(self):

        exit_code, parsed_stdout = self._invoke("python --version")
        tests._common.subprocess_helpers.HookEntryScriptInvocationHelper.assert_passthrough(
            self, exit_code, parsed_stdout
        )


class TestPreToolUseBashSafetyEntryScriptPlaybook(unittest.TestCase):

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
            },
            {
                "bash": "pwsh ../local/server/scripts/tests/all.ps1",
                "what": "Run all tests (Windows)",
                "when": "Final step after all changes have landed"
            }
        ]
        with open(self.playbook_abs_path, "w", encoding = "utf-8") as open_playbook_file_handle:
            json.dump(playbook_entries, open_playbook_file_handle)


    def _invoke(self, command, working_directory = None):

        if working_directory is None:
            working_directory = self.temp_project_directory
        return tests._common.subprocess_helpers.HookEntryScriptInvocationHelper.invoke_entry_script(
            entry_script_relative_path = "bash_playbook/pretooluse_bash.py",
            pretooluse_payload = tests._common.fixtures.PreToolUsePayloadFixtureBuilder.build_bash_payload(
                bash_command_string = command,
                working_directory = working_directory
            )
        )


    def test_playbook_match_is_allowed(self):

        exit_code, parsed_stdout = self._invoke("python -m unittest discover -s tests -t . -v")
        tests._common.subprocess_helpers.HookEntryScriptInvocationHelper.assert_allow_decision(
            self, exit_code, parsed_stdout
        )


    def test_playbook_prefix_match_is_allowed(self):

        exit_code, parsed_stdout = self._invoke("python -m unittest tests.playbook.test_rule_checks -v")
        tests._common.subprocess_helpers.HookEntryScriptInvocationHelper.assert_allow_decision(
            self, exit_code, parsed_stdout
        )


    def test_playbook_match_with_sequential_operator_is_allowed(self):

        exit_code, parsed_stdout = self._invoke("cd server && pwsh ../local/server/scripts/tests/all.ps1")
        tests._common.subprocess_helpers.HookEntryScriptInvocationHelper.assert_allow_decision(
            self, exit_code, parsed_stdout
        )


    def test_playbook_match_overrides_prohibited_command_deny(self):

        exit_code, parsed_stdout = self._invoke("cd server && pwsh ../local/server/scripts/tests/all.ps1")
        tests._common.subprocess_helpers.HookEntryScriptInvocationHelper.assert_allow_decision(
            self, exit_code, parsed_stdout
        )


    def test_non_matching_command_still_denied_by_safety(self):

        exit_code, parsed_stdout = self._invoke("pwsh some-random-script.ps1")
        tests._common.subprocess_helpers.HookEntryScriptInvocationHelper.assert_deny_decision(
            self, exit_code, parsed_stdout, "prohibited"
        )


    def test_project_root_relative_playbook_match_after_cd_is_allowed(self):

        scripts_directory = os.path.join(self.temp_project_directory, "server", "scripts", "tests")
        os.makedirs(scripts_directory)
        script_file_path = os.path.join(scripts_directory, "all-fast.sh")
        open(script_file_path, mode = "w").close()
        with open(self.playbook_abs_path, mode = "w", encoding = "utf-8") as open_playbook_file_handle:
            json.dump(
                obj = [{"bash": "*/server/scripts/tests/all-fast.sh *", "what": "test", "when": "test"}],
                fp = open_playbook_file_handle
            )
        sub_directory = os.path.join(self.temp_project_directory, "server", "app")
        os.makedirs(sub_directory)
        exit_code, parsed_stdout = self._invoke(
            command = "cd " + sub_directory.replace("\\", "/") + " && ../../server/scripts/tests/all-fast.sh",
            working_directory = self.temp_project_directory
        )
        tests._common.subprocess_helpers.HookEntryScriptInvocationHelper.assert_allow_decision(
            self, exit_code, parsed_stdout
        )


    def test_project_root_relative_playbook_match_overrides_prohibited_command(self):

        scripts_directory = os.path.join(self.temp_project_directory, "server", "scripts", "tests")
        os.makedirs(scripts_directory)
        script_file_path = os.path.join(scripts_directory, "all-fast.ps1")
        open(script_file_path, mode = "w").close()
        with open(self.playbook_abs_path, mode = "w", encoding = "utf-8") as open_playbook_file_handle:
            json.dump(
                obj = [{"bash": "pwsh */server/scripts/tests/all-fast.ps1 *", "what": "test", "when": "test"}],
                fp = open_playbook_file_handle
            )
        sub_directory = os.path.join(self.temp_project_directory, "server")
        exit_code, parsed_stdout = self._invoke(
            command = "pwsh ../server/scripts/tests/all-fast.ps1 --verbose",
            working_directory = sub_directory
        )
        tests._common.subprocess_helpers.HookEntryScriptInvocationHelper.assert_allow_decision(
            self, exit_code, parsed_stdout
        )


    def test_no_playbook_passes_through(self):

        empty_temp_directory = tempfile.mkdtemp()
        exit_code, parsed_stdout = self._invoke(
            command = "python --version",
            working_directory = empty_temp_directory
        )
        tests._common.subprocess_helpers.HookEntryScriptInvocationHelper.assert_passthrough(
            self, exit_code, parsed_stdout
        )


if __name__ == "__main__":
    unittest.main()
