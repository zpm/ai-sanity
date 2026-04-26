import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "hooks"))

import tests._common.fixtures
import tests.required_reading.fixtures_required_reads
import tests._common.subprocess_helpers
import required_reading._manifest


class PreToolUseRequiredReadsSubprocessTestCase(
    tests.required_reading.fixtures_required_reads.HomeOverrideEnvVarTestCaseMixin,
    unittest.TestCase
):

    def test_edit_of_python_file_with_matching_rule_emits_deny_envelope(self):

        python_style_doc_abs_path = os.path.join(self.sandboxed_home_abs_path, "python.md")
        with open(python_style_doc_abs_path, "w", encoding = "utf-8") as open_doc_file_handle:
            open_doc_file_handle.write("# python style\n")
        tests.required_reading.fixtures_required_reads.RequiredReadsManifestFixtureBuilder.write_manifest_file(
            manifest_directory_abs_path = self.sandboxed_home_abs_path,
            rule_dicts = [
                {"extension": ".py", "read": python_style_doc_abs_path}
            ]
        )
        edited_file_abs_path = os.path.join(self.sandboxed_home_abs_path, "project", "src", "main.py")
        os.makedirs(os.path.dirname(edited_file_abs_path), exist_ok = True)
        exit_code, parsed_stdout = tests._common.subprocess_helpers.HookEntryScriptInvocationHelper.invoke_entry_script(
            entry_script_relative_path = "required_reading/pretooluse.py",
            pretooluse_payload = tests._common.fixtures.PreToolUsePayloadFixtureBuilder.build_edit_payload(
                new_string_content = "x",
                file_path = edited_file_abs_path
            )
        )
        tests._common.subprocess_helpers.HookEntryScriptInvocationHelper.assert_deny_decision(
            self, exit_code, parsed_stdout, expected_message_substring = "python.md"
        )

    def test_edit_of_unmatched_file_passes_through(self):

        python_style_doc_abs_path = os.path.join(self.sandboxed_home_abs_path, "python.md")
        with open(python_style_doc_abs_path, "w", encoding = "utf-8") as open_doc_file_handle:
            open_doc_file_handle.write("# python style\n")
        tests.required_reading.fixtures_required_reads.RequiredReadsManifestFixtureBuilder.write_manifest_file(
            manifest_directory_abs_path = self.sandboxed_home_abs_path,
            rule_dicts = [
                {"extension": ".py", "read": python_style_doc_abs_path}
            ]
        )
        edited_file_abs_path = os.path.join(self.sandboxed_home_abs_path, "notes.txt")
        exit_code, parsed_stdout = tests._common.subprocess_helpers.HookEntryScriptInvocationHelper.invoke_entry_script(
            entry_script_relative_path = "required_reading/pretooluse.py",
            pretooluse_payload = tests._common.fixtures.PreToolUsePayloadFixtureBuilder.build_edit_payload(
                new_string_content = "x",
                file_path = edited_file_abs_path
            )
        )
        tests._common.subprocess_helpers.HookEntryScriptInvocationHelper.assert_passthrough(self, exit_code, parsed_stdout)

    def test_deny_message_lists_every_unsatisfied_rule_read_target(self):

        python_style_doc_abs_path = os.path.join(self.sandboxed_home_abs_path, "python.md")
        claude_md_abs_path = os.path.join(self.sandboxed_home_abs_path, "CLAUDE.md")
        with open(python_style_doc_abs_path, "w", encoding = "utf-8") as open_doc_file_handle:
            open_doc_file_handle.write("# python style")
        with open(claude_md_abs_path, "w", encoding = "utf-8") as open_doc_file_handle:
            open_doc_file_handle.write("# claude md")
        tests.required_reading.fixtures_required_reads.RequiredReadsManifestFixtureBuilder.write_manifest_file(
            manifest_directory_abs_path = self.sandboxed_home_abs_path,
            rule_dicts = [
                {"read": claude_md_abs_path},
                {"extension": ".py", "read": python_style_doc_abs_path}
            ]
        )
        edited_file_abs_path = os.path.join(self.sandboxed_home_abs_path, "main.py")
        exit_code, parsed_stdout = tests._common.subprocess_helpers.HookEntryScriptInvocationHelper.invoke_entry_script(
            entry_script_relative_path = "required_reading/pretooluse.py",
            pretooluse_payload = tests._common.fixtures.PreToolUsePayloadFixtureBuilder.build_edit_payload(
                new_string_content = "x",
                file_path = edited_file_abs_path
            )
        )
        tests._common.subprocess_helpers.HookEntryScriptInvocationHelper.assert_deny_decision(self, exit_code, parsed_stdout)
        permission_decision_reason_value = parsed_stdout["hookSpecificOutput"]["permissionDecisionReason"]
        self.assertIn("python.md", permission_decision_reason_value)
        self.assertIn("claude.md", permission_decision_reason_value)

    def test_malformed_project_manifest_does_not_prevent_global_rule_from_firing(self):

        python_style_doc_abs_path = os.path.join(self.sandboxed_home_abs_path, "python.md")
        with open(python_style_doc_abs_path, "w", encoding = "utf-8") as open_doc_file_handle:
            open_doc_file_handle.write("# python style")
        tests.required_reading.fixtures_required_reads.RequiredReadsManifestFixtureBuilder.write_manifest_file(
            manifest_directory_abs_path = self.sandboxed_home_abs_path,
            rule_dicts = [
                {"extension": ".py", "read": python_style_doc_abs_path}
            ]
        )
        project_directory_abs_path = os.path.join(self.sandboxed_home_abs_path, "project")
        os.makedirs(project_directory_abs_path, exist_ok = True)
        tests.required_reading.fixtures_required_reads.RequiredReadsManifestFixtureBuilder.write_raw_manifest_body(
            manifest_directory_abs_path = project_directory_abs_path,
            raw_manifest_body_string = "{this is not valid json at all"
        )
        edited_file_abs_path = os.path.join(project_directory_abs_path, "src", "main.py")
        os.makedirs(os.path.dirname(edited_file_abs_path), exist_ok = True)
        exit_code, parsed_stdout = tests._common.subprocess_helpers.HookEntryScriptInvocationHelper.invoke_entry_script(
            entry_script_relative_path = "required_reading/pretooluse.py",
            pretooluse_payload = tests._common.fixtures.PreToolUsePayloadFixtureBuilder.build_edit_payload(
                new_string_content = "x",
                file_path = edited_file_abs_path
            )
        )
        tests._common.subprocess_helpers.HookEntryScriptInvocationHelper.assert_deny_decision(
            self, exit_code, parsed_stdout, expected_message_substring = "python.md"
        )

    def test_notebook_edit_with_matching_rule_emits_deny(self):

        notebook_style_doc_abs_path = os.path.join(self.sandboxed_home_abs_path, "notebook-style.md")
        with open(notebook_style_doc_abs_path, "w", encoding = "utf-8") as open_doc_file_handle:
            open_doc_file_handle.write("# notebook style")
        tests.required_reading.fixtures_required_reads.RequiredReadsManifestFixtureBuilder.write_manifest_file(
            manifest_directory_abs_path = self.sandboxed_home_abs_path,
            rule_dicts = [
                {"extension": ".ipynb", "read": notebook_style_doc_abs_path}
            ]
        )
        edited_notebook_abs_path = os.path.join(self.sandboxed_home_abs_path, "analysis.ipynb")
        notebook_edit_payload = tests._common.fixtures.PreToolUsePayloadFixtureBuilder.build_base_payload(
            tool_name = "NotebookEdit",
            tool_input = {
                "notebook_path": edited_notebook_abs_path,
                "new_source": "print('x')",
                "cell_id": "cell-0"
            }
        )
        exit_code, parsed_stdout = tests._common.subprocess_helpers.HookEntryScriptInvocationHelper.invoke_entry_script(
            entry_script_relative_path = "required_reading/pretooluse.py",
            pretooluse_payload = notebook_edit_payload
        )
        tests._common.subprocess_helpers.HookEntryScriptInvocationHelper.assert_deny_decision(
            self, exit_code, parsed_stdout, expected_message_substring = "notebook-style.md"
        )

    def test_payload_missing_file_path_field_passes_through(self):

        malformed_edit_payload = tests._common.fixtures.PreToolUsePayloadFixtureBuilder.build_base_payload(
            tool_name = "Edit",
            tool_input = {}
        )
        exit_code, parsed_stdout = tests._common.subprocess_helpers.HookEntryScriptInvocationHelper.invoke_entry_script(
            entry_script_relative_path = "required_reading/pretooluse.py",
            pretooluse_payload = malformed_edit_payload
        )
        tests._common.subprocess_helpers.HookEntryScriptInvocationHelper.assert_passthrough(self, exit_code, parsed_stdout)

    def test_read_of_python_file_with_matching_rule_emits_deny_envelope(self):

        python_style_doc_abs_path = os.path.join(self.sandboxed_home_abs_path, "python.md")
        with open(python_style_doc_abs_path, "w", encoding = "utf-8") as open_doc_file_handle:
            open_doc_file_handle.write("# python style\n")
        tests.required_reading.fixtures_required_reads.RequiredReadsManifestFixtureBuilder.write_manifest_file(
            manifest_directory_abs_path = self.sandboxed_home_abs_path,
            rule_dicts = [
                {"extension": ".py", "read": python_style_doc_abs_path}
            ]
        )
        read_target_abs_path = os.path.join(self.sandboxed_home_abs_path, "project", "src", "main.py")
        os.makedirs(os.path.dirname(read_target_abs_path), exist_ok = True)
        exit_code, parsed_stdout = tests._common.subprocess_helpers.HookEntryScriptInvocationHelper.invoke_entry_script(
            entry_script_relative_path = "required_reading/pretooluse.py",
            pretooluse_payload = tests._common.fixtures.PreToolUsePayloadFixtureBuilder.build_read_payload(
                file_path = read_target_abs_path
            )
        )
        tests._common.subprocess_helpers.HookEntryScriptInvocationHelper.assert_deny_decision(
            self, exit_code, parsed_stdout, expected_message_substring = "python.md"
        )

    def test_read_of_wildcard_only_file_demands_global_claude_md(self):

        claude_md_abs_path = os.path.join(self.sandboxed_home_abs_path, "CLAUDE.md")
        with open(claude_md_abs_path, "w", encoding = "utf-8") as open_doc_file_handle:
            open_doc_file_handle.write("# claude md\n")
        tests.required_reading.fixtures_required_reads.RequiredReadsManifestFixtureBuilder.write_manifest_file(
            manifest_directory_abs_path = self.sandboxed_home_abs_path,
            rule_dicts = [
                {"read": claude_md_abs_path}
            ]
        )
        unrelated_read_target_abs_path = os.path.join(self.sandboxed_home_abs_path, "notes.txt")
        exit_code, parsed_stdout = tests._common.subprocess_helpers.HookEntryScriptInvocationHelper.invoke_entry_script(
            entry_script_relative_path = "required_reading/pretooluse.py",
            pretooluse_payload = tests._common.fixtures.PreToolUsePayloadFixtureBuilder.build_read_payload(
                file_path = unrelated_read_target_abs_path
            )
        )
        tests._common.subprocess_helpers.HookEntryScriptInvocationHelper.assert_deny_decision(
            self, exit_code, parsed_stdout, expected_message_substring = "claude.md"
        )

    def test_read_of_cross_target_doc_passes_through_even_when_wildcard_rule_unsatisfied(self):

        python_style_doc_abs_path = os.path.join(self.sandboxed_home_abs_path, "python.md")
        claude_md_abs_path = os.path.join(self.sandboxed_home_abs_path, "CLAUDE.md")
        with open(python_style_doc_abs_path, "w", encoding = "utf-8") as open_doc_file_handle:
            open_doc_file_handle.write("# python style\n")
        with open(claude_md_abs_path, "w", encoding = "utf-8") as open_doc_file_handle:
            open_doc_file_handle.write("# claude md\n")
        tests.required_reading.fixtures_required_reads.RequiredReadsManifestFixtureBuilder.write_manifest_file(
            manifest_directory_abs_path = self.sandboxed_home_abs_path,
            rule_dicts = [
                {"read": claude_md_abs_path},
                {"extension": ".py", "read": python_style_doc_abs_path}
            ]
        )
        exit_code, parsed_stdout = tests._common.subprocess_helpers.HookEntryScriptInvocationHelper.invoke_entry_script(
            entry_script_relative_path = "required_reading/pretooluse.py",
            pretooluse_payload = tests._common.fixtures.PreToolUsePayloadFixtureBuilder.build_read_payload(
                file_path = python_style_doc_abs_path
            )
        )
        tests._common.subprocess_helpers.HookEntryScriptInvocationHelper.assert_passthrough(self, exit_code, parsed_stdout)

    def test_read_of_self_target_doc_passes_through_to_break_deadlock(self):

        markdown_style_doc_abs_path = os.path.join(self.sandboxed_home_abs_path, "markdown.md")
        with open(markdown_style_doc_abs_path, "w", encoding = "utf-8") as open_doc_file_handle:
            open_doc_file_handle.write("# markdown style\n")
        tests.required_reading.fixtures_required_reads.RequiredReadsManifestFixtureBuilder.write_manifest_file(
            manifest_directory_abs_path = self.sandboxed_home_abs_path,
            rule_dicts = [
                {"extension": ".md", "read": markdown_style_doc_abs_path}
            ]
        )
        exit_code, parsed_stdout = tests._common.subprocess_helpers.HookEntryScriptInvocationHelper.invoke_entry_script(
            entry_script_relative_path = "required_reading/pretooluse.py",
            pretooluse_payload = tests._common.fixtures.PreToolUsePayloadFixtureBuilder.build_read_payload(
                file_path = markdown_style_doc_abs_path
            )
        )
        tests._common.subprocess_helpers.HookEntryScriptInvocationHelper.assert_passthrough(self, exit_code, parsed_stdout)

    def test_edit_of_self_target_doc_still_demands_prior_read(self):

        markdown_style_doc_abs_path = os.path.join(self.sandboxed_home_abs_path, "markdown.md")
        with open(markdown_style_doc_abs_path, "w", encoding = "utf-8") as open_doc_file_handle:
            open_doc_file_handle.write("# markdown style\n")
        tests.required_reading.fixtures_required_reads.RequiredReadsManifestFixtureBuilder.write_manifest_file(
            manifest_directory_abs_path = self.sandboxed_home_abs_path,
            rule_dicts = [
                {"extension": ".md", "read": markdown_style_doc_abs_path}
            ]
        )
        exit_code, parsed_stdout = tests._common.subprocess_helpers.HookEntryScriptInvocationHelper.invoke_entry_script(
            entry_script_relative_path = "required_reading/pretooluse.py",
            pretooluse_payload = tests._common.fixtures.PreToolUsePayloadFixtureBuilder.build_edit_payload(
                new_string_content = "x",
                file_path = markdown_style_doc_abs_path
            )
        )
        tests._common.subprocess_helpers.HookEntryScriptInvocationHelper.assert_deny_decision(
            self, exit_code, parsed_stdout, expected_message_substring = "markdown.md"
        )

    def test_read_of_unmatched_file_with_no_wildcard_rule_passes_through(self):

        python_style_doc_abs_path = os.path.join(self.sandboxed_home_abs_path, "python.md")
        with open(python_style_doc_abs_path, "w", encoding = "utf-8") as open_doc_file_handle:
            open_doc_file_handle.write("# python style\n")
        tests.required_reading.fixtures_required_reads.RequiredReadsManifestFixtureBuilder.write_manifest_file(
            manifest_directory_abs_path = self.sandboxed_home_abs_path,
            rule_dicts = [
                {"extension": ".py", "read": python_style_doc_abs_path}
            ]
        )
        read_target_abs_path = os.path.join(self.sandboxed_home_abs_path, "notes.txt")
        exit_code, parsed_stdout = tests._common.subprocess_helpers.HookEntryScriptInvocationHelper.invoke_entry_script(
            entry_script_relative_path = "required_reading/pretooluse.py",
            pretooluse_payload = tests._common.fixtures.PreToolUsePayloadFixtureBuilder.build_read_payload(
                file_path = read_target_abs_path
            )
        )
        tests._common.subprocess_helpers.HookEntryScriptInvocationHelper.assert_passthrough(self, exit_code, parsed_stdout)

    def test_project_override_silences_global_rule_end_to_end(self):

        hooks_repo_root_abs_path = required_reading._manifest.RequiredReadsManifestLoader.get_hooks_repo_root_abs_path()
        hooks_repo_python_style_abs_path = os.path.join(hooks_repo_root_abs_path, "styleguides", "python.md")
        project_directory_abs_path = os.path.join(self.sandboxed_home_abs_path, "project")
        project_python_doc_abs_path = os.path.join(project_directory_abs_path, "project-python.md")
        os.makedirs(project_directory_abs_path, exist_ok = True)
        with open(project_python_doc_abs_path, "w", encoding = "utf-8") as open_doc_file_handle:
            open_doc_file_handle.write("# project python style")
        tests.required_reading.fixtures_required_reads.RequiredReadsManifestFixtureBuilder.write_manifest_file(
            manifest_directory_abs_path = project_directory_abs_path,
            rule_dicts = [
                {
                    "extension": ".py",
                    "read": project_python_doc_abs_path,
                    "override": hooks_repo_python_style_abs_path
                }
            ]
        )
        edited_file_abs_path = os.path.join(project_directory_abs_path, "src", "main.py")
        os.makedirs(os.path.dirname(edited_file_abs_path), exist_ok = True)
        exit_code, parsed_stdout = tests._common.subprocess_helpers.HookEntryScriptInvocationHelper.invoke_entry_script(
            entry_script_relative_path = "required_reading/pretooluse.py",
            pretooluse_payload = tests._common.fixtures.PreToolUsePayloadFixtureBuilder.build_edit_payload(
                new_string_content = "x",
                file_path = edited_file_abs_path
            )
        )
        tests._common.subprocess_helpers.HookEntryScriptInvocationHelper.assert_deny_decision(self, exit_code, parsed_stdout)
        permission_decision_reason_value = parsed_stdout["hookSpecificOutput"]["permissionDecisionReason"]
        self.assertIn("project-python.md", permission_decision_reason_value)
        self.assertNotIn("styleguides/python.md", permission_decision_reason_value)

    def test_read_of_claude_md_passes_through_without_styleguide(self):

        markdown_style_doc_abs_path = os.path.join(self.sandboxed_home_abs_path, "markdown.md")
        with open(markdown_style_doc_abs_path, "w", encoding = "utf-8") as open_doc_file_handle:
            open_doc_file_handle.write("# markdown style\n")
        tests.required_reading.fixtures_required_reads.RequiredReadsManifestFixtureBuilder.write_manifest_file(
            manifest_directory_abs_path = self.sandboxed_home_abs_path,
            rule_dicts = [
                {"extension": ".md", "read": markdown_style_doc_abs_path}
            ]
        )
        claude_md_abs_path = os.path.join(self.sandboxed_home_abs_path, "project", "CLAUDE.md")
        os.makedirs(os.path.dirname(claude_md_abs_path), exist_ok = True)
        exit_code, parsed_stdout = tests._common.subprocess_helpers.HookEntryScriptInvocationHelper.invoke_entry_script(
            entry_script_relative_path = "required_reading/pretooluse.py",
            pretooluse_payload = tests._common.fixtures.PreToolUsePayloadFixtureBuilder.build_read_payload(
                file_path = claude_md_abs_path
            )
        )
        tests._common.subprocess_helpers.HookEntryScriptInvocationHelper.assert_passthrough(self, exit_code, parsed_stdout)

    def test_read_of_agents_md_passes_through_without_styleguide(self):

        markdown_style_doc_abs_path = os.path.join(self.sandboxed_home_abs_path, "markdown.md")
        with open(markdown_style_doc_abs_path, "w", encoding = "utf-8") as open_doc_file_handle:
            open_doc_file_handle.write("# markdown style\n")
        tests.required_reading.fixtures_required_reads.RequiredReadsManifestFixtureBuilder.write_manifest_file(
            manifest_directory_abs_path = self.sandboxed_home_abs_path,
            rule_dicts = [
                {"extension": ".md", "read": markdown_style_doc_abs_path}
            ]
        )
        agents_md_abs_path = os.path.join(self.sandboxed_home_abs_path, "project", "agents.md")
        os.makedirs(os.path.dirname(agents_md_abs_path), exist_ok = True)
        exit_code, parsed_stdout = tests._common.subprocess_helpers.HookEntryScriptInvocationHelper.invoke_entry_script(
            entry_script_relative_path = "required_reading/pretooluse.py",
            pretooluse_payload = tests._common.fixtures.PreToolUsePayloadFixtureBuilder.build_read_payload(
                file_path = agents_md_abs_path
            )
        )
        tests._common.subprocess_helpers.HookEntryScriptInvocationHelper.assert_passthrough(self, exit_code, parsed_stdout)

    def test_edit_of_claude_md_still_demands_styleguide(self):

        markdown_style_doc_abs_path = os.path.join(self.sandboxed_home_abs_path, "markdown.md")
        with open(markdown_style_doc_abs_path, "w", encoding = "utf-8") as open_doc_file_handle:
            open_doc_file_handle.write("# markdown style\n")
        tests.required_reading.fixtures_required_reads.RequiredReadsManifestFixtureBuilder.write_manifest_file(
            manifest_directory_abs_path = self.sandboxed_home_abs_path,
            rule_dicts = [
                {"extension": ".md", "read": markdown_style_doc_abs_path}
            ]
        )
        claude_md_abs_path = os.path.join(self.sandboxed_home_abs_path, "project", "CLAUDE.md")
        os.makedirs(os.path.dirname(claude_md_abs_path), exist_ok = True)
        exit_code, parsed_stdout = tests._common.subprocess_helpers.HookEntryScriptInvocationHelper.invoke_entry_script(
            entry_script_relative_path = "required_reading/pretooluse.py",
            pretooluse_payload = tests._common.fixtures.PreToolUsePayloadFixtureBuilder.build_edit_payload(
                new_string_content = "x",
                file_path = claude_md_abs_path
            )
        )
        tests._common.subprocess_helpers.HookEntryScriptInvocationHelper.assert_deny_decision(
            self, exit_code, parsed_stdout, expected_message_substring = "markdown.md"
        )

    def test_rule_with_missing_read_target_hard_fails_with_configuration_error(self):

        tests.required_reading.fixtures_required_reads.RequiredReadsManifestFixtureBuilder.write_manifest_file(
            manifest_directory_abs_path = self.sandboxed_home_abs_path,
            rule_dicts = [
                {
                    "extension": ".py",
                    "read": os.path.join(self.sandboxed_home_abs_path, "does-not-exist.md")
                }
            ]
        )
        edited_file_abs_path = os.path.join(self.sandboxed_home_abs_path, "main.py")
        exit_code, parsed_stdout = tests._common.subprocess_helpers.HookEntryScriptInvocationHelper.invoke_entry_script(
            entry_script_relative_path = "required_reading/pretooluse.py",
            pretooluse_payload = tests._common.fixtures.PreToolUsePayloadFixtureBuilder.build_edit_payload(
                new_string_content = "x",
                file_path = edited_file_abs_path
            )
        )
        tests._common.subprocess_helpers.HookEntryScriptInvocationHelper.assert_deny_decision(
            self, exit_code, parsed_stdout, expected_message_substring = "configuration error"
        )


class PostToolUseReadObserverSubprocessTestCase(
    tests.required_reading.fixtures_required_reads.HomeOverrideEnvVarTestCaseMixin,
    unittest.TestCase
):

    def test_read_of_required_doc_causes_next_pretooluse_edit_to_pass_through(self):

        python_style_doc_abs_path = os.path.join(self.sandboxed_home_abs_path, "python.md")
        with open(python_style_doc_abs_path, "w", encoding = "utf-8") as open_doc_file_handle:
            open_doc_file_handle.write("# python style")
        tests.required_reading.fixtures_required_reads.RequiredReadsManifestFixtureBuilder.write_manifest_file(
            manifest_directory_abs_path = self.sandboxed_home_abs_path,
            rule_dicts = [
                {"extension": ".py", "read": python_style_doc_abs_path}
            ]
        )
        self.satisfy_hooks_repo_global_rules_for_extension(".py")
        read_payload = tests._common.fixtures.PreToolUsePayloadFixtureBuilder.build_posttooluse_read_payload(
            file_path = python_style_doc_abs_path,
            working_directory = self.sandboxed_home_abs_path
        )
        tests._common.subprocess_helpers.HookEntryScriptInvocationHelper.invoke_entry_script(
            entry_script_relative_path = "required_reading/posttooluse_observer.py",
            pretooluse_payload = read_payload
        )
        edit_payload = tests._common.fixtures.PreToolUsePayloadFixtureBuilder.build_edit_payload(
            new_string_content = "x",
            file_path = os.path.join(self.sandboxed_home_abs_path, "main.py")
        )
        exit_code, parsed_stdout = tests._common.subprocess_helpers.HookEntryScriptInvocationHelper.invoke_entry_script(
            entry_script_relative_path = "required_reading/pretooluse.py",
            pretooluse_payload = edit_payload
        )
        tests._common.subprocess_helpers.HookEntryScriptInvocationHelper.assert_passthrough(self, exit_code, parsed_stdout)

    def test_read_of_unrelated_doc_does_not_satisfy_any_rule(self):

        python_style_doc_abs_path = os.path.join(self.sandboxed_home_abs_path, "python.md")
        unrelated_doc_abs_path = os.path.join(self.sandboxed_home_abs_path, "unrelated.md")
        with open(python_style_doc_abs_path, "w", encoding = "utf-8") as open_doc_file_handle:
            open_doc_file_handle.write("# python style")
        with open(unrelated_doc_abs_path, "w", encoding = "utf-8") as open_doc_file_handle:
            open_doc_file_handle.write("# unrelated")
        tests.required_reading.fixtures_required_reads.RequiredReadsManifestFixtureBuilder.write_manifest_file(
            manifest_directory_abs_path = self.sandboxed_home_abs_path,
            rule_dicts = [
                {"extension": ".py", "read": python_style_doc_abs_path}
            ]
        )
        read_of_unrelated_payload = tests._common.fixtures.PreToolUsePayloadFixtureBuilder.build_posttooluse_read_payload(
            file_path = unrelated_doc_abs_path,
            working_directory = self.sandboxed_home_abs_path
        )
        tests._common.subprocess_helpers.HookEntryScriptInvocationHelper.invoke_entry_script(
            entry_script_relative_path = "required_reading/posttooluse_observer.py",
            pretooluse_payload = read_of_unrelated_payload
        )
        edit_payload = tests._common.fixtures.PreToolUsePayloadFixtureBuilder.build_edit_payload(
            new_string_content = "x",
            file_path = os.path.join(self.sandboxed_home_abs_path, "main.py")
        )
        exit_code, parsed_stdout = tests._common.subprocess_helpers.HookEntryScriptInvocationHelper.invoke_entry_script(
            entry_script_relative_path = "required_reading/pretooluse.py",
            pretooluse_payload = edit_payload
        )
        tests._common.subprocess_helpers.HookEntryScriptInvocationHelper.assert_deny_decision(self, exit_code, parsed_stdout)

    def test_read_of_home_anchored_doc_satisfies_project_rule_via_cwd_fallback(self):

        home_doc_abs_path = os.path.join(self.sandboxed_home_abs_path, "shared-style.md")
        with open(home_doc_abs_path, "w", encoding = "utf-8") as open_doc_file_handle:
            open_doc_file_handle.write("# shared style")
        project_directory_abs_path = os.path.join(self.sandboxed_home_abs_path, "project")
        os.makedirs(project_directory_abs_path, exist_ok = True)
        tests.required_reading.fixtures_required_reads.RequiredReadsManifestFixtureBuilder.write_manifest_file(
            manifest_directory_abs_path = project_directory_abs_path,
            rule_dicts = [
                {"extension": ".py", "read": home_doc_abs_path}
            ]
        )
        self.satisfy_hooks_repo_global_rules_for_extension(".py")
        read_payload = tests._common.fixtures.PreToolUsePayloadFixtureBuilder.build_posttooluse_read_payload(
            file_path = home_doc_abs_path,
            working_directory = project_directory_abs_path
        )
        tests._common.subprocess_helpers.HookEntryScriptInvocationHelper.invoke_entry_script(
            entry_script_relative_path = "required_reading/posttooluse_observer.py",
            pretooluse_payload = read_payload
        )
        edit_payload = tests._common.fixtures.PreToolUsePayloadFixtureBuilder.build_edit_payload(
            new_string_content = "x",
            file_path = os.path.join(project_directory_abs_path, "main.py")
        )
        exit_code, parsed_stdout = tests._common.subprocess_helpers.HookEntryScriptInvocationHelper.invoke_entry_script(
            entry_script_relative_path = "required_reading/pretooluse.py",
            pretooluse_payload = edit_payload
        )
        tests._common.subprocess_helpers.HookEntryScriptInvocationHelper.assert_passthrough(self, exit_code, parsed_stdout)

    def test_no_manifest_anywhere_is_fast_path_noop(self):

        read_payload = tests._common.fixtures.PreToolUsePayloadFixtureBuilder.build_posttooluse_read_payload(
            file_path = os.path.join(self.sandboxed_home_abs_path, "any.md"),
            working_directory = self.sandboxed_home_abs_path
        )
        exit_code, parsed_stdout = tests._common.subprocess_helpers.HookEntryScriptInvocationHelper.invoke_entry_script(
            entry_script_relative_path = "required_reading/posttooluse_observer.py",
            pretooluse_payload = read_payload
        )
        tests._common.subprocess_helpers.HookEntryScriptInvocationHelper.assert_passthrough(self, exit_code, parsed_stdout)

    def test_non_read_tool_posttooluse_payload_passes_through(self):

        not_read_payload = tests._common.fixtures.PreToolUsePayloadFixtureBuilder.build_posttooluse_read_payload(
            file_path = "/tmp/any.md"
        )
        not_read_payload["tool_name"] = "Edit"
        exit_code, parsed_stdout = tests._common.subprocess_helpers.HookEntryScriptInvocationHelper.invoke_entry_script(
            entry_script_relative_path = "required_reading/posttooluse_observer.py",
            pretooluse_payload = not_read_payload
        )
        tests._common.subprocess_helpers.HookEntryScriptInvocationHelper.assert_passthrough(self, exit_code, parsed_stdout)


class PreCompactRequiredReadsSubprocessTestCase(
    tests.required_reading.fixtures_required_reads.HomeOverrideEnvVarTestCaseMixin,
    unittest.TestCase
):

    def test_precompact_clears_existing_satisfaction_flags_for_the_session(self):

        python_style_doc_abs_path = os.path.join(self.sandboxed_home_abs_path, "python.md")
        with open(python_style_doc_abs_path, "w", encoding = "utf-8") as open_doc_file_handle:
            open_doc_file_handle.write("# python style")
        tests.required_reading.fixtures_required_reads.RequiredReadsManifestFixtureBuilder.write_manifest_file(
            manifest_directory_abs_path = self.sandboxed_home_abs_path,
            rule_dicts = [
                {"extension": ".py", "read": python_style_doc_abs_path}
            ]
        )
        read_payload = tests._common.fixtures.PreToolUsePayloadFixtureBuilder.build_posttooluse_read_payload(
            file_path = python_style_doc_abs_path,
            working_directory = self.sandboxed_home_abs_path
        )
        tests._common.subprocess_helpers.HookEntryScriptInvocationHelper.invoke_entry_script(
            entry_script_relative_path = "required_reading/posttooluse_observer.py",
            pretooluse_payload = read_payload
        )
        precompact_payload = tests._common.fixtures.PreToolUsePayloadFixtureBuilder.build_precompact_payload()
        tests._common.subprocess_helpers.HookEntryScriptInvocationHelper.invoke_entry_script(
            entry_script_relative_path = "required_reading/precompact.py",
            pretooluse_payload = precompact_payload
        )
        post_compact_edit_payload = tests._common.fixtures.PreToolUsePayloadFixtureBuilder.build_edit_payload(
            new_string_content = "x",
            file_path = os.path.join(self.sandboxed_home_abs_path, "main.py")
        )
        exit_code, parsed_stdout = tests._common.subprocess_helpers.HookEntryScriptInvocationHelper.invoke_entry_script(
            entry_script_relative_path = "required_reading/pretooluse.py",
            pretooluse_payload = post_compact_edit_payload
        )
        tests._common.subprocess_helpers.HookEntryScriptInvocationHelper.assert_deny_decision(self, exit_code, parsed_stdout)

    def test_precompact_on_session_without_prior_flags_is_a_no_op(self):

        precompact_payload = tests._common.fixtures.PreToolUsePayloadFixtureBuilder.build_precompact_payload(
            session_id = "session-with-no-prior-flags"
        )
        exit_code, parsed_stdout = tests._common.subprocess_helpers.HookEntryScriptInvocationHelper.invoke_entry_script(
            entry_script_relative_path = "required_reading/precompact.py",
            pretooluse_payload = precompact_payload
        )
        tests._common.subprocess_helpers.HookEntryScriptInvocationHelper.assert_passthrough(self, exit_code, parsed_stdout)

    def test_precompact_payload_missing_session_id_does_not_crash(self):

        precompact_payload = {"hook_event_name": "PreCompact"}
        exit_code, parsed_stdout = tests._common.subprocess_helpers.HookEntryScriptInvocationHelper.invoke_entry_script(
            entry_script_relative_path = "required_reading/precompact.py",
            pretooluse_payload = precompact_payload
        )
        tests._common.subprocess_helpers.HookEntryScriptInvocationHelper.assert_passthrough(self, exit_code, parsed_stdout)


if __name__ == "__main__":
    unittest.main()
