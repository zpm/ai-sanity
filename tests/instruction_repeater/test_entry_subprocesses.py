########################################################################################################################
# tests/instruction_repeater/test_entry_subprocesses.py
#
# instruction-repeater entry-script subprocess tests
########################################################################################################################


import json
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "hooks"))

import tests._common.fixtures
import tests._common.subprocess_helpers


HOOK_ENTRY_SCRIPT_INVOCATION_HELPER = tests._common.subprocess_helpers.HookEntryScriptInvocationHelper
PAYLOAD_FIXTURE_BUILDER = tests._common.fixtures.PreToolUsePayloadFixtureBuilder


class UserPromptSubmitInstructionRepeaterSubprocessTestCase(
    tests._common.fixtures.HomeOverrideEnvVarTestCaseMixin,
    unittest.TestCase
):


    def test_first_prompt_in_session_injects_instruction_text(self):

        userpromptsubmit_payload = PAYLOAD_FIXTURE_BUILDER.build_userpromptsubmit_payload(
            session_id = "session-first-prompt"
        )
        exit_code, raw_stdout = HOOK_ENTRY_SCRIPT_INVOCATION_HELPER.invoke_entry_script_raw_stdout(
            entry_script_relative_path = "instruction_repeater/userpromptsubmit.py",
            payload = userpromptsubmit_payload
        )
        HOOK_ENTRY_SCRIPT_INVOCATION_HELPER.assert_context_injection(
            self, exit_code, raw_stdout, expected_substring = "claude.md"
        )


    def test_second_prompt_in_same_session_is_silent(self):

        userpromptsubmit_payload = PAYLOAD_FIXTURE_BUILDER.build_userpromptsubmit_payload(
            session_id = "session-second-prompt"
        )
        HOOK_ENTRY_SCRIPT_INVOCATION_HELPER.invoke_entry_script_raw_stdout(
            entry_script_relative_path = "instruction_repeater/userpromptsubmit.py",
            payload = userpromptsubmit_payload
        )
        exit_code, raw_stdout = HOOK_ENTRY_SCRIPT_INVOCATION_HELPER.invoke_entry_script_raw_stdout(
            entry_script_relative_path = "instruction_repeater/userpromptsubmit.py",
            payload = userpromptsubmit_payload
        )
        HOOK_ENTRY_SCRIPT_INVOCATION_HELPER.assert_silent_passthrough(self, exit_code, raw_stdout)


    def test_different_sessions_each_get_their_own_injection(self):

        payload_session_a = PAYLOAD_FIXTURE_BUILDER.build_userpromptsubmit_payload(
            session_id = "session-a-independent"
        )
        payload_session_b = PAYLOAD_FIXTURE_BUILDER.build_userpromptsubmit_payload(
            session_id = "session-b-independent"
        )
        exit_code_a, raw_stdout_a = HOOK_ENTRY_SCRIPT_INVOCATION_HELPER.invoke_entry_script_raw_stdout(
            entry_script_relative_path = "instruction_repeater/userpromptsubmit.py",
            payload = payload_session_a
        )
        exit_code_b, raw_stdout_b = HOOK_ENTRY_SCRIPT_INVOCATION_HELPER.invoke_entry_script_raw_stdout(
            entry_script_relative_path = "instruction_repeater/userpromptsubmit.py",
            payload = payload_session_b
        )
        HOOK_ENTRY_SCRIPT_INVOCATION_HELPER.assert_context_injection(
            self, exit_code_a, raw_stdout_a, expected_substring = "claude.md"
        )
        HOOK_ENTRY_SCRIPT_INVOCATION_HELPER.assert_context_injection(
            self, exit_code_b, raw_stdout_b, expected_substring = "claude.md"
        )


    def test_payload_missing_session_id_does_not_crash(self):

        minimal_payload = {"hook_event_name": "UserPromptSubmit"}
        exit_code, raw_stdout = HOOK_ENTRY_SCRIPT_INVOCATION_HELPER.invoke_entry_script_raw_stdout(
            entry_script_relative_path = "instruction_repeater/userpromptsubmit.py",
            payload = minimal_payload
        )
        self.assertEqual(exit_code, 0)


class ContextBoundaryReinjectionSubprocessTestCase(
    tests._common.fixtures.HomeOverrideEnvVarTestCaseMixin,
    unittest.TestCase
):


    def _write_transcript_fixture(self, context_token_counts_by_turn):

        """Writes a transcript with one answered prompt per given (previous, current) count pair shape: an assistant
        message at the first count, a typed prompt, then an assistant message at the second count. Returns the path."""
        previous_context_token_count, current_context_token_count = context_token_counts_by_turn
        transcript_lines = [
            json.dumps({
                "type": "assistant",
                "message": {"usage": {
                    "input_tokens": previous_context_token_count,
                    "cache_creation_input_tokens": 0,
                    "cache_read_input_tokens": 0
                }}
            }, ensure_ascii = False),
            json.dumps({
                "type": "user",
                "message": {"role": "user", "content": [{"type": "text", "text": "a typed user prompt"}]}
            }, ensure_ascii = False),
            json.dumps({
                "type": "assistant",
                "message": {"usage": {
                    "input_tokens": current_context_token_count,
                    "cache_creation_input_tokens": 0,
                    "cache_read_input_tokens": 0
                }}
            }, ensure_ascii = False)
        ]
        transcript_fixture_abs_path = os.path.join(self.sandboxed_home_abs_path, "transcript-fixture.jsonl")
        with open(transcript_fixture_abs_path, "w", encoding = "utf-8") as open_transcript_file:
            open_transcript_file.write("\n".join(transcript_lines) + "\n")
        return transcript_fixture_abs_path


    def _set_session_flag_via_first_prompt(self, session_id):

        """Invokes the entry script once with a null transcript so the session flag is set."""
        first_prompt_payload = PAYLOAD_FIXTURE_BUILDER.build_userpromptsubmit_payload(session_id = session_id)
        HOOK_ENTRY_SCRIPT_INVOCATION_HELPER.invoke_entry_script_raw_stdout(
            entry_script_relative_path = "instruction_repeater/userpromptsubmit.py",
            payload = first_prompt_payload
        )


    def test_boundary_crossing_injects_reread_instruction(self):

        session_id = "session-boundary-crossed"
        self._set_session_flag_via_first_prompt(session_id = session_id)
        transcript_fixture_abs_path = self._write_transcript_fixture(
            context_token_counts_by_turn = (48_000, 52_000)
        )
        crossing_payload = PAYLOAD_FIXTURE_BUILDER.build_userpromptsubmit_payload(
            session_id = session_id,
            transcript_path = transcript_fixture_abs_path
        )
        exit_code, raw_stdout = HOOK_ENTRY_SCRIPT_INVOCATION_HELPER.invoke_entry_script_raw_stdout(
            entry_script_relative_path = "instruction_repeater/userpromptsubmit.py",
            payload = crossing_payload
        )
        HOOK_ENTRY_SCRIPT_INVOCATION_HELPER.assert_context_injection(
            self, exit_code, raw_stdout, expected_substring = "Re-read the global claude.md"
        )
        self.assertIn("50,000-token mark", raw_stdout)


    def test_same_bucket_is_silent(self):

        session_id = "session-same-bucket"
        self._set_session_flag_via_first_prompt(session_id = session_id)
        transcript_fixture_abs_path = self._write_transcript_fixture(
            context_token_counts_by_turn = (52_000, 54_000)
        )
        same_bucket_payload = PAYLOAD_FIXTURE_BUILDER.build_userpromptsubmit_payload(
            session_id = session_id,
            transcript_path = transcript_fixture_abs_path
        )
        exit_code, raw_stdout = HOOK_ENTRY_SCRIPT_INVOCATION_HELPER.invoke_entry_script_raw_stdout(
            entry_script_relative_path = "instruction_repeater/userpromptsubmit.py",
            payload = same_bucket_payload
        )
        HOOK_ENTRY_SCRIPT_INVOCATION_HELPER.assert_silent_passthrough(self, exit_code, raw_stdout)


    def test_count_drop_after_compaction_is_silent(self):

        session_id = "session-count-dropped"
        self._set_session_flag_via_first_prompt(session_id = session_id)
        transcript_fixture_abs_path = self._write_transcript_fixture(
            context_token_counts_by_turn = (180_000, 40_000)
        )
        dropped_count_payload = PAYLOAD_FIXTURE_BUILDER.build_userpromptsubmit_payload(
            session_id = session_id,
            transcript_path = transcript_fixture_abs_path
        )
        exit_code, raw_stdout = HOOK_ENTRY_SCRIPT_INVOCATION_HELPER.invoke_entry_script_raw_stdout(
            entry_script_relative_path = "instruction_repeater/userpromptsubmit.py",
            payload = dropped_count_payload
        )
        HOOK_ENTRY_SCRIPT_INVOCATION_HELPER.assert_silent_passthrough(self, exit_code, raw_stdout)


    def test_first_prompt_injects_full_instruction_even_when_boundary_crossed(self):

        transcript_fixture_abs_path = self._write_transcript_fixture(
            context_token_counts_by_turn = (48_000, 52_000)
        )
        first_prompt_payload = PAYLOAD_FIXTURE_BUILDER.build_userpromptsubmit_payload(
            session_id = "session-first-prompt-crossing",
            transcript_path = transcript_fixture_abs_path
        )
        exit_code, raw_stdout = HOOK_ENTRY_SCRIPT_INVOCATION_HELPER.invoke_entry_script_raw_stdout(
            entry_script_relative_path = "instruction_repeater/userpromptsubmit.py",
            payload = first_prompt_payload
        )
        HOOK_ENTRY_SCRIPT_INVOCATION_HELPER.assert_context_injection(
            self, exit_code, raw_stdout, expected_substring = "Please read the global claude.md"
        )


class PreCompactInstructionRepeaterSubprocessTestCase(
    tests._common.fixtures.HomeOverrideEnvVarTestCaseMixin,
    unittest.TestCase
):


    def test_precompact_clears_flag_so_next_prompt_reinjects(self):

        session_id = "session-compact-cycle"
        userpromptsubmit_payload = PAYLOAD_FIXTURE_BUILDER.build_userpromptsubmit_payload(
            session_id = session_id
        )
        exit_code_first, raw_stdout_first = HOOK_ENTRY_SCRIPT_INVOCATION_HELPER.invoke_entry_script_raw_stdout(
            entry_script_relative_path = "instruction_repeater/userpromptsubmit.py",
            payload = userpromptsubmit_payload
        )
        HOOK_ENTRY_SCRIPT_INVOCATION_HELPER.assert_context_injection(
            self, exit_code_first, raw_stdout_first, expected_substring = "claude.md"
        )
        precompact_payload = PAYLOAD_FIXTURE_BUILDER.build_precompact_payload(session_id = session_id)
        HOOK_ENTRY_SCRIPT_INVOCATION_HELPER.invoke_entry_script(
            entry_script_relative_path = "instruction_repeater/precompact.py",
            pretooluse_payload = precompact_payload
        )
        exit_code_reinject, raw_stdout_reinject = HOOK_ENTRY_SCRIPT_INVOCATION_HELPER.invoke_entry_script_raw_stdout(
            entry_script_relative_path = "instruction_repeater/userpromptsubmit.py",
            payload = userpromptsubmit_payload
        )
        HOOK_ENTRY_SCRIPT_INVOCATION_HELPER.assert_context_injection(
            self, exit_code_reinject, raw_stdout_reinject, expected_substring = "claude.md"
        )


    def test_precompact_on_session_without_prior_flag_is_a_no_op(self):

        precompact_payload = PAYLOAD_FIXTURE_BUILDER.build_precompact_payload(
            session_id = "session-no-prior-flag"
        )
        exit_code, parsed_stdout = HOOK_ENTRY_SCRIPT_INVOCATION_HELPER.invoke_entry_script(
            entry_script_relative_path = "instruction_repeater/precompact.py",
            pretooluse_payload = precompact_payload
        )
        HOOK_ENTRY_SCRIPT_INVOCATION_HELPER.assert_passthrough(self, exit_code, parsed_stdout)


    def test_precompact_payload_missing_session_id_does_not_crash(self):

        precompact_payload = {"hook_event_name": "PreCompact"}
        exit_code, parsed_stdout = HOOK_ENTRY_SCRIPT_INVOCATION_HELPER.invoke_entry_script(
            entry_script_relative_path = "instruction_repeater/precompact.py",
            pretooluse_payload = precompact_payload
        )
        HOOK_ENTRY_SCRIPT_INVOCATION_HELPER.assert_passthrough(self, exit_code, parsed_stdout)


    def test_precompact_for_one_session_does_not_affect_another(self):

        payload_session_a = PAYLOAD_FIXTURE_BUILDER.build_userpromptsubmit_payload(
            session_id = "session-a-isolated"
        )
        payload_session_b = PAYLOAD_FIXTURE_BUILDER.build_userpromptsubmit_payload(
            session_id = "session-b-isolated"
        )
        HOOK_ENTRY_SCRIPT_INVOCATION_HELPER.invoke_entry_script_raw_stdout(
            entry_script_relative_path = "instruction_repeater/userpromptsubmit.py",
            payload = payload_session_a
        )
        HOOK_ENTRY_SCRIPT_INVOCATION_HELPER.invoke_entry_script_raw_stdout(
            entry_script_relative_path = "instruction_repeater/userpromptsubmit.py",
            payload = payload_session_b
        )
        precompact_payload_a = PAYLOAD_FIXTURE_BUILDER.build_precompact_payload(
            session_id = "session-a-isolated"
        )
        HOOK_ENTRY_SCRIPT_INVOCATION_HELPER.invoke_entry_script(
            entry_script_relative_path = "instruction_repeater/precompact.py",
            pretooluse_payload = precompact_payload_a
        )
        exit_code_a, raw_stdout_a = HOOK_ENTRY_SCRIPT_INVOCATION_HELPER.invoke_entry_script_raw_stdout(
            entry_script_relative_path = "instruction_repeater/userpromptsubmit.py",
            payload = payload_session_a
        )
        HOOK_ENTRY_SCRIPT_INVOCATION_HELPER.assert_context_injection(
            self, exit_code_a, raw_stdout_a, expected_substring = "claude.md"
        )
        exit_code_b, raw_stdout_b = HOOK_ENTRY_SCRIPT_INVOCATION_HELPER.invoke_entry_script_raw_stdout(
            entry_script_relative_path = "instruction_repeater/userpromptsubmit.py",
            payload = payload_session_b
        )
        HOOK_ENTRY_SCRIPT_INVOCATION_HELPER.assert_silent_passthrough(self, exit_code_b, raw_stdout_b)


if __name__ == "__main__":
    unittest.main()
