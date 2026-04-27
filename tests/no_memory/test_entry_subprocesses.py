########################################################################################################################
# tests/no_memory/test_entry_subprocesses.py
#
# no-memory entry-script subprocess tests
########################################################################################################################


import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "hooks"))

import tests._common.fixtures
import tests._common.subprocess_helpers


HOOK_ENTRY_SCRIPT_INVOCATION_HELPER = tests._common.subprocess_helpers.HookEntryScriptInvocationHelper


class TestPreToolUseWriteEntryScript(unittest.TestCase):

    def test_write_inside_auto_memory_directory_is_denied(self):

        exit_code, parsed_stdout = HOOK_ENTRY_SCRIPT_INVOCATION_HELPER.invoke_entry_script(
            entry_script_relative_path = "no_memory/pretooluse_write.py",
            pretooluse_payload = tests._common.fixtures.PreToolUsePayloadFixtureBuilder.build_write_payload(
                file_content = "ok",
                file_path = "/c/Users/zachm/.claude/projects/abc/memory/example.md"
            )
        )
        HOOK_ENTRY_SCRIPT_INVOCATION_HELPER.assert_deny_decision(self, exit_code, parsed_stdout, "auto-memory")


    def test_write_with_memory_md_substring_in_content_passes(self):

        exit_code, parsed_stdout = HOOK_ENTRY_SCRIPT_INVOCATION_HELPER.invoke_entry_script(
            entry_script_relative_path = "no_memory/pretooluse_write.py",
            pretooluse_payload = tests._common.fixtures.PreToolUsePayloadFixtureBuilder.build_write_payload(
                file_content = "this is a doc that talks about MEMORY.md as a deprecated concept",
                file_path = "/tmp/example.md"
            )
        )
        HOOK_ENTRY_SCRIPT_INVOCATION_HELPER.assert_passthrough(self, exit_code, parsed_stdout)


class TestPreToolUseBashMemoryEntryScript(unittest.TestCase):

    def test_npm_install_passes_through_to_settings_json(self):

        exit_code, parsed_stdout = HOOK_ENTRY_SCRIPT_INVOCATION_HELPER.invoke_entry_script(
            entry_script_relative_path = "no_memory/pretooluse_bash.py",
            pretooluse_payload = tests._common.fixtures.PreToolUsePayloadFixtureBuilder.build_bash_payload(
                bash_command_string = "npm install lodash"
            )
        )
        HOOK_ENTRY_SCRIPT_INVOCATION_HELPER.assert_passthrough(self, exit_code, parsed_stdout)


    def test_python_dash_m_pip_install_passes_through_to_settings_json(self):

        exit_code, parsed_stdout = HOOK_ENTRY_SCRIPT_INVOCATION_HELPER.invoke_entry_script(
            entry_script_relative_path = "no_memory/pretooluse_bash.py",
            pretooluse_payload = tests._common.fixtures.PreToolUsePayloadFixtureBuilder.build_bash_payload(
                bash_command_string = "python -m pip install requests"
            )
        )
        HOOK_ENTRY_SCRIPT_INVOCATION_HELPER.assert_passthrough(self, exit_code, parsed_stdout)


    def test_uv_pip_list_passes(self):

        exit_code, parsed_stdout = HOOK_ENTRY_SCRIPT_INVOCATION_HELPER.invoke_entry_script(
            entry_script_relative_path = "no_memory/pretooluse_bash.py",
            pretooluse_payload = tests._common.fixtures.PreToolUsePayloadFixtureBuilder.build_bash_payload(
                bash_command_string = "uv pip list"
            )
        )
        HOOK_ENTRY_SCRIPT_INVOCATION_HELPER.assert_passthrough(self, exit_code, parsed_stdout)


    def test_git_log_passes(self):

        exit_code, parsed_stdout = HOOK_ENTRY_SCRIPT_INVOCATION_HELPER.invoke_entry_script(
            entry_script_relative_path = "no_memory/pretooluse_bash.py",
            pretooluse_payload = tests._common.fixtures.PreToolUsePayloadFixtureBuilder.build_bash_payload(
                bash_command_string = "git log"
            )
        )
        HOOK_ENTRY_SCRIPT_INVOCATION_HELPER.assert_passthrough(self, exit_code, parsed_stdout)


    def test_git_clone_passes_through_to_settings_json(self):

        exit_code, parsed_stdout = HOOK_ENTRY_SCRIPT_INVOCATION_HELPER.invoke_entry_script(
            entry_script_relative_path = "no_memory/pretooluse_bash.py",
            pretooluse_payload = tests._common.fixtures.PreToolUsePayloadFixtureBuilder.build_bash_payload(
                bash_command_string = "git clone https://example.com/repo.git"
            )
        )
        HOOK_ENTRY_SCRIPT_INVOCATION_HELPER.assert_passthrough(self, exit_code, parsed_stdout)


class TestPreToolUseReadEntryScript(unittest.TestCase):

    def test_read_of_memory_md_is_denied(self):

        exit_code, parsed_stdout = HOOK_ENTRY_SCRIPT_INVOCATION_HELPER.invoke_entry_script(
            entry_script_relative_path = "no_memory/pretooluse_read.py",
            pretooluse_payload = tests._common.fixtures.PreToolUsePayloadFixtureBuilder.build_read_payload(
                file_path = "/some/dir/MEMORY.md"
            )
        )
        HOOK_ENTRY_SCRIPT_INVOCATION_HELPER.assert_deny_decision(self, exit_code, parsed_stdout)


    def test_read_of_normal_file_passes(self):

        exit_code, parsed_stdout = HOOK_ENTRY_SCRIPT_INVOCATION_HELPER.invoke_entry_script(
            entry_script_relative_path = "no_memory/pretooluse_read.py",
            pretooluse_payload = tests._common.fixtures.PreToolUsePayloadFixtureBuilder.build_read_payload(
                file_path = "/tmp/example.txt"
            )
        )
        HOOK_ENTRY_SCRIPT_INVOCATION_HELPER.assert_passthrough(self, exit_code, parsed_stdout)


    def test_grep_for_memory_md_pattern_in_normal_path_passes(self):

        exit_code, parsed_stdout = HOOK_ENTRY_SCRIPT_INVOCATION_HELPER.invoke_entry_script(
            entry_script_relative_path = "no_memory/pretooluse_read.py",
            pretooluse_payload = tests._common.fixtures.PreToolUsePayloadFixtureBuilder.build_grep_payload(
                grep_pattern = "MEMORY.md",
                grep_path = "/tmp/some-project"
            )
        )
        HOOK_ENTRY_SCRIPT_INVOCATION_HELPER.assert_passthrough(self, exit_code, parsed_stdout)


class TestUnicodePayloadHandling(unittest.TestCase):

    def test_edit_payload_with_unicode_ellipsis_passes_through(self):

        exit_code, parsed_stdout = HOOK_ENTRY_SCRIPT_INVOCATION_HELPER.invoke_entry_script(
            entry_script_relative_path = "no_memory/pretooluse_write.py",
            pretooluse_payload = tests._common.fixtures.PreToolUsePayloadFixtureBuilder.build_edit_payload(
                new_string_content = "loading… please wait \U0001f680",
                file_path = "/tmp/example.py"
            )
        )
        HOOK_ENTRY_SCRIPT_INVOCATION_HELPER.assert_passthrough(self, exit_code, parsed_stdout)


    def test_write_payload_with_emoji_and_smart_quotes_passes_through(self):

        exit_code, parsed_stdout = HOOK_ENTRY_SCRIPT_INVOCATION_HELPER.invoke_entry_script(
            entry_script_relative_path = "no_memory/pretooluse_write.py",
            pretooluse_payload = tests._common.fixtures.PreToolUsePayloadFixtureBuilder.build_write_payload(
                file_content = "“Hello” — said the \U0001f60a developer",
                file_path = "/tmp/example.txt"
            )
        )
        HOOK_ENTRY_SCRIPT_INVOCATION_HELPER.assert_passthrough(self, exit_code, parsed_stdout)


    def test_bash_payload_with_unicode_in_command_passes_through(self):

        exit_code, parsed_stdout = HOOK_ENTRY_SCRIPT_INVOCATION_HELPER.invoke_entry_script(
            entry_script_relative_path = "no_memory/pretooluse_bash.py",
            pretooluse_payload = tests._common.fixtures.PreToolUsePayloadFixtureBuilder.build_bash_payload(
                bash_command_string = "echo '…   \U0001f680'"
            )
        )
        HOOK_ENTRY_SCRIPT_INVOCATION_HELPER.assert_passthrough(self, exit_code, parsed_stdout)


    def test_read_payload_with_unicode_in_path_passes_through(self):

        exit_code, parsed_stdout = HOOK_ENTRY_SCRIPT_INVOCATION_HELPER.invoke_entry_script(
            entry_script_relative_path = "no_memory/pretooluse_read.py",
            pretooluse_payload = tests._common.fixtures.PreToolUsePayloadFixtureBuilder.build_read_payload(
                file_path = "/tmp/docs/café/notes.txt"
            )
        )
        HOOK_ENTRY_SCRIPT_INVOCATION_HELPER.assert_passthrough(self, exit_code, parsed_stdout)


    def test_git_safety_pretooluse_with_unicode_in_command_passes_through(self):

        exit_code, parsed_stdout = HOOK_ENTRY_SCRIPT_INVOCATION_HELPER.invoke_entry_script(
            entry_script_relative_path = "bash_safety/pretooluse_bash.py",
            pretooluse_payload = tests._common.fixtures.PreToolUsePayloadFixtureBuilder.build_bash_payload(
                bash_command_string = "python 'café \U0001f680'"
            )
        )
        HOOK_ENTRY_SCRIPT_INVOCATION_HELPER.assert_passthrough(self, exit_code, parsed_stdout)



HOOK_ENTRY_SCRIPT_INVOCATION_HELPER = tests._common.subprocess_helpers.HookEntryScriptInvocationHelper
if __name__ == "__main__":
    unittest.main()
