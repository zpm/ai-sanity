########################################################################################################################
# tests/no_questions/test_entry_subprocesses.py
#
# no-questions entry-script subprocess tests
########################################################################################################################


import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "hooks"))

import tests._common.fixtures
import tests._common.subprocess_helpers


HOOK_ENTRY_SCRIPT_INVOCATION_HELPER = tests._common.subprocess_helpers.HookEntryScriptInvocationHelper


class TestPreToolUseNoQuestionsEntryScript(unittest.TestCase):

    def test_ask_user_question_is_denied(self):

        exit_code, parsed_stdout = HOOK_ENTRY_SCRIPT_INVOCATION_HELPER.invoke_entry_script(
            entry_script_relative_path = "no_questions/pretooluse.py",
            pretooluse_payload = tests._common.fixtures.PreToolUsePayloadFixtureBuilder.build_ask_user_question_payload()
        )
        HOOK_ENTRY_SCRIPT_INVOCATION_HELPER.assert_deny_decision(
            self,
            exit_code,
            parsed_stdout,
            "AskUserQuestion is disabled"
        )


    def test_ask_user_question_with_questions_is_denied(self):

        exit_code, parsed_stdout = HOOK_ENTRY_SCRIPT_INVOCATION_HELPER.invoke_entry_script(
            entry_script_relative_path = "no_questions/pretooluse.py",
            pretooluse_payload = tests._common.fixtures.PreToolUsePayloadFixtureBuilder.build_ask_user_question_payload(
                questions = [
                    {
                        "question": "Which approach do you prefer?",
                        "header": "Approach",
                        "options": [
                            {
                                "label": "Option A",
                                "description": "First approach"
                            },
                            {
                                "label": "Option B",
                                "description": "Second approach"
                            }
                        ],
                        "multiSelect": False
                    }
                ]
            )
        )
        HOOK_ENTRY_SCRIPT_INVOCATION_HELPER.assert_deny_decision(
            self,
            exit_code,
            parsed_stdout,
            "AskUserQuestion is disabled"
        )


if __name__ == "__main__":
    unittest.main()
