########################################################################################################################
# hooks/_common/_hook_io.py
#
# hook stdin and stdout helpers
########################################################################################################################


import json
import sys


class PreToolUseHookIo:

    """Stdin and stdout helpers shared by every PreToolUse entry script. The PreToolUse hook contract is documented at
    https://code.claude.com/docs/en/hooks: read a JSON payload from stdin, then either exit 0 with a hookSpecificOutput
    JSON object on stdout to deny/allow/ask, or exit 0 with no stdout to pass through to normal permission rules."""


    @staticmethod
    def read_pretooluse_payload_from_stdin():

        """Reads and parses the PreToolUse JSON payload Claude Code pipes to stdin and returns it as a dict. Reads
        from the raw byte buffer to bypass Windows text-mode stdin (which defaults to cp1252 and silently corrupts
        multi-byte characters). The bytes are passed directly to json.loads, which auto-detects encoding."""
        return json.loads(sys.stdin.buffer.read())


    @staticmethod
    def emit_deny_decision_and_exit(deny_reason_shown_to_claude):

        """Writes a deny-decision hookSpecificOutput JSON object to stdout and exits, which blocks the in-flight tool
        call. The deny_reason_shown_to_claude argument is surfaced verbatim to Claude so the message must explain which
        CLAUDE.md rule was violated and what Claude should do instead."""
        json.dump(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": deny_reason_shown_to_claude
                }
            },
            sys.stdout
        )
        sys.exit(0)


    @staticmethod
    def emit_allow_decision_and_exit():

        """Writes an allow-decision hookSpecificOutput JSON object to stdout and exits, which permits the in-flight
        tool call to proceed without further permission checks from settings.json."""
        json.dump(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "allow"
                }
            },
            sys.stdout
        )
        sys.exit(0)


    @staticmethod
    def emit_passthrough_and_exit():

        """Writes nothing to stdout and exits cleanly, which lets the tool call proceed to the normal settings.json
        permission rule evaluation pipeline."""
        sys.exit(0)


class PostToolUseHookIo:

    """Stdin and stdout helpers for PostToolUse entry scripts. Per the PostToolUse hook contract documented at
    https://code.claude.com/docs/en/hooks, PostToolUse hooks observe a completed tool call and cannot deny it; their
    usefulness comes from writing to external state (e.g. the required-reads satisfaction flags) based on what the
    tool did. The passthrough emit here is identical to PreToolUse passthrough: no stdout, exit 0."""


    @staticmethod
    def read_posttooluse_payload_from_stdin():

        """Reads and parses the PostToolUse JSON payload Claude Code pipes to stdin. Reads from the raw byte buffer
        and passes bytes directly to json.loads for encoding auto-detection."""
        return json.loads(sys.stdin.buffer.read())


    @staticmethod
    def emit_passthrough_and_exit():

        """Writes nothing to stdout and exits 0. PostToolUse hooks have no per-decision envelope to emit; the
        observation they make (e.g. writing a satisfaction flag to disk) already happened before this call."""
        sys.exit(0)


class PreCompactHookIo:

    """Stdin and stdout helpers for PreCompact entry scripts. PreCompact fires when Claude Code is about to
    compress the conversation context. The hook has no decision envelope; any cleanup it performs (e.g. clearing
    required-reads satisfaction flags so docs are re-demanded after compaction) happens via external state writes."""


    @staticmethod
    def read_precompact_payload_from_stdin():

        """Reads and parses the PreCompact JSON payload Claude Code pipes to stdin. Reads from the raw byte buffer
        and passes bytes directly to json.loads for encoding auto-detection."""
        return json.loads(sys.stdin.buffer.read())


    @staticmethod
    def emit_passthrough_and_exit():

        """Writes nothing to stdout and exits 0."""
        sys.exit(0)


class UserPromptSubmitHookIo:

    """Stdin and stdout helpers for UserPromptSubmit entry scripts. UserPromptSubmit fires before Claude processes
    each user message. Unlike PreToolUse hooks, the output contract is plain text, not a JSON decision envelope:
    text written to stdout (exit 0) is injected into Claude's context as additional instructions visible to the
    model. No stdout (exit 0) means no injection. Non-zero exit is logged but does not block the prompt."""


    @staticmethod
    def read_userpromptsubmit_payload_from_stdin():

        """Reads and parses the UserPromptSubmit JSON payload Claude Code pipes to stdin. Reads from the raw byte
        buffer and passes bytes directly to json.loads for encoding auto-detection."""
        return json.loads(sys.stdin.buffer.read())


    @staticmethod
    def emit_context_injection_and_exit(instruction_text_string):

        """Writes plain text to stdout and exits 0. Claude Code injects this text into the model's context before
        processing the user message. The text is not wrapped in a JSON envelope."""
        sys.stdout.write(instruction_text_string)
        sys.exit(0)


    @staticmethod
    def emit_passthrough_and_exit():

        """Writes nothing to stdout and exits 0. No text is injected into the model's context."""
        sys.exit(0)
