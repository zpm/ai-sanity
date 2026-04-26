import os
import sys
import tempfile
import time
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "hooks"))

import tests.fixtures
import tests.fixtures_required_reads
import required_reading._manifest
import required_reading._state
import required_reading.pretooluse


class TestRequiredReadsPathNormalizer(tests.fixtures_required_reads.HomeOverrideEnvVarTestCaseMixin, unittest.TestCase):

    """Unit tests for `required_reading._manifest.RequiredReadsPathNormalizer.normalize_path`. Every path comparison in the required-reads
    subsystem goes through this function, so the tests focus on the three documented behaviors: tilde expansion with
    the test override, relative-path resolution against a base directory, and forward-slash output."""

    def test_tilde_expansion_uses_home_override_when_set(self):

        normalized_path_string = required_reading._manifest.RequiredReadsPathNormalizer.normalize_path("~/foo/bar.md")
        expected_prefix = self.sandboxed_home_abs_path.replace("\\", "/").lower()
        self.assertTrue(normalized_path_string.startswith(expected_prefix))
        self.assertTrue(normalized_path_string.endswith("/foo/bar.md"))

    def test_bare_tilde_expands_to_home_override(self):

        normalized_path_string = required_reading._manifest.RequiredReadsPathNormalizer.normalize_path("~")
        self.assertEqual(normalized_path_string, self.sandboxed_home_abs_path.replace("\\", "/").lower())

    def test_relative_path_resolved_against_base_directory(self):

        base_directory_abs_path = os.path.join(self.sandboxed_home_abs_path, "some", "project", ".ai-sanity")
        normalized_path_string = required_reading._manifest.RequiredReadsPathNormalizer.normalize_path(
            "../docs/stack.md",
            base_directory_abs_path = base_directory_abs_path
        )
        expected_suffix = "/some/project/docs/stack.md"
        self.assertTrue(normalized_path_string.endswith(expected_suffix))

    def test_absolute_path_ignores_base_directory(self):

        base_directory_abs_path = os.path.join(self.sandboxed_home_abs_path, "irrelevant")
        absolute_input_path_string = os.path.join(self.sandboxed_home_abs_path, "absolute", "foo.md")
        normalized_path_string = required_reading._manifest.RequiredReadsPathNormalizer.normalize_path(
            absolute_input_path_string,
            base_directory_abs_path = base_directory_abs_path
        )
        self.assertEqual(normalized_path_string, absolute_input_path_string.replace("\\", "/").lower())

    def test_output_uses_forward_slashes_only(self):

        normalized_path_string = required_reading._manifest.RequiredReadsPathNormalizer.normalize_path("~/a/b/c.md")
        self.assertNotIn("\\", normalized_path_string)

    def test_output_is_lowercased(self):

        normalized_path_string = required_reading._manifest.RequiredReadsPathNormalizer.normalize_path("~/Foo/Bar.MD")
        self.assertEqual(normalized_path_string, normalized_path_string.lower())


class TestRequiredReadsManifestLoaderLoadRecords(tests.fixtures_required_reads.HomeOverrideEnvVarTestCaseMixin, unittest.TestCase):

    """Unit tests for `required_reading._manifest.RequiredReadsManifestLoader.load_manifest_rule_records`."""

    def test_well_formed_manifest_returns_one_record_per_rule(self):

        manifest_abs_path = tests.fixtures_required_reads.RequiredReadsManifestFixtureBuilder.write_manifest_file(
            manifest_directory_abs_path = self.sandboxed_home_abs_path,
            rule_dicts = [
                {"extension": ".py", "read": "~/docs/python.md"},
                {"extension": ".md", "read": "~/docs/markdown.md"}
            ]
        )
        loaded_rule_records = required_reading._manifest.RequiredReadsManifestLoader.load_manifest_rule_records(
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
        loaded_rule_records = required_reading._manifest.RequiredReadsManifestLoader.load_manifest_rule_records(
            manifest_abs_path = manifest_abs_path,
            is_global_manifest = True
        )
        self.assertEqual(loaded_rule_records, [])

    def test_top_level_not_object_returns_empty_list(self):

        manifest_abs_path = tests.fixtures_required_reads.RequiredReadsManifestFixtureBuilder.write_raw_manifest_body(
            manifest_directory_abs_path = self.sandboxed_home_abs_path,
            raw_manifest_body_string = "[1, 2, 3]"
        )
        loaded_rule_records = required_reading._manifest.RequiredReadsManifestLoader.load_manifest_rule_records(
            manifest_abs_path = manifest_abs_path,
            is_global_manifest = True
        )
        self.assertEqual(loaded_rule_records, [])

    def test_missing_rules_key_returns_empty_list(self):

        manifest_abs_path = tests.fixtures_required_reads.RequiredReadsManifestFixtureBuilder.write_raw_manifest_body(
            manifest_directory_abs_path = self.sandboxed_home_abs_path,
            raw_manifest_body_string = "{\"other\": []}"
        )
        loaded_rule_records = required_reading._manifest.RequiredReadsManifestLoader.load_manifest_rule_records(
            manifest_abs_path = manifest_abs_path,
            is_global_manifest = True
        )
        self.assertEqual(loaded_rule_records, [])

    def test_rules_value_not_list_returns_empty_list(self):

        manifest_abs_path = tests.fixtures_required_reads.RequiredReadsManifestFixtureBuilder.write_raw_manifest_body(
            manifest_directory_abs_path = self.sandboxed_home_abs_path,
            raw_manifest_body_string = "{\"rules\": {}}"
        )
        loaded_rule_records = required_reading._manifest.RequiredReadsManifestLoader.load_manifest_rule_records(
            manifest_abs_path = manifest_abs_path,
            is_global_manifest = True
        )
        self.assertEqual(loaded_rule_records, [])

    def test_missing_file_returns_empty_list(self):

        loaded_rule_records = required_reading._manifest.RequiredReadsManifestLoader.load_manifest_rule_records(
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
        loaded_rule_records = required_reading._manifest.RequiredReadsManifestLoader.load_manifest_rule_records(
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
        loaded_rule_records = required_reading._manifest.RequiredReadsManifestLoader.load_manifest_rule_records(
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
        loaded_rule_records = required_reading._manifest.RequiredReadsManifestLoader.load_manifest_rule_records(
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
        loaded_rule_records = required_reading._manifest.RequiredReadsManifestLoader.load_manifest_rule_records(
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
        loaded_rule_records = required_reading._manifest.RequiredReadsManifestLoader.load_manifest_rule_records(
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
        loaded_rule_records = required_reading._manifest.RequiredReadsManifestLoader.load_manifest_rule_records(
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
        loaded_rule_records = required_reading._manifest.RequiredReadsManifestLoader.load_manifest_rule_records(
            manifest_abs_path = manifest_abs_path,
            is_global_manifest = False
        )
        self.assertEqual(len(loaded_rule_records), 1)
        expected_read_abs_path_suffix = "/some-project/docs/python.md"
        self.assertTrue(loaded_rule_records[0].read_abs_path.endswith(expected_read_abs_path_suffix))
        self.assertNotIn("/.ai-sanity/docs/", loaded_rule_records[0].read_abs_path)

    def test_dedupe_key_defaults_to_normalized_read_path(self):

        manifest_abs_path = tests.fixtures_required_reads.RequiredReadsManifestFixtureBuilder.write_manifest_file(
            manifest_directory_abs_path = self.sandboxed_home_abs_path,
            rule_dicts = [
                {"extension": ".py", "read": "~/docs/python.md"}
            ]
        )
        loaded_rule_records = required_reading._manifest.RequiredReadsManifestLoader.load_manifest_rule_records(
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
        loaded_rule_records = required_reading._manifest.RequiredReadsManifestLoader.load_manifest_rule_records(
            manifest_abs_path = manifest_abs_path,
            is_global_manifest = True
        )
        self.assertEqual(loaded_rule_records[0].dedupe_key, "python-style-guide")


class TestRequiredReadsManifestLoaderDiscovery(tests.fixtures_required_reads.HomeOverrideEnvVarTestCaseMixin, unittest.TestCase):

    def test_hooks_repo_global_manifest_appears_as_non_project(self):

        project_directory_abs_path = os.path.join(self.sandboxed_home_abs_path, "some", "project")
        os.makedirs(project_directory_abs_path, exist_ok = True)
        edited_file_abs_path = os.path.join(project_directory_abs_path, "src", "foo.py")
        discovered_manifests = required_reading._manifest.RequiredReadsManifestLoader.discover_manifests(
            edited_file_abs_path = edited_file_abs_path
        )
        non_project_manifests = [
            dm for dm in discovered_manifests if not dm.is_project_walkup_manifest
        ]
        self.assertTrue(len(non_project_manifests) >= 1)
        self.assertTrue(any(
            dm.manifest_abs_path.endswith("/.ai-sanity/required-reading.global.json")
            for dm in non_project_manifests
        ))

    def test_discovery_order_is_global_then_project(self):

        project_directory_abs_path = os.path.join(self.sandboxed_home_abs_path, "some", "project")
        os.makedirs(project_directory_abs_path, exist_ok = True)
        tests.fixtures_required_reads.RequiredReadsManifestFixtureBuilder.write_manifest_file(
            manifest_directory_abs_path = project_directory_abs_path,
            rule_dicts = []
        )
        edited_file_abs_path = os.path.join(project_directory_abs_path, "src", "foo.py")
        discovered_manifests = required_reading._manifest.RequiredReadsManifestLoader.discover_manifests(
            edited_file_abs_path = edited_file_abs_path
        )
        manifest_paths = [dm.manifest_abs_path for dm in discovered_manifests]
        global_index = next(i for i, p in enumerate(manifest_paths) if "required-reading.global.json" in p)
        project_index = next(i for i, dm in enumerate(discovered_manifests) if dm.is_project_walkup_manifest)
        self.assertLess(global_index, project_index)

    def test_walk_passes_intermediate_directories_without_manifests(self):

        deep_directory_abs_path = os.path.join(self.sandboxed_home_abs_path, "a", "b", "c", "d")
        os.makedirs(deep_directory_abs_path, exist_ok = True)
        tests.fixtures_required_reads.RequiredReadsManifestFixtureBuilder.write_manifest_file(
            manifest_directory_abs_path = os.path.join(self.sandboxed_home_abs_path, "a", "b"),
            rule_dicts = []
        )
        edited_file_abs_path = os.path.join(deep_directory_abs_path, "foo.py")
        discovered_manifests = required_reading._manifest.RequiredReadsManifestLoader.discover_manifests(
            edited_file_abs_path = edited_file_abs_path
        )
        project_manifests = [dm for dm in discovered_manifests if dm.is_project_walkup_manifest]
        self.assertEqual(len(project_manifests), 1)
        self.assertIn("/a/b/.ai-sanity/required-reading.json", project_manifests[0].manifest_abs_path)

    def test_walk_stops_at_home_and_does_not_escape_above(self):

        grandparent_directory_abs_path = os.path.dirname(self.sandboxed_home_abs_path)
        tests.fixtures_required_reads.RequiredReadsManifestFixtureBuilder.write_manifest_file(
            manifest_directory_abs_path = grandparent_directory_abs_path,
            rule_dicts = []
        )
        edited_file_abs_path = os.path.join(self.sandboxed_home_abs_path, "project", "src", "foo.py")
        discovered_manifests = required_reading._manifest.RequiredReadsManifestLoader.discover_manifests(
            edited_file_abs_path = edited_file_abs_path
        )
        project_manifests = [dm for dm in discovered_manifests if dm.is_project_walkup_manifest]
        self.assertEqual(project_manifests, [])

    def test_no_manifests_anywhere_returns_only_hooks_repo_global(self):

        edited_file_abs_path = os.path.join(self.sandboxed_home_abs_path, "a", "b", "foo.py")
        discovered_manifests = required_reading._manifest.RequiredReadsManifestLoader.discover_manifests(
            edited_file_abs_path = edited_file_abs_path
        )
        project_manifests = [dm for dm in discovered_manifests if dm.is_project_walkup_manifest]
        self.assertEqual(project_manifests, [])


class TestRequiredReadsState(tests.fixtures_required_reads.HomeOverrideEnvVarTestCaseMixin, unittest.TestCase):

    def test_unmarked_dedupe_key_is_not_satisfied(self):

        self.assertFalse(required_reading._state.RequiredReadsState.is_dedupe_key_satisfied(
            claude_session_id_string = "session-unmarked",
            dedupe_key_string = "some-key"
        ))

    def test_marked_dedupe_key_reads_back_as_satisfied(self):

        required_reading._state.RequiredReadsState.mark_dedupe_key_satisfied(
            claude_session_id_string = "session-alpha",
            dedupe_key_string = "python-style-guide"
        )
        self.assertTrue(required_reading._state.RequiredReadsState.is_dedupe_key_satisfied(
            claude_session_id_string = "session-alpha",
            dedupe_key_string = "python-style-guide"
        ))

    def test_second_mark_for_same_key_is_idempotent(self):

        required_reading._state.RequiredReadsState.mark_dedupe_key_satisfied(
            claude_session_id_string = "session-beta",
            dedupe_key_string = "k"
        )
        required_reading._state.RequiredReadsState.mark_dedupe_key_satisfied(
            claude_session_id_string = "session-beta",
            dedupe_key_string = "k"
        )
        self.assertTrue(required_reading._state.RequiredReadsState.is_dedupe_key_satisfied(
            claude_session_id_string = "session-beta",
            dedupe_key_string = "k"
        ))

    def test_different_sessions_do_not_share_flags(self):

        required_reading._state.RequiredReadsState.mark_dedupe_key_satisfied(
            claude_session_id_string = "session-one",
            dedupe_key_string = "shared-key"
        )
        self.assertFalse(required_reading._state.RequiredReadsState.is_dedupe_key_satisfied(
            claude_session_id_string = "session-two",
            dedupe_key_string = "shared-key"
        ))

    def test_clear_session_removes_all_flags_for_that_session(self):

        required_reading._state.RequiredReadsState.mark_dedupe_key_satisfied(
            claude_session_id_string = "session-clear",
            dedupe_key_string = "a"
        )
        required_reading._state.RequiredReadsState.mark_dedupe_key_satisfied(
            claude_session_id_string = "session-clear",
            dedupe_key_string = "b"
        )
        required_reading._state.RequiredReadsState.clear_session(claude_session_id_string = "session-clear")
        self.assertFalse(required_reading._state.RequiredReadsState.is_dedupe_key_satisfied(
            claude_session_id_string = "session-clear",
            dedupe_key_string = "a"
        ))
        self.assertFalse(required_reading._state.RequiredReadsState.is_dedupe_key_satisfied(
            claude_session_id_string = "session-clear",
            dedupe_key_string = "b"
        ))

    def test_clear_session_on_nonexistent_session_is_a_no_op(self):

        required_reading._state.RequiredReadsState.clear_session(claude_session_id_string = "session-never-existed")

    def test_sweep_stale_removes_old_session_directories_and_keeps_fresh_ones(self):

        required_reading._state.RequiredReadsState.mark_dedupe_key_satisfied(
            claude_session_id_string = "session-old",
            dedupe_key_string = "k"
        )
        required_reading._state.RequiredReadsState.mark_dedupe_key_satisfied(
            claude_session_id_string = "session-new",
            dedupe_key_string = "k"
        )
        old_session_directory_abs_path = required_reading._state.RequiredReadsState.get_session_directory_abs_path(
            claude_session_id_string = "session-old"
        )
        ten_days_ago_wall_clock_seconds = time.time() - (10 * 24 * 60 * 60)
        os.utime(old_session_directory_abs_path, (ten_days_ago_wall_clock_seconds, ten_days_ago_wall_clock_seconds))
        required_reading._state.RequiredReadsState.sweep_stale_session_directories()
        self.assertFalse(required_reading._state.RequiredReadsState.is_dedupe_key_satisfied(
            claude_session_id_string = "session-old",
            dedupe_key_string = "k"
        ))
        self.assertTrue(required_reading._state.RequiredReadsState.is_dedupe_key_satisfied(
            claude_session_id_string = "session-new",
            dedupe_key_string = "k"
        ))

    def test_sweep_stale_with_no_state_base_directory_is_a_no_op(self):

        required_reading._state.RequiredReadsState.sweep_stale_session_directories()


class PreToolUseRequiredReadsRuleRecordBuilder:

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

        return required_reading._manifest.RequiredReadsRuleRecord(
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

    def test_edit_payload_returns_normalized_file_path(self):

        edit_payload = tests.fixtures.PreToolUsePayloadFixtureBuilder.build_edit_payload(
            new_string_content = "x",
            file_path = "/tmp/foo.py"
        )
        extracted_abs_path = required_reading.pretooluse.PreToolUseRequiredReadsRuleChecks.extract_edited_file_abs_path_or_none(
            pretooluse_payload = edit_payload
        )
        self.assertIsNotNone(extracted_abs_path)
        self.assertTrue(extracted_abs_path.endswith("/tmp/foo.py"))

    def test_write_payload_returns_normalized_file_path(self):

        write_payload = tests.fixtures.PreToolUsePayloadFixtureBuilder.build_write_payload(
            file_content = "x",
            file_path = "/tmp/bar.py"
        )
        extracted_abs_path = required_reading.pretooluse.PreToolUseRequiredReadsRuleChecks.extract_edited_file_abs_path_or_none(
            pretooluse_payload = write_payload
        )
        self.assertIsNotNone(extracted_abs_path)
        self.assertTrue(extracted_abs_path.endswith("/tmp/bar.py"))

    def test_notebook_edit_payload_returns_notebook_path(self):

        notebook_edit_payload = tests.fixtures.PreToolUsePayloadFixtureBuilder.build_base_payload(
            tool_name = "NotebookEdit",
            tool_input = {"notebook_path": "/tmp/book.ipynb", "new_source": "x", "cell_id": "c"}
        )
        extracted_abs_path = required_reading.pretooluse.PreToolUseRequiredReadsRuleChecks.extract_edited_file_abs_path_or_none(
            pretooluse_payload = notebook_edit_payload
        )
        self.assertIsNotNone(extracted_abs_path)
        self.assertTrue(extracted_abs_path.endswith("/tmp/book.ipynb"))

    def test_read_payload_returns_normalized_file_path(self):

        read_payload = tests.fixtures.PreToolUsePayloadFixtureBuilder.build_read_payload(
            file_path = "/tmp/foo.py"
        )
        extracted_abs_path = required_reading.pretooluse.PreToolUseRequiredReadsRuleChecks.extract_edited_file_abs_path_or_none(
            pretooluse_payload = read_payload
        )
        self.assertIsNotNone(extracted_abs_path)
        self.assertTrue(extracted_abs_path.endswith("/tmp/foo.py"))

    def test_unknown_tool_returns_none(self):

        unrelated_payload = tests.fixtures.PreToolUsePayloadFixtureBuilder.build_bash_payload(
            bash_command_string = "echo hello"
        )
        extracted_abs_path = required_reading.pretooluse.PreToolUseRequiredReadsRuleChecks.extract_edited_file_abs_path_or_none(
            pretooluse_payload = unrelated_payload
        )
        self.assertIsNone(extracted_abs_path)

    def test_missing_file_path_field_returns_none(self):

        empty_edit_payload = tests.fixtures.PreToolUsePayloadFixtureBuilder.build_base_payload(
            tool_name = "Edit",
            tool_input = {}
        )
        extracted_abs_path = required_reading.pretooluse.PreToolUseRequiredReadsRuleChecks.extract_edited_file_abs_path_or_none(
            pretooluse_payload = empty_edit_payload
        )
        self.assertIsNone(extracted_abs_path)


class TestApplyProjectOverridesAgainstGlobalRules(unittest.TestCase):

    def test_project_override_drops_matching_global_rule(self):

        global_python_rule_record = PreToolUseRequiredReadsRuleRecordBuilder.build_rule_record(
            is_global_manifest = True,
            read_abs_path = "/home/zachm/Dev/ai-sanity/styleguides/python.md"
        )
        project_override_rule_record = PreToolUseRequiredReadsRuleRecordBuilder.build_rule_record(
            is_global_manifest = False,
            read_abs_path = "/project/docs/project-python-style.md",
            override_abs_path = "/home/zachm/Dev/ai-sanity/styleguides/python.md"
        )
        surviving_rule_records = required_reading.pretooluse.PreToolUseRequiredReadsRuleChecks.apply_project_overrides_against_global_rules(
            rule_records = [global_python_rule_record, project_override_rule_record]
        )
        self.assertEqual(len(surviving_rule_records), 1)
        self.assertFalse(surviving_rule_records[0].is_global_manifest)

    def test_project_rule_without_override_keeps_global(self):

        global_python_rule_record = PreToolUseRequiredReadsRuleRecordBuilder.build_rule_record(
            is_global_manifest = True,
            read_abs_path = "/home/zachm/Dev/ai-sanity/styleguides/python.md"
        )
        project_extra_rule_record = PreToolUseRequiredReadsRuleRecordBuilder.build_rule_record(
            is_global_manifest = False,
            read_abs_path = "/project/docs/product.md",
            override_abs_path = None
        )
        surviving_rule_records = required_reading.pretooluse.PreToolUseRequiredReadsRuleChecks.apply_project_overrides_against_global_rules(
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
        surviving_rule_records = required_reading.pretooluse.PreToolUseRequiredReadsRuleChecks.apply_project_overrides_against_global_rules(
            rule_records = [project_a_rule_record, project_b_override_rule_record]
        )
        self.assertEqual(len(surviving_rule_records), 2)


class TestFilterRulesByMatchCriterion(unittest.TestCase):

    def test_wildcard_rule_matches_every_path(self):

        wildcard_rule_record = PreToolUseRequiredReadsRuleRecordBuilder.build_rule_record(
            match_extension_suffix = None,
            match_filepath_substring = None
        )
        match_passed_rule_records = required_reading.pretooluse.PreToolUseRequiredReadsRuleChecks.filter_rules_by_match_criterion(
            rule_records = [wildcard_rule_record],
            candidate_file_abs_path = "/anywhere/foo.xyz"
        )
        self.assertEqual(len(match_passed_rule_records), 1)

    def test_extension_matches_when_path_ends_with_suffix(self):

        python_rule_record = PreToolUseRequiredReadsRuleRecordBuilder.build_rule_record(
            match_extension_suffix = ".py",
            match_filepath_substring = None
        )
        match_passed_rule_records = required_reading.pretooluse.PreToolUseRequiredReadsRuleChecks.filter_rules_by_match_criterion(
            rule_records = [python_rule_record],
            candidate_file_abs_path = "/c/users/zachm/dev/ai-sanity/hooks/bar.py"
        )
        self.assertEqual(len(match_passed_rule_records), 1)

    def test_extension_rejects_when_path_does_not_end_with_suffix(self):

        python_rule_record = PreToolUseRequiredReadsRuleRecordBuilder.build_rule_record(
            match_extension_suffix = ".py",
            match_filepath_substring = None
        )
        match_passed_rule_records = required_reading.pretooluse.PreToolUseRequiredReadsRuleChecks.filter_rules_by_match_criterion(
            rule_records = [python_rule_record],
            candidate_file_abs_path = "/c/users/zachm/dev/foo.md"
        )
        self.assertEqual(match_passed_rule_records, [])

    def test_filepath_matches_when_substring_appears_in_path(self):

        server_rule_record = PreToolUseRequiredReadsRuleRecordBuilder.build_rule_record(
            match_extension_suffix = None,
            match_filepath_substring = "/server/"
        )
        match_passed_rule_records = required_reading.pretooluse.PreToolUseRequiredReadsRuleChecks.filter_rules_by_match_criterion(
            rule_records = [server_rule_record],
            candidate_file_abs_path = "/c/users/zachm/dev/project/server/api/foo.py"
        )
        self.assertEqual(len(match_passed_rule_records), 1)

    def test_filepath_rejects_when_substring_absent_from_path(self):

        server_rule_record = PreToolUseRequiredReadsRuleRecordBuilder.build_rule_record(
            match_extension_suffix = None,
            match_filepath_substring = "/server/"
        )
        match_passed_rule_records = required_reading.pretooluse.PreToolUseRequiredReadsRuleChecks.filter_rules_by_match_criterion(
            rule_records = [server_rule_record],
            candidate_file_abs_path = "/c/users/zachm/dev/project/client/index.js"
        )
        self.assertEqual(match_passed_rule_records, [])


class TestIsReadOfAManifestListedDoc(tests.fixtures_required_reads.HomeOverrideEnvVarTestCaseMixin, unittest.TestCase):

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
        normalized_candidate_abs_path = required_reading._manifest.RequiredReadsPathNormalizer.normalize_path(markdown_doc_abs_path)
        is_manifest_listed = required_reading.pretooluse.PreToolUseRequiredReadsRuleChecks.is_read_of_a_manifest_listed_doc(
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
        normalized_candidate_abs_path = required_reading._manifest.RequiredReadsPathNormalizer.normalize_path(python_doc_abs_path)
        is_manifest_listed = required_reading.pretooluse.PreToolUseRequiredReadsRuleChecks.is_read_of_a_manifest_listed_doc(
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
        unrelated_abs_path = required_reading._manifest.RequiredReadsPathNormalizer.normalize_path(
            os.path.join(self.sandboxed_home_abs_path, "project", "notes.md")
        )
        is_manifest_listed = required_reading.pretooluse.PreToolUseRequiredReadsRuleChecks.is_read_of_a_manifest_listed_doc(
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
        normalized_candidate_abs_path = required_reading._manifest.RequiredReadsPathNormalizer.normalize_path(markdown_doc_abs_path)
        is_manifest_listed = required_reading.pretooluse.PreToolUseRequiredReadsRuleChecks.is_read_of_a_manifest_listed_doc(
            tool_name_string = "Edit",
            candidate_file_abs_path = normalized_candidate_abs_path,
            edited_file_abs_path = normalized_candidate_abs_path
        )
        self.assertFalse(is_manifest_listed)


class TestPartitionRulesIntoUnsatisfiedFireAndAlreadySatisfied(tests.fixtures_required_reads.HomeOverrideEnvVarTestCaseMixin, unittest.TestCase):

    def test_no_flags_set_means_every_rule_fires(self):

        python_rule_record = PreToolUseRequiredReadsRuleRecordBuilder.build_rule_record(
            dedupe_key = "python-style-guide"
        )
        markdown_rule_record = PreToolUseRequiredReadsRuleRecordBuilder.build_rule_record(
            dedupe_key = "markdown-style-guide"
        )
        rules_to_fire_list, rules_already_satisfied_list = (
            required_reading.pretooluse.PreToolUseRequiredReadsRuleChecks.partition_rules_into_unsatisfied_fire_and_already_satisfied(
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
        required_reading._state.RequiredReadsState.mark_dedupe_key_satisfied(
            claude_session_id_string = "session-partial",
            dedupe_key_string = "python-style-guide"
        )
        rules_to_fire_list, rules_already_satisfied_list = (
            required_reading.pretooluse.PreToolUseRequiredReadsRuleChecks.partition_rules_into_unsatisfied_fire_and_already_satisfied(
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
        required_reading._state.RequiredReadsState.mark_dedupe_key_satisfied(
            claude_session_id_string = "session-shared",
            dedupe_key_string = "shared-key"
        )
        rules_to_fire_list, rules_already_satisfied_list = (
            required_reading.pretooluse.PreToolUseRequiredReadsRuleChecks.partition_rules_into_unsatisfied_fire_and_already_satisfied(
                rule_records = [first_rule_record, second_rule_record],
                claude_session_id_string = "session-shared"
            )
        )
        self.assertEqual(rules_to_fire_list, [])
        self.assertEqual(len(rules_already_satisfied_list), 2)


class TestBuildDenyReasonString(unittest.TestCase):

    def test_deny_reason_lists_every_unsatisfied_rule_read_path_and_rule_id(self):

        first_unsatisfied_rule_record = PreToolUseRequiredReadsRuleRecordBuilder.build_rule_record(
            rule_id = "required-reads.json#0",
            manifest_abs_path = "/home/zachm/Dev/project/.ai-sanity/required-reads.json",
            read_abs_path = "/home/zachm/Dev/ai-sanity/styleguides/python.md"
        )
        second_unsatisfied_rule_record = PreToolUseRequiredReadsRuleRecordBuilder.build_rule_record(
            rule_id = "required-reads.json#3",
            manifest_abs_path = "/home/zachm/Dev/project/.ai-sanity/required-reads.json",
            read_abs_path = "/home/zachm/Dev/project/docs/CLAUDE.md"
        )
        deny_reason_string = required_reading.pretooluse.PreToolUseRequiredReadsRuleChecks.build_deny_reason_string(
            unsatisfied_rule_records = [first_unsatisfied_rule_record, second_unsatisfied_rule_record],
            edited_file_abs_path = "/home/zachm/Dev/project/src/main.py"
        )
        self.assertIn("/home/zachm/Dev/project/src/main.py", deny_reason_string)
        self.assertIn("/home/zachm/Dev/ai-sanity/styleguides/python.md", deny_reason_string)
        self.assertIn("/home/zachm/Dev/project/docs/CLAUDE.md", deny_reason_string)
        self.assertIn("required-reads.json#0", deny_reason_string)
        self.assertIn("required-reads.json#3", deny_reason_string)

    def test_partition_rules_keeps_present_and_flags_required_missing(self):

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
        present_records, required_missing_records = (
            required_reading.pretooluse.PreToolUseRequiredReadsRuleChecks.partition_rules_by_missing_read_targets(
                rule_records = [present_rule_record, missing_rule_record]
            )
        )
        self.assertEqual(len(present_records), 1)
        self.assertEqual(present_records[0].rule_id, "m#present")
        self.assertEqual(len(required_missing_records), 1)
        self.assertEqual(required_missing_records[0].rule_id, "m#missing")

class TestIsFileInsideConfigDirectory(unittest.TestCase):

    def test_file_under_home_dot_claude_returns_true(self):

        self.assertTrue(required_reading.pretooluse.PreToolUseRequiredReadsRuleChecks.is_file_inside_config_directory(
            edited_file_abs_path = "c:/users/zachm/.claude/plans/foo.md"
        ))

    def test_settings_json_under_home_dot_claude_returns_true(self):

        self.assertTrue(required_reading.pretooluse.PreToolUseRequiredReadsRuleChecks.is_file_inside_config_directory(
            edited_file_abs_path = "c:/users/zachm/.claude/settings.json"
        ))

    def test_file_under_project_dot_claude_returns_true(self):

        self.assertTrue(required_reading.pretooluse.PreToolUseRequiredReadsRuleChecks.is_file_inside_config_directory(
            edited_file_abs_path = "c:/users/zachm/dev/project/.claude/required-reads.json"
        ))

    def test_file_under_project_dot_ai_sanity_returns_true(self):

        self.assertTrue(required_reading.pretooluse.PreToolUseRequiredReadsRuleChecks.is_file_inside_config_directory(
            edited_file_abs_path = "c:/users/zachm/dev/project/.ai-sanity/required-reading.json"
        ))

    def test_regular_project_file_returns_false(self):

        self.assertFalse(required_reading.pretooluse.PreToolUseRequiredReadsRuleChecks.is_file_inside_config_directory(
            edited_file_abs_path = "c:/users/zachm/dev/project/src/foo.py"
        ))

    def test_partial_dot_claude_name_match_without_segment_boundary_returns_false(self):

        self.assertFalse(required_reading.pretooluse.PreToolUseRequiredReadsRuleChecks.is_file_inside_config_directory(
            edited_file_abs_path = "c:/users/zachm/dev/project/src/.claude-config/foo.py"
        ))

    def test_partial_dot_ai_sanity_name_match_without_segment_boundary_returns_false(self):

        self.assertFalse(required_reading.pretooluse.PreToolUseRequiredReadsRuleChecks.is_file_inside_config_directory(
            edited_file_abs_path = "c:/users/zachm/dev/project/src/.ai-sanity-extra/foo.py"
        ))


if __name__ == "__main__":
    unittest.main()
