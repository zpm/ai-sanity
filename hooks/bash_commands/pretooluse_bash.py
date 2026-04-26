import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common import _hook_io
from bash_commands._command_parser import BashCommandParser


class PreToolUseBashCommandRuleChecks:

    """Allow and deny rule checks for the Bash matcher. Each deny method takes the full PreToolUse payload dict and
    returns either a string deny-reason on violation or None to pass. The allow method returns True if the command
    should be auto-allowed without prompting."""

    _ALLOWED_SIMPLE_COMMANDS = frozenset({
        "cd", "cp", "mkdir", "mv", "pwd", "touch", "wc", "which", "echo", "printf",
    })

    _ALLOWED_GIT_SUBCOMMANDS = frozenset({
        "diff", "status", "log", "ls-files", "show", "mv",
    })

    _FULLY_DENIED_PACKAGE_MANAGERS = frozenset({"yarn", "pnpm", "brew"})

    _PACKAGE_MANAGER_DENIED_SUBCOMMANDS = {
        "pip": frozenset({"install"}),
        "pip3": frozenset({"install"}),
        "npm": frozenset({"install"}),
        "cargo": frozenset({"install", "add"}),
        "gem": frozenset({"install"}),
        "bun": frozenset({"install", "add"}),
        "poetry": frozenset({"add", "install"}),
    }

    _UV_DENIED_DIRECT_SUBCOMMANDS = frozenset({"add", "remove"})
    _UV_PIP_DENIED_SUBCOMMANDS = frozenset({"install", "uninstall", "sync", "compile"})

    _PYTHON_INTERPRETERS = frozenset({"python", "python3", "py"})

    _DENIED_SYSTEM_OPERATIONS = frozenset({"sudo", "chmod", "chown", "curl", "wget", "docker"})

    _DENIED_SHELL_SPAWNERS = frozenset({"bash", "cmd", "cmd.exe", "powershell"})

    _DENIED_TEXT_MANIPULATION = frozenset({"sed", "awk", "tee"})

    @staticmethod
    def check_allowed_command(pretooluse_payload):

        """Returns True if the first command clause starts with an allowed command (simple commands like echo, cp,
        mkdir, or git read-only subcommands). Only the first clause is checked since it determines the command
        identity; dangerous commands in later clauses are caught by the deny checks which run first."""
        bash_command_string = (pretooluse_payload.get("tool_input") or {}).get("command", "")
        clauses = BashCommandParser.extract_command_clauses(bash_command_string)
        if not clauses:
            return False
        checks = PreToolUseBashCommandRuleChecks
        first_clause = clauses[0]
        first_token = first_clause[0]
        if first_token in checks._ALLOWED_SIMPLE_COMMANDS:
            return True
        if first_token == "git":
            if len(first_clause) < 2:
                return False
            if first_clause[1] in checks._ALLOWED_GIT_SUBCOMMANDS:
                return True
        return False

    @staticmethod
    def check_no_package_managers(pretooluse_payload):

        """Rejects package manager install/add commands. Fully denies yarn, pnpm, and brew (all subcommands). For pip,
        npm, cargo, gem, bun, poetry, and uv, only denies install/add/remove subcommands. Also catches python -m pip
        install variants."""
        bash_command_string = (pretooluse_payload.get("tool_input") or {}).get("command", "")
        clauses = BashCommandParser.extract_command_clauses(bash_command_string)
        deny_message = "Package installation is strictly prohibited. Suggest the command to the user instead of running it."
        checks = PreToolUseBashCommandRuleChecks
        for clause in clauses:
            first = clause[0]
            second = clause[1] if len(clause) > 1 else None
            if first in checks._FULLY_DENIED_PACKAGE_MANAGERS:
                return deny_message
            if first in checks._PACKAGE_MANAGER_DENIED_SUBCOMMANDS:
                if second is not None and second in checks._PACKAGE_MANAGER_DENIED_SUBCOMMANDS[first]:
                    return deny_message
            if first == "uv" and second is not None:
                if second in checks._UV_DENIED_DIRECT_SUBCOMMANDS:
                    return deny_message
                if second == "pip":
                    third = clause[2] if len(clause) > 2 else None
                    if third is not None and third in checks._UV_PIP_DENIED_SUBCOMMANDS:
                        return deny_message
            if first in checks._PYTHON_INTERPRETERS and second == "-m":
                third = clause[2] if len(clause) > 2 else None
                fourth = clause[3] if len(clause) > 3 else None
                if third == "pip" and fourth == "install":
                    return deny_message
        return None

    @staticmethod
    def check_no_system_operations(pretooluse_payload):

        """Rejects sudo, chmod, chown, curl, wget, and docker commands."""
        bash_command_string = (pretooluse_payload.get("tool_input") or {}).get("command", "")
        clauses = BashCommandParser.extract_command_clauses(bash_command_string)
        checks = PreToolUseBashCommandRuleChecks
        for clause in clauses:
            if clause[0] in checks._DENIED_SYSTEM_OPERATIONS:
                return (
                    "System operations (sudo, chmod, chown, curl, wget, docker) are strictly prohibited."
                    " Have the user run the command instead."
                )
        return None

    @staticmethod
    def check_no_shell_spawning(pretooluse_payload):

        """Rejects bash, cmd, cmd.exe, and powershell sub-shell invocations."""
        bash_command_string = (pretooluse_payload.get("tool_input") or {}).get("command", "")
        clauses = BashCommandParser.extract_command_clauses(bash_command_string)
        checks = PreToolUseBashCommandRuleChecks
        for clause in clauses:
            if clause[0] in checks._DENIED_SHELL_SPAWNERS:
                return "Spawning sub-shells is strictly prohibited. Run commands directly."
        return None

    @staticmethod
    def check_no_github_api(pretooluse_payload):

        """Rejects gh api calls while allowing other gh subcommands (gh pr, gh issue, etc.)."""
        bash_command_string = (pretooluse_payload.get("tool_input") or {}).get("command", "")
        clauses = BashCommandParser.extract_command_clauses(bash_command_string)
        for clause in clauses:
            if clause[0] == "gh" and len(clause) > 1 and clause[1] == "api":
                return "Direct GitHub API calls via `gh api` are prohibited."
        return None

    @staticmethod
    def check_no_text_manipulation(pretooluse_payload):

        """Rejects sed, awk, and tee commands."""
        bash_command_string = (pretooluse_payload.get("tool_input") or {}).get("command", "")
        clauses = BashCommandParser.extract_command_clauses(bash_command_string)
        checks = PreToolUseBashCommandRuleChecks
        for clause in clauses:
            if clause[0] in checks._DENIED_TEXT_MANIPULATION:
                return "Text manipulation via sed/awk/tee is prohibited. Use the Edit tool instead."
        return None

    @staticmethod
    def check_no_taskkill(pretooluse_payload):

        """Rejects taskkill commands."""
        bash_command_string = (pretooluse_payload.get("tool_input") or {}).get("command", "")
        clauses = BashCommandParser.extract_command_clauses(bash_command_string)
        for clause in clauses:
            if clause[0] == "taskkill":
                return "Process termination via taskkill is prohibited. Have the user run the command instead."
        return None


class PreToolUseBashCommandHookEntry:

    """Composes Bash command rule checks: deny first, then allow, then passthrough."""

    _deny_check_methods_to_run_in_order = (
        PreToolUseBashCommandRuleChecks.check_no_package_managers,
        PreToolUseBashCommandRuleChecks.check_no_system_operations,
        PreToolUseBashCommandRuleChecks.check_no_shell_spawning,
        PreToolUseBashCommandRuleChecks.check_no_github_api,
        PreToolUseBashCommandRuleChecks.check_no_text_manipulation,
        PreToolUseBashCommandRuleChecks.check_no_taskkill,
    )

    @staticmethod
    def main():

        """Reads the payload, runs deny checks first (any violation blocks immediately), then checks if the command
        is in the allowed set (auto-permits without prompting), otherwise passes through to settings.json permission
        rules. Any unexpected error falls through to passthrough so a bug in this hook cannot block a command."""
        try:
            pretooluse_payload = _hook_io.PreToolUseHookIo.read_pretooluse_payload_from_stdin()
            for deny_check_method in PreToolUseBashCommandHookEntry._deny_check_methods_to_run_in_order:
                deny_reason_or_none = deny_check_method(pretooluse_payload)
                if deny_reason_or_none is not None:
                    _hook_io.PreToolUseHookIo.emit_deny_decision_and_exit(deny_reason_or_none)
            if PreToolUseBashCommandRuleChecks.check_allowed_command(pretooluse_payload):
                _hook_io.PreToolUseHookIo.emit_allow_decision_and_exit()
            _hook_io.PreToolUseHookIo.emit_passthrough_and_exit()
        except Exception:
            _hook_io.PreToolUseHookIo.emit_passthrough_and_exit()


if __name__ == "__main__":
    PreToolUseBashCommandHookEntry.main()
