########################################################################################################################
# tests/bash_safety/test_rule_checks.py
#
# unit tests for individual bash safety rule checks
########################################################################################################################


import os
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "hooks"))

import tests.fixtures
import bash_safety.pretooluse_bash


class TestNoGitWriteCommandsCheck(unittest.TestCase):

    def _build_bash_payload(self, command):

        return tests.fixtures.PreToolUsePayloadFixtureBuilder.build_bash_payload(command)

    def test_blocks_git_commit(self):

        result = bash_safety.pretooluse_bash.NoGitWriteCommandsCheck.check(
            self._build_bash_payload("git commit -m 'msg'")
        )
        self.assertIsNotNone(result)
        self.assertIn("strictly prohibited", result)

    def test_blocks_git_push(self):

        result = bash_safety.pretooluse_bash.NoGitWriteCommandsCheck.check(
            self._build_bash_payload("git push origin main")
        )
        self.assertIsNotNone(result)

    def test_blocks_git_pull(self):

        result = bash_safety.pretooluse_bash.NoGitWriteCommandsCheck.check(
            self._build_bash_payload("git pull")
        )
        self.assertIsNotNone(result)

    def test_blocks_git_fetch(self):

        result = bash_safety.pretooluse_bash.NoGitWriteCommandsCheck.check(
            self._build_bash_payload("git fetch origin")
        )
        self.assertIsNotNone(result)

    def test_blocks_git_merge(self):

        result = bash_safety.pretooluse_bash.NoGitWriteCommandsCheck.check(
            self._build_bash_payload("git merge feature")
        )
        self.assertIsNotNone(result)

    def test_blocks_git_rebase(self):

        result = bash_safety.pretooluse_bash.NoGitWriteCommandsCheck.check(
            self._build_bash_payload("git rebase main")
        )
        self.assertIsNotNone(result)

    def test_blocks_git_reset(self):

        result = bash_safety.pretooluse_bash.NoGitWriteCommandsCheck.check(
            self._build_bash_payload("git reset --hard HEAD")
        )
        self.assertIsNotNone(result)

    def test_blocks_git_checkout(self):

        result = bash_safety.pretooluse_bash.NoGitWriteCommandsCheck.check(
            self._build_bash_payload("git checkout feature")
        )
        self.assertIsNotNone(result)

    def test_blocks_git_branch(self):

        result = bash_safety.pretooluse_bash.NoGitWriteCommandsCheck.check(
            self._build_bash_payload("git branch new-feature")
        )
        self.assertIsNotNone(result)

    def test_blocks_git_branch_no_args(self):

        result = bash_safety.pretooluse_bash.NoGitWriteCommandsCheck.check(
            self._build_bash_payload("git branch")
        )
        self.assertIsNotNone(result)

    def test_blocks_git_stash(self):

        result = bash_safety.pretooluse_bash.NoGitWriteCommandsCheck.check(
            self._build_bash_payload("git stash")
        )
        self.assertIsNotNone(result)

    def test_blocks_git_stash_pop(self):

        result = bash_safety.pretooluse_bash.NoGitWriteCommandsCheck.check(
            self._build_bash_payload("git stash pop")
        )
        self.assertIsNotNone(result)

    def test_blocks_git_add(self):

        result = bash_safety.pretooluse_bash.NoGitWriteCommandsCheck.check(
            self._build_bash_payload("git add .")
        )
        self.assertIsNotNone(result)

    def test_blocks_git_tag(self):

        result = bash_safety.pretooluse_bash.NoGitWriteCommandsCheck.check(
            self._build_bash_payload("git tag v1.0")
        )
        self.assertIsNotNone(result)

    def test_blocks_git_rm(self):

        result = bash_safety.pretooluse_bash.NoGitWriteCommandsCheck.check(
            self._build_bash_payload("git rm file.txt")
        )
        self.assertIsNotNone(result)

    def test_blocks_git_clean(self):

        result = bash_safety.pretooluse_bash.NoGitWriteCommandsCheck.check(
            self._build_bash_payload("git clean -fd")
        )
        self.assertIsNotNone(result)

    def test_blocks_git_config(self):

        result = bash_safety.pretooluse_bash.NoGitWriteCommandsCheck.check(
            self._build_bash_payload("git config user.name test")
        )
        self.assertIsNotNone(result)

    def test_blocks_git_remote(self):

        result = bash_safety.pretooluse_bash.NoGitWriteCommandsCheck.check(
            self._build_bash_payload("git remote add origin url")
        )
        self.assertIsNotNone(result)

    def test_blocks_git_clone(self):

        result = bash_safety.pretooluse_bash.NoGitWriteCommandsCheck.check(
            self._build_bash_payload("git clone https://github.com/foo/bar")
        )
        self.assertIsNotNone(result)

    def test_blocks_git_init(self):

        result = bash_safety.pretooluse_bash.NoGitWriteCommandsCheck.check(
            self._build_bash_payload("git init")
        )
        self.assertIsNotNone(result)

    def test_blocks_git_cherry_pick(self):

        result = bash_safety.pretooluse_bash.NoGitWriteCommandsCheck.check(
            self._build_bash_payload("git cherry-pick abc123")
        )
        self.assertIsNotNone(result)

    def test_blocks_git_revert(self):

        result = bash_safety.pretooluse_bash.NoGitWriteCommandsCheck.check(
            self._build_bash_payload("git revert HEAD")
        )
        self.assertIsNotNone(result)

    def test_blocks_git_filter_branch(self):

        result = bash_safety.pretooluse_bash.NoGitWriteCommandsCheck.check(
            self._build_bash_payload("git filter-branch --all")
        )
        self.assertIsNotNone(result)

    def test_blocks_git_update_ref(self):

        result = bash_safety.pretooluse_bash.NoGitWriteCommandsCheck.check(
            self._build_bash_payload("git update-ref refs/heads/main abc")
        )
        self.assertIsNotNone(result)

    def test_blocks_git_commit_after_pipe(self):

        result = bash_safety.pretooluse_bash.NoGitWriteCommandsCheck.check(
            self._build_bash_payload("echo hello | git commit -m test")
        )
        self.assertIsNotNone(result)

    def test_blocks_git_push_after_and(self):

        result = bash_safety.pretooluse_bash.NoGitWriteCommandsCheck.check(
            self._build_bash_payload("echo hello && git push origin main")
        )
        self.assertIsNotNone(result)

    def test_blocks_git_add_after_semicolon(self):

        result = bash_safety.pretooluse_bash.NoGitWriteCommandsCheck.check(
            self._build_bash_payload("ls ; git add .")
        )
        self.assertIsNotNone(result)

    def test_blocks_git_commit_no_space_semicolon(self):

        result = bash_safety.pretooluse_bash.NoGitWriteCommandsCheck.check(
            self._build_bash_payload("echo ok;git commit -m x")
        )
        self.assertIsNotNone(result)

    def test_blocks_git_push_no_space_and(self):

        result = bash_safety.pretooluse_bash.NoGitWriteCommandsCheck.check(
            self._build_bash_payload("echo ok&&git push")
        )
        self.assertIsNotNone(result)

    def test_blocks_git_add_no_space_pipe(self):

        result = bash_safety.pretooluse_bash.NoGitWriteCommandsCheck.check(
            self._build_bash_payload("echo ok|git add .")
        )
        self.assertIsNotNone(result)

    def test_passes_git_diff(self):

        result = bash_safety.pretooluse_bash.NoGitWriteCommandsCheck.check(
            self._build_bash_payload("git diff HEAD")
        )
        self.assertIsNone(result)

    def test_passes_git_status(self):

        result = bash_safety.pretooluse_bash.NoGitWriteCommandsCheck.check(
            self._build_bash_payload("git status")
        )
        self.assertIsNone(result)

    def test_passes_git_log(self):

        result = bash_safety.pretooluse_bash.NoGitWriteCommandsCheck.check(
            self._build_bash_payload("git log --oneline")
        )
        self.assertIsNone(result)

    def test_passes_git_ls_files(self):

        result = bash_safety.pretooluse_bash.NoGitWriteCommandsCheck.check(
            self._build_bash_payload("git ls-files")
        )
        self.assertIsNone(result)

    def test_passes_git_show(self):

        result = bash_safety.pretooluse_bash.NoGitWriteCommandsCheck.check(
            self._build_bash_payload("git show HEAD")
        )
        self.assertIsNone(result)

    def test_passes_git_mv(self):

        result = bash_safety.pretooluse_bash.NoGitWriteCommandsCheck.check(
            self._build_bash_payload("git mv old.txt new.txt")
        )
        self.assertIsNone(result)

    def test_passes_non_git_command(self):

        result = bash_safety.pretooluse_bash.NoGitWriteCommandsCheck.check(
            self._build_bash_payload("echo hello")
        )
        self.assertIsNone(result)

    def test_passes_git_alone(self):

        result = bash_safety.pretooluse_bash.NoGitWriteCommandsCheck.check(
            self._build_bash_payload("git")
        )
        self.assertIsNone(result)

    def test_passes_on_malformed_quoting(self):

        result = bash_safety.pretooluse_bash.NoGitWriteCommandsCheck.check(
            self._build_bash_payload("git commit -m \"broken")
        )
        self.assertIsNone(result)

    def test_passes_on_empty_command(self):

        result = bash_safety.pretooluse_bash.NoGitWriteCommandsCheck.check(
            self._build_bash_payload("")
        )
        self.assertIsNone(result)


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

        payload = tests.fixtures.PreToolUsePayloadFixtureBuilder.build_bash_payload(
            bash_command_string = "mv tracked-example.txt renamed.txt",
            working_directory = self.git_repo_temp_directory
        )
        result = bash_safety.pretooluse_bash.RequireGitMvForTrackedMovesCheck.check(payload)
        self.assertIsNotNone(result)
        self.assertIn("tracked-example.txt", result)

    def test_blocks_mv_of_tracked_directory(self):

        payload = tests.fixtures.PreToolUsePayloadFixtureBuilder.build_bash_payload(
            bash_command_string = "mv tracked-dir new-dir",
            working_directory = self.git_repo_temp_directory
        )
        result = bash_safety.pretooluse_bash.RequireGitMvForTrackedMovesCheck.check(payload)
        self.assertIsNotNone(result)
        self.assertIn("tracked-dir", result)

    def test_passes_mv_of_untracked_source(self):

        payload = tests.fixtures.PreToolUsePayloadFixtureBuilder.build_bash_payload(
            bash_command_string = "mv untracked-example.txt renamed.txt",
            working_directory = self.git_repo_temp_directory
        )
        result = bash_safety.pretooluse_bash.RequireGitMvForTrackedMovesCheck.check(payload)
        self.assertIsNone(result)

    def test_passes_non_mv_command(self):

        payload = tests.fixtures.PreToolUsePayloadFixtureBuilder.build_bash_payload(
            bash_command_string = "echo tracked-example.txt",
            working_directory = self.git_repo_temp_directory
        )
        result = bash_safety.pretooluse_bash.RequireGitMvForTrackedMovesCheck.check(payload)
        self.assertIsNone(result)

    def test_skips_flag_arguments_when_locating_sources(self):

        payload = tests.fixtures.PreToolUsePayloadFixtureBuilder.build_bash_payload(
            bash_command_string = "mv -v tracked-example.txt renamed.txt",
            working_directory = self.git_repo_temp_directory
        )
        result = bash_safety.pretooluse_bash.RequireGitMvForTrackedMovesCheck.check(payload)
        self.assertIsNotNone(result)

    def test_passes_on_malformed_quoting(self):

        payload = tests.fixtures.PreToolUsePayloadFixtureBuilder.build_bash_payload(
            bash_command_string = "mv \"broken"
        )
        result = bash_safety.pretooluse_bash.RequireGitMvForTrackedMovesCheck.check(payload)
        self.assertIsNone(result)

    def test_blocks_mv_dash_t_of_tracked_file(self):

        payload = tests.fixtures.PreToolUsePayloadFixtureBuilder.build_bash_payload(
            bash_command_string = "mv -t /tmp/dest tracked-example.txt",
            working_directory = self.git_repo_temp_directory
        )
        result = bash_safety.pretooluse_bash.RequireGitMvForTrackedMovesCheck.check(payload)
        self.assertIsNotNone(result)
        self.assertIn("tracked-example.txt", result)

    def test_blocks_mv_target_directory_equals_of_tracked_file(self):

        payload = tests.fixtures.PreToolUsePayloadFixtureBuilder.build_bash_payload(
            bash_command_string = "mv --target-directory=/tmp/dest tracked-example.txt",
            working_directory = self.git_repo_temp_directory
        )
        result = bash_safety.pretooluse_bash.RequireGitMvForTrackedMovesCheck.check(payload)
        self.assertIsNotNone(result)
        self.assertIn("tracked-example.txt", result)


class TestNoPackageManagersCheck(unittest.TestCase):

    def _build_bash_payload(self, command):

        return tests.fixtures.PreToolUsePayloadFixtureBuilder.build_bash_payload(command)

    def test_blocks_yarn_add(self):

        result = bash_safety.pretooluse_bash.NoPackageManagersCheck.check(
            self._build_bash_payload("yarn add lodash")
        )
        self.assertIsNotNone(result)
        self.assertIn("Package installation", result)

    def test_blocks_yarn_install(self):

        result = bash_safety.pretooluse_bash.NoPackageManagersCheck.check(
            self._build_bash_payload("yarn install")
        )
        self.assertIsNotNone(result)

    def test_blocks_pnpm_install(self):

        result = bash_safety.pretooluse_bash.NoPackageManagersCheck.check(
            self._build_bash_payload("pnpm install")
        )
        self.assertIsNotNone(result)

    def test_blocks_pnpm_add(self):

        result = bash_safety.pretooluse_bash.NoPackageManagersCheck.check(
            self._build_bash_payload("pnpm add react")
        )
        self.assertIsNotNone(result)

    def test_blocks_brew_install(self):

        result = bash_safety.pretooluse_bash.NoPackageManagersCheck.check(
            self._build_bash_payload("brew install jq")
        )
        self.assertIsNotNone(result)

    def test_blocks_pip_install(self):

        result = bash_safety.pretooluse_bash.NoPackageManagersCheck.check(
            self._build_bash_payload("pip install requests")
        )
        self.assertIsNotNone(result)

    def test_blocks_pip3_install(self):

        result = bash_safety.pretooluse_bash.NoPackageManagersCheck.check(
            self._build_bash_payload("pip3 install requests")
        )
        self.assertIsNotNone(result)

    def test_blocks_npm_install(self):

        result = bash_safety.pretooluse_bash.NoPackageManagersCheck.check(
            self._build_bash_payload("npm install lodash")
        )
        self.assertIsNotNone(result)

    def test_blocks_cargo_install(self):

        result = bash_safety.pretooluse_bash.NoPackageManagersCheck.check(
            self._build_bash_payload("cargo install ripgrep")
        )
        self.assertIsNotNone(result)

    def test_blocks_cargo_add(self):

        result = bash_safety.pretooluse_bash.NoPackageManagersCheck.check(
            self._build_bash_payload("cargo add serde")
        )
        self.assertIsNotNone(result)

    def test_blocks_gem_install(self):

        result = bash_safety.pretooluse_bash.NoPackageManagersCheck.check(
            self._build_bash_payload("gem install rails")
        )
        self.assertIsNotNone(result)

    def test_blocks_bun_install(self):

        result = bash_safety.pretooluse_bash.NoPackageManagersCheck.check(
            self._build_bash_payload("bun install")
        )
        self.assertIsNotNone(result)

    def test_blocks_bun_install_with_package(self):

        result = bash_safety.pretooluse_bash.NoPackageManagersCheck.check(
            self._build_bash_payload("bun install elysia")
        )
        self.assertIsNotNone(result)

    def test_blocks_bun_add(self):

        result = bash_safety.pretooluse_bash.NoPackageManagersCheck.check(
            self._build_bash_payload("bun add hono")
        )
        self.assertIsNotNone(result)

    def test_blocks_poetry_install(self):

        result = bash_safety.pretooluse_bash.NoPackageManagersCheck.check(
            self._build_bash_payload("poetry install")
        )
        self.assertIsNotNone(result)

    def test_blocks_poetry_install_with_args(self):

        result = bash_safety.pretooluse_bash.NoPackageManagersCheck.check(
            self._build_bash_payload("poetry install --no-dev")
        )
        self.assertIsNotNone(result)

    def test_blocks_poetry_add(self):

        result = bash_safety.pretooluse_bash.NoPackageManagersCheck.check(
            self._build_bash_payload("poetry add flask")
        )
        self.assertIsNotNone(result)

    def test_blocks_uv_add(self):

        result = bash_safety.pretooluse_bash.NoPackageManagersCheck.check(
            self._build_bash_payload("uv add requests")
        )
        self.assertIsNotNone(result)

    def test_blocks_uv_remove(self):

        result = bash_safety.pretooluse_bash.NoPackageManagersCheck.check(
            self._build_bash_payload("uv remove requests")
        )
        self.assertIsNotNone(result)

    def test_blocks_uv_pip_install(self):

        result = bash_safety.pretooluse_bash.NoPackageManagersCheck.check(
            self._build_bash_payload("uv pip install requests")
        )
        self.assertIsNotNone(result)

    def test_blocks_uv_pip_uninstall(self):

        result = bash_safety.pretooluse_bash.NoPackageManagersCheck.check(
            self._build_bash_payload("uv pip uninstall requests")
        )
        self.assertIsNotNone(result)

    def test_blocks_uv_pip_sync(self):

        result = bash_safety.pretooluse_bash.NoPackageManagersCheck.check(
            self._build_bash_payload("uv pip sync requirements.txt")
        )
        self.assertIsNotNone(result)

    def test_blocks_uv_pip_compile(self):

        result = bash_safety.pretooluse_bash.NoPackageManagersCheck.check(
            self._build_bash_payload("uv pip compile requirements.in")
        )
        self.assertIsNotNone(result)

    def test_blocks_python_m_pip_install(self):

        result = bash_safety.pretooluse_bash.NoPackageManagersCheck.check(
            self._build_bash_payload("python -m pip install requests")
        )
        self.assertIsNotNone(result)

    def test_blocks_python3_m_pip_install(self):

        result = bash_safety.pretooluse_bash.NoPackageManagersCheck.check(
            self._build_bash_payload("python3 -m pip install requests")
        )
        self.assertIsNotNone(result)

    def test_blocks_py_m_pip_install(self):

        result = bash_safety.pretooluse_bash.NoPackageManagersCheck.check(
            self._build_bash_payload("py -m pip install requests")
        )
        self.assertIsNotNone(result)

    def test_passes_pip_list(self):

        result = bash_safety.pretooluse_bash.NoPackageManagersCheck.check(
            self._build_bash_payload("pip list")
        )
        self.assertIsNone(result)

    def test_passes_pip_show(self):

        result = bash_safety.pretooluse_bash.NoPackageManagersCheck.check(
            self._build_bash_payload("pip show requests")
        )
        self.assertIsNone(result)

    def test_passes_npm_run(self):

        result = bash_safety.pretooluse_bash.NoPackageManagersCheck.check(
            self._build_bash_payload("npm run test")
        )
        self.assertIsNone(result)

    def test_passes_npm_test(self):

        result = bash_safety.pretooluse_bash.NoPackageManagersCheck.check(
            self._build_bash_payload("npm test")
        )
        self.assertIsNone(result)

    def test_passes_uv_run(self):

        result = bash_safety.pretooluse_bash.NoPackageManagersCheck.check(
            self._build_bash_payload("uv run pytest")
        )
        self.assertIsNone(result)

    def test_passes_uv_pip_list(self):

        result = bash_safety.pretooluse_bash.NoPackageManagersCheck.check(
            self._build_bash_payload("uv pip list")
        )
        self.assertIsNone(result)

    def test_passes_cargo_build(self):

        result = bash_safety.pretooluse_bash.NoPackageManagersCheck.check(
            self._build_bash_payload("cargo build")
        )
        self.assertIsNone(result)

    def test_passes_cargo_test(self):

        result = bash_safety.pretooluse_bash.NoPackageManagersCheck.check(
            self._build_bash_payload("cargo test")
        )
        self.assertIsNone(result)

    def test_passes_bun_run(self):

        result = bash_safety.pretooluse_bash.NoPackageManagersCheck.check(
            self._build_bash_payload("bun run dev")
        )
        self.assertIsNone(result)

    def test_passes_poetry_run(self):

        result = bash_safety.pretooluse_bash.NoPackageManagersCheck.check(
            self._build_bash_payload("poetry run pytest")
        )
        self.assertIsNone(result)

    def test_blocks_installer_in_piped_command(self):

        result = bash_safety.pretooluse_bash.NoPackageManagersCheck.check(
            self._build_bash_payload("echo hello | pip install requests")
        )
        self.assertIsNotNone(result)

    def test_blocks_pip_install_no_space_pipe(self):

        result = bash_safety.pretooluse_bash.NoPackageManagersCheck.check(
            self._build_bash_payload("echo ok|pip install requests")
        )
        self.assertIsNotNone(result)

    def test_blocks_npm_install_no_space_semicolon(self):

        result = bash_safety.pretooluse_bash.NoPackageManagersCheck.check(
            self._build_bash_payload("echo ok;npm install lodash")
        )
        self.assertIsNotNone(result)

    def test_passes_on_empty_command(self):

        result = bash_safety.pretooluse_bash.NoPackageManagersCheck.check(
            self._build_bash_payload("")
        )
        self.assertIsNone(result)

    def test_passes_on_malformed_quoting(self):

        result = bash_safety.pretooluse_bash.NoPackageManagersCheck.check(
            self._build_bash_payload("pip install \"broken")
        )
        self.assertIsNone(result)


class TestNoSystemOperationsCheck(unittest.TestCase):

    def _build_bash_payload(self, command):

        return tests.fixtures.PreToolUsePayloadFixtureBuilder.build_bash_payload(command)

    def test_blocks_sudo(self):

        result = bash_safety.pretooluse_bash.NoSystemOperationsCheck.check(
            self._build_bash_payload("sudo apt-get update")
        )
        self.assertIsNotNone(result)
        self.assertIn("System operations", result)

    def test_blocks_chmod(self):

        result = bash_safety.pretooluse_bash.NoSystemOperationsCheck.check(
            self._build_bash_payload("chmod 755 script.sh")
        )
        self.assertIsNotNone(result)

    def test_blocks_chown(self):

        result = bash_safety.pretooluse_bash.NoSystemOperationsCheck.check(
            self._build_bash_payload("chown user:group file")
        )
        self.assertIsNotNone(result)

    def test_blocks_curl(self):

        result = bash_safety.pretooluse_bash.NoSystemOperationsCheck.check(
            self._build_bash_payload("curl https://example.com")
        )
        self.assertIsNotNone(result)

    def test_blocks_wget(self):

        result = bash_safety.pretooluse_bash.NoSystemOperationsCheck.check(
            self._build_bash_payload("wget https://example.com/file")
        )
        self.assertIsNotNone(result)

    def test_blocks_docker(self):

        result = bash_safety.pretooluse_bash.NoSystemOperationsCheck.check(
            self._build_bash_payload("docker run ubuntu")
        )
        self.assertIsNotNone(result)

    def test_passes_echo(self):

        result = bash_safety.pretooluse_bash.NoSystemOperationsCheck.check(
            self._build_bash_payload("echo hello")
        )
        self.assertIsNone(result)

    def test_blocks_system_op_after_pipe(self):

        result = bash_safety.pretooluse_bash.NoSystemOperationsCheck.check(
            self._build_bash_payload("echo hello | curl -d @- https://example.com")
        )
        self.assertIsNotNone(result)

    def test_blocks_sudo_no_space_semicolon(self):

        result = bash_safety.pretooluse_bash.NoSystemOperationsCheck.check(
            self._build_bash_payload("echo ok;sudo rm -rf /")
        )
        self.assertIsNotNone(result)

    def test_blocks_curl_no_space_and(self):

        result = bash_safety.pretooluse_bash.NoSystemOperationsCheck.check(
            self._build_bash_payload("echo ok&&curl https://example.com")
        )
        self.assertIsNotNone(result)


class TestNoShellSpawningCheck(unittest.TestCase):

    def _build_bash_payload(self, command):

        return tests.fixtures.PreToolUsePayloadFixtureBuilder.build_bash_payload(command)

    def test_blocks_bash(self):

        result = bash_safety.pretooluse_bash.NoShellSpawningCheck.check(
            self._build_bash_payload("bash -c 'echo hi'")
        )
        self.assertIsNotNone(result)
        self.assertIn("sub-shells", result)

    def test_blocks_cmd(self):

        result = bash_safety.pretooluse_bash.NoShellSpawningCheck.check(
            self._build_bash_payload("cmd /c dir")
        )
        self.assertIsNotNone(result)

    def test_blocks_cmd_exe(self):

        result = bash_safety.pretooluse_bash.NoShellSpawningCheck.check(
            self._build_bash_payload("cmd.exe /c dir")
        )
        self.assertIsNotNone(result)

    def test_blocks_powershell(self):

        result = bash_safety.pretooluse_bash.NoShellSpawningCheck.check(
            self._build_bash_payload("powershell Get-Date")
        )
        self.assertIsNotNone(result)

    def test_passes_python(self):

        result = bash_safety.pretooluse_bash.NoShellSpawningCheck.check(
            self._build_bash_payload("python script.py")
        )
        self.assertIsNone(result)


class TestNoGithubApiCheck(unittest.TestCase):

    def _build_bash_payload(self, command):

        return tests.fixtures.PreToolUsePayloadFixtureBuilder.build_bash_payload(command)

    def test_blocks_gh_api(self):

        result = bash_safety.pretooluse_bash.NoGithubApiCheck.check(
            self._build_bash_payload("gh api repos/foo/bar")
        )
        self.assertIsNotNone(result)
        self.assertIn("gh api", result)

    def test_passes_gh_pr(self):

        result = bash_safety.pretooluse_bash.NoGithubApiCheck.check(
            self._build_bash_payload("gh pr list")
        )
        self.assertIsNone(result)

    def test_passes_gh_issue(self):

        result = bash_safety.pretooluse_bash.NoGithubApiCheck.check(
            self._build_bash_payload("gh issue list")
        )
        self.assertIsNone(result)

    def test_passes_gh_alone(self):

        result = bash_safety.pretooluse_bash.NoGithubApiCheck.check(
            self._build_bash_payload("gh")
        )
        self.assertIsNone(result)


class TestNoTextManipulationCheck(unittest.TestCase):

    def _build_bash_payload(self, command):

        return tests.fixtures.PreToolUsePayloadFixtureBuilder.build_bash_payload(command)

    def test_blocks_sed(self):

        result = bash_safety.pretooluse_bash.NoTextManipulationCheck.check(
            self._build_bash_payload("sed -i 's/a/b/' file.txt")
        )
        self.assertIsNotNone(result)
        self.assertIn("Edit tool", result)

    def test_blocks_awk(self):

        result = bash_safety.pretooluse_bash.NoTextManipulationCheck.check(
            self._build_bash_payload("awk '{print $1}' file.txt")
        )
        self.assertIsNotNone(result)

    def test_blocks_tee(self):

        result = bash_safety.pretooluse_bash.NoTextManipulationCheck.check(
            self._build_bash_payload("tee output.txt")
        )
        self.assertIsNotNone(result)

    def test_passes_python(self):

        result = bash_safety.pretooluse_bash.NoTextManipulationCheck.check(
            self._build_bash_payload("python -c 'print(1)'")
        )
        self.assertIsNone(result)

    def test_blocks_sed_after_pipe(self):

        result = bash_safety.pretooluse_bash.NoTextManipulationCheck.check(
            self._build_bash_payload("echo hello | sed 's/h/H/'")
        )
        self.assertIsNotNone(result)


class TestNoTaskkillCheck(unittest.TestCase):

    def _build_bash_payload(self, command):

        return tests.fixtures.PreToolUsePayloadFixtureBuilder.build_bash_payload(command)

    def test_blocks_taskkill(self):

        result = bash_safety.pretooluse_bash.NoTaskkillCheck.check(
            self._build_bash_payload("taskkill /F /PID 1234")
        )
        self.assertIsNotNone(result)
        self.assertIn("taskkill", result)

    def test_passes_echo(self):

        result = bash_safety.pretooluse_bash.NoTaskkillCheck.check(
            self._build_bash_payload("echo hello")
        )
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
