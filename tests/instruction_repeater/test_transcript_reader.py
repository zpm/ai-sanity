########################################################################################################################
# tests/instruction_repeater/test_transcript_reader.py
#
# instruction-repeater transcript reader unit tests
########################################################################################################################


import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "hooks"))

import instruction_repeater._transcript_reader


TRANSCRIPT_READER = instruction_repeater._transcript_reader.TranscriptPromptContextTokenReader


def _build_assistant_entry_jsonl_line(context_token_total, is_sidechain = False):

    """Builds a single JSONL line representing an assistant message whose usage sums to the given total."""
    entry = {
        "type": "assistant",
        "isSidechain": is_sidechain,
        "message": {
            "usage": {
                "input_tokens": context_token_total,
                "cache_creation_input_tokens": 0,
                "cache_read_input_tokens": 0,
                "output_tokens": 100
            }
        },
        "uuid": "test-uuid",
        "timestamp": "2026-08-10T00:00:00Z"
    }
    return json.dumps(entry, ensure_ascii = False)


def _build_prompt_entry_jsonl_line(content_as_string = False, is_meta = False):

    """Builds a single JSONL line representing a typed user prompt. Current transcripts carry prompts as a list of
    text blocks; older transcripts carry a plain string."""
    if content_as_string:
        content_value = "a typed user prompt"
    else:
        content_value = [{"type": "text", "text": "a typed user prompt"}]
    entry = {
        "type": "user",
        "isSidechain": False,
        "message": {
            "role": "user",
            "content": content_value
        },
        "uuid": "test-uuid",
        "timestamp": "2026-08-10T00:00:00Z"
    }
    if is_meta:
        entry["isMeta"] = True
    return json.dumps(entry, ensure_ascii = False)


def _build_tool_result_user_entry_jsonl_line():

    """Builds a single JSONL line representing a tool result, which arrives as a user entry with tool_result blocks."""
    entry = {
        "type": "user",
        "isSidechain": False,
        "message": {
            "role": "user",
            "content": [{"type": "tool_result", "tool_use_id": "test-tool-use-id", "content": "tool output"}]
        },
        "uuid": "test-uuid",
        "timestamp": "2026-08-10T00:00:00Z"
    }
    return json.dumps(entry, ensure_ascii = False)


def _write_transcript_file(lines):

    """Writes the given lines to a temp file and returns the absolute path. Caller is responsible for cleanup."""
    temp_file_handle = tempfile.NamedTemporaryFile(
        mode = "w",
        suffix = ".jsonl",
        delete = False,
        encoding = "utf-8"
    )
    temp_file_handle.write("\n".join(lines) + "\n")
    temp_file_handle.close()
    return temp_file_handle.name


class TranscriptPromptContextTokenReaderTestCase(unittest.TestCase):


    def setUp(self):

        self._temp_files_to_clean_up = []


    def tearDown(self):

        for temp_file_path in self._temp_files_to_clean_up:
            try:
                os.remove(temp_file_path)
            except OSError:
                pass


    def _write_and_track_transcript(self, lines):

        """Writes lines to a temp transcript file, tracks it for cleanup, and returns the path."""
        temp_file_path = _write_transcript_file(lines)
        self._temp_files_to_clean_up.append(temp_file_path)
        return temp_file_path


    def _read_counts(self, lines):

        """Writes the transcript and returns the reader's (current, previous) tuple."""
        transcript_path = self._write_and_track_transcript(lines)
        return TRANSCRIPT_READER.read_current_and_previous_prompt_context_token_counts(
            transcript_file_abs_path = transcript_path
        )


    def test_answered_latest_prompt_returns_count_at_that_prompt(self):

        current_count, previous_count = self._read_counts([
            _build_assistant_entry_jsonl_line(context_token_total = 10_000),
            _build_prompt_entry_jsonl_line(),
            _build_assistant_entry_jsonl_line(context_token_total = 60_000)
        ])
        self.assertEqual(current_count, 60_000)
        self.assertEqual(previous_count, 10_000)


    def test_in_flight_latest_prompt_returns_count_at_prior_prompt(self):

        current_count, previous_count = self._read_counts([
            _build_assistant_entry_jsonl_line(context_token_total = 10_000),
            _build_prompt_entry_jsonl_line(),
            _build_assistant_entry_jsonl_line(context_token_total = 60_000),
            _build_prompt_entry_jsonl_line()
        ])
        self.assertEqual(current_count, 60_000)
        self.assertEqual(previous_count, 10_000)


    def test_tool_result_entries_are_not_prompts(self):

        current_count, previous_count = self._read_counts([
            _build_assistant_entry_jsonl_line(context_token_total = 10_000),
            _build_prompt_entry_jsonl_line(),
            _build_assistant_entry_jsonl_line(context_token_total = 30_000),
            _build_tool_result_user_entry_jsonl_line(),
            _build_assistant_entry_jsonl_line(context_token_total = 60_000)
        ])
        self.assertEqual(current_count, 60_000)
        self.assertEqual(previous_count, 10_000)


    def test_meta_prompt_entries_are_skipped(self):

        current_count, previous_count = self._read_counts([
            _build_assistant_entry_jsonl_line(context_token_total = 10_000),
            _build_prompt_entry_jsonl_line(),
            _build_assistant_entry_jsonl_line(context_token_total = 40_000),
            _build_prompt_entry_jsonl_line(is_meta = True),
            _build_assistant_entry_jsonl_line(context_token_total = 60_000)
        ])
        self.assertEqual(current_count, 60_000)
        self.assertEqual(previous_count, 10_000)


    def test_sidechain_assistant_entries_are_ignored(self):

        current_count, previous_count = self._read_counts([
            _build_assistant_entry_jsonl_line(context_token_total = 10_000),
            _build_prompt_entry_jsonl_line(),
            _build_assistant_entry_jsonl_line(context_token_total = 5_000, is_sidechain = True),
            _build_assistant_entry_jsonl_line(context_token_total = 60_000)
        ])
        self.assertEqual(current_count, 60_000)
        self.assertEqual(previous_count, 10_000)


    def test_string_content_prompt_is_recognized(self):

        current_count, previous_count = self._read_counts([
            _build_assistant_entry_jsonl_line(context_token_total = 10_000),
            _build_prompt_entry_jsonl_line(content_as_string = True),
            _build_assistant_entry_jsonl_line(context_token_total = 60_000)
        ])
        self.assertEqual(current_count, 60_000)
        self.assertEqual(previous_count, 10_000)


    def test_transcript_without_prompts_returns_none_previous(self):

        current_count, previous_count = self._read_counts([
            _build_assistant_entry_jsonl_line(context_token_total = 10_000)
        ])
        self.assertEqual(current_count, 10_000)
        self.assertIsNone(previous_count)


    def test_first_prompt_only_returns_none_counts(self):

        current_count, previous_count = self._read_counts([
            _build_prompt_entry_jsonl_line()
        ])
        self.assertIsNone(current_count)
        self.assertIsNone(previous_count)


    def test_prompt_before_any_assistant_message_returns_none_previous(self):

        current_count, previous_count = self._read_counts([
            _build_prompt_entry_jsonl_line(),
            _build_assistant_entry_jsonl_line(context_token_total = 20_000),
            _build_prompt_entry_jsonl_line()
        ])
        self.assertEqual(current_count, 20_000)
        self.assertIsNone(previous_count)


    def test_malformed_lines_are_skipped(self):

        current_count, previous_count = self._read_counts([
            _build_assistant_entry_jsonl_line(context_token_total = 10_000),
            "this is not valid json {",
            _build_prompt_entry_jsonl_line(),
            _build_assistant_entry_jsonl_line(context_token_total = 60_000)
        ])
        self.assertEqual(current_count, 60_000)
        self.assertEqual(previous_count, 10_000)


    def test_empty_file_returns_none_counts(self):

        current_count, previous_count = self._read_counts([])
        self.assertIsNone(current_count)
        self.assertIsNone(previous_count)


    def test_nonexistent_file_returns_none_counts(self):

        current_count, previous_count = TRANSCRIPT_READER.read_current_and_previous_prompt_context_token_counts(
            transcript_file_abs_path = "/tmp/does-not-exist-test-transcript.jsonl"
        )
        self.assertIsNone(current_count)
        self.assertIsNone(previous_count)


    def test_none_path_returns_none_counts(self):

        current_count, previous_count = TRANSCRIPT_READER.read_current_and_previous_prompt_context_token_counts(
            transcript_file_abs_path = None
        )
        self.assertIsNone(current_count)
        self.assertIsNone(previous_count)


if __name__ == "__main__":
    unittest.main()
