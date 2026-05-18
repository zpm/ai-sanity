########################################################################################################################
# hooks/instruction_repeater/userpromptsubmit.py
#
# instruction-repeater user-prompt-submit hook
########################################################################################################################


import os
import sys

# hot patch so that imports work when script is invoked directly (how claude invokes hooks)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import _common._hook_io
import instruction_repeater._state


_INSTRUCTION_TEXT = (
    "Please read the global claude.md and the project claude.md and follow all instructions."
    " Before proceeding with any task below you must explicitly acknowledge to the user that you"
    " have read the documents (or that they do not exist), and give them a two-sentence summary"
    " of the important rules you will remember. Also state your model name and context window."
)


class UserPromptSubmitInstructionRepeaterEntry:

    """Single-purpose entry: read the UserPromptSubmit payload, check the session flag, and inject the instruction
    text on first fire. Subsequent fires within the same session emit nothing. The PreCompact hook clears the flag
    so the instruction is re-injected after context compaction."""


    @staticmethod
    def main():

        """Reads the payload, checks the session flag, injects instruction text or exits silent."""
        try:
            userpromptsubmit_payload = (
                _common._hook_io.UserPromptSubmitHookIo.read_userpromptsubmit_payload_from_stdin()
            )
            try:
                instruction_repeater._state.InstructionRepeaterState.sweep_stale_flag_files()
            except OSError:
                pass
            claude_session_id_string = userpromptsubmit_payload.get("session_id") or "unknown-session"
            if instruction_repeater._state.InstructionRepeaterState.is_flag_set(
                claude_session_id_string = claude_session_id_string
            ):
                _common._hook_io.UserPromptSubmitHookIo.emit_passthrough_and_exit()
                return
            instruction_repeater._state.InstructionRepeaterState.set_flag(
                claude_session_id_string = claude_session_id_string
            )
            _common._hook_io.UserPromptSubmitHookIo.emit_context_injection_and_exit(_INSTRUCTION_TEXT)
        except Exception:
            raise


if __name__ == "__main__":
    UserPromptSubmitInstructionRepeaterEntry.main()
