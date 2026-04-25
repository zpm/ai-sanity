import os
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import tests.fixtures
from git_safety.pretooluse_bash import PreToolUseBashGitSafetyRuleChecks


class TestCheckDenyGitWriteCommands(unittest.TestCase):

    def _build(self, command):

        return tests.fixtures.PreToolUsePayloadFixtureBuilder.build_bash_payload(command)

    def test_blocks_git_commit(self):

        result = PreToolUseBashGitSafetyRuleChecks.check_deny_git_write_commands(self._build("git commit -m 'msg'"))
        self.assertIsNotNone(result)
        self.assertIn("strictly prohibited", result)

    def test_blocks_git_push(self):

        result = PreToolUseBashGitSafetyRuleChecks.check_deny_git_write_commands(self._build("git push origin main"))
        self.assertIsNotNone(result)

    def test_blocks_git_pull(self):

        result = PreToolUseBashGitSafetyRuleChecks.check_deny_git_write_commands(self._build("git pull"))
        self.assertIsNotNone(result)

    def test_blocks_git_fetch(self):

        result = PreToolUseBashGitSafetyRuleChecks.check_deny_git_write_commands(self._build("git fetch origin"))
        self.assertIsNotNone(result)

    def test_blocks_git_merge(self):

        result = PreToolUseBashGitSafetyRuleChecks.check_deny_git_write_commands(self._build("git merge feature"))
        self.assertIsNotNone(result)

    def test_blocks_git_rebase(self):

        result = PreToolUseBashGitSafetyRuleChecks.check_deny_git_write_commands(self._build("git rebase main"))
        self.assertIsNotNone(result)

    def test_blocks_git_reset(self):

        result = PreToolUseBashGitSafetyRuleChecks.check_deny_git_write_commands(self._build("git reset --hard HEAD"))
        self.assertIsNotNone(result)

    def test_blocks_git_checkout(self):

        result = PreToolUseBashGitSafetyRuleChecks.check_deny_git_write_commands(self._build("git checkout feature"))
        self.assertIsNotNone(result)

    def test_blocks_git_branch(self):

        result = PreToolUseBashGitSafetyRuleChecks.check_deny_git_write_commands(self._build("git branch new-feature"))
        self.assertIsNotNone(result)

    def test_blocks_git_branch_no_args(self):

        result = PreToolUseBashGitSafetyRuleChecks.check_deny_git_write_commands(self._build("git branch"))
        self.assertIsNotNone(result)

    def test_blocks_git_stash(self):

        result = PreToolUseBashGitSafetyRuleChecks.check_deny_git_write_commands(self._build("git stash"))
        self.assertIsNotNone(result)

    def test_blocks_git_stash_pop(self):

        result = PreToolUseBashGitSafetyRuleChecks.check_deny_git_write_commands(self._build("git stash pop"))
        self.assertIsNotNone(result)

    def test_blocks_git_add(self):

        result = PreToolUseBashGitSafetyRuleChecks.check_deny_git_write_commands(self._build("git add ."))
        self.assertIsNotNone(result)

    def test_blocks_git_tag(self):

        result = PreToolUseBashGitSafetyRuleChecks.check_deny_git_write_commands(self._build("git tag v1.0"))
        self.assertIsNotNone(result)

    def test_blocks_git_rm(self):

        result = PreToolUseBashGitSafetyRuleChecks.check_deny_git_write_commands(self._build("git rm file.txt"))
        self.assertIsNotNone(result)

    def test_blocks_git_clean(self):

        result = PreToolUseBashGitSafetyRuleChecks.check_deny_git_write_commands(self._build("git clean -fd"))
        self.assertIsNotNone(result)

    def test_blocks_git_config(self):

        result = PreToolUseBashGitSafetyRuleChecks.check_deny_git_write_commands(self._build("git config user.name test"))
        self.assertIsNotNone(result)

    def test_blocks_git_remote(self):

        result = PreToolUseBashGitSafetyRuleChecks.check_deny_git_write_commands(self._build("git remote add origin url"))
        self.assertIsNotNone(result)

    def test_blocks_git_clone(self):

        result = PreToolUseBashGitSafetyRuleChecks.check_deny_git_write_commands(self._build("git clone https://github.com/foo/bar"))
        self.assertIsNotNone(result)

    def test_blocks_git_init(self):

        result = PreToolUseBashGitSafetyRuleChecks.check_deny_git_write_commands(self._build("git init"))
        self.assertIsNotNone(result)

    def test_blocks_git_cherry_pick(self):

        result = PreToolUseBashGitSafetyRuleChecks.check_deny_git_write_commands(self._build("git cherry-pick abc123"))
        self.assertIsNotNone(result)

    def test_blocks_git_revert(self):

        result = PreToolUseBashGitSafetyRuleChecks.check_deny_git_write_commands(self._build("git revert HEAD"))
        self.assertIsNotNone(result)

    def test_blocks_git_filter_branch(self):

        result = PreToolUseBashGitSafetyRuleChecks.check_deny_git_write_commands(self._build("git filter-branch --all"))
        self.assertIsNotNone(result)

    def test_blocks_git_update_ref(self):

        result = PreToolUseBashGitSafetyRuleChecks.check_deny_git_write_commands(self._build("git update-ref refs/heads/main abc"))
        self.assertIsNotNone(result)

    def test_passes_git_diff(self):

        result = PreToolUseBashGitSafetyRuleChecks.check_deny_git_write_commands(self._build("git diff HEAD"))
        self.assertIsNone(result)

    def test_passes_git_status(self):

        result = PreToolUseBashGitSafetyRuleChecks.check_deny_git_write_commands(self._build("git status"))
        self.assertIsNone(result)

    def test_passes_git_log(self):

        result = PreToolUseBashGitSafetyRuleChecks.check_deny_git_write_commands(self._build("git log --oneline"))
        self.assertIsNone(result)

    def test_passes_git_ls_files(self):

        result = PreToolUseBashGitSafetyRuleChecks.check_deny_git_write_commands(self._build("git ls-files"))
        self.assertIsNone(result)

    def test_passes_git_show(self):

        result = PreToolUseBashGitSafetyRuleChecks.check_deny_git_write_commands(self._build("git show HEAD"))
        self.assertIsNone(result)

    def test_passes_git_mv(self):

        result = PreToolUseBashGitSafetyRuleChecks.check_deny_git_write_commands(self._build("git mv old.txt new.txt"))
        self.assertIsNone(result)

    def test_passes_non_git_command(self):

        result = PreToolUseBashGitSafetyRuleChecks.check_deny_git_write_commands(self._build("echo hello"))
        self.assertIsNone(result)

    def test_passes_git_alone(self):

        result = PreToolUseBashGitSafetyRuleChecks.check_deny_git_write_commands(self._build("git"))
        self.assertIsNone(result)

    def test_passes_on_malformed_quoting(self):

        result = PreToolUseBashGitSafetyRuleChecks.check_deny_git_write_commands(self._build("git commit -m \"broken"))
        self.assertIsNone(result)

    def test_passes_on_empty_command(self):

        result = PreToolUseBashGitSafetyRuleChecks.check_deny_git_write_commands(self._build(""))
        self.assertIsNone(result)


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
