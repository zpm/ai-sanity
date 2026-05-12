########################################################################################################################
# tests/context_alarm/test_transcript_reader.py
#
# context-alarm transcript reader unit tests
########################################################################################################################


import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "hooks"))

import context_alarm._transcript_reader


TRANSCRIPT_READER = context_alarm._transcript_reader.TranscriptContextTokenReader


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


def _build_non_assistant_entry_jsonl_line(entry_type):

    """Builds a single JSONL line representing a non-assistant entry (e.g. last-prompt, ai-title)."""
    entry = {"type": entry_type, "sessionId": "test-session"}
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


class TranscriptContextTokenReaderTestCase(unittest.TestCase):


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


    def test_normal_transcript_returns_sum_of_token_fields(self):

        transcript_path = self._write_and_track_transcript([
            _build_assistant_entry_jsonl_line(
                input_tokens = 10,
                cache_creation_input_tokens = 5000,
                cache_read_input_tokens = 195000
            )
        ])
        result = TRANSCRIPT_READER.read_last_context_token_count(
            transcript_file_abs_path = transcript_path
        )
        self.assertEqual(result, 200010)


    def test_empty_file_returns_none(self):

        transcript_path = self._write_and_track_transcript([])
        result = TRANSCRIPT_READER.read_last_context_token_count(
            transcript_file_abs_path = transcript_path
        )
        self.assertIsNone(result)


    def test_nonexistent_file_returns_none(self):

        result = TRANSCRIPT_READER.read_last_context_token_count(
            transcript_file_abs_path = "/tmp/does-not-exist-test-transcript.jsonl"
        )
        self.assertIsNone(result)


    def test_none_path_returns_none(self):

        result = TRANSCRIPT_READER.read_last_context_token_count(
            transcript_file_abs_path = None
        )
        self.assertIsNone(result)


    def test_malformed_last_line_skips_to_previous_valid_entry(self):

        transcript_path = self._write_and_track_transcript([
            _build_assistant_entry_jsonl_line(
                input_tokens = 10,
                cache_creation_input_tokens = 7000,
                cache_read_input_tokens = 60000
            ),
            "this is not valid json {"
        ])
        result = TRANSCRIPT_READER.read_last_context_token_count(
            transcript_file_abs_path = transcript_path
        )
        self.assertEqual(result, 67010)


    def test_no_assistant_messages_returns_none(self):

        transcript_path = self._write_and_track_transcript([
            _build_non_assistant_entry_jsonl_line("last-prompt"),
            _build_non_assistant_entry_jsonl_line("ai-title")
        ])
        result = TRANSCRIPT_READER.read_last_context_token_count(
            transcript_file_abs_path = transcript_path
        )
        self.assertIsNone(result)


    def test_missing_usage_fields_default_to_zero(self):

        entry = {
            "type": "assistant",
            "message": {
                "usage": {
                    "input_tokens": 42
                }
            }
        }
        transcript_path = self._write_and_track_transcript([
            json.dumps(entry, ensure_ascii = False)
        ])
        result = TRANSCRIPT_READER.read_last_context_token_count(
            transcript_file_abs_path = transcript_path
        )
        self.assertEqual(result, 42)


    def test_multiple_assistant_messages_returns_last_one(self):

        transcript_path = self._write_and_track_transcript([
            _build_assistant_entry_jsonl_line(
                input_tokens = 1,
                cache_creation_input_tokens = 1000,
                cache_read_input_tokens = 50000
            ),
            _build_non_assistant_entry_jsonl_line("user"),
            _build_assistant_entry_jsonl_line(
                input_tokens = 5,
                cache_creation_input_tokens = 3000,
                cache_read_input_tokens = 250000
            ),
            _build_non_assistant_entry_jsonl_line("last-prompt")
        ])
        result = TRANSCRIPT_READER.read_last_context_token_count(
            transcript_file_abs_path = transcript_path
        )
        self.assertEqual(result, 253005)


    def test_assistant_message_without_usage_object_is_skipped(self):

        entry_no_usage = {
            "type": "assistant",
            "message": {"content": "hello"}
        }
        transcript_path = self._write_and_track_transcript([
            _build_assistant_entry_jsonl_line(
                input_tokens = 10,
                cache_creation_input_tokens = 2000,
                cache_read_input_tokens = 80000
            ),
            json.dumps(entry_no_usage, ensure_ascii = False)
        ])
        result = TRANSCRIPT_READER.read_last_context_token_count(
            transcript_file_abs_path = transcript_path
        )
        self.assertEqual(result, 82010)


if __name__ == "__main__":
    unittest.main()
