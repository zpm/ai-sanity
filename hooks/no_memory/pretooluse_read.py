########################################################################################################################
# hooks/no_memory/pretooluse_read.py
#
# no-memory read pre-tool hook
########################################################################################################################


import os
import sys

# hot patch so that imports work when script is invoked directly (how claude invokes hooks)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import _common._hook_io
import no_memory._checker


MEMORY_PATH_CHECKER = no_memory._checker.MemoryPathChecker


class PreToolUseReadRuleChecks:

    """Rule checks that apply only to the Read, Glob, and Grep matcher. Each method takes the full PreToolUse payload
    dict and returns either a string deny-reason on violation or None to pass."""


    @staticmethod
    def check_no_memory_access_for_read_or_glob_or_grep(pretooluse_payload):

        """Per-matcher path extraction. Read uses file_path. Glob uses path and pattern (Glob's pattern is itself a
        glob over file paths so it is path-like). Grep uses path only - its pattern is a regex search pattern over
        file contents, NOT a path, and scanning it would overblock harmless content searches that mention the literal
        string MEMORY.md."""
        read_like_tool_name = pretooluse_payload.get("tool_name", "")
        tool_input_dict = pretooluse_payload.get("tool_input") or {}
        if read_like_tool_name == "Read":
            return MEMORY_PATH_CHECKER.assert_paths_are_not_memory_locations(tool_input_dict.get("file_path"))
        if read_like_tool_name == "Glob":
            return MEMORY_PATH_CHECKER.assert_paths_are_not_memory_locations(
                tool_input_dict.get("path"),
                tool_input_dict.get("pattern")
            )
        if read_like_tool_name == "Grep":
            return MEMORY_PATH_CHECKER.assert_paths_are_not_memory_locations(tool_input_dict.get("path"))
        return None


class PreToolUseReadHookEntry:

    """Composes every rule check that applies to Read, Glob, and Grep tool calls."""

    _rule_check_methods_to_run_in_order = (
        PreToolUseReadRuleChecks.check_no_memory_access_for_read_or_glob_or_grep,
    )


    @staticmethod
    def main():

        """Reads the payload, runs every applicable rule check, denies on the first violation, otherwise passes
        through."""
        try:
            pretooluse_payload = _common._hook_io.PreToolUseHookIo.read_pretooluse_payload_from_stdin()
            for rule_check_method in PreToolUseReadHookEntry._rule_check_methods_to_run_in_order:
                deny_reason_or_none = rule_check_method(pretooluse_payload)
                if deny_reason_or_none is not None:
                    _common._hook_io.PreToolUseHookIo.emit_deny_decision_and_exit(deny_reason_or_none)
            _common._hook_io.PreToolUseHookIo.emit_passthrough_and_exit()
        except Exception as e:
            _common._hook_io.PreToolUseHookIo.emit_deny_decision_and_exit(f"no_memory/pretooluse_read hook crashed: {e}")


if __name__ == "__main__":
    PreToolUseReadHookEntry.main()
