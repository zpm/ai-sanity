########################################################################################################################
# hooks/instruction_repeater/precompact.py
#
# instruction-repeater pre-compact hook
########################################################################################################################


import os
import sys

# hot patch so that imports work when script is invoked directly (how claude invokes hooks)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import _common._hook_io
import instruction_repeater._state


class PreCompactInstructionRepeaterEntry:

    """Single-purpose entry: read the PreCompact payload, extract the session id, clear the session's
    instruction-repeater flag so the instruction is re-injected after compaction."""


    @staticmethod
    def main():

        """Reads the payload, clears the session flag, exits 0."""
        try:
            precompact_payload = _common._hook_io.PreCompactHookIo.read_precompact_payload_from_stdin()
            claude_session_id_string = precompact_payload.get("session_id") or "unknown-session"
            instruction_repeater._state.InstructionRepeaterState.clear_flag(
                claude_session_id_string = claude_session_id_string
            )
            _common._hook_io.PreCompactHookIo.emit_passthrough_and_exit()
        except Exception:
            raise


if __name__ == "__main__":
    PreCompactInstructionRepeaterEntry.main()
