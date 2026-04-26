########################################################################################################################
# tests/bash_safety/test_json_driven.py
#
# JSON-driven integration tests for the bash_safety entry script
########################################################################################################################


import json
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "hooks"))

import tests._common.fixtures
import tests._common.subprocess_helpers


COMMAND_TESTS_JSON_ABS_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "command_tests.json"
)


class TestBashSafetyJsonDriven(unittest.TestCase):

    def setUp(self):

        with open(COMMAND_TESTS_JSON_ABS_PATH, "r", encoding = "utf-8") as open_json_file_handle:
            self.command_tests = json.load(open_json_file_handle)

    def _invoke_and_assert(self, bash_command_string, assert_method):

        exit_code, parsed_stdout = tests._common.subprocess_helpers.HookEntryScriptInvocationHelper.invoke_entry_script(
            entry_script_relative_path = "bash_safety/pretooluse_bash.py",
            pretooluse_payload = tests._common.fixtures.PreToolUsePayloadFixtureBuilder.build_bash_payload(
                bash_command_string = bash_command_string
            )
        )
        assert_method(self, exit_code, parsed_stdout)

    def test_allow_commands(self):

        for bash_command_string in self.command_tests["allow"]:
            with self.subTest(command = bash_command_string):
                self._invoke_and_assert(
                    bash_command_string,
                    tests._common.subprocess_helpers.HookEntryScriptInvocationHelper.assert_allow_decision
                )

    def test_deny_commands(self):

        for bash_command_string in self.command_tests["deny"]:
            with self.subTest(command = bash_command_string):
                self._invoke_and_assert(
                    bash_command_string,
                    tests._common.subprocess_helpers.HookEntryScriptInvocationHelper.assert_deny_decision
                )

    def test_ask_commands(self):

        for bash_command_string in self.command_tests["ask"]:
            with self.subTest(command = bash_command_string):
                self._invoke_and_assert(
                    bash_command_string,
                    tests._common.subprocess_helpers.HookEntryScriptInvocationHelper.assert_passthrough
                )


if __name__ == "__main__":
    unittest.main()
