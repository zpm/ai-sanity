########################################################################################################################
# tests/playbook/test_rule_checks.py
#
# unit tests for playbook exact match check
########################################################################################################################


import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "hooks"))

import tests.fixtures
import playbook.pretooluse_bash


class TestPlaybookExactMatchCheck(unittest.TestCase):

    def setUp(self):

        self.temp_project_directory = tempfile.mkdtemp()
        self.dot_ai_sanity_directory = os.path.join(self.temp_project_directory, ".ai-sanity")
        os.makedirs(self.dot_ai_sanity_directory)
        self.playbook_abs_path = os.path.join(self.dot_ai_sanity_directory, "playbook.json")
        self._write_playbook([
            {
                "bash": "./test_hooks.sh",
                "what": "Runs repo tests on mac",
                "when": "Run as a final step after all changes have landed"
            },
            {
                "bash": "pwsh ./test_hooks.ps1",
                "what": "Runs repo tests on Windows",
                "when": "Run as a final step after all changes have landed"
            },
            {
                "bash": "./test_hooks.sh --verbose",
                "what": "Runs repo tests with verbose output",
                "when": "When debugging test failures"
            }
        ])

    def _write_playbook(self, playbook_entries):

        with open(self.playbook_abs_path, "w", encoding = "utf-8") as open_playbook_file_handle:
            json.dump(playbook_entries, open_playbook_file_handle)

    def _build_bash_payload(self, command):

        return tests.fixtures.PreToolUsePayloadFixtureBuilder.build_bash_payload(
            bash_command_string = command,
            working_directory = self.temp_project_directory
        )

    def test_exact_match_returns_entry(self):

        result = playbook.pretooluse_bash.PlaybookExactMatchCheck.check(
            self._build_bash_payload("./test_hooks.sh")
        )
        self.assertIsNotNone(result)
        self.assertEqual(result["bash"], "./test_hooks.sh")

    def test_second_entry_matches(self):

        result = playbook.pretooluse_bash.PlaybookExactMatchCheck.check(
            self._build_bash_payload("pwsh ./test_hooks.ps1")
        )
        self.assertIsNotNone(result)
        self.assertEqual(result["bash"], "pwsh ./test_hooks.ps1")

    def test_non_matching_command_returns_none(self):

        result = playbook.pretooluse_bash.PlaybookExactMatchCheck.check(
            self._build_bash_payload("ls -la")
        )
        self.assertIsNone(result)

    def test_multi_clause_and_rejects_even_if_first_matches(self):

        result = playbook.pretooluse_bash.PlaybookExactMatchCheck.check(
            self._build_bash_payload("./test_hooks.sh && rm -rf /")
        )
        self.assertIsNone(result)

    def test_multi_clause_semicolon_rejects(self):

        result = playbook.pretooluse_bash.PlaybookExactMatchCheck.check(
            self._build_bash_payload("./test_hooks.sh; rm -rf /")
        )
        self.assertIsNone(result)

    def test_multi_clause_pipe_rejects(self):

        result = playbook.pretooluse_bash.PlaybookExactMatchCheck.check(
            self._build_bash_payload("./test_hooks.sh | cat")
        )
        self.assertIsNone(result)

    def test_extra_whitespace_still_matches(self):

        result = playbook.pretooluse_bash.PlaybookExactMatchCheck.check(
            self._build_bash_payload("  ./test_hooks.sh  ")
        )
        self.assertIsNotNone(result)
        self.assertEqual(result["bash"], "./test_hooks.sh")

    def test_quoted_command_still_matches(self):

        result = playbook.pretooluse_bash.PlaybookExactMatchCheck.check(
            self._build_bash_payload("'./test_hooks.sh'")
        )
        self.assertIsNotNone(result)
        self.assertEqual(result["bash"], "./test_hooks.sh")

    def test_empty_command_returns_none(self):

        result = playbook.pretooluse_bash.PlaybookExactMatchCheck.check(
            self._build_bash_payload("")
        )
        self.assertIsNone(result)

    def test_malformed_quoting_returns_none(self):

        result = playbook.pretooluse_bash.PlaybookExactMatchCheck.check(
            self._build_bash_payload("./test_hooks.sh \"broken")
        )
        self.assertIsNone(result)

    def test_command_with_args_matches_entry_with_args(self):

        result = playbook.pretooluse_bash.PlaybookExactMatchCheck.check(
            self._build_bash_payload("./test_hooks.sh --verbose")
        )
        self.assertIsNotNone(result)
        self.assertEqual(result["bash"], "./test_hooks.sh --verbose")

    def test_command_with_args_does_not_match_bare_entry(self):

        result = playbook.pretooluse_bash.PlaybookExactMatchCheck.check(
            self._build_bash_payload("./test_hooks.sh --unexpected")
        )
        self.assertIsNone(result)

    def test_missing_playbook_returns_none(self):

        empty_temp_directory = tempfile.mkdtemp()
        payload = tests.fixtures.PreToolUsePayloadFixtureBuilder.build_bash_payload(
            bash_command_string = "./test_hooks.sh",
            working_directory = empty_temp_directory
        )
        result = playbook.pretooluse_bash.PlaybookExactMatchCheck.check(payload)
        self.assertIsNone(result)

    def test_bad_json_playbook_returns_none(self):

        with open(self.playbook_abs_path, "w", encoding = "utf-8") as open_playbook_file_handle:
            open_playbook_file_handle.write("{not valid json")
        result = playbook.pretooluse_bash.PlaybookExactMatchCheck.check(
            self._build_bash_payload("./test_hooks.sh")
        )
        self.assertIsNone(result)

    def test_playbook_with_wrong_shape_returns_none(self):

        with open(self.playbook_abs_path, "w", encoding = "utf-8") as open_playbook_file_handle:
            json.dump({"not": "a list"}, open_playbook_file_handle)
        result = playbook.pretooluse_bash.PlaybookExactMatchCheck.check(
            self._build_bash_payload("./test_hooks.sh")
        )
        self.assertIsNone(result)

    def test_playbook_entry_missing_bash_field_is_skipped(self):

        self._write_playbook([
            {"what": "no bash field", "when": "never"}
        ])
        result = playbook.pretooluse_bash.PlaybookExactMatchCheck.check(
            self._build_bash_payload("./test_hooks.sh")
        )
        self.assertIsNone(result)

    def test_no_space_semicolon_injection_rejects(self):

        result = playbook.pretooluse_bash.PlaybookExactMatchCheck.check(
            self._build_bash_payload("./test_hooks.sh;rm -rf /")
        )
        self.assertIsNone(result)

    def test_no_space_and_injection_rejects(self):

        result = playbook.pretooluse_bash.PlaybookExactMatchCheck.check(
            self._build_bash_payload("./test_hooks.sh&&rm -rf /")
        )
        self.assertIsNone(result)

    def test_no_space_pipe_injection_rejects(self):

        result = playbook.pretooluse_bash.PlaybookExactMatchCheck.check(
            self._build_bash_payload("./test_hooks.sh|cat")
        )
        self.assertIsNone(result)


class TestFindPlaybookAbsPath(unittest.TestCase):

    def test_finds_playbook_in_current_directory(self):

        temp_project_directory = tempfile.mkdtemp()
        dot_ai_sanity_directory = os.path.join(temp_project_directory, ".ai-sanity")
        os.makedirs(dot_ai_sanity_directory)
        playbook_abs_path = os.path.join(dot_ai_sanity_directory, "playbook.json")
        with open(playbook_abs_path, "w") as open_file_handle:
            open_file_handle.write("[]")
        result = playbook.pretooluse_bash.PlaybookExactMatchCheck.find_playbook_abs_path(temp_project_directory)
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
        result = playbook.pretooluse_bash.PlaybookExactMatchCheck.find_playbook_abs_path(child_directory)
        self.assertEqual(result, playbook_abs_path)

    def test_returns_none_when_no_playbook_exists(self):

        temp_directory = tempfile.mkdtemp()
        result = playbook.pretooluse_bash.PlaybookExactMatchCheck.find_playbook_abs_path(temp_directory)
        self.assertIsNone(result)


class TestNormalizeCommandForMatching(unittest.TestCase):

    def test_strips_whitespace(self):

        result = playbook.pretooluse_bash.PlaybookExactMatchCheck.normalize_command_for_matching(
            "  ./test_hooks.sh  "
        )
        self.assertEqual(result, "./test_hooks.sh")

    def test_strips_quotes(self):

        result = playbook.pretooluse_bash.PlaybookExactMatchCheck.normalize_command_for_matching(
            "'./test_hooks.sh'"
        )
        self.assertEqual(result, "./test_hooks.sh")

    def test_preserves_arguments(self):

        result = playbook.pretooluse_bash.PlaybookExactMatchCheck.normalize_command_for_matching(
            "./test_hooks.sh --verbose"
        )
        self.assertEqual(result, "./test_hooks.sh --verbose")

    def test_empty_string_returns_empty(self):

        result = playbook.pretooluse_bash.PlaybookExactMatchCheck.normalize_command_for_matching("")
        self.assertEqual(result, "")

    def test_malformed_quoting_falls_back_to_strip(self):

        result = playbook.pretooluse_bash.PlaybookExactMatchCheck.normalize_command_for_matching(
            "./test_hooks.sh \"broken"
        )
        self.assertEqual(result, "./test_hooks.sh \"broken")


if __name__ == "__main__":
    unittest.main()
