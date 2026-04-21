########################################################################################################################
# ~/.claude/hooks/tests/test_rule_checks.py
#
# Unit tests for every rule check method across _lib and the per-matcher entry scripts
########################################################################################################################
import os
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pretooluse_bash
import pretooluse_read
import pretooluse_write
import tests.fixtures


class TestCheckNoEmOrEnDash(unittest.TestCase):

    def test_blocks_em_dash_in_write_content(self):

        payload_with_em_dash = tests.fixtures.PreToolUsePayloadFixtureBuilder.build_write_payload(
            file_content = "hello \u2014 world"
        )
        rule_check_class = pretooluse_write.PreToolUseWriteRuleChecks
        deny_reason = rule_check_class.check_no_em_or_en_dash_in_write_or_edit_content(payload_with_em_dash)
        self.assertIsNotNone(deny_reason)
        self.assertIn("Em dash", deny_reason)

    def test_blocks_en_dash_in_write_content(self):

        payload_with_en_dash = tests.fixtures.PreToolUsePayloadFixtureBuilder.build_write_payload(
            file_content = "hello \u2013 world"
        )
        rule_check_class = pretooluse_write.PreToolUseWriteRuleChecks
        deny_reason = rule_check_class.check_no_em_or_en_dash_in_write_or_edit_content(payload_with_en_dash)
        self.assertIsNotNone(deny_reason)
        self.assertIn("En dash", deny_reason)

    def test_blocks_em_dash_in_edit_new_string(self):

        payload_with_em_dash_edit = tests.fixtures.PreToolUsePayloadFixtureBuilder.build_edit_payload(
            new_string_content = "foo \u2014 bar"
        )
        rule_check_class = pretooluse_write.PreToolUseWriteRuleChecks
        deny_reason = rule_check_class.check_no_em_or_en_dash_in_write_or_edit_content(payload_with_em_dash_edit)
        self.assertIsNotNone(deny_reason)

    def test_passes_plain_hyphen(self):

        payload_with_plain_hyphen = tests.fixtures.PreToolUsePayloadFixtureBuilder.build_write_payload(
            file_content = "hello - world"
        )
        rule_check_class = pretooluse_write.PreToolUseWriteRuleChecks
        deny_reason = rule_check_class.check_no_em_or_en_dash_in_write_or_edit_content(payload_with_plain_hyphen)
        self.assertIsNone(deny_reason)


class TestCheckRequireGitMv(unittest.TestCase):

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

        payload_for_tracked_mv = tests.fixtures.PreToolUsePayloadFixtureBuilder.build_bash_payload(
            bash_command_string = "mv tracked-example.txt renamed.txt",
            working_directory = self.git_repo_temp_directory
        )
        rule_check_class = pretooluse_bash.PreToolUseBashRuleChecks
        deny_reason = rule_check_class.check_require_git_mv_for_tracked_file_moves(payload_for_tracked_mv)
        self.assertIsNotNone(deny_reason)
        self.assertIn("tracked-example.txt", deny_reason)

    def test_blocks_mv_of_tracked_directory(self):

        payload_for_tracked_dir_mv = tests.fixtures.PreToolUsePayloadFixtureBuilder.build_bash_payload(
            bash_command_string = "mv tracked-dir new-dir",
            working_directory = self.git_repo_temp_directory
        )
        rule_check_class = pretooluse_bash.PreToolUseBashRuleChecks
        deny_reason = rule_check_class.check_require_git_mv_for_tracked_file_moves(payload_for_tracked_dir_mv)
        self.assertIsNotNone(deny_reason)
        self.assertIn("tracked-dir", deny_reason)

    def test_passes_mv_of_untracked_source(self):

        payload_for_untracked_mv = tests.fixtures.PreToolUsePayloadFixtureBuilder.build_bash_payload(
            bash_command_string = "mv untracked-example.txt renamed.txt",
            working_directory = self.git_repo_temp_directory
        )
        rule_check_class = pretooluse_bash.PreToolUseBashRuleChecks
        deny_reason = rule_check_class.check_require_git_mv_for_tracked_file_moves(payload_for_untracked_mv)
        self.assertIsNone(deny_reason)

    def test_passes_non_mv_command(self):

        payload_for_non_mv = tests.fixtures.PreToolUsePayloadFixtureBuilder.build_bash_payload(
            bash_command_string = "echo tracked-example.txt",
            working_directory = self.git_repo_temp_directory
        )
        rule_check_class = pretooluse_bash.PreToolUseBashRuleChecks
        deny_reason = rule_check_class.check_require_git_mv_for_tracked_file_moves(payload_for_non_mv)
        self.assertIsNone(deny_reason)

    def test_skips_flag_arguments_when_locating_sources(self):

        payload_with_flag = tests.fixtures.PreToolUsePayloadFixtureBuilder.build_bash_payload(
            bash_command_string = "mv -v tracked-example.txt renamed.txt",
            working_directory = self.git_repo_temp_directory
        )
        rule_check_class = pretooluse_bash.PreToolUseBashRuleChecks
        deny_reason = rule_check_class.check_require_git_mv_for_tracked_file_moves(payload_with_flag)
        self.assertIsNotNone(deny_reason)

    def test_passes_on_malformed_quoting(self):

        payload_with_unbalanced_quote = tests.fixtures.PreToolUsePayloadFixtureBuilder.build_bash_payload(
            bash_command_string = "mv \"broken"
        )
        rule_check_class = pretooluse_bash.PreToolUseBashRuleChecks
        deny_reason = rule_check_class.check_require_git_mv_for_tracked_file_moves(payload_with_unbalanced_quote)
        self.assertIsNone(deny_reason)


class TestCheckNoMemoryAccess(unittest.TestCase):

    def test_blocks_read_under_auto_memory_directory(self):

        payload = tests.fixtures.PreToolUsePayloadFixtureBuilder.build_read_payload(
            file_path = "/c/Users/zachm/.claude/projects/abc/memory/example.md"
        )
        deny_reason = pretooluse_read.PreToolUseReadRuleChecks.check_no_memory_access_for_read_or_glob_or_grep(payload)
        self.assertIsNotNone(deny_reason)

    def test_blocks_read_of_memory_md_filename_anywhere(self):

        payload = tests.fixtures.PreToolUsePayloadFixtureBuilder.build_read_payload(
            file_path = "/some/dir/MEMORY.md"
        )
        deny_reason = pretooluse_read.PreToolUseReadRuleChecks.check_no_memory_access_for_read_or_glob_or_grep(payload)
        self.assertIsNotNone(deny_reason)

    def test_blocks_glob_pattern_targeting_memory_md(self):

        payload = tests.fixtures.PreToolUsePayloadFixtureBuilder.build_glob_payload(
            glob_pattern_string = "**/MEMORY.md"
        )
        deny_reason = pretooluse_read.PreToolUseReadRuleChecks.check_no_memory_access_for_read_or_glob_or_grep(payload)
        self.assertIsNotNone(deny_reason)

    def test_passes_grep_for_literal_memory_md_string_inside_files(self):

        payload = tests.fixtures.PreToolUsePayloadFixtureBuilder.build_grep_payload(
            grep_pattern = "MEMORY.md",
            grep_path = "/tmp/some-project"
        )
        deny_reason = pretooluse_read.PreToolUseReadRuleChecks.check_no_memory_access_for_read_or_glob_or_grep(payload)
        self.assertIsNone(deny_reason)

    def test_blocks_grep_with_path_inside_memory_directory(self):

        payload = tests.fixtures.PreToolUsePayloadFixtureBuilder.build_grep_payload(
            grep_pattern = "anything",
            grep_path = "/c/Users/zachm/.claude/projects/abc/memory"
        )
        deny_reason = pretooluse_read.PreToolUseReadRuleChecks.check_no_memory_access_for_read_or_glob_or_grep(payload)
        self.assertIsNotNone(deny_reason)

    def test_blocks_bash_cd_into_memory_directory(self):

        payload = tests.fixtures.PreToolUsePayloadFixtureBuilder.build_bash_payload(
            bash_command_string = "cd ~/.claude/projects/abc/memory && touch foo.md"
        )
        deny_reason = pretooluse_bash.PreToolUseBashRuleChecks.check_no_memory_access_for_bash(payload)
        self.assertIsNotNone(deny_reason)

    def test_passes_bash_echo_mentioning_memory_md_substring(self):

        payload = tests.fixtures.PreToolUsePayloadFixtureBuilder.build_bash_payload(
            bash_command_string = "echo 'search for MEMORY.md term'"
        )
        deny_reason = pretooluse_bash.PreToolUseBashRuleChecks.check_no_memory_access_for_bash(payload)
        self.assertIsNone(deny_reason)

    def test_passes_read_under_plans_directory(self):

        payload = tests.fixtures.PreToolUsePayloadFixtureBuilder.build_read_payload(
            file_path = "/c/Users/zachm/.claude/plans/example.md"
        )
        deny_reason = pretooluse_read.PreToolUseReadRuleChecks.check_no_memory_access_for_read_or_glob_or_grep(payload)
        self.assertIsNone(deny_reason)

    def test_passes_unrelated_path(self):

        payload = tests.fixtures.PreToolUsePayloadFixtureBuilder.build_read_payload(
            file_path = "/tmp/foo.txt"
        )
        deny_reason = pretooluse_read.PreToolUseReadRuleChecks.check_no_memory_access_for_read_or_glob_or_grep(payload)
        self.assertIsNone(deny_reason)


if __name__ == "__main__":
    unittest.main()
