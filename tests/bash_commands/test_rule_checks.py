import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "hooks"))

import tests.fixtures
from bash_commands.pretooluse_bash import PreToolUseBashCommandRuleChecks


class TestCheckAllowedCommand(unittest.TestCase):

    def _build(self, command):

        return tests.fixtures.PreToolUsePayloadFixtureBuilder.build_bash_payload(command)

    def test_allows_echo(self):

        self.assertTrue(PreToolUseBashCommandRuleChecks.check_allowed_command(self._build("echo hello")))

    def test_allows_printf(self):

        self.assertTrue(PreToolUseBashCommandRuleChecks.check_allowed_command(self._build("printf '%s' hello")))

    def test_allows_cp(self):

        self.assertTrue(PreToolUseBashCommandRuleChecks.check_allowed_command(self._build("cp src.txt dst.txt")))

    def test_allows_mkdir(self):

        self.assertTrue(PreToolUseBashCommandRuleChecks.check_allowed_command(self._build("mkdir -p new_dir")))

    def test_allows_mv(self):

        self.assertTrue(PreToolUseBashCommandRuleChecks.check_allowed_command(self._build("mv old.txt new.txt")))

    def test_allows_pwd(self):

        self.assertTrue(PreToolUseBashCommandRuleChecks.check_allowed_command(self._build("pwd")))

    def test_allows_touch(self):

        self.assertTrue(PreToolUseBashCommandRuleChecks.check_allowed_command(self._build("touch file.txt")))

    def test_allows_wc(self):

        self.assertTrue(PreToolUseBashCommandRuleChecks.check_allowed_command(self._build("wc -l file.txt")))

    def test_allows_which(self):

        self.assertTrue(PreToolUseBashCommandRuleChecks.check_allowed_command(self._build("which python")))

    def test_allows_cd(self):

        self.assertTrue(PreToolUseBashCommandRuleChecks.check_allowed_command(self._build("cd /tmp")))

    def test_allows_git_diff(self):

        self.assertTrue(PreToolUseBashCommandRuleChecks.check_allowed_command(self._build("git diff HEAD")))

    def test_allows_git_diff_no_args(self):

        self.assertTrue(PreToolUseBashCommandRuleChecks.check_allowed_command(self._build("git diff")))

    def test_allows_git_status(self):

        self.assertTrue(PreToolUseBashCommandRuleChecks.check_allowed_command(self._build("git status")))

    def test_allows_git_log(self):

        self.assertTrue(PreToolUseBashCommandRuleChecks.check_allowed_command(self._build("git log --oneline")))

    def test_allows_git_ls_files(self):

        self.assertTrue(PreToolUseBashCommandRuleChecks.check_allowed_command(self._build("git ls-files")))

    def test_allows_git_show(self):

        self.assertTrue(PreToolUseBashCommandRuleChecks.check_allowed_command(self._build("git show HEAD")))

    def test_allows_git_mv(self):

        self.assertTrue(PreToolUseBashCommandRuleChecks.check_allowed_command(self._build("git mv old.txt new.txt")))

    def test_rejects_git_alone(self):

        self.assertFalse(PreToolUseBashCommandRuleChecks.check_allowed_command(self._build("git")))

    def test_rejects_python(self):

        self.assertFalse(PreToolUseBashCommandRuleChecks.check_allowed_command(self._build("python script.py")))

    def test_rejects_npm_run(self):

        self.assertFalse(PreToolUseBashCommandRuleChecks.check_allowed_command(self._build("npm run test")))

    def test_rejects_gh_pr(self):

        self.assertFalse(PreToolUseBashCommandRuleChecks.check_allowed_command(self._build("gh pr list")))

    def test_rejects_empty_command(self):

        self.assertFalse(PreToolUseBashCommandRuleChecks.check_allowed_command(self._build("")))

    def test_rejects_malformed_quoting(self):

        self.assertFalse(PreToolUseBashCommandRuleChecks.check_allowed_command(self._build("echo \"broken")))


class TestCheckNoPackageManagers(unittest.TestCase):

    def _build(self, command):

        return tests.fixtures.PreToolUsePayloadFixtureBuilder.build_bash_payload(command)

    def test_blocks_yarn_add(self):

        result = PreToolUseBashCommandRuleChecks.check_no_package_managers(self._build("yarn add lodash"))
        self.assertIsNotNone(result)
        self.assertIn("Package installation", result)

    def test_blocks_yarn_install(self):

        result = PreToolUseBashCommandRuleChecks.check_no_package_managers(self._build("yarn install"))
        self.assertIsNotNone(result)

    def test_blocks_pnpm_install(self):

        result = PreToolUseBashCommandRuleChecks.check_no_package_managers(self._build("pnpm install"))
        self.assertIsNotNone(result)

    def test_blocks_pnpm_add(self):

        result = PreToolUseBashCommandRuleChecks.check_no_package_managers(self._build("pnpm add react"))
        self.assertIsNotNone(result)

    def test_blocks_brew_install(self):

        result = PreToolUseBashCommandRuleChecks.check_no_package_managers(self._build("brew install jq"))
        self.assertIsNotNone(result)

    def test_blocks_pip_install(self):

        result = PreToolUseBashCommandRuleChecks.check_no_package_managers(self._build("pip install requests"))
        self.assertIsNotNone(result)

    def test_blocks_pip3_install(self):

        result = PreToolUseBashCommandRuleChecks.check_no_package_managers(self._build("pip3 install requests"))
        self.assertIsNotNone(result)

    def test_blocks_npm_install(self):

        result = PreToolUseBashCommandRuleChecks.check_no_package_managers(self._build("npm install lodash"))
        self.assertIsNotNone(result)

    def test_blocks_cargo_install(self):

        result = PreToolUseBashCommandRuleChecks.check_no_package_managers(self._build("cargo install ripgrep"))
        self.assertIsNotNone(result)

    def test_blocks_cargo_add(self):

        result = PreToolUseBashCommandRuleChecks.check_no_package_managers(self._build("cargo add serde"))
        self.assertIsNotNone(result)

    def test_blocks_gem_install(self):

        result = PreToolUseBashCommandRuleChecks.check_no_package_managers(self._build("gem install rails"))
        self.assertIsNotNone(result)

    def test_blocks_bun_install(self):

        result = PreToolUseBashCommandRuleChecks.check_no_package_managers(self._build("bun install"))
        self.assertIsNotNone(result)

    def test_blocks_bun_install_with_package(self):

        result = PreToolUseBashCommandRuleChecks.check_no_package_managers(self._build("bun install elysia"))
        self.assertIsNotNone(result)

    def test_blocks_bun_add(self):

        result = PreToolUseBashCommandRuleChecks.check_no_package_managers(self._build("bun add hono"))
        self.assertIsNotNone(result)

    def test_blocks_poetry_install(self):

        result = PreToolUseBashCommandRuleChecks.check_no_package_managers(self._build("poetry install"))
        self.assertIsNotNone(result)

    def test_blocks_poetry_install_with_args(self):

        result = PreToolUseBashCommandRuleChecks.check_no_package_managers(self._build("poetry install --no-dev"))
        self.assertIsNotNone(result)

    def test_blocks_poetry_add(self):

        result = PreToolUseBashCommandRuleChecks.check_no_package_managers(self._build("poetry add flask"))
        self.assertIsNotNone(result)

    def test_blocks_uv_add(self):

        result = PreToolUseBashCommandRuleChecks.check_no_package_managers(self._build("uv add requests"))
        self.assertIsNotNone(result)

    def test_blocks_uv_remove(self):

        result = PreToolUseBashCommandRuleChecks.check_no_package_managers(self._build("uv remove requests"))
        self.assertIsNotNone(result)

    def test_blocks_uv_pip_install(self):

        result = PreToolUseBashCommandRuleChecks.check_no_package_managers(self._build("uv pip install requests"))
        self.assertIsNotNone(result)

    def test_blocks_uv_pip_uninstall(self):

        result = PreToolUseBashCommandRuleChecks.check_no_package_managers(self._build("uv pip uninstall requests"))
        self.assertIsNotNone(result)

    def test_blocks_uv_pip_sync(self):

        result = PreToolUseBashCommandRuleChecks.check_no_package_managers(self._build("uv pip sync requirements.txt"))
        self.assertIsNotNone(result)

    def test_blocks_uv_pip_compile(self):

        result = PreToolUseBashCommandRuleChecks.check_no_package_managers(self._build("uv pip compile requirements.in"))
        self.assertIsNotNone(result)

    def test_blocks_python_m_pip_install(self):

        result = PreToolUseBashCommandRuleChecks.check_no_package_managers(self._build("python -m pip install requests"))
        self.assertIsNotNone(result)

    def test_blocks_python3_m_pip_install(self):

        result = PreToolUseBashCommandRuleChecks.check_no_package_managers(self._build("python3 -m pip install requests"))
        self.assertIsNotNone(result)

    def test_blocks_py_m_pip_install(self):

        result = PreToolUseBashCommandRuleChecks.check_no_package_managers(self._build("py -m pip install requests"))
        self.assertIsNotNone(result)

    def test_passes_pip_list(self):

        result = PreToolUseBashCommandRuleChecks.check_no_package_managers(self._build("pip list"))
        self.assertIsNone(result)

    def test_passes_pip_show(self):

        result = PreToolUseBashCommandRuleChecks.check_no_package_managers(self._build("pip show requests"))
        self.assertIsNone(result)

    def test_passes_npm_run(self):

        result = PreToolUseBashCommandRuleChecks.check_no_package_managers(self._build("npm run test"))
        self.assertIsNone(result)

    def test_passes_npm_test(self):

        result = PreToolUseBashCommandRuleChecks.check_no_package_managers(self._build("npm test"))
        self.assertIsNone(result)

    def test_passes_uv_run(self):

        result = PreToolUseBashCommandRuleChecks.check_no_package_managers(self._build("uv run pytest"))
        self.assertIsNone(result)

    def test_passes_uv_pip_list(self):

        result = PreToolUseBashCommandRuleChecks.check_no_package_managers(self._build("uv pip list"))
        self.assertIsNone(result)

    def test_passes_cargo_build(self):

        result = PreToolUseBashCommandRuleChecks.check_no_package_managers(self._build("cargo build"))
        self.assertIsNone(result)

    def test_passes_cargo_test(self):

        result = PreToolUseBashCommandRuleChecks.check_no_package_managers(self._build("cargo test"))
        self.assertIsNone(result)

    def test_passes_bun_run(self):

        result = PreToolUseBashCommandRuleChecks.check_no_package_managers(self._build("bun run dev"))
        self.assertIsNone(result)

    def test_passes_poetry_run(self):

        result = PreToolUseBashCommandRuleChecks.check_no_package_managers(self._build("poetry run pytest"))
        self.assertIsNone(result)

    def test_blocks_installer_in_piped_command(self):

        result = PreToolUseBashCommandRuleChecks.check_no_package_managers(self._build("echo hello | pip install requests"))
        self.assertIsNotNone(result)

    def test_passes_on_empty_command(self):

        result = PreToolUseBashCommandRuleChecks.check_no_package_managers(self._build(""))
        self.assertIsNone(result)

    def test_passes_on_malformed_quoting(self):

        result = PreToolUseBashCommandRuleChecks.check_no_package_managers(self._build("pip install \"broken"))
        self.assertIsNone(result)


class TestCheckNoSystemOperations(unittest.TestCase):

    def _build(self, command):

        return tests.fixtures.PreToolUsePayloadFixtureBuilder.build_bash_payload(command)

    def test_blocks_sudo(self):

        result = PreToolUseBashCommandRuleChecks.check_no_system_operations(self._build("sudo apt-get update"))
        self.assertIsNotNone(result)
        self.assertIn("System operations", result)

    def test_blocks_chmod(self):

        result = PreToolUseBashCommandRuleChecks.check_no_system_operations(self._build("chmod 755 script.sh"))
        self.assertIsNotNone(result)

    def test_blocks_chown(self):

        result = PreToolUseBashCommandRuleChecks.check_no_system_operations(self._build("chown user:group file"))
        self.assertIsNotNone(result)

    def test_blocks_curl(self):

        result = PreToolUseBashCommandRuleChecks.check_no_system_operations(self._build("curl https://example.com"))
        self.assertIsNotNone(result)

    def test_blocks_wget(self):

        result = PreToolUseBashCommandRuleChecks.check_no_system_operations(self._build("wget https://example.com/file"))
        self.assertIsNotNone(result)

    def test_blocks_docker(self):

        result = PreToolUseBashCommandRuleChecks.check_no_system_operations(self._build("docker run ubuntu"))
        self.assertIsNotNone(result)

    def test_passes_echo(self):

        result = PreToolUseBashCommandRuleChecks.check_no_system_operations(self._build("echo hello"))
        self.assertIsNone(result)

    def test_blocks_system_op_after_pipe(self):

        result = PreToolUseBashCommandRuleChecks.check_no_system_operations(self._build("echo hello | curl -d @- https://example.com"))
        self.assertIsNotNone(result)


class TestCheckNoShellSpawning(unittest.TestCase):

    def _build(self, command):

        return tests.fixtures.PreToolUsePayloadFixtureBuilder.build_bash_payload(command)

    def test_blocks_bash(self):

        result = PreToolUseBashCommandRuleChecks.check_no_shell_spawning(self._build("bash -c 'echo hi'"))
        self.assertIsNotNone(result)
        self.assertIn("sub-shells", result)

    def test_blocks_cmd(self):

        result = PreToolUseBashCommandRuleChecks.check_no_shell_spawning(self._build("cmd /c dir"))
        self.assertIsNotNone(result)

    def test_blocks_cmd_exe(self):

        result = PreToolUseBashCommandRuleChecks.check_no_shell_spawning(self._build("cmd.exe /c dir"))
        self.assertIsNotNone(result)

    def test_blocks_powershell(self):

        result = PreToolUseBashCommandRuleChecks.check_no_shell_spawning(self._build("powershell Get-Date"))
        self.assertIsNotNone(result)

    def test_passes_python(self):

        result = PreToolUseBashCommandRuleChecks.check_no_shell_spawning(self._build("python script.py"))
        self.assertIsNone(result)


class TestCheckNoGithubApi(unittest.TestCase):

    def _build(self, command):

        return tests.fixtures.PreToolUsePayloadFixtureBuilder.build_bash_payload(command)

    def test_blocks_gh_api(self):

        result = PreToolUseBashCommandRuleChecks.check_no_github_api(self._build("gh api repos/foo/bar"))
        self.assertIsNotNone(result)
        self.assertIn("gh api", result)

    def test_passes_gh_pr(self):

        result = PreToolUseBashCommandRuleChecks.check_no_github_api(self._build("gh pr list"))
        self.assertIsNone(result)

    def test_passes_gh_issue(self):

        result = PreToolUseBashCommandRuleChecks.check_no_github_api(self._build("gh issue list"))
        self.assertIsNone(result)

    def test_passes_gh_alone(self):

        result = PreToolUseBashCommandRuleChecks.check_no_github_api(self._build("gh"))
        self.assertIsNone(result)


class TestCheckNoTextManipulation(unittest.TestCase):

    def _build(self, command):

        return tests.fixtures.PreToolUsePayloadFixtureBuilder.build_bash_payload(command)

    def test_blocks_sed(self):

        result = PreToolUseBashCommandRuleChecks.check_no_text_manipulation(self._build("sed -i 's/a/b/' file.txt"))
        self.assertIsNotNone(result)
        self.assertIn("Edit tool", result)

    def test_blocks_awk(self):

        result = PreToolUseBashCommandRuleChecks.check_no_text_manipulation(self._build("awk '{print $1}' file.txt"))
        self.assertIsNotNone(result)

    def test_blocks_tee(self):

        result = PreToolUseBashCommandRuleChecks.check_no_text_manipulation(self._build("tee output.txt"))
        self.assertIsNotNone(result)

    def test_passes_python(self):

        result = PreToolUseBashCommandRuleChecks.check_no_text_manipulation(self._build("python -c 'print(1)'"))
        self.assertIsNone(result)

    def test_blocks_sed_after_pipe(self):

        result = PreToolUseBashCommandRuleChecks.check_no_text_manipulation(self._build("echo hello | sed 's/h/H/'"))
        self.assertIsNotNone(result)


class TestCheckNoTaskkill(unittest.TestCase):

    def _build(self, command):

        return tests.fixtures.PreToolUsePayloadFixtureBuilder.build_bash_payload(command)

    def test_blocks_taskkill(self):

        result = PreToolUseBashCommandRuleChecks.check_no_taskkill(self._build("taskkill /F /PID 1234"))
        self.assertIsNotNone(result)
        self.assertIn("taskkill", result)

    def test_passes_echo(self):

        result = PreToolUseBashCommandRuleChecks.check_no_taskkill(self._build("echo hello"))
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
