########################################################################################################################
# ~/.claude/hooks/tests/test_entry_subprocesses.py
#
# Subprocess integration tests for pretooluse_*.py entry scripts
########################################################################################################################
import json
import os
import subprocess
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import tests.fixtures


HOOKS_DIRECTORY_ABSOLUTE_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PYTHON_INTERPRETER_FOR_TESTS = os.environ.get("HOOK_TEST_PYTHON_INTERPRETER", sys.executable)


class HookEntryScriptInvocationHelper:

    """Subprocess wrapper around the three pretooluse_*.py entry scripts. Centralises stdin piping, stdout JSON parsing,
    and exit code capture so test bodies stay focused on the assertion."""

    @staticmethod
    def invoke_entry_script(entry_script_filename, pretooluse_payload):

        """Runs the named entry script with the payload piped to stdin and returns (exit_code, parsed_stdout_or_None).
        parsed_stdout is None when the script emitted no stdout, which is the passthrough signal; the payload is
        serialised with ensure_ascii=False and piped as raw UTF-8 bytes to match the wire format Claude Code uses."""
        entry_script_absolute_path = os.path.join(HOOKS_DIRECTORY_ABSOLUTE_PATH, entry_script_filename)
        payload_utf8_bytes = json.dumps(pretooluse_payload, ensure_ascii = False).encode("utf-8")
        completed_subprocess = subprocess.run(
            [PYTHON_INTERPRETER_FOR_TESTS, entry_script_absolute_path],
            input = payload_utf8_bytes,
            capture_output = True,
            timeout = 10
        )
        stdout_text = completed_subprocess.stdout.decode("utf-8")
        parsed_stdout_or_none = json.loads(stdout_text) if stdout_text.strip() else None
        return completed_subprocess.returncode, parsed_stdout_or_none

    @staticmethod
    def assert_deny_decision(testcase, exit_code, parsed_stdout, expected_message_substring = ""):

        """Asserts that the script emitted a deny decision (exit 0 with hookSpecificOutput on stdout) and optionally
        that the deny reason contains the given substring."""
        testcase.assertEqual(exit_code, 0)
        testcase.assertIsNotNone(parsed_stdout)
        permission_decision_value = parsed_stdout["hookSpecificOutput"]["permissionDecision"]
        testcase.assertEqual(permission_decision_value, "deny")
        if expected_message_substring:
            permission_decision_reason_value = parsed_stdout["hookSpecificOutput"]["permissionDecisionReason"]
            testcase.assertIn(expected_message_substring, permission_decision_reason_value)

    @staticmethod
    def assert_passthrough(testcase, exit_code, parsed_stdout):

        """Asserts that the script emitted a passthrough (exit 0 with no stdout)."""
        testcase.assertEqual(exit_code, 0)
        testcase.assertIsNone(parsed_stdout)


class TestPreToolUseWriteEntryScript(unittest.TestCase):

    def test_em_dash_in_write_content_is_denied(self):

        exit_code, parsed_stdout = HookEntryScriptInvocationHelper.invoke_entry_script(
            entry_script_filename = "pretooluse_write.py",
            pretooluse_payload = tests.fixtures.PreToolUsePayloadFixtureBuilder.build_write_payload(
                file_content = "hello \u2014 world"
            )
        )
        HookEntryScriptInvocationHelper.assert_deny_decision(self, exit_code, parsed_stdout, "Em dash")

    def test_em_dash_as_raw_utf8_bytes_is_denied_windows_cp1252_regression(self):

        """Regression guard for the Windows cp1252 stdin bug: asserts the payload bytes really contain the three-byte
        UTF-8 em dash sequence (not the ASCII-escaped form that silently sidesteps the mojibake) before verifying the
        hook denies."""
        em_dash_utf8_bytes = bytes([0xe2, 0x80, 0x94])
        em_dash_character = em_dash_utf8_bytes.decode("utf-8")
        pretooluse_payload = tests.fixtures.PreToolUsePayloadFixtureBuilder.build_write_payload(
            file_content = f"hello {em_dash_character} world"
        )
        payload_utf8_bytes = json.dumps(pretooluse_payload, ensure_ascii = False).encode("utf-8")
        self.assertIn(em_dash_utf8_bytes, payload_utf8_bytes)
        exit_code, parsed_stdout = HookEntryScriptInvocationHelper.invoke_entry_script(
            entry_script_filename = "pretooluse_write.py",
            pretooluse_payload = pretooluse_payload
        )
        HookEntryScriptInvocationHelper.assert_deny_decision(self, exit_code, parsed_stdout, "Em dash")

    def test_plain_hyphen_in_write_content_passes(self):

        exit_code, parsed_stdout = HookEntryScriptInvocationHelper.invoke_entry_script(
            entry_script_filename = "pretooluse_write.py",
            pretooluse_payload = tests.fixtures.PreToolUsePayloadFixtureBuilder.build_write_payload(
                file_content = "hello - world"
            )
        )
        HookEntryScriptInvocationHelper.assert_passthrough(self, exit_code, parsed_stdout)

    def test_write_inside_auto_memory_directory_is_denied(self):

        exit_code, parsed_stdout = HookEntryScriptInvocationHelper.invoke_entry_script(
            entry_script_filename = "pretooluse_write.py",
            pretooluse_payload = tests.fixtures.PreToolUsePayloadFixtureBuilder.build_write_payload(
                file_content = "ok",
                file_path = "/c/Users/zachm/.claude/projects/abc/memory/example.md"
            )
        )
        HookEntryScriptInvocationHelper.assert_deny_decision(self, exit_code, parsed_stdout, "auto-memory")

    def test_write_with_memory_md_substring_in_content_passes(self):

        exit_code, parsed_stdout = HookEntryScriptInvocationHelper.invoke_entry_script(
            entry_script_filename = "pretooluse_write.py",
            pretooluse_payload = tests.fixtures.PreToolUsePayloadFixtureBuilder.build_write_payload(
                file_content = "this is a doc that talks about MEMORY.md as a deprecated concept",
                file_path = "/tmp/example.md"
            )
        )
        HookEntryScriptInvocationHelper.assert_passthrough(self, exit_code, parsed_stdout)


class TestPreToolUseBashEntryScript(unittest.TestCase):

    def test_npm_install_passes_through_to_settings_json(self):

        exit_code, parsed_stdout = HookEntryScriptInvocationHelper.invoke_entry_script(
            entry_script_filename = "pretooluse_bash.py",
            pretooluse_payload = tests.fixtures.PreToolUsePayloadFixtureBuilder.build_bash_payload(
                bash_command_string = "npm install lodash"
            )
        )
        HookEntryScriptInvocationHelper.assert_passthrough(self, exit_code, parsed_stdout)

    def test_python_dash_m_pip_install_passes_through_to_settings_json(self):

        exit_code, parsed_stdout = HookEntryScriptInvocationHelper.invoke_entry_script(
            entry_script_filename = "pretooluse_bash.py",
            pretooluse_payload = tests.fixtures.PreToolUsePayloadFixtureBuilder.build_bash_payload(
                bash_command_string = "python -m pip install requests"
            )
        )
        HookEntryScriptInvocationHelper.assert_passthrough(self, exit_code, parsed_stdout)

    def test_uv_pip_list_passes(self):

        exit_code, parsed_stdout = HookEntryScriptInvocationHelper.invoke_entry_script(
            entry_script_filename = "pretooluse_bash.py",
            pretooluse_payload = tests.fixtures.PreToolUsePayloadFixtureBuilder.build_bash_payload(
                bash_command_string = "uv pip list"
            )
        )
        HookEntryScriptInvocationHelper.assert_passthrough(self, exit_code, parsed_stdout)

    def test_git_log_passes(self):

        exit_code, parsed_stdout = HookEntryScriptInvocationHelper.invoke_entry_script(
            entry_script_filename = "pretooluse_bash.py",
            pretooluse_payload = tests.fixtures.PreToolUsePayloadFixtureBuilder.build_bash_payload(
                bash_command_string = "git log"
            )
        )
        HookEntryScriptInvocationHelper.assert_passthrough(self, exit_code, parsed_stdout)

    def test_git_clone_passes_through_to_settings_json(self):

        exit_code, parsed_stdout = HookEntryScriptInvocationHelper.invoke_entry_script(
            entry_script_filename = "pretooluse_bash.py",
            pretooluse_payload = tests.fixtures.PreToolUsePayloadFixtureBuilder.build_bash_payload(
                bash_command_string = "git clone https://example.com/repo.git"
            )
        )
        HookEntryScriptInvocationHelper.assert_passthrough(self, exit_code, parsed_stdout)


class TestPreToolUseReadEntryScript(unittest.TestCase):

    def test_read_of_memory_md_is_denied(self):

        exit_code, parsed_stdout = HookEntryScriptInvocationHelper.invoke_entry_script(
            entry_script_filename = "pretooluse_read.py",
            pretooluse_payload = tests.fixtures.PreToolUsePayloadFixtureBuilder.build_read_payload(
                file_path = "/some/dir/MEMORY.md"
            )
        )
        HookEntryScriptInvocationHelper.assert_deny_decision(self, exit_code, parsed_stdout)

    def test_read_of_normal_file_passes(self):

        exit_code, parsed_stdout = HookEntryScriptInvocationHelper.invoke_entry_script(
            entry_script_filename = "pretooluse_read.py",
            pretooluse_payload = tests.fixtures.PreToolUsePayloadFixtureBuilder.build_read_payload(
                file_path = "/tmp/example.txt"
            )
        )
        HookEntryScriptInvocationHelper.assert_passthrough(self, exit_code, parsed_stdout)

    def test_grep_for_memory_md_pattern_in_normal_path_passes(self):

        exit_code, parsed_stdout = HookEntryScriptInvocationHelper.invoke_entry_script(
            entry_script_filename = "pretooluse_read.py",
            pretooluse_payload = tests.fixtures.PreToolUsePayloadFixtureBuilder.build_grep_payload(
                grep_pattern = "MEMORY.md",
                grep_path = "/tmp/some-project"
            )
        )
        HookEntryScriptInvocationHelper.assert_passthrough(self, exit_code, parsed_stdout)


if __name__ == "__main__":
    unittest.main()