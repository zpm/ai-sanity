import os
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import tests.fixtures
from git_safety.pretooluse_bash import PreToolUseBashGitSafetyRuleChecks


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
        deny_reason = PreToolUseBashGitSafetyRuleChecks.check_require_git_mv_for_tracked_file_moves(payload_for_tracked_mv)
        self.assertIsNotNone(deny_reason)
        self.assertIn("tracked-example.txt", deny_reason)

    def test_blocks_mv_of_tracked_directory(self):

        payload_for_tracked_dir_mv = tests.fixtures.PreToolUsePayloadFixtureBuilder.build_bash_payload(
            bash_command_string = "mv tracked-dir new-dir",
            working_directory = self.git_repo_temp_directory
        )
        deny_reason = PreToolUseBashGitSafetyRuleChecks.check_require_git_mv_for_tracked_file_moves(payload_for_tracked_dir_mv)
        self.assertIsNotNone(deny_reason)
        self.assertIn("tracked-dir", deny_reason)

    def test_passes_mv_of_untracked_source(self):

        payload_for_untracked_mv = tests.fixtures.PreToolUsePayloadFixtureBuilder.build_bash_payload(
            bash_command_string = "mv untracked-example.txt renamed.txt",
            working_directory = self.git_repo_temp_directory
        )
        deny_reason = PreToolUseBashGitSafetyRuleChecks.check_require_git_mv_for_tracked_file_moves(payload_for_untracked_mv)
        self.assertIsNone(deny_reason)

    def test_passes_non_mv_command(self):

        payload_for_non_mv = tests.fixtures.PreToolUsePayloadFixtureBuilder.build_bash_payload(
            bash_command_string = "echo tracked-example.txt",
            working_directory = self.git_repo_temp_directory
        )
        deny_reason = PreToolUseBashGitSafetyRuleChecks.check_require_git_mv_for_tracked_file_moves(payload_for_non_mv)
        self.assertIsNone(deny_reason)

    def test_skips_flag_arguments_when_locating_sources(self):

        payload_with_flag = tests.fixtures.PreToolUsePayloadFixtureBuilder.build_bash_payload(
            bash_command_string = "mv -v tracked-example.txt renamed.txt",
            working_directory = self.git_repo_temp_directory
        )
        deny_reason = PreToolUseBashGitSafetyRuleChecks.check_require_git_mv_for_tracked_file_moves(payload_with_flag)
        self.assertIsNotNone(deny_reason)

    def test_passes_on_malformed_quoting(self):

        payload_with_unbalanced_quote = tests.fixtures.PreToolUsePayloadFixtureBuilder.build_bash_payload(
            bash_command_string = "mv \"broken"
        )
        deny_reason = PreToolUseBashGitSafetyRuleChecks.check_require_git_mv_for_tracked_file_moves(payload_with_unbalanced_quote)
        self.assertIsNone(deny_reason)

    def test_blocks_mv_dash_t_of_tracked_file(self):

        payload = tests.fixtures.PreToolUsePayloadFixtureBuilder.build_bash_payload(
            bash_command_string = "mv -t /tmp/dest tracked-example.txt",
            working_directory = self.git_repo_temp_directory
        )
        deny_reason = PreToolUseBashGitSafetyRuleChecks.check_require_git_mv_for_tracked_file_moves(payload)
        self.assertIsNotNone(deny_reason)
        self.assertIn("tracked-example.txt", deny_reason)

    def test_blocks_mv_target_directory_equals_of_tracked_file(self):

        payload = tests.fixtures.PreToolUsePayloadFixtureBuilder.build_bash_payload(
            bash_command_string = "mv --target-directory=/tmp/dest tracked-example.txt",
            working_directory = self.git_repo_temp_directory
        )
        deny_reason = PreToolUseBashGitSafetyRuleChecks.check_require_git_mv_for_tracked_file_moves(payload)
        self.assertIsNotNone(deny_reason)
        self.assertIn("tracked-example.txt", deny_reason)


if __name__ == "__main__":
    unittest.main()
