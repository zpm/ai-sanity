import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "hooks"))

import tests.fixtures
import tests._subprocess_helpers


class TestPreToolUseBashCommandEntryScript(unittest.TestCase):

    def _invoke(self, command):

        return tests._subprocess_helpers.HookEntryScriptInvocationHelper.invoke_entry_script(
            entry_script_relative_path = "bash_commands/pretooluse_bash.py",
            pretooluse_payload = tests.fixtures.PreToolUsePayloadFixtureBuilder.build_bash_payload(
                bash_command_string = command
            )
        )

    def test_pip_install_is_denied(self):

        exit_code, parsed_stdout = self._invoke("pip install requests")
        tests._subprocess_helpers.HookEntryScriptInvocationHelper.assert_deny_decision(
            self, exit_code, parsed_stdout, "Package installation"
        )

    def test_sudo_is_denied(self):

        exit_code, parsed_stdout = self._invoke("sudo apt-get update")
        tests._subprocess_helpers.HookEntryScriptInvocationHelper.assert_deny_decision(
            self, exit_code, parsed_stdout, "System operations"
        )

    def test_bash_subshell_is_denied(self):

        exit_code, parsed_stdout = self._invoke("bash -c 'echo hi'")
        tests._subprocess_helpers.HookEntryScriptInvocationHelper.assert_deny_decision(
            self, exit_code, parsed_stdout, "sub-shells"
        )

    def test_gh_api_is_denied(self):

        exit_code, parsed_stdout = self._invoke("gh api repos/foo/bar")
        tests._subprocess_helpers.HookEntryScriptInvocationHelper.assert_deny_decision(
            self, exit_code, parsed_stdout, "gh api"
        )

    def test_sed_is_denied(self):

        exit_code, parsed_stdout = self._invoke("sed -i 's/a/b/' file.txt")
        tests._subprocess_helpers.HookEntryScriptInvocationHelper.assert_deny_decision(
            self, exit_code, parsed_stdout, "Edit tool"
        )

    def test_cat_passes_through(self):

        exit_code, parsed_stdout = self._invoke("cat file.txt")
        tests._subprocess_helpers.HookEntryScriptInvocationHelper.assert_passthrough(self, exit_code, parsed_stdout)

    def test_ls_passes_through(self):

        exit_code, parsed_stdout = self._invoke("ls -la")
        tests._subprocess_helpers.HookEntryScriptInvocationHelper.assert_passthrough(self, exit_code, parsed_stdout)

    def test_taskkill_is_denied(self):

        exit_code, parsed_stdout = self._invoke("taskkill /F /PID 1234")
        tests._subprocess_helpers.HookEntryScriptInvocationHelper.assert_deny_decision(
            self, exit_code, parsed_stdout, "taskkill"
        )

    def test_echo_is_allowed(self):

        exit_code, parsed_stdout = self._invoke("echo hello world")
        tests._subprocess_helpers.HookEntryScriptInvocationHelper.assert_allow_decision(
            self, exit_code, parsed_stdout
        )

    def test_git_diff_is_allowed(self):

        exit_code, parsed_stdout = self._invoke("git diff HEAD")
        tests._subprocess_helpers.HookEntryScriptInvocationHelper.assert_allow_decision(
            self, exit_code, parsed_stdout
        )

    def test_cp_is_allowed(self):

        exit_code, parsed_stdout = self._invoke("cp src.txt dst.txt")
        tests._subprocess_helpers.HookEntryScriptInvocationHelper.assert_allow_decision(
            self, exit_code, parsed_stdout
        )

    def test_unknown_command_passes_through(self):

        exit_code, parsed_stdout = self._invoke("python script.py")
        tests._subprocess_helpers.HookEntryScriptInvocationHelper.assert_passthrough(self, exit_code, parsed_stdout)


if __name__ == "__main__":
    unittest.main()
