########################################################################################################################
# hooks/required_reading/precompact.py
#
# required-reading pre-compact hook
########################################################################################################################


import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import _common._hook_io
import required_reading._state


class PreCompactRequiredReadsEntry:

    """Single-purpose entry: read the PreCompact payload, extract the session id, clear the session's required-reads
    state directory. Any error falls through to a silent exit 0; this hook cannot usefully deny or emit anything."""


    @staticmethod
    def main():

        """Reads the payload, clears the session's satisfaction flags, exits 0. Empty session id degrades to the
        unknown-session default, which clears that bucket instead of the active session (harmless)."""
        try:
            precompact_payload = _common._hook_io.PreCompactHookIo.read_precompact_payload_from_stdin()
            claude_session_id_string = precompact_payload.get("session_id") or "unknown-session"
            required_reading._state.RequiredReadsState.clear_session(
                claude_session_id_string = claude_session_id_string
            )
            _common._hook_io.PreCompactHookIo.emit_passthrough_and_exit()
        except Exception:
            _common._hook_io.PreCompactHookIo.emit_passthrough_and_exit()


if __name__ == "__main__":
    PreCompactRequiredReadsEntry.main()
