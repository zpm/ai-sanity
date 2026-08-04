########################################################################################################################
# hooks/context_alarm/userpromptsubmit.py
#
# context-alarm user-prompt-submit hook
########################################################################################################################


import os
import sys

# hot patch so that imports work when script is invoked directly (how claude invokes hooks)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import _common._hook_io
import context_alarm._transcript_reader


# gentle brackets are checked highest-first so the injection names the highest mark the context has passed
_CONTEXT_TOKEN_COUNT_GENTLE_BRACKET_THRESHOLDS = [400_000, 300_000, 200_000]
_CONTEXT_TOKEN_COUNT_FIRM_WARNING_THRESHOLD = 500_000


class UserPromptSubmitContextAlarmEntry:

    """Single-purpose entry: read the UserPromptSubmit payload, extract the transcript path, read the last assistant
    message's total context token count from the transcript JSONL, and inject an escalating compact reminder. The
    context window is 1M tokens but quality degrades past 200k, so the injection asks claude to gently remind the
    user once per bracket (200k, 300k, 400k), then firmly every turn past 500k."""


    @staticmethod
    def main():

        """Reads the payload, checks the transcript for context size, injects a reminder or exits silent."""
        userpromptsubmit_payload = (
            _common._hook_io.UserPromptSubmitHookIo.read_userpromptsubmit_payload_from_stdin()
        )
        transcript_file_abs_path = userpromptsubmit_payload.get("transcript_path")
        try:
            last_context_token_count = (
                context_alarm._transcript_reader.TranscriptContextTokenReader.read_last_context_token_count(
                    transcript_file_abs_path = transcript_file_abs_path
                )
            )
        except Exception:
            _common._hook_io.UserPromptSubmitHookIo.emit_passthrough_and_exit()
            return
        if last_context_token_count is None:
            _common._hook_io.UserPromptSubmitHookIo.emit_passthrough_and_exit()
            return
        formatted_context_token_count = f"{last_context_token_count:,}"
        if last_context_token_count > _CONTEXT_TOKEN_COUNT_FIRM_WARNING_THRESHOLD:
            firm_warning_injection_text = (
                f"Context is at {formatted_context_token_count} tokens, far past the 200,000-token degradation"
                " point. Tell the user they should run /compact now."
            )
            _common._hook_io.UserPromptSubmitHookIo.emit_context_injection_and_exit(firm_warning_injection_text)
            return
        # once-per-bracket dedup is delegated to the model: its earlier reminder is visible in the conversation,
        # so the injection tells it to stay silent if it already reminded at this mark
        for gentle_bracket_threshold in _CONTEXT_TOKEN_COUNT_GENTLE_BRACKET_THRESHOLDS:
            if last_context_token_count > gentle_bracket_threshold:
                formatted_gentle_bracket_threshold = f"{gentle_bracket_threshold:,}"
                gentle_reminder_injection_text = (
                    f"Context is at {formatted_context_token_count} tokens, past the"
                    f" {formatted_gentle_bracket_threshold} mark. The context window is 1,000,000 tokens but quality"
                    f" degrades past 200,000. If you have not already reminded the user at the"
                    f" {formatted_gentle_bracket_threshold} mark in this conversation, gently suggest at a natural"
                    " stopping point that they run /compact soon. If you already have, stay silent."
                )
                _common._hook_io.UserPromptSubmitHookIo.emit_context_injection_and_exit(gentle_reminder_injection_text)
                return
        _common._hook_io.UserPromptSubmitHookIo.emit_passthrough_and_exit()


if __name__ == "__main__":
    UserPromptSubmitContextAlarmEntry.main()
