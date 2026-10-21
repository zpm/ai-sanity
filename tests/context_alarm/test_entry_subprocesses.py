########################################################################################################################
# tests/context_alarm/test_entry_subprocesses.py
#
# context-alarm entry-script subprocess tests
########################################################################################################################


import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "hooks"))

import tests._common.fixtures
import tests._common.subprocess_helpers


HOOK_ENTRY_SCRIPT_INVOCATION_HELPER = tests._common.subprocess_helpers.HookEntryScriptInvocationHelper
PAYLOAD_FIXTURE_BUILDER = tests._common.fixtures.PreToolUsePayloadFixtureBuilder


def _build_assistant_entry_jsonl_line(input_tokens, cache_creation_input_tokens, cache_read_input_tokens):

    """Builds a single JSONL line representing an assistant message with the given token counts."""
    entry = {
        "type": "assistant",
        "parentUuid": "test-parent",
        "isSidechain": False,
        "message": {
            "usage": {
                "input_tokens": input_tokens,
                "cache_creation_input_tokens": cache_creation_input_tokens,
                "cache_read_input_tokens": cache_read_input_tokens,
                "output_tokens": 100
            }
        },
        "requestId": "test-request",
        "uuid": "test-uuid",
        "timestamp": "2026-05-12T00:00:00Z",
        "userType": "external"
    }
    return json.dumps(entry, ensure_ascii = False)


class UserPromptSubmitContextAlarmSubprocessTestCase(
    tests._common.fixtures.HomeOverrideEnvVarTestCaseMixin,
    unittest.TestCase
):


    def setUp(self):

        super().setUp()
        self._temp_files_to_clean_up = []


    def tearDown(self):

        for temp_file_path in self._temp_files_to_clean_up:
            try:
                os.remove(temp_file_path)
            except OSError:
                pass
        super().tearDown()


    def _write_and_track_transcript(self, lines):

        """Writes lines to a temp transcript file, tracks it for cleanup, and returns the path."""
        temp_file_handle = tempfile.NamedTemporaryFile(
            mode = "w",
            suffix = ".jsonl",
            delete = False,
            encoding = "utf-8"
        )
        temp_file_handle.write("\n".join(lines) + "\n")
        temp_file_handle.close()
        self._temp_files_to_clean_up.append(temp_file_handle.name)
        return temp_file_handle.name


    def _invoke_entry_script_with_token_count(self, session_id, total_token_count):

        """Writes a one-line transcript totaling total_token_count and invokes the entry script against it."""
        transcript_path = self._write_and_track_transcript([
            _build_assistant_entry_jsonl_line(
                input_tokens = total_token_count,
                cache_creation_input_tokens = 0,
                cache_read_input_tokens = 0
            )
        ])
        userpromptsubmit_payload = PAYLOAD_FIXTURE_BUILDER.build_userpromptsubmit_payload(
            session_id = session_id,
            transcript_path = transcript_path
        )
        return HOOK_ENTRY_SCRIPT_INVOCATION_HELPER.invoke_entry_script_raw_stdout(
            entry_script_relative_path = "context_alarm/userpromptsubmit.py",
            payload = userpromptsubmit_payload
        )


    def test_large_context_is_silent(self):

        exit_code, raw_stdout = self._invoke_entry_script_with_token_count(
            session_id = "session-large-context",
            total_token_count = 612345
        )
        HOOK_ENTRY_SCRIPT_INVOCATION_HELPER.assert_silent_passthrough(self, exit_code, raw_stdout)


    def test_small_context_is_silent(self):

        exit_code, raw_stdout = self._invoke_entry_script_with_token_count(
            session_id = "session-small-context",
            total_token_count = 55010
        )
        HOOK_ENTRY_SCRIPT_INVOCATION_HELPER.assert_silent_passthrough(self, exit_code, raw_stdout)


    def test_non_numeric_usage_values_are_silent(self):

        transcript_path = self._write_and_track_transcript([
            _build_assistant_entry_jsonl_line(
                input_tokens = "not-a-number",
                cache_creation_input_tokens = 0,
                cache_read_input_tokens = 0
            )
        ])
        userpromptsubmit_payload = PAYLOAD_FIXTURE_BUILDER.build_userpromptsubmit_payload(
            session_id = "session-non-numeric-usage",
            transcript_path = transcript_path
        )
        exit_code, raw_stdout = HOOK_ENTRY_SCRIPT_INVOCATION_HELPER.invoke_entry_script_raw_stdout(
            entry_script_relative_path = "context_alarm/userpromptsubmit.py",
            payload = userpromptsubmit_payload
        )
        HOOK_ENTRY_SCRIPT_INVOCATION_HELPER.assert_silent_passthrough(self, exit_code, raw_stdout)


    def test_nonexistent_transcript_file_is_silent(self):

        userpromptsubmit_payload = PAYLOAD_FIXTURE_BUILDER.build_userpromptsubmit_payload(
            session_id = "session-missing-transcript",
            transcript_path = "/tmp/does-not-exist-transcript.jsonl"
        )
        exit_code, raw_stdout = HOOK_ENTRY_SCRIPT_INVOCATION_HELPER.invoke_entry_script_raw_stdout(
            entry_script_relative_path = "context_alarm/userpromptsubmit.py",
            payload = userpromptsubmit_payload
        )
        HOOK_ENTRY_SCRIPT_INVOCATION_HELPER.assert_silent_passthrough(self, exit_code, raw_stdout)


    def test_empty_transcript_file_is_silent(self):

        transcript_path = self._write_and_track_transcript([])
        userpromptsubmit_payload = PAYLOAD_FIXTURE_BUILDER.build_userpromptsubmit_payload(
            session_id = "session-empty-transcript",
            transcript_path = transcript_path
        )
        exit_code, raw_stdout = HOOK_ENTRY_SCRIPT_INVOCATION_HELPER.invoke_entry_script_raw_stdout(
            entry_script_relative_path = "context_alarm/userpromptsubmit.py",
            payload = userpromptsubmit_payload
        )
        HOOK_ENTRY_SCRIPT_INVOCATION_HELPER.assert_silent_passthrough(self, exit_code, raw_stdout)


if __name__ == "__main__":
    unittest.main()
