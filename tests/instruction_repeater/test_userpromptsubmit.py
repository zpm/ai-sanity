########################################################################################################################
# tests/instruction_repeater/test_userpromptsubmit.py
#
# instruction-repeater boundary check unit tests
########################################################################################################################


import contextlib
import io
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "hooks"))

import instruction_repeater.userpromptsubmit
import tests._common.subprocess_helpers


HOOK_ENTRY_SCRIPT_INVOCATION_HELPER = tests._common.subprocess_helpers.HookEntryScriptInvocationHelper
INSTRUCTION_REPEATER_ENTRY = instruction_repeater.userpromptsubmit.UserPromptSubmitInstructionRepeaterEntry


def _build_assistant_entry_jsonl_line(context_token_total):

    """Builds a single JSONL line representing an assistant message whose usage sums to the given total."""
    entry = {
        "type": "assistant",
        "message": {
            "usage": {
                "input_tokens": context_token_total,
                "cache_creation_input_tokens": 0,
                "cache_read_input_tokens": 0
            }
        }
    }
    return json.dumps(entry, ensure_ascii = False)


def _build_prompt_entry_jsonl_line():

    """Builds a single JSONL line representing a typed user prompt."""
    entry = {
        "type": "user",
        "message": {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": "a typed user prompt"
                }
            ]
        }
    }
    return json.dumps(entry, ensure_ascii = False)


class ContextBoundaryCheckTestCase(unittest.TestCase):

    """Calls the boundary check directly, because the entry script skips the check while _REINJECTION_CYCLE_ENABLED
    is False."""


    def setUp(self):

        self._temp_files_to_clean_up = []


    def tearDown(self):

        for temp_file_path in self._temp_files_to_clean_up:
            try:
                os.remove(temp_file_path)
            except OSError:
                pass


    def _run_boundary_check(self, previous_context_token_count, current_context_token_count):

        """Writes a transcript with one answered prompt between the two counts, runs the boundary check in-process
        against it, and returns (exit_code, raw_stdout)."""
        temp_file_handle = tempfile.NamedTemporaryFile(
            mode = "w",
            suffix = ".jsonl",
            delete = False,
            encoding = "utf-8"
        )
        temp_file_handle.write("\n".join([
            _build_assistant_entry_jsonl_line(context_token_total = previous_context_token_count),
            _build_prompt_entry_jsonl_line(),
            _build_assistant_entry_jsonl_line(context_token_total = current_context_token_count)
        ]) + "\n")
        temp_file_handle.close()
        self._temp_files_to_clean_up.append(temp_file_handle.name)
        captured_stdout = io.StringIO()
        with contextlib.redirect_stdout(captured_stdout):
            with self.assertRaises(SystemExit) as raised_system_exit_context:
                INSTRUCTION_REPEATER_ENTRY._check_context_boundary_and_emit(
                    transcript_file_abs_path = temp_file_handle.name
                )
        return raised_system_exit_context.exception.code, captured_stdout.getvalue()


    def test_boundary_crossing_injects_reread_instruction(self):

        exit_code, raw_stdout = self._run_boundary_check(
            previous_context_token_count = 95_000,
            current_context_token_count = 105_000
        )
        HOOK_ENTRY_SCRIPT_INVOCATION_HELPER.assert_context_injection(
            self, exit_code, raw_stdout, expected_substring = "re-read the global claude.md"
        )
        self.assertIn("100,000-token mark", raw_stdout)
        self.assertIn("using the Read tool, not from memory", raw_stdout)


    def test_same_bucket_is_silent(self):

        exit_code, raw_stdout = self._run_boundary_check(
            previous_context_token_count = 52_000,
            current_context_token_count = 54_000
        )
        HOOK_ENTRY_SCRIPT_INVOCATION_HELPER.assert_silent_passthrough(self, exit_code, raw_stdout)


    def test_count_drop_after_compaction_is_silent(self):

        exit_code, raw_stdout = self._run_boundary_check(
            previous_context_token_count = 180_000,
            current_context_token_count = 40_000
        )
        HOOK_ENTRY_SCRIPT_INVOCATION_HELPER.assert_silent_passthrough(self, exit_code, raw_stdout)


if __name__ == "__main__":
    unittest.main()
