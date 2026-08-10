########################################################################################################################
# hooks/instruction_repeater/_transcript_reader.py
#
# transcript JSONL reader for prompt-boundary context token counts
########################################################################################################################


import json
import os


class TranscriptPromptContextTokenReader:

    """Reads the context token counts needed for the 50k-boundary re-injection check from a Claude Code transcript
    JSONL file. Returns two counts: the current context size (last assistant message's usage) and the context size
    as of the previous user prompt. The caller compares which 50k bucket each count falls in; a bucket increase means
    the context crossed a boundary since the previous prompt. Stateless by design: the transcript is the only input."""


    @staticmethod
    def _is_real_user_prompt_entry(parsed_entry):

        """Returns True if the entry is a typed user prompt. Tool results also arrive as type "user" entries, but
        their content is a list containing tool_result blocks; typed prompts are a plain string (older transcripts)
        or a list of text blocks (current transcripts). Meta entries are never prompts."""
        if parsed_entry.get("type") != "user":
            return False
        if parsed_entry.get("isMeta"):
            return False
        message_object = parsed_entry.get("message")
        if not isinstance(message_object, dict):
            return False
        content_value = message_object.get("content")
        if isinstance(content_value, str):
            return True
        if isinstance(content_value, list):
            for content_block in content_value:
                if isinstance(content_block, dict) and content_block.get("type") == "tool_result":
                    return False
            return True
        return False


    @staticmethod
    def _extract_assistant_context_token_count(parsed_entry):

        """Returns the total context token count from an assistant entry's usage object, or None if the entry is not
        an assistant message with usage data. The sum of input_tokens, cache_creation_input_tokens, and
        cache_read_input_tokens equals the total context window usage for that turn."""
        if parsed_entry.get("type") != "assistant":
            return None
        message_object = parsed_entry.get("message")
        if not isinstance(message_object, dict):
            return None
        usage_object = message_object.get("usage")
        if not isinstance(usage_object, dict):
            return None
        return (
            int(usage_object.get("input_tokens", 0) or 0)
            + int(usage_object.get("cache_creation_input_tokens", 0) or 0)
            + int(usage_object.get("cache_read_input_tokens", 0) or 0)
        )


    @staticmethod
    def read_current_and_previous_prompt_context_token_counts(transcript_file_abs_path):

        """Returns (current_context_token_count, previous_prompt_context_token_count), either of which may be None
        when the transcript is missing, unreadable, or too short to contain both. The whole file is read: the previous
        prompt can sit megabytes behind the tail when the intervening turn was tool-heavy."""
        reader_class = TranscriptPromptContextTokenReader
        if not transcript_file_abs_path or not os.path.isfile(transcript_file_abs_path):
            return (None, None)
        # the just-submitted prompt is usually already written to the transcript when UserPromptSubmit fires, so the
        # latest prompt entry is the in-flight one and the previous prompt is the entry before it. tracking whether
        # any assistant usage follows the latest prompt distinguishes that ordering from a transcript where the
        # in-flight prompt has not been written yet.
        last_assistant_context_token_count = None
        context_token_count_at_latest_prompt = None
        context_token_count_at_prior_prompt = None
        latest_prompt_seen = False
        assistant_usage_seen_after_latest_prompt = False
        try:
            with open(transcript_file_abs_path, "r", encoding = "utf-8", errors = "replace") as open_transcript_file:
                for raw_transcript_line in open_transcript_file:
                    stripped_transcript_line = raw_transcript_line.strip()
                    if not stripped_transcript_line:
                        continue
                    try:
                        parsed_entry = json.loads(stripped_transcript_line)
                    except (json.JSONDecodeError, ValueError):
                        continue
                    if not isinstance(parsed_entry, dict):
                        continue
                    # sidechain entries carry a subagent's context counts, which would corrupt the main-thread totals
                    if parsed_entry.get("isSidechain"):
                        continue
                    assistant_context_token_count = reader_class._extract_assistant_context_token_count(
                        parsed_entry = parsed_entry
                    )
                    if assistant_context_token_count is not None and assistant_context_token_count > 0:
                        last_assistant_context_token_count = assistant_context_token_count
                        if latest_prompt_seen:
                            assistant_usage_seen_after_latest_prompt = True
                        continue
                    if reader_class._is_real_user_prompt_entry(parsed_entry = parsed_entry):
                        context_token_count_at_prior_prompt = context_token_count_at_latest_prompt
                        context_token_count_at_latest_prompt = last_assistant_context_token_count
                        latest_prompt_seen = True
                        assistant_usage_seen_after_latest_prompt = False
        except OSError:
            return (None, None)
        if last_assistant_context_token_count is None or not latest_prompt_seen:
            return (last_assistant_context_token_count, None)
        if assistant_usage_seen_after_latest_prompt:
            return (last_assistant_context_token_count, context_token_count_at_latest_prompt)
        return (last_assistant_context_token_count, context_token_count_at_prior_prompt)
