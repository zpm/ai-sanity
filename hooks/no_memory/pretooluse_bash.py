import os
import shlex
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import _common._hook_io
import no_memory._checker


class PreToolUseBashMemoryRuleChecks:

    """Memory-access rule checks for the Bash matcher. Each method takes the full PreToolUse payload dict and returns
    either a string deny-reason on violation or None to pass."""

    @staticmethod
    def check_no_memory_access_for_bash(pretooluse_payload):

        """Bash-side memory check. Tokenises the command and checks each token against the auto-memory directory and
        MEMORY.md path patterns. This is more accurate than scanning the raw command string: `echo "search for
        MEMORY.md term"` shlex-splits into a single token whose start position is not preceded by `/` or `\\`, so the
        regex correctly does not match. Falls back to scanning the raw command string when tokenisation fails
        (malformed quoting), to avoid bypass via crafted broken syntax."""
        bash_command_string = (pretooluse_payload.get("tool_input") or {}).get("command", "")
        try:
            command_tokens = shlex.split(bash_command_string)
            return no_memory._checker.MemoryPathChecker.assert_paths_are_not_memory_locations(*command_tokens)
        except ValueError:
            return no_memory._checker.MemoryPathChecker.assert_paths_are_not_memory_locations(bash_command_string)


class PreToolUseBashMemoryHookEntry:

    """Composes memory-access rule checks for Bash tool calls."""

    _rule_check_methods_to_run_in_order = (
        PreToolUseBashMemoryRuleChecks.check_no_memory_access_for_bash,
    )

    @staticmethod
    def main():

        """Reads the payload, runs every applicable rule check, denies on the first violation, otherwise passes
        through. Any unexpected error falls through to passthrough so a bug in this hook cannot block a command."""
        try:
            pretooluse_payload = _common._hook_io.PreToolUseHookIo.read_pretooluse_payload_from_stdin()
            for rule_check_method in PreToolUseBashMemoryHookEntry._rule_check_methods_to_run_in_order:
                deny_reason_or_none = rule_check_method(pretooluse_payload)
                if deny_reason_or_none is not None:
                    _common._hook_io.PreToolUseHookIo.emit_deny_decision_and_exit(deny_reason_or_none)
            _common._hook_io.PreToolUseHookIo.emit_passthrough_and_exit()
        except Exception:
            _common._hook_io.PreToolUseHookIo.emit_passthrough_and_exit()


if __name__ == "__main__":
    PreToolUseBashMemoryHookEntry.main()
