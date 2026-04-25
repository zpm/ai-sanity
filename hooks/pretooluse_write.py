########################################################################################################################
# hooks/pretooluse_write.py
#
# PreToolUse entry script for the Write|Edit|NotebookEdit matcher and its rule check methods
########################################################################################################################
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import _lib


class PreToolUseWriteRuleChecks:

    """Rule checks that apply only to the Write, Edit, and NotebookEdit matcher. Each method takes the full PreToolUse
    payload dict and returns either a string deny-reason on violation or None to pass."""

    @staticmethod
    def check_no_memory_access_for_write_or_edit_or_notebook_edit(pretooluse_payload):

        """Extracts the file_path or notebook_path field appropriate to the tool and asks the shared MemoryPathChecker
        whether the path is in the auto-memory area. Per-matcher extraction avoids overblocking legitimate writes that
        happen to contain the literal string 'MEMORY.md' inside their content payload."""
        write_like_tool_name = pretooluse_payload.get("tool_name", "")
        tool_input_dict = pretooluse_payload.get("tool_input") or {}
        if write_like_tool_name == "NotebookEdit":
            return _lib.MemoryPathChecker.assert_paths_are_not_memory_locations(tool_input_dict.get("notebook_path"))
        return _lib.MemoryPathChecker.assert_paths_are_not_memory_locations(tool_input_dict.get("file_path"))


class PreToolUseWriteHookEntry:

    """Composes every rule check that applies to Write, Edit, and NotebookEdit tool calls in declaration order. The
    first check that returns a deny reason wins."""

    _rule_check_methods_to_run_in_order = (
        PreToolUseWriteRuleChecks.check_no_memory_access_for_write_or_edit_or_notebook_edit,
    )

    @staticmethod
    def main():

        """Reads the payload, runs every applicable rule check, denies on the first violation, otherwise passes through."""
        pretooluse_payload = _lib.PreToolUseHookIo.read_pretooluse_payload_from_stdin()
        for rule_check_method in PreToolUseWriteHookEntry._rule_check_methods_to_run_in_order:
            deny_reason_or_none = rule_check_method(pretooluse_payload)
            if deny_reason_or_none is not None:
                _lib.PreToolUseHookIo.emit_deny_decision_and_exit(deny_reason_or_none)
        _lib.PreToolUseHookIo.emit_passthrough_and_exit()


if __name__ == "__main__":
    PreToolUseWriteHookEntry.main()
