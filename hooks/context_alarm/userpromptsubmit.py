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


class UserPromptSubmitContextAlarmEntry:

    """Single-purpose entry: read the UserPromptSubmit payload, extract the transcript path, and read the last
    assistant message's total context token count from the transcript JSONL. The entry injects nothing, because the
    VS Code context counter already shows the count to the user."""


    @staticmethod
    def main():

        """Reads the payload and the transcript's context token count, then exits silent."""
        userpromptsubmit_payload = (
            _common._hook_io.UserPromptSubmitHookIo.read_userpromptsubmit_payload_from_stdin()
        )
        transcript_file_abs_path = userpromptsubmit_payload.get("transcript_path")
        try:
            context_alarm._transcript_reader.TranscriptContextTokenReader.read_last_context_token_count(
                transcript_file_abs_path = transcript_file_abs_path
            )
        except Exception:
            pass
        _common._hook_io.UserPromptSubmitHookIo.emit_passthrough_and_exit()


if __name__ == "__main__":
    UserPromptSubmitContextAlarmEntry.main()
