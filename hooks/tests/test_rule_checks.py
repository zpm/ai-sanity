########################################################################################################################
# hooks/tests/test_rule_checks.py
#
# Unit tests for every rule check method across _lib and the per-matcher entry scripts
########################################################################################################################
import os
import subprocess
import sys
import tempfile
import time
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import _lib
import pretooluse_bash
import pretooluse_read
import pretooluse_required_reads
import pretooluse_write
import tests.fixtures
import tests.fixtures_required_reads


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


class TestRequiredReadsPathNormalizer(tests.fixtures_required_reads.HomeOverrideEnvVarTestCaseMixin, unittest.TestCase):

    """Unit tests for `_lib.RequiredReadsPathNormalizer.normalize_path`. Every path comparison in the required-reads
    subsystem goes through this function, so the tests focus on the three documented behaviors: tilde expansion with
    the test override, relative-path resolution against a base directory, and forward-slash output."""

    def test_tilde_expansion_uses_home_override_when_set(self):

        normalized_path_string = _lib.RequiredReadsPathNormalizer.normalize_path("~/foo/bar.md")
        expected_prefix = self.sandboxed_home_abs_path.replace("\\", "/").lower()
        self.assertTrue(normalized_path_string.startswith(expected_prefix))
        self.assertTrue(normalized_path_string.endswith("/foo/bar.md"))

    def test_bare_tilde_expands_to_home_override(self):

        normalized_path_string = _lib.RequiredReadsPathNormalizer.normalize_path("~")
        self.assertEqual(normalized_path_string, self.sandboxed_home_abs_path.replace("\\", "/").lower())

    def test_relative_path_resolved_against_base_directory(self):

        base_directory_abs_path = os.path.join(self.sandboxed_home_abs_path, "some", "project", ".claude")
        normalized_path_string = _lib.RequiredReadsPathNormalizer.normalize_path(
            "../docs/stack.md",
            base_directory_abs_path = base_directory_abs_path
        )
        expected_suffix = "/some/project/docs/stack.md"
        self.assertTrue(normalized_path_string.endswith(expected_suffix))

    def test_absolute_path_ignores_base_directory(self):

        base_directory_abs_path = os.path.join(self.sandboxed_home_abs_path, "irrelevant")
        absolute_input_path_string = os.path.join(self.sandboxed_home_abs_path, "absolute", "foo.md")
        normalized_path_string = _lib.RequiredReadsPathNormalizer.normalize_path(
            absolute_input_path_string,
            base_directory_abs_path = base_directory_abs_path
        )
        self.assertEqual(normalized_path_string, absolute_input_path_string.replace("\\", "/").lower())

    def test_output_uses_forward_slashes_only(self):

        normalized_path_string = _lib.RequiredReadsPathNormalizer.normalize_path("~/a/b/c.md")
        self.assertNotIn("\\", normalized_path_string)

    def test_output_is_lowercased(self):

        normalized_path_string = _lib.RequiredReadsPathNormalizer.normalize_path("~/Foo/Bar.MD")
        self.assertEqual(normalized_path_string, normalized_path_string.lower())


class TestRequiredReadsManifestLoaderLoadRecords(tests.fixtures_required_reads.HomeOverrideEnvVarTestCaseMixin, unittest.TestCase):

    """Unit tests for `_lib.RequiredReadsManifestLoader.load_manifest_rule_records`. Behavior under study: well-formed
    manifests return one record per valid rule; malformed JSON, wrong top-level shape, and missing required fields all
    degrade to empty-list or per-rule skip (never a raised exception). All rules are block-mode; the loader has no
    mode concept."""

    def test_well_formed_manifest_returns_one_record_per_rule(self):

        manifest_abs_path = tests.fixtures_required_reads.RequiredReadsManifestFixtureBuilder.write_manifest_file(
            manifest_directory_abs_path = self.sandboxed_home_abs_path,
            rule_dicts = [
                {"extension": ".py", "read": "~/docs/python.md"},
                {"extension": ".md", "read": "~/docs/markdown.md"}
            ]
        )
        loaded_rule_records = _lib.RequiredReadsManifestLoader.load_manifest_rule_records(
            manifest_abs_path = manifest_abs_path,
            is_global_manifest = True
        )
        self.assertEqual(len(loaded_rule_records), 2)
        self.assertEqual(loaded_rule_records[0].match_extension_suffix, ".py")
        self.assertIsNone(loaded_rule_records[0].match_filepath_substring)
        self.assertTrue(loaded_rule_records[0].is_global_manifest)

    def test_malformed_json_returns_empty_list(self):

        manifest_abs_path = tests.fixtures_required_reads.RequiredReadsManifestFixtureBuilder.write_raw_manifest_body(
            manifest_directory_abs_path = self.sandboxed_home_abs_path,
            raw_manifest_body_string = "{not valid json"
        )
        loaded_rule_records = _lib.RequiredReadsManifestLoader.load_manifest_rule_records(
            manifest_abs_path = manifest_abs_path,
            is_global_manifest = True
        )
        self.assertEqual(loaded_rule_records, [])

    def test_top_level_not_object_returns_empty_list(self):

        manifest_abs_path = tests.fixtures_required_reads.RequiredReadsManifestFixtureBuilder.write_raw_manifest_body(
            manifest_directory_abs_path = self.sandboxed_home_abs_path,
            raw_manifest_body_string = "[1, 2, 3]"
        )
        loaded_rule_records = _lib.RequiredReadsManifestLoader.load_manifest_rule_records(
            manifest_abs_path = manifest_abs_path,
            is_global_manifest = True
        )
        self.assertEqual(loaded_rule_records, [])

    def test_missing_rules_key_returns_empty_list(self):

        manifest_abs_path = tests.fixtures_required_reads.RequiredReadsManifestFixtureBuilder.write_raw_manifest_body(
            manifest_directory_abs_path = self.sandboxed_home_abs_path,
            raw_manifest_body_string = "{\"other\": []}"
        )
        loaded_rule_records = _lib.RequiredReadsManifestLoader.load_manifest_rule_records(
            manifest_abs_path = manifest_abs_path,
            is_global_manifest = True
        )
        self.assertEqual(loaded_rule_records, [])

    def test_rules_value_not_list_returns_empty_list(self):

        manifest_abs_path = tests.fixtures_required_reads.RequiredReadsManifestFixtureBuilder.write_raw_manifest_body(
            manifest_directory_abs_path = self.sandboxed_home_abs_path,
            raw_manifest_body_string = "{\"rules\": {}}"
        )
        loaded_rule_records = _lib.RequiredReadsManifestLoader.load_manifest_rule_records(
            manifest_abs_path = manifest_abs_path,
            is_global_manifest = True
        )
        self.assertEqual(loaded_rule_records, [])

    def test_missing_file_returns_empty_list(self):

        loaded_rule_records = _lib.RequiredReadsManifestLoader.load_manifest_rule_records(
            manifest_abs_path = os.path.join(self.sandboxed_home_abs_path, "does", "not", "exist.json"),
            is_global_manifest = True
        )
        self.assertEqual(loaded_rule_records, [])

    def test_rule_with_only_read_is_a_valid_wildcard(self):

        manifest_abs_path = tests.fixtures_required_reads.RequiredReadsManifestFixtureBuilder.write_manifest_file(
            manifest_directory_abs_path = self.sandboxed_home_abs_path,
            rule_dicts = [
                {"read": "~/docs/always.md"}
            ]
        )
        loaded_rule_records = _lib.RequiredReadsManifestLoader.load_manifest_rule_records(
            manifest_abs_path = manifest_abs_path,
            is_global_manifest = True
        )
        self.assertEqual(len(loaded_rule_records), 1)
        self.assertIsNone(loaded_rule_records[0].match_extension_suffix)
        self.assertIsNone(loaded_rule_records[0].match_filepath_substring)

    def test_rule_missing_read_field_is_skipped_but_siblings_kept(self):

        manifest_abs_path = tests.fixtures_required_reads.RequiredReadsManifestFixtureBuilder.write_manifest_file(
            manifest_directory_abs_path = self.sandboxed_home_abs_path,
            rule_dicts = [
                {"extension": ".py"},
                {"extension": ".md", "read": "~/docs/markdown.md"}
            ]
        )
        loaded_rule_records = _lib.RequiredReadsManifestLoader.load_manifest_rule_records(
            manifest_abs_path = manifest_abs_path,
            is_global_manifest = True
        )
        self.assertEqual(len(loaded_rule_records), 1)
        self.assertEqual(loaded_rule_records[0].match_extension_suffix, ".md")

    def test_rule_with_both_extension_and_filepath_is_skipped(self):

        manifest_abs_path = tests.fixtures_required_reads.RequiredReadsManifestFixtureBuilder.write_manifest_file(
            manifest_directory_abs_path = self.sandboxed_home_abs_path,
            rule_dicts = [
                {"extension": ".py", "filepath": "/server/", "read": "~/docs/both.md"},
                {"extension": ".md", "read": "~/docs/markdown.md"}
            ]
        )
        loaded_rule_records = _lib.RequiredReadsManifestLoader.load_manifest_rule_records(
            manifest_abs_path = manifest_abs_path,
            is_global_manifest = True
        )
        self.assertEqual(len(loaded_rule_records), 1)
        self.assertEqual(loaded_rule_records[0].match_extension_suffix, ".md")

    def test_filepath_rule_populates_only_filepath_field(self):

        manifest_abs_path = tests.fixtures_required_reads.RequiredReadsManifestFixtureBuilder.write_manifest_file(
            manifest_directory_abs_path = self.sandboxed_home_abs_path,
            rule_dicts = [
                {"filepath": "/server/", "read": "~/docs/backend.md"}
            ]
        )
        loaded_rule_records = _lib.RequiredReadsManifestLoader.load_manifest_rule_records(
            manifest_abs_path = manifest_abs_path,
            is_global_manifest = True
        )
        self.assertEqual(len(loaded_rule_records), 1)
        self.assertIsNone(loaded_rule_records[0].match_extension_suffix)
        self.assertEqual(loaded_rule_records[0].match_filepath_substring, "/server/")

    def test_match_field_values_are_lowercased_at_load_time(self):

        manifest_abs_path = tests.fixtures_required_reads.RequiredReadsManifestFixtureBuilder.write_manifest_file(
            manifest_directory_abs_path = self.sandboxed_home_abs_path,
            rule_dicts = [
                {"extension": ".PY", "read": "~/docs/python.md"},
                {"filepath": "/Server/", "read": "~/docs/backend.md"}
            ]
        )
        loaded_rule_records = _lib.RequiredReadsManifestLoader.load_manifest_rule_records(
            manifest_abs_path = manifest_abs_path,
            is_global_manifest = True
        )
        self.assertEqual(loaded_rule_records[0].match_extension_suffix, ".py")
        self.assertEqual(loaded_rule_records[1].match_filepath_substring, "/server/")

    def test_unknown_fields_including_comment_and_legacy_match_and_mode_are_ignored(self):

        manifest_abs_path = tests.fixtures_required_reads.RequiredReadsManifestFixtureBuilder.write_manifest_file(
            manifest_directory_abs_path = self.sandboxed_home_abs_path,
            rule_dicts = [
                {
                    "extension": ".py",
                    "read": "~/docs/python.md",
                    "comment": "this is a documentation string, loader ignores it",
                    "mode": "anything-at-all",
                    "match": "**/*.py",
                    "future_extension_field": {"unexpected": "shape"}
                }
            ]
        )
        loaded_rule_records = _lib.RequiredReadsManifestLoader.load_manifest_rule_records(
            manifest_abs_path = manifest_abs_path,
            is_global_manifest = True
        )
        self.assertEqual(len(loaded_rule_records), 1)
        self.assertEqual(loaded_rule_records[0].match_extension_suffix, ".py")

    def test_relative_read_path_resolved_against_project_root_not_manifest_directory(self):

        project_root_abs_path = os.path.join(self.sandboxed_home_abs_path, "some-project")
        os.makedirs(project_root_abs_path, exist_ok = True)
        manifest_abs_path = tests.fixtures_required_reads.RequiredReadsManifestFixtureBuilder.write_manifest_file(
            manifest_directory_abs_path = project_root_abs_path,
            rule_dicts = [
                {"extension": ".py", "read": "./docs/python.md"}
            ]
        )
        loaded_rule_records = _lib.RequiredReadsManifestLoader.load_manifest_rule_records(
            manifest_abs_path = manifest_abs_path,
            is_global_manifest = False
        )
        self.assertEqual(len(loaded_rule_records), 1)
        expected_read_abs_path_suffix = "/some-project/docs/python.md"
        self.assertTrue(loaded_rule_records[0].read_abs_path.endswith(expected_read_abs_path_suffix))
        self.assertNotIn("/.claude/docs/", loaded_rule_records[0].read_abs_path)

    def test_dedupe_key_defaults_to_normalized_read_path(self):

        manifest_abs_path = tests.fixtures_required_reads.RequiredReadsManifestFixtureBuilder.write_manifest_file(
            manifest_directory_abs_path = self.sandboxed_home_abs_path,
            rule_dicts = [
                {"extension": ".py", "read": "~/docs/python.md"}
            ]
        )
        loaded_rule_records = _lib.RequiredReadsManifestLoader.load_manifest_rule_records(
            manifest_abs_path = manifest_abs_path,
            is_global_manifest = True
        )
        self.assertEqual(loaded_rule_records[0].dedupe_key, loaded_rule_records[0].read_abs_path)

    def test_explicit_dedupe_key_overrides_default(self):

        manifest_abs_path = tests.fixtures_required_reads.RequiredReadsManifestFixtureBuilder.write_manifest_file(
            manifest_directory_abs_path = self.sandboxed_home_abs_path,
            rule_dicts = [
                {"extension": ".py", "read": "~/docs/python.md", "dedupe_key": "python-style-guide"}
            ]
        )
        loaded_rule_records = _lib.RequiredReadsManifestLoader.load_manifest_rule_records(
            manifest_abs_path = manifest_abs_path,
            is_global_manifest = True
        )
        self.assertEqual(loaded_rule_records[0].dedupe_key, "python-style-guide")


class TestRequiredReadsManifestLoaderDiscovery(tests.fixtures_required_reads.HomeOverrideEnvVarTestCaseMixin, unittest.TestCase):

    """Unit tests for `_lib.RequiredReadsManifestLoader.discover_manifest_abs_paths`. Behavior under study: walk up
    from the edited file collecting `.claude/required-reads.json` files, append the global manifest last, stop at
    home, handle missing manifests as no-ops."""

    def test_only_global_manifest_present_returns_global_alone(self):

        tests.fixtures_required_reads.RequiredReadsManifestFixtureBuilder.write_manifest_file(
            manifest_directory_abs_path = self.sandboxed_home_abs_path,
            rule_dicts = []
        )
        project_directory_abs_path = os.path.join(self.sandboxed_home_abs_path, "some", "project")
        os.makedirs(project_directory_abs_path, exist_ok = True)
        edited_file_abs_path = os.path.join(project_directory_abs_path, "src", "foo.py")
        discovered_manifest_abs_paths = _lib.RequiredReadsManifestLoader.discover_manifest_abs_paths(
            edited_file_abs_path = edited_file_abs_path
        )
        self.assertEqual(len(discovered_manifest_abs_paths), 1)
        self.assertTrue(discovered_manifest_abs_paths[0].endswith("/.claude/required-reads.json"))

    def test_project_manifest_in_nearest_claude_directory_appears_first(self):

        project_directory_abs_path = os.path.join(self.sandboxed_home_abs_path, "some", "project")
        os.makedirs(project_directory_abs_path, exist_ok = True)
        tests.fixtures_required_reads.RequiredReadsManifestFixtureBuilder.write_manifest_file(
            manifest_directory_abs_path = self.sandboxed_home_abs_path,
            rule_dicts = []
        )
        tests.fixtures_required_reads.RequiredReadsManifestFixtureBuilder.write_manifest_file(
            manifest_directory_abs_path = project_directory_abs_path,
            rule_dicts = []
        )
        edited_file_abs_path = os.path.join(project_directory_abs_path, "src", "foo.py")
        discovered_manifest_abs_paths = _lib.RequiredReadsManifestLoader.discover_manifest_abs_paths(
            edited_file_abs_path = edited_file_abs_path
        )
        self.assertEqual(len(discovered_manifest_abs_paths), 2)
        self.assertIn("/some/project/.claude/required-reads.json", discovered_manifest_abs_paths[0])
        self.assertTrue(discovered_manifest_abs_paths[1].endswith("/.claude/required-reads.json"))

    def test_walk_passes_intermediate_directories_without_manifests(self):

        deep_directory_abs_path = os.path.join(self.sandboxed_home_abs_path, "a", "b", "c", "d")
        os.makedirs(deep_directory_abs_path, exist_ok = True)
        tests.fixtures_required_reads.RequiredReadsManifestFixtureBuilder.write_manifest_file(
            manifest_directory_abs_path = os.path.join(self.sandboxed_home_abs_path, "a", "b"),
            rule_dicts = []
        )
        edited_file_abs_path = os.path.join(deep_directory_abs_path, "foo.py")
        discovered_manifest_abs_paths = _lib.RequiredReadsManifestLoader.discover_manifest_abs_paths(
            edited_file_abs_path = edited_file_abs_path
        )
        self.assertEqual(len(discovered_manifest_abs_paths), 1)
        self.assertIn("/a/b/.claude/required-reads.json", discovered_manifest_abs_paths[0])

    def test_walk_stops_at_home_and_does_not_escape_above(self):

        grandparent_directory_abs_path = os.path.dirname(self.sandboxed_home_abs_path)
        tests.fixtures_required_reads.RequiredReadsManifestFixtureBuilder.write_manifest_file(
            manifest_directory_abs_path = grandparent_directory_abs_path,
            rule_dicts = []
        )
        edited_file_abs_path = os.path.join(self.sandboxed_home_abs_path, "project", "src", "foo.py")
        discovered_manifest_abs_paths = _lib.RequiredReadsManifestLoader.discover_manifest_abs_paths(
            edited_file_abs_path = edited_file_abs_path
        )
        # only the grandparent manifest exists, not the global; walk should NOT have found the grandparent
        self.assertEqual(discovered_manifest_abs_paths, [])

    def test_no_manifests_anywhere_returns_empty_list(self):

        edited_file_abs_path = os.path.join(self.sandboxed_home_abs_path, "a", "b", "foo.py")
        discovered_manifest_abs_paths = _lib.RequiredReadsManifestLoader.discover_manifest_abs_paths(
            edited_file_abs_path = edited_file_abs_path
        )
        self.assertEqual(discovered_manifest_abs_paths, [])


class TestRequiredReadsState(tests.fixtures_required_reads.HomeOverrideEnvVarTestCaseMixin, unittest.TestCase):

    """Unit tests for `_lib.RequiredReadsState`. The state subsystem holds per-session satisfaction flags used by the
    required-reads hook trio. Tests verify first-write + read, idempotent re-write, session clear, and stale-directory
    sweep behavior. The `HOOK_TEST_HOME_OVERRIDE` env var (set by the mixin) makes the default state directory
    resolve under the sandboxed home."""

    def test_unmarked_dedupe_key_is_not_satisfied(self):

        self.assertFalse(_lib.RequiredReadsState.is_dedupe_key_satisfied(
            claude_session_id_string = "session-unmarked",
            dedupe_key_string = "some-key"
        ))

    def test_marked_dedupe_key_reads_back_as_satisfied(self):

        _lib.RequiredReadsState.mark_dedupe_key_satisfied(
            claude_session_id_string = "session-alpha",
            dedupe_key_string = "python-style-guide"
        )
        self.assertTrue(_lib.RequiredReadsState.is_dedupe_key_satisfied(
            claude_session_id_string = "session-alpha",
            dedupe_key_string = "python-style-guide"
        ))

    def test_second_mark_for_same_key_is_idempotent(self):

        _lib.RequiredReadsState.mark_dedupe_key_satisfied(
            claude_session_id_string = "session-beta",
            dedupe_key_string = "k"
        )
        _lib.RequiredReadsState.mark_dedupe_key_satisfied(
            claude_session_id_string = "session-beta",
            dedupe_key_string = "k"
        )
        self.assertTrue(_lib.RequiredReadsState.is_dedupe_key_satisfied(
            claude_session_id_string = "session-beta",
            dedupe_key_string = "k"
        ))

    def test_different_sessions_do_not_share_flags(self):

        _lib.RequiredReadsState.mark_dedupe_key_satisfied(
            claude_session_id_string = "session-one",
            dedupe_key_string = "shared-key"
        )
        self.assertFalse(_lib.RequiredReadsState.is_dedupe_key_satisfied(
            claude_session_id_string = "session-two",
            dedupe_key_string = "shared-key"
        ))

    def test_clear_session_removes_all_flags_for_that_session(self):

        _lib.RequiredReadsState.mark_dedupe_key_satisfied(
            claude_session_id_string = "session-clear",
            dedupe_key_string = "a"
        )
        _lib.RequiredReadsState.mark_dedupe_key_satisfied(
            claude_session_id_string = "session-clear",
            dedupe_key_string = "b"
        )
        _lib.RequiredReadsState.clear_session(claude_session_id_string = "session-clear")
        self.assertFalse(_lib.RequiredReadsState.is_dedupe_key_satisfied(
            claude_session_id_string = "session-clear",
            dedupe_key_string = "a"
        ))
        self.assertFalse(_lib.RequiredReadsState.is_dedupe_key_satisfied(
            claude_session_id_string = "session-clear",
            dedupe_key_string = "b"
        ))

    def test_clear_session_on_nonexistent_session_is_a_no_op(self):

        _lib.RequiredReadsState.clear_session(claude_session_id_string = "session-never-existed")

    def test_sweep_stale_removes_old_session_directories_and_keeps_fresh_ones(self):

        _lib.RequiredReadsState.mark_dedupe_key_satisfied(
            claude_session_id_string = "session-old",
            dedupe_key_string = "k"
        )
        _lib.RequiredReadsState.mark_dedupe_key_satisfied(
            claude_session_id_string = "session-new",
            dedupe_key_string = "k"
        )
        old_session_directory_abs_path = _lib.RequiredReadsState.get_session_directory_abs_path(
            claude_session_id_string = "session-old"
        )
        # backdate the old session directory by ten days so it falls outside the default seven-day window
        ten_days_ago_wall_clock_seconds = time.time() - (10 * 24 * 60 * 60)
        os.utime(old_session_directory_abs_path, (ten_days_ago_wall_clock_seconds, ten_days_ago_wall_clock_seconds))
        _lib.RequiredReadsState.sweep_stale_session_directories()
        self.assertFalse(_lib.RequiredReadsState.is_dedupe_key_satisfied(
            claude_session_id_string = "session-old",
            dedupe_key_string = "k"
        ))
        self.assertTrue(_lib.RequiredReadsState.is_dedupe_key_satisfied(
            claude_session_id_string = "session-new",
            dedupe_key_string = "k"
        ))

    def test_sweep_stale_with_no_state_base_directory_is_a_no_op(self):

        _lib.RequiredReadsState.sweep_stale_session_directories()


class PreToolUseRequiredReadsRuleRecordBuilder:

    """Shared helper for the PreToolUseRequiredReads unit tests. Produces `RequiredReadsRuleRecord` instances from
    keyword arguments with sensible defaults so tests can focus on the field(s) under study."""

    @staticmethod
    def build_rule_record(rule_id = "manifest.json#0",
        manifest_abs_path = "/fake/manifest.json",
        is_global_manifest = True,
        match_extension_suffix = ".py",
        match_filepath_substring = None,
        read_abs_path = "/fake/docs/python.md",
        override_abs_path = None,
        dedupe_key = None
    ):

        """Returns a RequiredReadsRuleRecord. The dedupe_key defaults to the read_abs_path, matching the loader's
        default behavior."""
        return _lib.RequiredReadsRuleRecord(
            rule_id = rule_id,
            manifest_abs_path = manifest_abs_path,
            is_global_manifest = is_global_manifest,
            match_extension_suffix = match_extension_suffix,
            match_filepath_substring = match_filepath_substring,
            read_abs_path = read_abs_path,
            override_abs_path = override_abs_path,
            dedupe_key = dedupe_key if dedupe_key is not None else read_abs_path
        )


class TestExtractEditedFilePath(unittest.TestCase):

    """Unit tests for `PreToolUseRequiredReadsRuleChecks.extract_edited_file_abs_path_or_none`."""

    def test_edit_payload_returns_normalized_file_path(self):

        edit_payload = tests.fixtures.PreToolUsePayloadFixtureBuilder.build_edit_payload(
            new_string_content = "x",
            file_path = "/tmp/foo.py"
        )
        extracted_abs_path = pretooluse_required_reads.PreToolUseRequiredReadsRuleChecks.extract_edited_file_abs_path_or_none(
            pretooluse_payload = edit_payload
        )
        self.assertIsNotNone(extracted_abs_path)
        self.assertTrue(extracted_abs_path.endswith("/tmp/foo.py"))

    def test_write_payload_returns_normalized_file_path(self):

        write_payload = tests.fixtures.PreToolUsePayloadFixtureBuilder.build_write_payload(
            file_content = "x",
            file_path = "/tmp/bar.py"
        )
        extracted_abs_path = pretooluse_required_reads.PreToolUseRequiredReadsRuleChecks.extract_edited_file_abs_path_or_none(
            pretooluse_payload = write_payload
        )
        self.assertIsNotNone(extracted_abs_path)
        self.assertTrue(extracted_abs_path.endswith("/tmp/bar.py"))

    def test_notebook_edit_payload_returns_notebook_path(self):

        notebook_edit_payload = tests.fixtures.PreToolUsePayloadFixtureBuilder.build_base_payload(
            tool_name = "NotebookEdit",
            tool_input = {"notebook_path": "/tmp/book.ipynb", "new_source": "x", "cell_id": "c"}
        )
        extracted_abs_path = pretooluse_required_reads.PreToolUseRequiredReadsRuleChecks.extract_edited_file_abs_path_or_none(
            pretooluse_payload = notebook_edit_payload
        )
        self.assertIsNotNone(extracted_abs_path)
        self.assertTrue(extracted_abs_path.endswith("/tmp/book.ipynb"))

    def test_read_payload_returns_normalized_file_path(self):

        read_payload = tests.fixtures.PreToolUsePayloadFixtureBuilder.build_read_payload(
            file_path = "/tmp/foo.py"
        )
        extracted_abs_path = pretooluse_required_reads.PreToolUseRequiredReadsRuleChecks.extract_edited_file_abs_path_or_none(
            pretooluse_payload = read_payload
        )
        self.assertIsNotNone(extracted_abs_path)
        self.assertTrue(extracted_abs_path.endswith("/tmp/foo.py"))

    def test_unknown_tool_returns_none(self):

        unrelated_payload = tests.fixtures.PreToolUsePayloadFixtureBuilder.build_bash_payload(
            bash_command_string = "echo hello"
        )
        extracted_abs_path = pretooluse_required_reads.PreToolUseRequiredReadsRuleChecks.extract_edited_file_abs_path_or_none(
            pretooluse_payload = unrelated_payload
        )
        self.assertIsNone(extracted_abs_path)

    def test_missing_file_path_field_returns_none(self):

        empty_edit_payload = tests.fixtures.PreToolUsePayloadFixtureBuilder.build_base_payload(
            tool_name = "Edit",
            tool_input = {}
        )
        extracted_abs_path = pretooluse_required_reads.PreToolUseRequiredReadsRuleChecks.extract_edited_file_abs_path_or_none(
            pretooluse_payload = empty_edit_payload
        )
        self.assertIsNone(extracted_abs_path)


class TestApplyProjectOverridesAgainstGlobalRules(unittest.TestCase):

    """Unit tests for `PreToolUseRequiredReadsRuleChecks.apply_project_overrides_against_global_rules`."""

    def test_project_override_drops_matching_global_rule(self):

        global_python_rule_record = PreToolUseRequiredReadsRuleRecordBuilder.build_rule_record(
            is_global_manifest = True,
            read_abs_path = "/home/zachm/Dev/ai-common/styleguides/python.md"
        )
        project_override_rule_record = PreToolUseRequiredReadsRuleRecordBuilder.build_rule_record(
            is_global_manifest = False,
            read_abs_path = "/project/docs/project-python-style.md",
            override_abs_path = "/home/zachm/Dev/ai-common/styleguides/python.md"
        )
        surviving_rule_records = pretooluse_required_reads.PreToolUseRequiredReadsRuleChecks.apply_project_overrides_against_global_rules(
            rule_records = [global_python_rule_record, project_override_rule_record]
        )
        self.assertEqual(len(surviving_rule_records), 1)
        self.assertFalse(surviving_rule_records[0].is_global_manifest)

    def test_project_rule_without_override_keeps_global(self):

        global_python_rule_record = PreToolUseRequiredReadsRuleRecordBuilder.build_rule_record(
            is_global_manifest = True,
            read_abs_path = "/home/zachm/Dev/ai-common/styleguides/python.md"
        )
        project_extra_rule_record = PreToolUseRequiredReadsRuleRecordBuilder.build_rule_record(
            is_global_manifest = False,
            read_abs_path = "/project/docs/product.md",
            override_abs_path = None
        )
        surviving_rule_records = pretooluse_required_reads.PreToolUseRequiredReadsRuleChecks.apply_project_overrides_against_global_rules(
            rule_records = [global_python_rule_record, project_extra_rule_record]
        )
        self.assertEqual(len(surviving_rule_records), 2)

    def test_project_rule_cannot_override_another_project_rule(self):

        project_a_rule_record = PreToolUseRequiredReadsRuleRecordBuilder.build_rule_record(
            is_global_manifest = False,
            read_abs_path = "/project/docs/stack.md"
        )
        project_b_override_rule_record = PreToolUseRequiredReadsRuleRecordBuilder.build_rule_record(
            is_global_manifest = False,
            read_abs_path = "/project/docs/alt-stack.md",
            override_abs_path = "/project/docs/stack.md"
        )
        surviving_rule_records = pretooluse_required_reads.PreToolUseRequiredReadsRuleChecks.apply_project_overrides_against_global_rules(
            rule_records = [project_a_rule_record, project_b_override_rule_record]
        )
        self.assertEqual(len(surviving_rule_records), 2)


class TestFilterRulesByMatchCriterion(unittest.TestCase):

    """Unit tests for `PreToolUseRequiredReadsRuleChecks.filter_rules_by_match_criterion`. A rule matches when it has
    no match fields (wildcard), or its extension suffix ends the path, or its filepath substring appears in the path.
    Case normalization happens upstream (all paths are lowercased during path normalization and all match values are
    lowercased at manifest load time), so the filter itself does plain string operations."""

    def test_wildcard_rule_matches_every_path(self):

        wildcard_rule_record = PreToolUseRequiredReadsRuleRecordBuilder.build_rule_record(
            match_extension_suffix = None,
            match_filepath_substring = None
        )
        match_passed_rule_records = pretooluse_required_reads.PreToolUseRequiredReadsRuleChecks.filter_rules_by_match_criterion(
            rule_records = [wildcard_rule_record],
            candidate_file_abs_path = "/anywhere/foo.xyz"
        )
        self.assertEqual(len(match_passed_rule_records), 1)

    def test_extension_matches_when_path_ends_with_suffix(self):

        python_rule_record = PreToolUseRequiredReadsRuleRecordBuilder.build_rule_record(
            match_extension_suffix = ".py",
            match_filepath_substring = None
        )
        match_passed_rule_records = pretooluse_required_reads.PreToolUseRequiredReadsRuleChecks.filter_rules_by_match_criterion(
            rule_records = [python_rule_record],
            candidate_file_abs_path = "/c/users/zachm/dev/ai-common/hooks/bar.py"
        )
        self.assertEqual(len(match_passed_rule_records), 1)

    def test_extension_rejects_when_path_does_not_end_with_suffix(self):

        python_rule_record = PreToolUseRequiredReadsRuleRecordBuilder.build_rule_record(
            match_extension_suffix = ".py",
            match_filepath_substring = None
        )
        match_passed_rule_records = pretooluse_required_reads.PreToolUseRequiredReadsRuleChecks.filter_rules_by_match_criterion(
            rule_records = [python_rule_record],
            candidate_file_abs_path = "/c/users/zachm/dev/foo.md"
        )
        self.assertEqual(match_passed_rule_records, [])

    def test_filepath_matches_when_substring_appears_in_path(self):

        server_rule_record = PreToolUseRequiredReadsRuleRecordBuilder.build_rule_record(
            match_extension_suffix = None,
            match_filepath_substring = "/server/"
        )
        match_passed_rule_records = pretooluse_required_reads.PreToolUseRequiredReadsRuleChecks.filter_rules_by_match_criterion(
            rule_records = [server_rule_record],
            candidate_file_abs_path = "/c/users/zachm/dev/project/server/api/foo.py"
        )
        self.assertEqual(len(match_passed_rule_records), 1)

    def test_filepath_rejects_when_substring_absent_from_path(self):

        server_rule_record = PreToolUseRequiredReadsRuleRecordBuilder.build_rule_record(
            match_extension_suffix = None,
            match_filepath_substring = "/server/"
        )
        match_passed_rule_records = pretooluse_required_reads.PreToolUseRequiredReadsRuleChecks.filter_rules_by_match_criterion(
            rule_records = [server_rule_record],
            candidate_file_abs_path = "/c/users/zachm/dev/project/client/index.js"
        )
        self.assertEqual(match_passed_rule_records, [])


class TestIsReadOfAManifestListedDoc(tests.fixtures_required_reads.HomeOverrideEnvVarTestCaseMixin, unittest.TestCase):

    """Unit tests for `PreToolUseRequiredReadsRuleChecks.is_read_of_a_manifest_listed_doc`. Reads of any
    manifest-listed `read` target must always passthrough so loading required context is never blocked. Self-target
    rules (the `.md` rule pointing at `markdown.md`) and cross-target chains (Reading `python.md` while wildcard
    rules want `CLAUDE.md`) both deadlock without this exemption."""

    def test_read_of_self_target_doc_returns_true(self):

        markdown_doc_abs_path = os.path.join(self.sandboxed_home_abs_path, "markdown.md")
        with open(markdown_doc_abs_path, "w", encoding = "utf-8") as open_doc_file_handle:
            open_doc_file_handle.write("# md")
        tests.fixtures_required_reads.RequiredReadsManifestFixtureBuilder.write_manifest_file(
            manifest_directory_abs_path = self.sandboxed_home_abs_path,
            rule_dicts = [
                {"extension": ".md", "read": markdown_doc_abs_path}
            ]
        )
        normalized_candidate_abs_path = _lib.RequiredReadsPathNormalizer.normalize_path(markdown_doc_abs_path)
        is_manifest_listed = pretooluse_required_reads.PreToolUseRequiredReadsRuleChecks.is_read_of_a_manifest_listed_doc(
            tool_name_string = "Read",
            candidate_file_abs_path = normalized_candidate_abs_path,
            edited_file_abs_path = normalized_candidate_abs_path
        )
        self.assertTrue(is_manifest_listed)

    def test_read_of_cross_target_doc_returns_true_even_when_other_rules_would_fire(self):

        python_doc_abs_path = os.path.join(self.sandboxed_home_abs_path, "python.md")
        claude_md_abs_path = os.path.join(self.sandboxed_home_abs_path, "CLAUDE.md")
        with open(python_doc_abs_path, "w", encoding = "utf-8") as open_doc_file_handle:
            open_doc_file_handle.write("# py")
        with open(claude_md_abs_path, "w", encoding = "utf-8") as open_doc_file_handle:
            open_doc_file_handle.write("# claude")
        tests.fixtures_required_reads.RequiredReadsManifestFixtureBuilder.write_manifest_file(
            manifest_directory_abs_path = self.sandboxed_home_abs_path,
            rule_dicts = [
                {"read": claude_md_abs_path},
                {"extension": ".py", "read": python_doc_abs_path}
            ]
        )
        normalized_candidate_abs_path = _lib.RequiredReadsPathNormalizer.normalize_path(python_doc_abs_path)
        is_manifest_listed = pretooluse_required_reads.PreToolUseRequiredReadsRuleChecks.is_read_of_a_manifest_listed_doc(
            tool_name_string = "Read",
            candidate_file_abs_path = normalized_candidate_abs_path,
            edited_file_abs_path = normalized_candidate_abs_path
        )
        self.assertTrue(is_manifest_listed)

    def test_read_of_unrelated_file_returns_false(self):

        markdown_doc_abs_path = os.path.join(self.sandboxed_home_abs_path, "markdown.md")
        with open(markdown_doc_abs_path, "w", encoding = "utf-8") as open_doc_file_handle:
            open_doc_file_handle.write("# md")
        tests.fixtures_required_reads.RequiredReadsManifestFixtureBuilder.write_manifest_file(
            manifest_directory_abs_path = self.sandboxed_home_abs_path,
            rule_dicts = [
                {"extension": ".md", "read": markdown_doc_abs_path}
            ]
        )
        unrelated_abs_path = _lib.RequiredReadsPathNormalizer.normalize_path(
            os.path.join(self.sandboxed_home_abs_path, "project", "notes.md")
        )
        is_manifest_listed = pretooluse_required_reads.PreToolUseRequiredReadsRuleChecks.is_read_of_a_manifest_listed_doc(
            tool_name_string = "Read",
            candidate_file_abs_path = unrelated_abs_path,
            edited_file_abs_path = unrelated_abs_path
        )
        self.assertFalse(is_manifest_listed)

    def test_edit_of_target_doc_returns_false(self):

        markdown_doc_abs_path = os.path.join(self.sandboxed_home_abs_path, "markdown.md")
        with open(markdown_doc_abs_path, "w", encoding = "utf-8") as open_doc_file_handle:
            open_doc_file_handle.write("# md")
        tests.fixtures_required_reads.RequiredReadsManifestFixtureBuilder.write_manifest_file(
            manifest_directory_abs_path = self.sandboxed_home_abs_path,
            rule_dicts = [
                {"extension": ".md", "read": markdown_doc_abs_path}
            ]
        )
        normalized_candidate_abs_path = _lib.RequiredReadsPathNormalizer.normalize_path(markdown_doc_abs_path)
        is_manifest_listed = pretooluse_required_reads.PreToolUseRequiredReadsRuleChecks.is_read_of_a_manifest_listed_doc(
            tool_name_string = "Edit",
            candidate_file_abs_path = normalized_candidate_abs_path,
            edited_file_abs_path = normalized_candidate_abs_path
        )
        self.assertFalse(is_manifest_listed)


class TestPartitionRulesIntoUnsatisfiedFireAndAlreadySatisfied(tests.fixtures_required_reads.HomeOverrideEnvVarTestCaseMixin, unittest.TestCase):

    """Unit tests for `PreToolUseRequiredReadsRuleChecks.partition_rules_into_unsatisfied_fire_and_already_satisfied`."""

    def test_no_flags_set_means_every_rule_fires(self):

        python_rule_record = PreToolUseRequiredReadsRuleRecordBuilder.build_rule_record(
            dedupe_key = "python-style-guide"
        )
        markdown_rule_record = PreToolUseRequiredReadsRuleRecordBuilder.build_rule_record(
            dedupe_key = "markdown-style-guide"
        )
        rules_to_fire_list, rules_already_satisfied_list = (
            pretooluse_required_reads.PreToolUseRequiredReadsRuleChecks.partition_rules_into_unsatisfied_fire_and_already_satisfied(
                rule_records = [python_rule_record, markdown_rule_record],
                claude_session_id_string = "session-empty"
            )
        )
        self.assertEqual(len(rules_to_fire_list), 2)
        self.assertEqual(rules_already_satisfied_list, [])

    def test_flag_already_set_for_dedupe_key_means_rule_is_skipped(self):

        python_rule_record = PreToolUseRequiredReadsRuleRecordBuilder.build_rule_record(
            dedupe_key = "python-style-guide"
        )
        _lib.RequiredReadsState.mark_dedupe_key_satisfied(
            claude_session_id_string = "session-partial",
            dedupe_key_string = "python-style-guide"
        )
        rules_to_fire_list, rules_already_satisfied_list = (
            pretooluse_required_reads.PreToolUseRequiredReadsRuleChecks.partition_rules_into_unsatisfied_fire_and_already_satisfied(
                rule_records = [python_rule_record],
                claude_session_id_string = "session-partial"
            )
        )
        self.assertEqual(rules_to_fire_list, [])
        self.assertEqual(len(rules_already_satisfied_list), 1)

    def test_rules_sharing_a_dedupe_key_collapse_to_one_satisfaction(self):

        first_rule_record = PreToolUseRequiredReadsRuleRecordBuilder.build_rule_record(
            rule_id = "m#0",
            match_extension_suffix = ".py",
            dedupe_key = "shared-key"
        )
        second_rule_record = PreToolUseRequiredReadsRuleRecordBuilder.build_rule_record(
            rule_id = "m#1",
            match_extension_suffix = ".pyi",
            dedupe_key = "shared-key"
        )
        _lib.RequiredReadsState.mark_dedupe_key_satisfied(
            claude_session_id_string = "session-shared",
            dedupe_key_string = "shared-key"
        )
        rules_to_fire_list, rules_already_satisfied_list = (
            pretooluse_required_reads.PreToolUseRequiredReadsRuleChecks.partition_rules_into_unsatisfied_fire_and_already_satisfied(
                rule_records = [first_rule_record, second_rule_record],
                claude_session_id_string = "session-shared"
            )
        )
        self.assertEqual(rules_to_fire_list, [])
        self.assertEqual(len(rules_already_satisfied_list), 2)


class TestBuildDenyReasonString(unittest.TestCase):

    """Unit tests for `PreToolUseRequiredReadsRuleChecks.build_deny_reason_string` and the missing-target helpers."""

    def test_deny_reason_lists_every_unsatisfied_rule_read_path_and_rule_id(self):

        first_unsatisfied_rule_record = PreToolUseRequiredReadsRuleRecordBuilder.build_rule_record(
            rule_id = "required-reads.json#0",
            manifest_abs_path = "/home/zachm/.claude/required-reads.json",
            read_abs_path = "/home/zachm/Dev/ai-common/styleguides/python.md"
        )
        second_unsatisfied_rule_record = PreToolUseRequiredReadsRuleRecordBuilder.build_rule_record(
            rule_id = "required-reads.json#3",
            manifest_abs_path = "/home/zachm/.claude/required-reads.json",
            read_abs_path = "/home/zachm/.claude/CLAUDE.md"
        )
        deny_reason_string = pretooluse_required_reads.PreToolUseRequiredReadsRuleChecks.build_deny_reason_string(
            unsatisfied_rule_records = [first_unsatisfied_rule_record, second_unsatisfied_rule_record],
            edited_file_abs_path = "/home/zachm/Dev/project/src/main.py"
        )
        self.assertIn("/home/zachm/Dev/project/src/main.py", deny_reason_string)
        self.assertIn("/home/zachm/Dev/ai-common/styleguides/python.md", deny_reason_string)
        self.assertIn("/home/zachm/.claude/CLAUDE.md", deny_reason_string)
        self.assertIn("required-reads.json#0", deny_reason_string)
        self.assertIn("required-reads.json#3", deny_reason_string)

    def test_find_rules_with_missing_read_targets_returns_only_missing_ones(self):

        present_doc_directory_abs_path = tempfile.mkdtemp()
        present_doc_abs_path = os.path.join(present_doc_directory_abs_path, "present.md")
        with open(present_doc_abs_path, "w", encoding = "utf-8") as open_doc_file_handle:
            open_doc_file_handle.write("# present")
        present_rule_record = PreToolUseRequiredReadsRuleRecordBuilder.build_rule_record(
            rule_id = "m#present",
            read_abs_path = present_doc_abs_path
        )
        missing_rule_record = PreToolUseRequiredReadsRuleRecordBuilder.build_rule_record(
            rule_id = "m#missing",
            read_abs_path = "/nowhere/does-not-exist.md"
        )
        rules_with_missing_targets = pretooluse_required_reads.PreToolUseRequiredReadsRuleChecks.find_rules_with_missing_read_targets(
            rule_records = [present_rule_record, missing_rule_record]
        )
        self.assertEqual(len(rules_with_missing_targets), 1)
        self.assertEqual(rules_with_missing_targets[0].rule_id, "m#missing")

    def test_build_missing_target_deny_reason_string_lists_every_missing_doc_with_no_escape_hatch(self):

        first_missing_rule_record = PreToolUseRequiredReadsRuleRecordBuilder.build_rule_record(
            rule_id = "m#first",
            read_abs_path = "/nowhere/a.md"
        )
        second_missing_rule_record = PreToolUseRequiredReadsRuleRecordBuilder.build_rule_record(
            rule_id = "m#second",
            read_abs_path = "/nowhere/b.md"
        )
        missing_target_deny_reason_string = pretooluse_required_reads.PreToolUseRequiredReadsRuleChecks.build_missing_target_deny_reason_string(
            rules_with_missing_targets = [first_missing_rule_record, second_missing_rule_record],
            edited_file_abs_path = "/tmp/foo.py"
        )
        self.assertIn("/nowhere/a.md", missing_target_deny_reason_string)
        self.assertIn("/nowhere/b.md", missing_target_deny_reason_string)
        self.assertIn("configuration error", missing_target_deny_reason_string)
        self.assertNotIn("skip", missing_target_deny_reason_string)


if __name__ == "__main__":
    unittest.main()
