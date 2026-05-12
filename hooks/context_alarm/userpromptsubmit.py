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


_CONTEXT_TOKEN_COUNT_WARNING_THRESHOLD = 200_000


class UserPromptSubmitContextAlarmEntry:

    """Single-purpose entry: read the UserPromptSubmit payload, extract the transcript path, read the last assistant
    message's total context token count from the transcript JSONL, and inject a warning if the count exceeds the
    threshold. Fires on every user message and warns every turn the context is over the limit."""


    @staticmethod
    def main():

        """Reads the payload, checks the transcript for context size, injects warning or exits silent."""
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
        if last_context_token_count is None or last_context_token_count <= _CONTEXT_TOKEN_COUNT_WARNING_THRESHOLD:
            _common._hook_io.UserPromptSubmitHookIo.emit_passthrough_and_exit()
            return
        formatted_context_token_count = f"{last_context_token_count:,}"
        formatted_warning_threshold = f"{_CONTEXT_TOKEN_COUNT_WARNING_THRESHOLD:,}"
        context_alarm_injection_text = (
            f"Context is at {formatted_context_token_count} tokens."
            f" Tell the user that context is over their limit of {formatted_warning_threshold}"
            " and that they should run /compact soon."
        )
        _common._hook_io.UserPromptSubmitHookIo.emit_context_injection_and_exit(context_alarm_injection_text)


if __name__ == "__main__":
    UserPromptSubmitContextAlarmEntry.main()
