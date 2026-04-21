########################################################################################################################
# ~/.claude/hooks/_lib.py
#
# IO helpers and the low-level memory-path checker shared by every PreToolUse entry script
########################################################################################################################
import json
import re
import sys


class PreToolUseHookIo:

    """Stdin and stdout helpers shared by every pretooluse_*.py entry script. The PreToolUse hook contract is documented
    at https://code.claude.com/docs/en/hooks: read a JSON payload from stdin, then either exit 0 with a hookSpecificOutput
    JSON object on stdout to deny/allow/ask, or exit 0 with no stdout to pass through to normal permission rules."""

    @staticmethod
    def read_pretooluse_payload_from_stdin():

        """Reads and parses the PreToolUse JSON payload Claude Code pipes to stdin and returns it as a dict. Uses the
        raw byte buffer with explicit UTF-8 decoding because text-mode stdin on Windows defaults to the cp1252 locale
        and silently mojibakes multi-byte characters before JSON parsing, erasing the em dash rule check."""
        return json.loads(sys.stdin.buffer.read().decode("utf-8"))

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
    def emit_passthrough_and_exit():

        """Writes nothing to stdout and exits cleanly, which lets the tool call proceed to the normal settings.json
        permission rule evaluation pipeline."""
        sys.exit(0)


class MemoryPathChecker:

    """Low-level check for whether a given path string references the auto-memory directory or a MEMORY.md file. Each
    matcher's entry script extracts the path arguments appropriate to its tool and passes them in. This avoids the
    'scan every text field' anti-pattern that would overblock legitimate searches for the literal string 'MEMORY.md'
    inside Grep regex patterns or the unrelated body of a Bash command."""

    _auto_memory_directory_path_pattern = re.compile(
        r"\.claude[/\\]projects[/\\][^/\\]+[/\\]memory(?:[/\\]|$)",
        re.IGNORECASE
    )
    _memory_md_filename_pattern = re.compile(
        r"(?:^|[/\\])MEMORY\.md\b",
        re.IGNORECASE
    )

    @staticmethod
    def assert_paths_are_not_memory_locations(*candidate_path_strings):

        """Returns a deny reason string if any candidate path string references the auto-memory directory layout
        (`<dir>/.claude/projects/<hash>/memory/...`) or a `MEMORY.md` filename. Returns None when all candidates pass.
        Empty/None candidates are skipped. The rule comes from CLAUDE.md ('YOU ARE NOT ALLOWED TO USE MEMORY.md or the
        external memory directory'). This is the losing side of a direct system-prompt conflict with the auto-memory
        system, so this hook is what makes CLAUDE.md actually win."""
        rule_check_class = MemoryPathChecker
        for candidate_path_string in candidate_path_strings:
            if not candidate_path_string:
                continue
            if rule_check_class._auto_memory_directory_path_pattern.search(candidate_path_string):
                return (
                    f"Refused: path `{candidate_path_string}` is inside the auto-memory directory. CLAUDE.md forbids"
                    f" using the external memory directory; the auto-memory system prompt is explicitly overridden."
                    f" Persistent rules must go in version-controlled CLAUDE.md files."
                )
            if rule_check_class._memory_md_filename_pattern.search(candidate_path_string):
                return (
                    f"Refused: path `{candidate_path_string}` references MEMORY.md. CLAUDE.md forbids using MEMORY.md;"
                    f" the auto-memory system prompt is explicitly overridden. Persistent rules must go in"
                    f" version-controlled CLAUDE.md files."
                )
        return None