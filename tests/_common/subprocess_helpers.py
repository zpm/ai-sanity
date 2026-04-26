import json
import os
import subprocess
import sys


HOOKS_DIRECTORY_ABSOLUTE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "hooks")
PYTHON_INTERPRETER_FOR_TESTS = os.environ.get("HOOK_TEST_PYTHON_INTERPRETER", sys.executable)


class HookEntryScriptInvocationHelper:

    """Subprocess wrapper around hook entry scripts. Centralises stdin piping, stdout JSON parsing, and exit code
    capture so test bodies stay focused on the assertion."""

    @staticmethod
    def invoke_entry_script(entry_script_relative_path, pretooluse_payload):

        """Runs the named entry script with the payload piped to stdin and returns (exit_code, parsed_stdout_or_None).
        parsed_stdout is None when the script emitted no stdout, which is the passthrough signal; the payload is
        serialised with ensure_ascii=False and piped as raw UTF-8 bytes to match the wire format Claude Code uses.
        The entry_script_relative_path is relative to the hooks root directory."""
        entry_script_absolute_path = os.path.join(HOOKS_DIRECTORY_ABSOLUTE_PATH, entry_script_relative_path)
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
    def assert_allow_decision(testcase, exit_code, parsed_stdout):

        """Asserts that the script emitted an allow decision (exit 0 with hookSpecificOutput on stdout)."""
        testcase.assertEqual(exit_code, 0)
        testcase.assertIsNotNone(parsed_stdout)
        permission_decision_value = parsed_stdout["hookSpecificOutput"]["permissionDecision"]
        testcase.assertEqual(permission_decision_value, "allow")

    @staticmethod
    def assert_passthrough(testcase, exit_code, parsed_stdout):

        """Asserts that the script emitted a passthrough (exit 0 with no stdout)."""
        testcase.assertEqual(exit_code, 0)
        testcase.assertIsNone(parsed_stdout)
