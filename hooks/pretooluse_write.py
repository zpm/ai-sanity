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

    _content_field_name_by_write_like_tool_name = {
        "Write": "content",
        "Edit": "new_string",
        "NotebookEdit": "new_source"
    }

    @staticmethod
    def check_no_em_or_en_dash_in_write_or_edit_content(pretooluse_payload):

        """Rejects Write/Edit/NotebookEdit payloads whose new content contains a U+2014 em dash or U+2013 en dash. The
        rule comes from CLAUDE.md ('Never use em dashes in code, comments, docs, or strings'); this check expands that
        to en dashes per the user's clarification on the spirit of the rule."""
        write_like_tool_name = pretooluse_payload.get("tool_name", "")
        rule_check_class = PreToolUseWriteRuleChecks
        content_field_name = rule_check_class._content_field_name_by_write_like_tool_name.get(write_like_tool_name)
        if content_field_name is None:
            return None
        new_content_string = (pretooluse_payload.get("tool_input") or {}).get(content_field_name) or ""
        if "\u2014" in new_content_string:
            return (
                "Em dash found in content. CLAUDE.md forbids em and en dashes in code, comments, docs, and strings."
                " Use a regular hyphen (-) instead."
            )
        if "\u2013" in new_content_string:
            return (
                "En dash found in content. CLAUDE.md forbids em and en dashes in code, comments, docs, and strings."
                " Use a regular hyphen (-) instead."
            )
        return None

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
        PreToolUseWriteRuleChecks.check_no_em_or_en_dash_in_write_or_edit_content,
        PreToolUseWriteRuleChecks.check_no_memory_access_for_write_or_edit_or_notebook_edit
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