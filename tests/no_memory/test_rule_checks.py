########################################################################################################################
# tests/no_memory/test_rule_checks.py
#
# no-memory rule-check tests
########################################################################################################################


import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "hooks"))

import tests._common.fixtures
import no_memory.pretooluse_bash
import no_memory.pretooluse_read


PRE_TOOL_USE_BASH_MEMORY_RULE_CHECKS = no_memory.pretooluse_bash.PreToolUseBashMemoryRuleChecks
PRE_TOOL_USE_READ_RULE_CHECKS = no_memory.pretooluse_read.PreToolUseReadRuleChecks


class TestCheckNoMemoryAccess(unittest.TestCase):

    def test_blocks_read_under_auto_memory_directory(self):

        payload = tests._common.fixtures.PreToolUsePayloadFixtureBuilder.build_read_payload(
            file_path = "/c/Users/zachm/.claude/projects/abc/memory/example.md"
        )
        deny_reason = PRE_TOOL_USE_READ_RULE_CHECKS.check_no_memory_access_for_read_or_glob_or_grep(payload)
        self.assertIsNotNone(deny_reason)


    def test_blocks_read_of_memory_md_filename_anywhere(self):

        payload = tests._common.fixtures.PreToolUsePayloadFixtureBuilder.build_read_payload(
            file_path = "/some/dir/MEMORY.md"
        )
        deny_reason = PRE_TOOL_USE_READ_RULE_CHECKS.check_no_memory_access_for_read_or_glob_or_grep(payload)
        self.assertIsNotNone(deny_reason)


    def test_blocks_glob_pattern_targeting_memory_md(self):

        payload = tests._common.fixtures.PreToolUsePayloadFixtureBuilder.build_glob_payload(
            glob_pattern_string = "**/MEMORY.md"
        )
        deny_reason = PRE_TOOL_USE_READ_RULE_CHECKS.check_no_memory_access_for_read_or_glob_or_grep(payload)
        self.assertIsNotNone(deny_reason)


    def test_passes_grep_for_literal_memory_md_string_inside_files(self):

        payload = tests._common.fixtures.PreToolUsePayloadFixtureBuilder.build_grep_payload(
            grep_pattern = "MEMORY.md",
            grep_path = "/tmp/some-project"
        )
        deny_reason = PRE_TOOL_USE_READ_RULE_CHECKS.check_no_memory_access_for_read_or_glob_or_grep(payload)
        self.assertIsNone(deny_reason)


    def test_blocks_grep_with_path_inside_memory_directory(self):

        payload = tests._common.fixtures.PreToolUsePayloadFixtureBuilder.build_grep_payload(
            grep_pattern = "anything",
            grep_path = "/c/Users/zachm/.claude/projects/abc/memory"
        )
        deny_reason = PRE_TOOL_USE_READ_RULE_CHECKS.check_no_memory_access_for_read_or_glob_or_grep(payload)
        self.assertIsNotNone(deny_reason)


    def test_blocks_bash_cd_into_memory_directory(self):

        payload = tests._common.fixtures.PreToolUsePayloadFixtureBuilder.build_bash_payload(
            bash_command_string = "cd ~/.claude/projects/abc/memory && touch foo.md"
        )
        deny_reason = PRE_TOOL_USE_BASH_MEMORY_RULE_CHECKS.check_no_memory_access_for_bash(payload)
        self.assertIsNotNone(deny_reason)


    def test_passes_bash_echo_mentioning_memory_md_substring(self):

        payload = tests._common.fixtures.PreToolUsePayloadFixtureBuilder.build_bash_payload(
            bash_command_string = "echo 'search for MEMORY.md term'"
        )
        deny_reason = PRE_TOOL_USE_BASH_MEMORY_RULE_CHECKS.check_no_memory_access_for_bash(payload)
        self.assertIsNone(deny_reason)


    def test_passes_read_under_plans_directory(self):

        payload = tests._common.fixtures.PreToolUsePayloadFixtureBuilder.build_read_payload(
            file_path = "/c/Users/zachm/.claude/plans/example.md"
        )
        deny_reason = PRE_TOOL_USE_READ_RULE_CHECKS.check_no_memory_access_for_read_or_glob_or_grep(payload)
        self.assertIsNone(deny_reason)


    def test_passes_unrelated_path(self):

        payload = tests._common.fixtures.PreToolUsePayloadFixtureBuilder.build_read_payload(
            file_path = "/tmp/foo.txt"
        )
        deny_reason = PRE_TOOL_USE_READ_RULE_CHECKS.check_no_memory_access_for_read_or_glob_or_grep(payload)
        self.assertIsNone(deny_reason)


if __name__ == "__main__":
    unittest.main()
