########################################################################################################################
# tests/bash_safety/test_rule_checks.py
#
# tests requiring filesystem fixtures or testing non-command logic that cannot be expressed in command_tests.json
########################################################################################################################


import os
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "hooks"))

import tests._common.fixtures
import bash_safety.pretooluse_bash
import _common._command_parser


class TestRequireGitMvForTrackedMovesCheck(unittest.TestCase):

    def setUp(self):

        self.git_repo_temp_directory = tempfile.mkdtemp()
        subprocess.run(
            ["git", "init", "-q"],
            cwd = self.git_repo_temp_directory,
            check = True
        )
        tracked_file_path = os.path.join(self.git_repo_temp_directory, "tracked-example.txt")
        open(tracked_file_path, "w").close()
        tracked_dir_path = os.path.join(self.git_repo_temp_directory, "tracked-dir")
        os.makedirs(tracked_dir_path)
        tracked_file_inside_dir_path = os.path.join(tracked_dir_path, "inside.txt")
        open(tracked_file_inside_dir_path, "w").close()
        subprocess.run(
            ["git", "add", "tracked-example.txt", "tracked-dir"],
            cwd = self.git_repo_temp_directory,
            check = True
        )
        subprocess.run(
            ["git", "-c", "user.email=test@test", "-c", "user.name=test", "commit", "-qm", "init"],
            cwd = self.git_repo_temp_directory,
            check = True
        )
        untracked_file_path = os.path.join(self.git_repo_temp_directory, "untracked-example.txt")
        open(untracked_file_path, "w").close()


    def test_blocks_mv_of_tracked_file(self):

        payload = tests._common.fixtures.PreToolUsePayloadFixtureBuilder.build_bash_payload(
            bash_command_string = "mv tracked-example.txt renamed.txt",
            working_directory = self.git_repo_temp_directory
        )
        result = bash_safety.pretooluse_bash.RequireGitMvForTrackedMovesCheck.check(payload)
        self.assertIsNotNone(result)
        self.assertIn("tracked-example.txt", result)


    def test_blocks_mv_of_tracked_directory(self):

        payload = tests._common.fixtures.PreToolUsePayloadFixtureBuilder.build_bash_payload(
            bash_command_string = "mv tracked-dir new-dir",
            working_directory = self.git_repo_temp_directory
        )
        result = bash_safety.pretooluse_bash.RequireGitMvForTrackedMovesCheck.check(payload)
        self.assertIsNotNone(result)
        self.assertIn("tracked-dir", result)


    def test_passes_mv_of_untracked_source(self):

        payload = tests._common.fixtures.PreToolUsePayloadFixtureBuilder.build_bash_payload(
            bash_command_string = "mv untracked-example.txt renamed.txt",
            working_directory = self.git_repo_temp_directory
        )
        result = bash_safety.pretooluse_bash.RequireGitMvForTrackedMovesCheck.check(payload)
        self.assertIsNone(result)


    def test_passes_non_mv_command(self):

        payload = tests._common.fixtures.PreToolUsePayloadFixtureBuilder.build_bash_payload(
            bash_command_string = "echo tracked-example.txt",
            working_directory = self.git_repo_temp_directory
        )
        result = bash_safety.pretooluse_bash.RequireGitMvForTrackedMovesCheck.check(payload)
        self.assertIsNone(result)


    def test_skips_flag_arguments_when_locating_sources(self):

        payload = tests._common.fixtures.PreToolUsePayloadFixtureBuilder.build_bash_payload(
            bash_command_string = "mv -v tracked-example.txt renamed.txt",
            working_directory = self.git_repo_temp_directory
        )
        result = bash_safety.pretooluse_bash.RequireGitMvForTrackedMovesCheck.check(payload)
        self.assertIsNotNone(result)


    def test_passes_on_malformed_quoting(self):

        payload = tests._common.fixtures.PreToolUsePayloadFixtureBuilder.build_bash_payload(
            bash_command_string = "mv \"broken"
        )
        result = bash_safety.pretooluse_bash.RequireGitMvForTrackedMovesCheck.check(payload)
        self.assertIsNone(result)


    def test_blocks_mv_dash_t_of_tracked_file(self):

        payload = tests._common.fixtures.PreToolUsePayloadFixtureBuilder.build_bash_payload(
            bash_command_string = "mv -t /tmp/dest tracked-example.txt",
            working_directory = self.git_repo_temp_directory
        )
        result = bash_safety.pretooluse_bash.RequireGitMvForTrackedMovesCheck.check(payload)
        self.assertIsNotNone(result)
        self.assertIn("tracked-example.txt", result)


    def test_blocks_mv_target_directory_equals_of_tracked_file(self):

        payload = tests._common.fixtures.PreToolUsePayloadFixtureBuilder.build_bash_payload(
            bash_command_string = "mv --target-directory=/tmp/dest tracked-example.txt",
            working_directory = self.git_repo_temp_directory
        )
        result = bash_safety.pretooluse_bash.RequireGitMvForTrackedMovesCheck.check(payload)
        self.assertIsNotNone(result)
        self.assertIn("tracked-example.txt", result)


class TestMalformedInputPassthrough(unittest.TestCase):

    """Verifies that malformed or empty commands pass through gracefully instead of crashing or denying. These are not
    valid commands so they live here instead of in command_tests.json."""

    _MALFORMED_COMMANDS = (
        "",
        "git commit -m \"broken",
        "mv \"broken",
        "pip install \"broken",
    )


    def test_malformed_commands_pass_through(self):

        for bash_command_string in self._MALFORMED_COMMANDS:
            with self.subTest(command = bash_command_string):
                exit_code, parsed_stdout = (
                    tests._common.subprocess_helpers.HookEntryScriptInvocationHelper.invoke_entry_script(
                        entry_script_relative_path = "bash_safety/pretooluse_bash.py",
                        pretooluse_payload = tests._common.fixtures.PreToolUsePayloadFixtureBuilder.build_bash_payload(
                            bash_command_string = bash_command_string
                        )
                    )
                )
                tests._common.subprocess_helpers.HookEntryScriptInvocationHelper.assert_passthrough(
                    self, exit_code, parsed_stdout
                )


class TestBashCommandParserClausesAndSeparators(unittest.TestCase):

    def test_single_command_returns_empty_separators(self):

        clauses, separators = (
            _common._command_parser.BashCommandParser.extract_command_clauses_and_separators("python -m unittest")
        )
        self.assertEqual(clauses, [["python", "-m", "unittest"]])
        self.assertEqual(separators, [])


    def test_pipe_returns_pipe_separator(self):

        clauses, separators = (
            _common._command_parser.BashCommandParser.extract_command_clauses_and_separators(
                "python -m unittest | tail"
            )
        )
        self.assertEqual(clauses, [["python", "-m", "unittest"], ["tail"]])
        self.assertEqual(separators, ["|"])


    def test_and_then_returns_and_separator(self):

        clauses, separators = (
            _common._command_parser.BashCommandParser.extract_command_clauses_and_separators(
                "python -m unittest && echo done"
            )
        )
        self.assertEqual(clauses, [["python", "-m", "unittest"], ["echo", "done"]])
        self.assertEqual(separators, ["&&"])


    def test_mixed_operators_returns_all_separators(self):

        clauses, separators = (
            _common._command_parser.BashCommandParser.extract_command_clauses_and_separators(
                "python -m unittest | tail && echo"
            )
        )
        self.assertEqual(clauses, [["python", "-m", "unittest"], ["tail"], ["echo"]])
        self.assertEqual(separators, ["|", "&&"])


    def test_semicolon_returns_semicolon_separator(self):

        clauses, separators = (
            _common._command_parser.BashCommandParser.extract_command_clauses_and_separators("a ; b")
        )
        self.assertEqual(clauses, [["a"], ["b"]])
        self.assertEqual(separators, [";"])


    def test_or_else_returns_or_separator(self):

        clauses, separators = (
            _common._command_parser.BashCommandParser.extract_command_clauses_and_separators("a || b")
        )
        self.assertEqual(clauses, [["a"], ["b"]])
        self.assertEqual(separators, ["||"])


    def test_empty_command_returns_empty(self):

        clauses, separators = (
            _common._command_parser.BashCommandParser.extract_command_clauses_and_separators("")
        )
        self.assertEqual(clauses, [])
        self.assertEqual(separators, [])


    def test_malformed_quoting_returns_empty(self):

        clauses, separators = (
            _common._command_parser.BashCommandParser.extract_command_clauses_and_separators("echo \"broken")
        )
        self.assertEqual(clauses, [])
        self.assertEqual(separators, [])


if __name__ == "__main__":
    unittest.main()
