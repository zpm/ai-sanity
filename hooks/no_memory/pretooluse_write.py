########################################################################################################################
# hooks/no_memory/pretooluse_write.py
#
# no-memory write pre-tool hook
########################################################################################################################


import os
import sys

# hot patch so that imports work when script is invoked directly (how claude invokes hooks)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import _common._hook_io
import no_memory._checker


MEMORY_PATH_CHECKER = no_memory._checker.MemoryPathChecker


class PreToolUseWriteRuleChecks:

    """Rule checks that apply only to the Write, Edit, and NotebookEdit matcher. Each method takes the full PreToolUse
    payload dict and returns either a string deny-reason on violation or None to pass."""


    @staticmethod
    def check_no_memory_access_for_write_or_edit_or_notebook_edit(pretooluse_payload):

        """Extracts the file_path or notebook_path field appropriate to the tool and asks the shared memory path
        checker whether the path is in the auto-memory area. Per-matcher extraction avoids overblocking legitimate
        writes that happen to contain the literal string 'MEMORY.md' inside their content payload."""
        write_like_tool_name = pretooluse_payload.get("tool_name", "")
        tool_input_dict = pretooluse_payload.get("tool_input") or {}
        if write_like_tool_name == "NotebookEdit":
            return MEMORY_PATH_CHECKER.assert_paths_are_not_memory_locations(tool_input_dict.get("notebook_path"))
        return MEMORY_PATH_CHECKER.assert_paths_are_not_memory_locations(tool_input_dict.get("file_path"))


class PreToolUseWriteHookEntry:

    """Composes every rule check that applies to Write, Edit, and NotebookEdit tool calls in declaration order. The
    first check that returns a deny reason wins."""

    _rule_check_methods_to_run_in_order = (
        PreToolUseWriteRuleChecks.check_no_memory_access_for_write_or_edit_or_notebook_edit,
    )


    @staticmethod
    def main():

        """Reads the payload, runs every applicable rule check, denies on the first violation, otherwise passes
        through."""
        try:
            pretooluse_payload = _common._hook_io.PreToolUseHookIo.read_pretooluse_payload_from_stdin()
            for rule_check_method in PreToolUseWriteHookEntry._rule_check_methods_to_run_in_order:
                deny_reason_or_none = rule_check_method(pretooluse_payload)
                if deny_reason_or_none is not None:
                    _common._hook_io.PreToolUseHookIo.emit_deny_decision_and_exit(deny_reason_or_none)
            _common._hook_io.PreToolUseHookIo.emit_passthrough_and_exit()
        except Exception as e:
            _common._hook_io.PreToolUseHookIo.emit_deny_decision_and_exit(f"no_memory/pretooluse_write hook crashed: {e}")


if __name__ == "__main__":
    PreToolUseWriteHookEntry.main()
