########################################################################################################################
# tests/bash_playbook/test_rule_checks.py
#
# tests requiring filesystem fixtures or testing non-command logic that cannot be expressed in command_tests.json
########################################################################################################################


import json
import os
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "hooks"))

import tests._common.fixtures
import tests._common.subprocess_helpers
import bash_playbook.pretooluse_bash
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
        result = bash_playbook.pretooluse_bash.RequireGitMvForTrackedMovesCheck.check(payload)
        self.assertIsNotNone(result)
        self.assertIn("tracked-example.txt", result)


    def test_blocks_mv_of_tracked_directory(self):

        payload = tests._common.fixtures.PreToolUsePayloadFixtureBuilder.build_bash_payload(
            bash_command_string = "mv tracked-dir new-dir",
            working_directory = self.git_repo_temp_directory
        )
        result = bash_playbook.pretooluse_bash.RequireGitMvForTrackedMovesCheck.check(payload)
        self.assertIsNotNone(result)
        self.assertIn("tracked-dir", result)


    def test_passes_mv_of_untracked_source(self):

        payload = tests._common.fixtures.PreToolUsePayloadFixtureBuilder.build_bash_payload(
            bash_command_string = "mv untracked-example.txt renamed.txt",
            working_directory = self.git_repo_temp_directory
        )
        result = bash_playbook.pretooluse_bash.RequireGitMvForTrackedMovesCheck.check(payload)
        self.assertIsNone(result)


    def test_passes_non_mv_command(self):

        payload = tests._common.fixtures.PreToolUsePayloadFixtureBuilder.build_bash_payload(
            bash_command_string = "echo tracked-example.txt",
            working_directory = self.git_repo_temp_directory
        )
        result = bash_playbook.pretooluse_bash.RequireGitMvForTrackedMovesCheck.check(payload)
        self.assertIsNone(result)


    def test_skips_flag_arguments_when_locating_sources(self):

        payload = tests._common.fixtures.PreToolUsePayloadFixtureBuilder.build_bash_payload(
            bash_command_string = "mv -v tracked-example.txt renamed.txt",
            working_directory = self.git_repo_temp_directory
        )
        result = bash_playbook.pretooluse_bash.RequireGitMvForTrackedMovesCheck.check(payload)
        self.assertIsNotNone(result)


    def test_passes_on_malformed_quoting(self):

        payload = tests._common.fixtures.PreToolUsePayloadFixtureBuilder.build_bash_payload(
            bash_command_string = "mv \"broken"
        )
        result = bash_playbook.pretooluse_bash.RequireGitMvForTrackedMovesCheck.check(payload)
        self.assertIsNone(result)


    def test_blocks_mv_dash_t_of_tracked_file(self):

        payload = tests._common.fixtures.PreToolUsePayloadFixtureBuilder.build_bash_payload(
            bash_command_string = "mv -t /tmp/dest tracked-example.txt",
            working_directory = self.git_repo_temp_directory
        )
        result = bash_playbook.pretooluse_bash.RequireGitMvForTrackedMovesCheck.check(payload)
        self.assertIsNotNone(result)
        self.assertIn("tracked-example.txt", result)


    def test_blocks_mv_target_directory_equals_of_tracked_file(self):

        payload = tests._common.fixtures.PreToolUsePayloadFixtureBuilder.build_bash_payload(
            bash_command_string = "mv --target-directory=/tmp/dest tracked-example.txt",
            working_directory = self.git_repo_temp_directory
        )
        result = bash_playbook.pretooluse_bash.RequireGitMvForTrackedMovesCheck.check(payload)
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
                        entry_script_relative_path = "bash_playbook/pretooluse_bash.py",
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


class TestPlaybookMatchCheck(unittest.TestCase):

    def setUp(self):

        self.temp_project_directory = tempfile.mkdtemp()
        self.dot_ai_sanity_directory = os.path.join(self.temp_project_directory, ".ai-sanity")
        os.makedirs(self.dot_ai_sanity_directory)
        self.playbook_abs_path = os.path.join(self.dot_ai_sanity_directory, "playbook.json")
        self._write_playbook([
            {
                "bash": "python -m unittest discover -s tests -t . -v",
                "what": "Runs the full test suite",
                "when": "Run as a final step after all changes have landed"
            },
            {
                "bash": "python -m unittest *",
                "what": "Run targeted tests",
                "when": "After modifying a specific hook"
            }
        ])


    def _write_playbook(self, playbook_entries):

        with open(self.playbook_abs_path, "w", encoding = "utf-8") as open_playbook_file_handle:
            json.dump(playbook_entries, open_playbook_file_handle)


    def _build_bash_payload(self, command):

        return tests._common.fixtures.PreToolUsePayloadFixtureBuilder.build_bash_payload(
            bash_command_string = command,
            working_directory = self.temp_project_directory
        )

    ####################################################################################################################
    # EXACT MATCH


    def test_exact_match_returns_entry(self):

        result = bash_playbook.pretooluse_bash.PlaybookMatchCheck.check(
            self._build_bash_payload("python -m unittest discover -s tests -t . -v")
        )
        self.assertIsNotNone(result)
        self.assertEqual(result["bash"], "python -m unittest discover -s tests -t . -v")


    def test_non_matching_command_returns_none(self):

        result = bash_playbook.pretooluse_bash.PlaybookMatchCheck.check(
            self._build_bash_payload("ls -la")
        )
        self.assertIsNone(result)


    def test_exact_entry_rejects_extra_args(self):

        self._write_playbook([
            {"bash": "python -m unittest discover -s tests -t . -v", "what": "exact only", "when": "test"}
        ])
        result = bash_playbook.pretooluse_bash.PlaybookMatchCheck.check(
            self._build_bash_payload("python -m unittest discover -s tests -t . -v --extra")
        )
        self.assertIsNone(result)


    def test_extra_whitespace_still_matches(self):

        result = bash_playbook.pretooluse_bash.PlaybookMatchCheck.check(
            self._build_bash_payload("  python -m unittest discover -s tests -t . -v  ")
        )
        self.assertIsNotNone(result)


    def test_empty_command_returns_none(self):

        result = bash_playbook.pretooluse_bash.PlaybookMatchCheck.check(
            self._build_bash_payload("")
        )
        self.assertIsNone(result)


    def test_malformed_quoting_returns_none(self):

        result = bash_playbook.pretooluse_bash.PlaybookMatchCheck.check(
            self._build_bash_payload("python -m unittest \"broken")
        )
        self.assertIsNone(result)

    ####################################################################################################################
    # PREFIX WILDCARD


    def test_prefix_match_targeted_test(self):

        result = bash_playbook.pretooluse_bash.PlaybookMatchCheck.check(
            self._build_bash_payload("python -m unittest tests.playbook.test_rule_checks -v")
        )
        self.assertIsNotNone(result)
        self.assertEqual(result["bash"], "python -m unittest *")


    def test_prefix_match_bare_command(self):

        result = bash_playbook.pretooluse_bash.PlaybookMatchCheck.check(
            self._build_bash_payload("python -m unittest")
        )
        self.assertIsNotNone(result)
        self.assertEqual(result["bash"], "python -m unittest *")


    def test_prefix_no_partial_token_match(self):

        result = bash_playbook.pretooluse_bash.PlaybookMatchCheck.check(
            self._build_bash_payload("python -m unittesting")
        )
        self.assertIsNone(result)


    def test_exact_match_preferred_over_prefix_when_both_match(self):

        result = bash_playbook.pretooluse_bash.PlaybookMatchCheck.check(
            self._build_bash_payload("python -m unittest discover -s tests -t . -v")
        )
        self.assertIsNotNone(result)
        self.assertEqual(result["bash"], "python -m unittest discover -s tests -t . -v")

    ####################################################################################################################
    # COMMANDS WITH SEQUENTIAL OPERATORS


    def test_playbook_entry_with_and_then_operator_matches(self):

        self._write_playbook([
            {"bash": "cd server && pwsh ../local/server/scripts/tests/all.ps1", "what": "test", "when": "test"}
        ])
        result = bash_playbook.pretooluse_bash.PlaybookMatchCheck.check(
            self._build_bash_payload("cd server && pwsh ../local/server/scripts/tests/all.ps1")
        )
        self.assertIsNotNone(result)


    def test_playbook_entry_with_and_then_operator_prefix_matches(self):

        self._write_playbook([
            {"bash": "cd server && pwsh ../local/server/scripts/tests/pytest.ps1 *", "what": "test", "when": "test"}
        ])
        result = bash_playbook.pretooluse_bash.PlaybookMatchCheck.check(
            self._build_bash_payload("cd server && pwsh ../local/server/scripts/tests/pytest.ps1 tests/test_sub.py")
        )
        self.assertIsNotNone(result)


    def test_non_matching_command_after_operator_returns_none(self):

        self._write_playbook([
            {"bash": "cd server && pwsh ../local/server/scripts/tests/all.ps1", "what": "test", "when": "test"}
        ])
        result = bash_playbook.pretooluse_bash.PlaybookMatchCheck.check(
            self._build_bash_payload("cd server && rm -rf /")
        )
        self.assertIsNone(result)

    ####################################################################################################################
    # COMMANDS WITH PIPES AND REDIRECTS


    def test_prefix_with_pipe_tail_matches(self):

        result = bash_playbook.pretooluse_bash.PlaybookMatchCheck.check(
            self._build_bash_payload("python -m unittest tests.foo -v 2>&1 | tail -80")
        )
        self.assertIsNotNone(result)


    def test_prefix_with_redirect_matches(self):

        result = bash_playbook.pretooluse_bash.PlaybookMatchCheck.check(
            self._build_bash_payload("python -m unittest tests.foo > output.txt")
        )
        self.assertIsNotNone(result)

    ####################################################################################################################
    # PLAYBOOK FILE ERRORS


    def test_missing_playbook_returns_none(self):

        empty_temp_directory = tempfile.mkdtemp()
        payload = tests._common.fixtures.PreToolUsePayloadFixtureBuilder.build_bash_payload(
            bash_command_string = "python -m unittest discover -s tests -t . -v",
            working_directory = empty_temp_directory
        )
        result = bash_playbook.pretooluse_bash.PlaybookMatchCheck.check(payload)
        self.assertIsNone(result)


    def test_bad_json_playbook_returns_none(self):

        with open(self.playbook_abs_path, "w", encoding = "utf-8") as open_playbook_file_handle:
            open_playbook_file_handle.write("{not valid json")
        result = bash_playbook.pretooluse_bash.PlaybookMatchCheck.check(
            self._build_bash_payload("python -m unittest discover -s tests -t . -v")
        )
        self.assertIsNone(result)


    def test_playbook_with_wrong_shape_returns_none(self):

        with open(self.playbook_abs_path, "w", encoding = "utf-8") as open_playbook_file_handle:
            json.dump({"not": "a list"}, open_playbook_file_handle)
        result = bash_playbook.pretooluse_bash.PlaybookMatchCheck.check(
            self._build_bash_payload("python -m unittest discover -s tests -t . -v")
        )
        self.assertIsNone(result)


    def test_playbook_entry_missing_bash_field_is_skipped(self):

        self._write_playbook([
            {"what": "no bash field", "when": "never"}
        ])
        result = bash_playbook.pretooluse_bash.PlaybookMatchCheck.check(
            self._build_bash_payload("python -m unittest discover -s tests -t . -v")
        )
        self.assertIsNone(result)


class TestPlaybookProjectRootRelativeMatch(unittest.TestCase):

    def setUp(self):

        self.temp_project_directory = tempfile.mkdtemp()
        self.dot_ai_sanity_directory = os.path.join(self.temp_project_directory, ".ai-sanity")
        os.makedirs(self.dot_ai_sanity_directory)
        self.playbook_abs_path = os.path.join(self.dot_ai_sanity_directory, "playbook.json")
        self.scripts_directory = os.path.join(self.temp_project_directory, "server", "scripts", "tests")
        os.makedirs(self.scripts_directory)
        self.script_file_path = os.path.join(self.scripts_directory, "all-fast.sh")
        open(self.script_file_path, mode = "w").close()
        self._write_playbook([
            {
                "bash": "*/server/scripts/tests/all-fast.sh *",
                "what": "Run all tests",
                "when": "Final step"
            }
        ])


    def _write_playbook(self, playbook_entries):

        with open(self.playbook_abs_path, mode = "w", encoding = "utf-8") as open_playbook_file_handle:
            json.dump(
                obj = playbook_entries,
                fp = open_playbook_file_handle
            )


    def _build_bash_payload(self, command, working_directory = None):

        return tests._common.fixtures.PreToolUsePayloadFixtureBuilder.build_bash_payload(
            bash_command_string = command,
            working_directory = working_directory or self.temp_project_directory
        )


    def test_matches_relative_path_from_project_root(self):

        result = bash_playbook.pretooluse_bash.PlaybookMatchCheck.check(
            self._build_bash_payload("./server/scripts/tests/all-fast.sh")
        )
        self.assertIsNotNone(result)


    def test_matches_from_subdirectory_with_traversal(self):

        sub_directory = os.path.join(self.temp_project_directory, "server")
        result = bash_playbook.pretooluse_bash.PlaybookMatchCheck.check(
            self._build_bash_payload(
                "../server/scripts/tests/all-fast.sh",
                working_directory = sub_directory
            )
        )
        self.assertIsNotNone(result)


    def test_matches_absolute_command_path(self):

        result = bash_playbook.pretooluse_bash.PlaybookMatchCheck.check(
            self._build_bash_payload(self.script_file_path.replace("\\", "/"))
        )
        self.assertIsNotNone(result)


    def test_matches_with_extra_args_via_prefix(self):

        result = bash_playbook.pretooluse_bash.PlaybookMatchCheck.check(
            self._build_bash_payload("./server/scripts/tests/all-fast.sh --verbose --coverage")
        )
        self.assertIsNotNone(result)


    def test_no_match_for_different_script(self):

        other_script_path = os.path.join(self.scripts_directory, "other.sh")
        open(other_script_path, mode = "w").close()
        result = bash_playbook.pretooluse_bash.PlaybookMatchCheck.check(
            self._build_bash_payload("./server/scripts/tests/other.sh")
        )
        self.assertIsNone(result)


    def test_exact_match_rejects_extra_args(self):

        self._write_playbook([
            {"bash": "*/server/scripts/tests/all-fast.sh", "what": "exact only", "when": "test"}
        ])
        result = bash_playbook.pretooluse_bash.PlaybookMatchCheck.check(
            self._build_bash_payload("./server/scripts/tests/all-fast.sh --extra")
        )
        self.assertIsNone(result)


    def test_matches_from_deeply_nested_subdirectory(self):

        deep_directory = os.path.join(self.temp_project_directory, "server", "src", "components")
        os.makedirs(deep_directory, exist_ok = True)
        result = bash_playbook.pretooluse_bash.PlaybookMatchCheck.check(
            self._build_bash_payload(
                "../../../server/scripts/tests/all-fast.sh",
                working_directory = deep_directory
            )
        )
        self.assertIsNotNone(result)


    def test_matches_with_project_root_on_non_first_token(self):

        self._write_playbook([
            {"bash": "pwsh */server/scripts/tests/all-fast.ps1 *", "what": "pwsh test", "when": "test"}
        ])
        sub_directory = os.path.join(self.temp_project_directory, "server")
        result = bash_playbook.pretooluse_bash.PlaybookMatchCheck.check(
            self._build_bash_payload(
                "pwsh ../server/scripts/tests/all-fast.ps1 --verbose",
                working_directory = sub_directory
            )
        )
        self.assertIsNotNone(result)


    def test_non_first_token_no_match_for_wrong_command_prefix(self):

        self._write_playbook([
            {"bash": "pwsh */server/scripts/tests/all-fast.ps1 *", "what": "pwsh test", "when": "test"}
        ])
        result = bash_playbook.pretooluse_bash.PlaybookMatchCheck.check(
            self._build_bash_payload("bash ./server/scripts/tests/all-fast.ps1")
        )
        self.assertIsNone(result)


    def test_bare_star_slash_entry_is_skipped(self):

        self._write_playbook([
            {"bash": "*/ *", "what": "empty path", "when": "test"}
        ])
        result = bash_playbook.pretooluse_bash.PlaybookMatchCheck.check(
            self._build_bash_payload("./server/scripts/tests/all-fast.sh")
        )
        self.assertIsNone(result)


class TestTildePathCheck(unittest.TestCase):


    def _build_bash_payload(self, command):

        return tests._common.fixtures.PreToolUsePayloadFixtureBuilder.build_bash_payload(
            bash_command_string = command
        )


    @unittest.skipUnless(sys.platform == "win32", "tilde check only fires on Windows")
    def test_denies_tilde_path_on_windows(self):

        result = bash_playbook.pretooluse_bash.TildePathCheck.check(
            self._build_bash_payload("cd ~/Dev/infinite-art/server/app")
        )
        self.assertIsNotNone(result)
        self.assertIn("tilde", result.lower())


    @unittest.skipUnless(sys.platform == "win32", "tilde check only fires on Windows")
    def test_denies_tilde_in_compound_command_on_windows(self):

        result = bash_playbook.pretooluse_bash.TildePathCheck.check(
            self._build_bash_payload("cd ~/Dev/project && pwsh ../../scripts/test.ps1")
        )
        self.assertIsNotNone(result)


    @unittest.skipUnless(sys.platform == "win32", "tilde check only fires on Windows")
    def test_denies_tilde_as_script_argument_on_windows(self):

        result = bash_playbook.pretooluse_bash.TildePathCheck.check(
            self._build_bash_payload("pwsh ~/Dev/infinite-art/server/scripts/tests/all-fast.ps1")
        )
        self.assertIsNotNone(result)


    @unittest.skipUnless(sys.platform != "win32", "tilde is valid on non-Windows platforms")
    def test_allows_tilde_path_on_non_windows(self):

        result = bash_playbook.pretooluse_bash.TildePathCheck.check(
            self._build_bash_payload("cd ~/Dev/infinite-art/server/app")
        )
        self.assertIsNone(result)


    def test_allows_command_without_tilde(self):

        result = bash_playbook.pretooluse_bash.TildePathCheck.check(
            self._build_bash_payload("cd /home/user/Dev/project")
        )
        self.assertIsNone(result)


    def test_allows_empty_command(self):

        result = bash_playbook.pretooluse_bash.TildePathCheck.check(
            self._build_bash_payload("")
        )
        self.assertIsNone(result)


class TestGitCommandsCheck(unittest.TestCase):

    def test_denied_subcommand_returns_deny_message(self):

        clauses = [["git", "push", "origin", "main"]]
        result = bash_playbook.pretooluse_bash.GitCommandsCheck.check(clauses)
        self.assertIsInstance(result, str)
        self.assertIn("write commands", result)


    def test_denied_subcommand_message_includes_format_guidance(self):

        clauses = [["git", "commit", "-m", "msg"]]
        result = bash_playbook.pretooluse_bash.GitCommandsCheck.check(clauses)
        self.assertIn("git <subcommand>", result)


    def test_global_flag_returns_global_flags_message(self):

        clauses = [["git", "-C", "/tmp", "mv", "a.txt", "b.txt"]]
        result = bash_playbook.pretooluse_bash.GitCommandsCheck.check(clauses)
        self.assertIsInstance(result, str)
        self.assertIn("global flags", result.lower())


    def test_global_flag_dash_c_returns_global_flags_message(self):

        clauses = [["git", "-c", "user.name=test", "commit", "-m", "msg"]]
        result = bash_playbook.pretooluse_bash.GitCommandsCheck.check(clauses)
        self.assertIn("global flags", result.lower())


    def test_global_flag_git_dir_returns_global_flags_message(self):

        clauses = [["git", "--git-dir=/tmp/.git", "push", "origin", "main"]]
        result = bash_playbook.pretooluse_bash.GitCommandsCheck.check(clauses)
        self.assertIn("global flags", result.lower())


    def test_allowed_read_command_returns_true(self):

        clauses = [["git", "status"]]
        result = bash_playbook.pretooluse_bash.GitCommandsCheck.check(clauses)
        self.assertTrue(result)


    def test_git_mv_is_allowed(self):

        clauses = [["git", "mv", "a.txt", "b.txt"]]
        result = bash_playbook.pretooluse_bash.GitCommandsCheck.check(clauses)
        self.assertTrue(result)


class TestFindPlaybookAbsPath(unittest.TestCase):

    def test_finds_playbook_in_current_directory(self):

        temp_project_directory = tempfile.mkdtemp()
        dot_ai_sanity_directory = os.path.join(temp_project_directory, ".ai-sanity")
        os.makedirs(dot_ai_sanity_directory)
        playbook_abs_path = os.path.join(dot_ai_sanity_directory, "playbook.json")
        with open(playbook_abs_path, "w") as open_file_handle:
            open_file_handle.write("[]")
        result = bash_playbook.pretooluse_bash.PlaybookMatchCheck.find_playbook_abs_path(temp_project_directory)
        self.assertEqual(result, playbook_abs_path)


    def test_finds_playbook_in_parent_directory(self):

        temp_project_directory = tempfile.mkdtemp()
        dot_ai_sanity_directory = os.path.join(temp_project_directory, ".ai-sanity")
        os.makedirs(dot_ai_sanity_directory)
        playbook_abs_path = os.path.join(dot_ai_sanity_directory, "playbook.json")
        with open(playbook_abs_path, "w") as open_file_handle:
            open_file_handle.write("[]")
        child_directory = os.path.join(temp_project_directory, "src", "hooks")
        os.makedirs(child_directory)
        result = bash_playbook.pretooluse_bash.PlaybookMatchCheck.find_playbook_abs_path(child_directory)
        self.assertEqual(result, playbook_abs_path)


    def test_returns_none_when_no_playbook_exists(self):

        temp_directory = tempfile.mkdtemp()
        result = bash_playbook.pretooluse_bash.PlaybookMatchCheck.find_playbook_abs_path(temp_directory)
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
