########################################################################################################################
# tests/playbook/test_rule_checks.py
#
# unit tests for playbook match check
########################################################################################################################


import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "hooks"))

import tests._common.fixtures
import playbook.pretooluse_bash


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

        result = playbook.pretooluse_bash.PlaybookMatchCheck.check(
            self._build_bash_payload("python -m unittest discover -s tests -t . -v")
        )
        self.assertIsNotNone(result)
        self.assertEqual(result["bash"], "python -m unittest discover -s tests -t . -v")

    def test_non_matching_command_returns_none(self):

        result = playbook.pretooluse_bash.PlaybookMatchCheck.check(
            self._build_bash_payload("ls -la")
        )
        self.assertIsNone(result)

    def test_exact_entry_rejects_extra_args(self):

        self._write_playbook([
            {"bash": "python -m unittest discover -s tests -t . -v", "what": "exact only", "when": "test"}
        ])
        result = playbook.pretooluse_bash.PlaybookMatchCheck.check(
            self._build_bash_payload("python -m unittest discover -s tests -t . -v --extra")
        )
        self.assertIsNone(result)

    def test_extra_whitespace_still_matches(self):

        result = playbook.pretooluse_bash.PlaybookMatchCheck.check(
            self._build_bash_payload("  python -m unittest discover -s tests -t . -v  ")
        )
        self.assertIsNotNone(result)

    def test_empty_command_returns_none(self):

        result = playbook.pretooluse_bash.PlaybookMatchCheck.check(
            self._build_bash_payload("")
        )
        self.assertIsNone(result)

    def test_malformed_quoting_returns_none(self):

        result = playbook.pretooluse_bash.PlaybookMatchCheck.check(
            self._build_bash_payload("python -m unittest \"broken")
        )
        self.assertIsNone(result)

    ####################################################################################################################
    # PREFIX WILDCARD

    def test_prefix_match_targeted_test(self):

        result = playbook.pretooluse_bash.PlaybookMatchCheck.check(
            self._build_bash_payload("python -m unittest tests.playbook.test_rule_checks -v")
        )
        self.assertIsNotNone(result)
        self.assertEqual(result["bash"], "python -m unittest *")

    def test_prefix_match_bare_command(self):

        result = playbook.pretooluse_bash.PlaybookMatchCheck.check(
            self._build_bash_payload("python -m unittest")
        )
        self.assertIsNotNone(result)
        self.assertEqual(result["bash"], "python -m unittest *")

    def test_prefix_no_partial_token_match(self):

        result = playbook.pretooluse_bash.PlaybookMatchCheck.check(
            self._build_bash_payload("python -m unittesting")
        )
        self.assertIsNone(result)

    def test_prefix_with_safe_pipe(self):

        result = playbook.pretooluse_bash.PlaybookMatchCheck.check(
            self._build_bash_payload("python -m unittest tests.foo -v 2>&1 | tail -80")
        )
        self.assertIsNotNone(result)

    def test_prefix_rejects_sequential_operator(self):

        result = playbook.pretooluse_bash.PlaybookMatchCheck.check(
            self._build_bash_payload("python -m unittest tests.foo && rm -rf /")
        )
        self.assertIsNone(result)

    def test_exact_match_preferred_over_prefix_when_both_match(self):

        result = playbook.pretooluse_bash.PlaybookMatchCheck.check(
            self._build_bash_payload("python -m unittest discover -s tests -t . -v")
        )
        self.assertIsNotNone(result)
        self.assertEqual(result["bash"], "python -m unittest discover -s tests -t . -v")

    ####################################################################################################################
    # PIPES WITH SAFE ALLOWLIST

    def test_pipe_to_tail_allows(self):

        result = playbook.pretooluse_bash.PlaybookMatchCheck.check(
            self._build_bash_payload("python -m unittest discover -s tests -t . -v | tail -5")
        )
        self.assertIsNotNone(result)

    def test_pipe_to_grep_allows(self):

        result = playbook.pretooluse_bash.PlaybookMatchCheck.check(
            self._build_bash_payload("python -m unittest discover -s tests -t . -v | grep FAIL")
        )
        self.assertIsNotNone(result)

    def test_pipe_to_head_allows(self):

        result = playbook.pretooluse_bash.PlaybookMatchCheck.check(
            self._build_bash_payload("python -m unittest discover -s tests -t . -v | head -20")
        )
        self.assertIsNotNone(result)

    def test_pipe_to_cat_allows(self):

        result = playbook.pretooluse_bash.PlaybookMatchCheck.check(
            self._build_bash_payload("python -m unittest discover -s tests -t . -v | cat")
        )
        self.assertIsNotNone(result)

    def test_pipe_chain_safe_targets_allows(self):

        result = playbook.pretooluse_bash.PlaybookMatchCheck.check(
            self._build_bash_payload("python -m unittest discover -s tests -t . -v | head -20 | grep ERROR")
        )
        self.assertIsNotNone(result)

    def test_pipe_to_unsafe_rm_rejects(self):

        result = playbook.pretooluse_bash.PlaybookMatchCheck.check(
            self._build_bash_payload("python -m unittest discover -s tests -t . -v | rm -rf /tmp")
        )
        self.assertIsNone(result)

    def test_pipe_to_python_rejects(self):

        result = playbook.pretooluse_bash.PlaybookMatchCheck.check(
            self._build_bash_payload("python -m unittest discover -s tests -t . -v | python -c 'import os'")
        )
        self.assertIsNone(result)

    def test_pipe_to_mv_rejects(self):

        result = playbook.pretooluse_bash.PlaybookMatchCheck.check(
            self._build_bash_payload("python -m unittest discover -s tests -t . -v | mv a b")
        )
        self.assertIsNone(result)

    def test_piped_command_not_first_clause_rejects(self):

        result = playbook.pretooluse_bash.PlaybookMatchCheck.check(
            self._build_bash_payload("echo pwned | python -m unittest discover -s tests -t . -v")
        )
        self.assertIsNone(result)

    def test_mixed_safe_and_unsafe_pipe_rejects(self):

        result = playbook.pretooluse_bash.PlaybookMatchCheck.check(
            self._build_bash_payload("python -m unittest discover -s tests -t . -v | tail -5 | rm foo")
        )
        self.assertIsNone(result)

    def test_no_space_pipe_to_cat_allows(self):

        result = playbook.pretooluse_bash.PlaybookMatchCheck.check(
            self._build_bash_payload("python -m unittest discover -s tests -t . -v|cat")
        )
        self.assertIsNotNone(result)

    ####################################################################################################################
    # SEQUENTIAL OPERATORS

    def test_and_then_rejects(self):

        result = playbook.pretooluse_bash.PlaybookMatchCheck.check(
            self._build_bash_payload("python -m unittest discover -s tests -t . -v && echo done")
        )
        self.assertIsNone(result)

    def test_or_else_rejects(self):

        result = playbook.pretooluse_bash.PlaybookMatchCheck.check(
            self._build_bash_payload("python -m unittest discover -s tests -t . -v || echo failed")
        )
        self.assertIsNone(result)

    def test_semicolon_rejects(self):

        result = playbook.pretooluse_bash.PlaybookMatchCheck.check(
            self._build_bash_payload("python -m unittest discover -s tests -t . -v; echo done")
        )
        self.assertIsNone(result)

    def test_no_space_semicolon_rejects(self):

        result = playbook.pretooluse_bash.PlaybookMatchCheck.check(
            self._build_bash_payload("python -m unittest discover -s tests -t . -v;rm -rf /")
        )
        self.assertIsNone(result)

    def test_no_space_and_rejects(self):

        result = playbook.pretooluse_bash.PlaybookMatchCheck.check(
            self._build_bash_payload("python -m unittest discover -s tests -t . -v&&rm -rf /")
        )
        self.assertIsNone(result)

    ####################################################################################################################
    # DESCRIPTOR MERGES VS FILE REDIRECTS

    def test_descriptor_merge_2_to_1_with_pipe_allows(self):

        result = playbook.pretooluse_bash.PlaybookMatchCheck.check(
            self._build_bash_payload("python -m unittest discover -s tests -t . -v 2>&1 | tail -5")
        )
        self.assertIsNotNone(result)

    def test_descriptor_merge_to_stderr_allows(self):

        result = playbook.pretooluse_bash.PlaybookMatchCheck.check(
            self._build_bash_payload("python -m unittest discover -s tests -t . -v >&2")
        )
        self.assertIsNotNone(result)

    def test_file_redirect_stdout_rejects(self):

        result = playbook.pretooluse_bash.PlaybookMatchCheck.check(
            self._build_bash_payload("python -m unittest discover -s tests -t . -v > output.txt")
        )
        self.assertIsNone(result)

    def test_file_redirect_append_rejects(self):

        result = playbook.pretooluse_bash.PlaybookMatchCheck.check(
            self._build_bash_payload("python -m unittest discover -s tests -t . -v >> log.txt")
        )
        self.assertIsNone(result)

    def test_file_redirect_stderr_rejects(self):

        result = playbook.pretooluse_bash.PlaybookMatchCheck.check(
            self._build_bash_payload("python -m unittest discover -s tests -t . -v 2> /dev/null")
        )
        self.assertIsNone(result)

    def test_stdin_redirect_rejects(self):

        result = playbook.pretooluse_bash.PlaybookMatchCheck.check(
            self._build_bash_payload("python -m unittest discover -s tests -t . -v < input.txt")
        )
        self.assertIsNone(result)

    def test_redirect_only_no_command_rejects(self):

        result = playbook.pretooluse_bash.PlaybookMatchCheck.check(
            self._build_bash_payload("> /tmp/file")
        )
        self.assertIsNone(result)

    def test_attached_file_redirect_rejects(self):

        result = playbook.pretooluse_bash.PlaybookMatchCheck.check(
            self._build_bash_payload("python -m unittest tests.foo >out.txt")
        )
        self.assertIsNone(result)

    def test_attached_stderr_redirect_rejects(self):

        result = playbook.pretooluse_bash.PlaybookMatchCheck.check(
            self._build_bash_payload("python -m unittest tests.foo 2>/dev/null")
        )
        self.assertIsNone(result)

    def test_attached_append_redirect_rejects(self):

        result = playbook.pretooluse_bash.PlaybookMatchCheck.check(
            self._build_bash_payload("python -m unittest tests.foo >>log.txt")
        )
        self.assertIsNone(result)

    def test_pipe_downstream_file_redirect_rejects(self):

        result = playbook.pretooluse_bash.PlaybookMatchCheck.check(
            self._build_bash_payload("python -m unittest tests.foo | tail -5 > out.txt")
        )
        self.assertIsNone(result)

    def test_pipe_downstream_attached_redirect_rejects(self):

        result = playbook.pretooluse_bash.PlaybookMatchCheck.check(
            self._build_bash_payload("python -m unittest tests.foo | tail -5 >out.txt")
        )
        self.assertIsNone(result)

    ####################################################################################################################
    # KNOWN LIMITATION: QUOTED OPERATORS

    def test_quoted_pipe_literal_matches_known_parser_limitation(self):

        result = playbook.pretooluse_bash.PlaybookMatchCheck.check(
            self._build_bash_payload("python -m unittest '|' cat")
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
        result = playbook.pretooluse_bash.PlaybookMatchCheck.check(payload)
        self.assertIsNone(result)

    def test_bad_json_playbook_returns_none(self):

        with open(self.playbook_abs_path, "w", encoding = "utf-8") as open_playbook_file_handle:
            open_playbook_file_handle.write("{not valid json")
        result = playbook.pretooluse_bash.PlaybookMatchCheck.check(
            self._build_bash_payload("python -m unittest discover -s tests -t . -v")
        )
        self.assertIsNone(result)

    def test_playbook_with_wrong_shape_returns_none(self):

        with open(self.playbook_abs_path, "w", encoding = "utf-8") as open_playbook_file_handle:
            json.dump({"not": "a list"}, open_playbook_file_handle)
        result = playbook.pretooluse_bash.PlaybookMatchCheck.check(
            self._build_bash_payload("python -m unittest discover -s tests -t . -v")
        )
        self.assertIsNone(result)

    def test_playbook_entry_missing_bash_field_is_skipped(self):

        self._write_playbook([
            {"what": "no bash field", "when": "never"}
        ])
        result = playbook.pretooluse_bash.PlaybookMatchCheck.check(
            self._build_bash_payload("python -m unittest discover -s tests -t . -v")
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
        result = playbook.pretooluse_bash.PlaybookMatchCheck.find_playbook_abs_path(temp_project_directory)
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
        result = playbook.pretooluse_bash.PlaybookMatchCheck.find_playbook_abs_path(child_directory)
        self.assertEqual(result, playbook_abs_path)

    def test_returns_none_when_no_playbook_exists(self):

        temp_directory = tempfile.mkdtemp()
        result = playbook.pretooluse_bash.PlaybookMatchCheck.find_playbook_abs_path(temp_directory)
        self.assertIsNone(result)


class TestStripDescriptorMergeTokensFromClause(unittest.TestCase):

    def test_no_redirects_unchanged(self):

        result = playbook.pretooluse_bash.PlaybookMatchCheck.strip_descriptor_merge_tokens_from_clause(
            ["python", "-m", "unittest"]
        )
        self.assertEqual(result, ["python", "-m", "unittest"])

    def test_strips_2_to_1(self):

        result = playbook.pretooluse_bash.PlaybookMatchCheck.strip_descriptor_merge_tokens_from_clause(
            ["python", "-m", "unittest", "2>&1"]
        )
        self.assertEqual(result, ["python", "-m", "unittest"])

    def test_strips_to_stderr(self):

        result = playbook.pretooluse_bash.PlaybookMatchCheck.strip_descriptor_merge_tokens_from_clause(
            ["python", "-m", "unittest", ">&2"]
        )
        self.assertEqual(result, ["python", "-m", "unittest"])

    def test_preserves_args_before_redirect(self):

        result = playbook.pretooluse_bash.PlaybookMatchCheck.strip_descriptor_merge_tokens_from_clause(
            ["python", "-m", "unittest", "--verbose", "2>&1"]
        )
        self.assertEqual(result, ["python", "-m", "unittest", "--verbose"])

    def test_file_redirect_returns_none(self):

        result = playbook.pretooluse_bash.PlaybookMatchCheck.strip_descriptor_merge_tokens_from_clause(
            ["python", "-m", "unittest", ">", "out.txt"]
        )
        self.assertIsNone(result)

    def test_stderr_file_redirect_returns_none(self):

        result = playbook.pretooluse_bash.PlaybookMatchCheck.strip_descriptor_merge_tokens_from_clause(
            ["python", "-m", "unittest", "2>", "/dev/null"]
        )
        self.assertIsNone(result)

    def test_stdin_redirect_returns_none(self):

        result = playbook.pretooluse_bash.PlaybookMatchCheck.strip_descriptor_merge_tokens_from_clause(
            ["python", "-m", "unittest", "<", "input.txt"]
        )
        self.assertIsNone(result)

    def test_empty_list_unchanged(self):

        result = playbook.pretooluse_bash.PlaybookMatchCheck.strip_descriptor_merge_tokens_from_clause([])
        self.assertEqual(result, [])

    def test_attached_stdout_redirect_returns_none(self):

        result = playbook.pretooluse_bash.PlaybookMatchCheck.strip_descriptor_merge_tokens_from_clause(
            ["python", "-m", "unittest", ">out.txt"]
        )
        self.assertIsNone(result)

    def test_attached_stderr_redirect_returns_none(self):

        result = playbook.pretooluse_bash.PlaybookMatchCheck.strip_descriptor_merge_tokens_from_clause(
            ["python", "-m", "unittest", "2>/dev/null"]
        )
        self.assertIsNone(result)

    def test_attached_append_redirect_returns_none(self):

        result = playbook.pretooluse_bash.PlaybookMatchCheck.strip_descriptor_merge_tokens_from_clause(
            ["python", "-m", "unittest", ">>log.txt"]
        )
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
