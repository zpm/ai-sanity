import os
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "hooks"))

import tests.fixtures
import tests._subprocess_helpers


class TestPreToolUseBashGitSafetyEntryScript(unittest.TestCase):

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

    def test_git_commit_is_denied(self):

        exit_code, parsed_stdout = tests._subprocess_helpers.HookEntryScriptInvocationHelper.invoke_entry_script(
            entry_script_relative_path = "git_safety/pretooluse_bash.py",
            pretooluse_payload = tests.fixtures.PreToolUsePayloadFixtureBuilder.build_bash_payload(
                bash_command_string = "git commit -m 'test'"
            )
        )
        tests._subprocess_helpers.HookEntryScriptInvocationHelper.assert_deny_decision(
            self, exit_code, parsed_stdout, "strictly prohibited"
        )

    def test_git_diff_passes_through(self):

        exit_code, parsed_stdout = tests._subprocess_helpers.HookEntryScriptInvocationHelper.invoke_entry_script(
            entry_script_relative_path = "git_safety/pretooluse_bash.py",
            pretooluse_payload = tests.fixtures.PreToolUsePayloadFixtureBuilder.build_bash_payload(
                bash_command_string = "git diff HEAD"
            )
        )
        tests._subprocess_helpers.HookEntryScriptInvocationHelper.assert_passthrough(self, exit_code, parsed_stdout)

    def test_mv_of_tracked_file_is_denied(self):

        exit_code, parsed_stdout = tests._subprocess_helpers.HookEntryScriptInvocationHelper.invoke_entry_script(
            entry_script_relative_path = "git_safety/pretooluse_bash.py",
            pretooluse_payload = tests.fixtures.PreToolUsePayloadFixtureBuilder.build_bash_payload(
                bash_command_string = "mv tracked-example.txt renamed.txt",
                working_directory = self.git_repo_temp_directory
            )
        )
        tests._subprocess_helpers.HookEntryScriptInvocationHelper.assert_deny_decision(
            self, exit_code, parsed_stdout, "tracked"
        )

    def test_non_mv_command_passes_through(self):

        exit_code, parsed_stdout = tests._subprocess_helpers.HookEntryScriptInvocationHelper.invoke_entry_script(
            entry_script_relative_path = "git_safety/pretooluse_bash.py",
            pretooluse_payload = tests.fixtures.PreToolUsePayloadFixtureBuilder.build_bash_payload(
                bash_command_string = "echo hello"
            )
        )
        tests._subprocess_helpers.HookEntryScriptInvocationHelper.assert_passthrough(self, exit_code, parsed_stdout)


if __name__ == "__main__":
    unittest.main()
