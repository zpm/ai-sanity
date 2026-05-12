########################################################################################################################
# hooks/context_alarm/_transcript_reader.py
#
# transcript JSONL reader for context token counts
########################################################################################################################


import json
import os


_TAIL_CHUNK_SIZE_BYTES = 65536


class TranscriptContextTokenReader:

    """Reads the last assistant message's token usage from a Claude Code transcript JSONL file. The transcript is
    written by Claude Code at the path provided in every hook payload's transcript_path field. Each assistant message
    entry contains a message.usage object with input_tokens, cache_creation_input_tokens, and cache_read_input_tokens.
    The sum of all three equals the total context window usage for that turn."""


    @staticmethod
    def read_last_context_token_count(transcript_file_abs_path):

        """Returns the total context token count from the most recent assistant message in the transcript, or None if
        the file cannot be read or contains no valid assistant message with usage data. Reads only the tail of the file
        for efficiency (the last assistant message is always near the end)."""
        if not transcript_file_abs_path or not os.path.isfile(transcript_file_abs_path):
            return None
        try:
            file_size_bytes = os.path.getsize(transcript_file_abs_path)
        except OSError:
            return None
        seek_offset_bytes = max(0, file_size_bytes - _TAIL_CHUNK_SIZE_BYTES)
        try:
            with open(transcript_file_abs_path, "rb") as open_transcript_file:
                open_transcript_file.seek(seek_offset_bytes)
                tail_chunk_bytes = open_transcript_file.read()
        except OSError:
            return None
        tail_chunk_text = tail_chunk_bytes.decode("utf-8", errors = "replace")
        tail_lines = tail_chunk_text.split("\n")
        # walk backward through lines to find the most recent assistant message with usage data
        for candidate_line in reversed(tail_lines):
            candidate_line_stripped = candidate_line.strip()
            if not candidate_line_stripped:
                continue
            try:
                parsed_entry = json.loads(candidate_line_stripped)
            except (json.JSONDecodeError, ValueError):
                continue
            if parsed_entry.get("type") != "assistant":
                continue
            message_object = parsed_entry.get("message")
            if not isinstance(message_object, dict):
                continue
            usage_object = message_object.get("usage")
            if not isinstance(usage_object, dict):
                continue
            input_tokens_count = usage_object.get("input_tokens", 0)
            cache_creation_input_tokens_count = usage_object.get("cache_creation_input_tokens", 0)
            cache_read_input_tokens_count = usage_object.get("cache_read_input_tokens", 0)
            return int(input_tokens_count) + int(cache_creation_input_tokens_count) + int(cache_read_input_tokens_count)
        return None
