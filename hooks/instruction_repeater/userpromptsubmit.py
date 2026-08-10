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
import instruction_repeater._transcript_reader


_INSTRUCTION_TEXT = (
    "Please read the global claude.md and the project claude.md and follow all instructions."
    " Before proceeding with any task below you must explicitly acknowledge to the user that you"
    " have read the documents (or that they do not exist), and give them a two-sentence summary"
    " of the important rules you will remember. Also state your model name and context window."
)

_REINJECTION_CYCLE_CONTEXT_TOKENS = 50_000


class UserPromptSubmitInstructionRepeaterEntry:

    """Single-purpose entry: read the UserPromptSubmit payload, check the session flag, and inject the instruction
    text on first fire. After that, re-inject a re-read instruction each time the context grows past another
    _REINJECTION_CYCLE_CONTEXT_TOKENS boundary, detected statelessly by comparing the transcript's current context
    token count against the count at the previous prompt. The PreCompact hook clears the session flag so the full
    instruction is re-injected after context compaction."""


    @staticmethod
    def main():

        """Reads the payload, checks the session flag and the context boundary, injects or exits silent."""
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
                UserPromptSubmitInstructionRepeaterEntry._check_context_boundary_and_emit(
                    transcript_file_abs_path = userpromptsubmit_payload.get("transcript_path")
                )
                return
            instruction_repeater._state.InstructionRepeaterState.set_flag(
                claude_session_id_string = claude_session_id_string
            )
            _common._hook_io.UserPromptSubmitHookIo.emit_context_injection_and_exit(_INSTRUCTION_TEXT)
        except Exception:
            raise


    @staticmethod
    def _check_context_boundary_and_emit(transcript_file_abs_path):

        """Injects a re-read instruction if the context crossed a cycle boundary since the previous prompt,
        otherwise emits passthrough. A transcript that cannot be read is a silent passthrough: a missed
        re-injection is cheap, a crashed prompt is not."""
        try:
            current_context_token_count, previous_prompt_context_token_count = (
                instruction_repeater._transcript_reader.TranscriptPromptContextTokenReader
                .read_current_and_previous_prompt_context_token_counts(
                    transcript_file_abs_path = transcript_file_abs_path
                )
            )
        except Exception:
            _common._hook_io.UserPromptSubmitHookIo.emit_passthrough_and_exit()
            return
        if current_context_token_count is None or previous_prompt_context_token_count is None:
            _common._hook_io.UserPromptSubmitHookIo.emit_passthrough_and_exit()
            return
        previous_cycle_bucket = previous_prompt_context_token_count // _REINJECTION_CYCLE_CONTEXT_TOKENS
        current_cycle_bucket = current_context_token_count // _REINJECTION_CYCLE_CONTEXT_TOKENS
        if previous_cycle_bucket >= current_cycle_bucket:
            _common._hook_io.UserPromptSubmitHookIo.emit_passthrough_and_exit()
            return
        crossed_boundary_context_tokens = current_cycle_bucket * _REINJECTION_CYCLE_CONTEXT_TOKENS
        reread_instruction_text = (
            f"Context has crossed the {crossed_boundary_context_tokens:,}-token mark"
            f" (now at {current_context_token_count:,} tokens). Re-read the global claude.md and the"
            " project claude.md now and follow all instructions. Briefly confirm to the user that you"
            " have re-read them."
        )
        _common._hook_io.UserPromptSubmitHookIo.emit_context_injection_and_exit(reread_instruction_text)


if __name__ == "__main__":
    UserPromptSubmitInstructionRepeaterEntry.main()
