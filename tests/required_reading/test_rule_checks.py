########################################################################################################################
# tests/required_reading/test_rule_checks.py
#
# required-reading rule-check tests
########################################################################################################################


import os
import sys
import tempfile
import time
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "hooks"))

import tests._common.fixtures
import tests.required_reading.fixtures_required_reads
import required_reading._manifest
import required_reading._state
import required_reading.pretooluse


HOME_OVERRIDE_ENV_VAR_TEST_CASE_MIXIN = tests.required_reading.fixtures_required_reads.HomeOverrideEnvVarTestCaseMixin
PRE_TOOL_USE_REQUIRED_READS_RULE_CHECKS = required_reading.pretooluse.PreToolUseRequiredReadsRuleChecks
REQUIRED_READS_MANIFEST_FIXTURE_BUILDER = (
    tests.required_reading.fixtures_required_reads.RequiredReadsManifestFixtureBuilder
)
REQUIRED_READS_PATH_NORMALIZER = required_reading._manifest.RequiredReadsPathNormalizer


class TestRequiredReadsPathNormalizer(HOME_OVERRIDE_ENV_VAR_TEST_CASE_MIXIN, unittest.TestCase):

    """Unit tests for `REQUIRED_READS_PATH_NORMALIZER.normalize_path`. Every path comparison in the required-reads
    subsystem goes through this function, so the tests focus on the three documented behaviors: tilde expansion with
    the test override, relative-path resolution against a base directory, and forward-slash output."""


    def test_tilde_expansion_uses_home_override_when_set(self):

        normalized_path_string = REQUIRED_READS_PATH_NORMALIZER.normalize_path("~/foo/bar.md")
        expected_prefix = self.sandboxed_home_abs_path.replace("\\", "/").lower()
        self.assertTrue(normalized_path_string.startswith(expected_prefix))
        self.assertTrue(normalized_path_string.endswith("/foo/bar.md"))


    def test_bare_tilde_expands_to_home_override(self):

        normalized_path_string = REQUIRED_READS_PATH_NORMALIZER.normalize_path("~")
        self.assertEqual(normalized_path_string, self.sandboxed_home_abs_path.replace("\\", "/").lower())


    def test_relative_path_resolved_against_base_directory(self):

        base_directory_abs_path = os.path.join(self.sandboxed_home_abs_path, "some", "project", ".ai-sanity")
        normalized_path_string = REQUIRED_READS_PATH_NORMALIZER.normalize_path(
            "../docs/stack.md",
            base_directory_abs_path = base_directory_abs_path
        )
        expected_suffix = "/some/project/docs/stack.md"
        self.assertTrue(normalized_path_string.endswith(expected_suffix))


    def test_absolute_path_ignores_base_directory(self):

        base_directory_abs_path = os.path.join(self.sandboxed_home_abs_path, "irrelevant")
        absolute_input_path_string = os.path.join(self.sandboxed_home_abs_path, "absolute", "foo.md")
        normalized_path_string = REQUIRED_READS_PATH_NORMALIZER.normalize_path(
            absolute_input_path_string,
            base_directory_abs_path = base_directory_abs_path
        )
        self.assertEqual(normalized_path_string, absolute_input_path_string.replace("\\", "/").lower())


    def test_output_uses_forward_slashes_only(self):

        normalized_path_string = REQUIRED_READS_PATH_NORMALIZER.normalize_path("~/a/b/c.md")
        self.assertNotIn("\\", normalized_path_string)


    def test_output_is_lowercased(self):

        normalized_path_string = REQUIRED_READS_PATH_NORMALIZER.normalize_path("~/Foo/Bar.MD")
        self.assertEqual(normalized_path_string, normalized_path_string.lower())


class TestRequiredReadsManifestLoaderLoadRecords(HOME_OVERRIDE_ENV_VAR_TEST_CASE_MIXIN, unittest.TestCase):

    """Unit tests for `required_reading._manifest.RequiredReadsManifestLoader.load_manifest_rule_records`."""


    def test_well_formed_manifest_returns_one_record_per_rule(self):

        manifest_abs_path = REQUIRED_READS_MANIFEST_FIXTURE_BUILDER.write_manifest_file(
            manifest_directory_abs_path = self.sandboxed_home_abs_path,
            rule_dicts = [
                {"extension": ".py", "read": "~/docs/python.md"},
                {"extension": ".md", "read": "~/docs/markdown.md"}
            ]
        )
        loaded_rule_records = required_reading._manifest.RequiredReadsManifestLoader.load_manifest_rule_records(
            manifest_abs_path = manifest_abs_path,

        )
        self.assertEqual(len(loaded_rule_records), 2)
        self.assertEqual(loaded_rule_records[0].match_extension_suffix, ".py")
        self.assertIsNone(loaded_rule_records[0].match_filepath_substring)



    def test_malformed_json_returns_empty_list(self):

        manifest_abs_path = REQUIRED_READS_MANIFEST_FIXTURE_BUILDER.write_raw_manifest_body(
            manifest_directory_abs_path = self.sandboxed_home_abs_path,
            raw_manifest_body_string = "{not valid json"
        )
        loaded_rule_records = required_reading._manifest.RequiredReadsManifestLoader.load_manifest_rule_records(
            manifest_abs_path = manifest_abs_path,

        )
        self.assertEqual(loaded_rule_records, [])


    def test_top_level_not_object_returns_empty_list(self):

        manifest_abs_path = REQUIRED_READS_MANIFEST_FIXTURE_BUILDER.write_raw_manifest_body(
            manifest_directory_abs_path = self.sandboxed_home_abs_path,
            raw_manifest_body_string = "[1, 2, 3]"
        )
        loaded_rule_records = required_reading._manifest.RequiredReadsManifestLoader.load_manifest_rule_records(
            manifest_abs_path = manifest_abs_path,

        )
        self.assertEqual(loaded_rule_records, [])


    def test_missing_rules_key_returns_empty_list(self):

        manifest_abs_path = REQUIRED_READS_MANIFEST_FIXTURE_BUILDER.write_raw_manifest_body(
            manifest_directory_abs_path = self.sandboxed_home_abs_path,
            raw_manifest_body_string = "{\"other\": []}"
        )
        loaded_rule_records = required_reading._manifest.RequiredReadsManifestLoader.load_manifest_rule_records(
            manifest_abs_path = manifest_abs_path,

        )
        self.assertEqual(loaded_rule_records, [])


    def test_rules_value_not_list_returns_empty_list(self):

        manifest_abs_path = REQUIRED_READS_MANIFEST_FIXTURE_BUILDER.write_raw_manifest_body(
            manifest_directory_abs_path = self.sandboxed_home_abs_path,
            raw_manifest_body_string = "{\"rules\": {}}"
        )
        loaded_rule_records = required_reading._manifest.RequiredReadsManifestLoader.load_manifest_rule_records(
            manifest_abs_path = manifest_abs_path,

        )
        self.assertEqual(loaded_rule_records, [])


    def test_missing_file_returns_empty_list(self):

        loaded_rule_records = required_reading._manifest.RequiredReadsManifestLoader.load_manifest_rule_records(
            manifest_abs_path = os.path.join(self.sandboxed_home_abs_path, "does", "not", "exist.json"),

        )
        self.assertEqual(loaded_rule_records, [])


    def test_rule_with_only_read_is_a_valid_wildcard(self):

        manifest_abs_path = REQUIRED_READS_MANIFEST_FIXTURE_BUILDER.write_manifest_file(
            manifest_directory_abs_path = self.sandboxed_home_abs_path,
            rule_dicts = [
                {"read": "~/docs/always.md"}
            ]
        )
        loaded_rule_records = required_reading._manifest.RequiredReadsManifestLoader.load_manifest_rule_records(
            manifest_abs_path = manifest_abs_path,

        )
        self.assertEqual(len(loaded_rule_records), 1)
        self.assertIsNone(loaded_rule_records[0].match_extension_suffix)
        self.assertIsNone(loaded_rule_records[0].match_filepath_substring)


    def test_rule_missing_read_field_is_skipped_but_siblings_kept(self):

        manifest_abs_path = REQUIRED_READS_MANIFEST_FIXTURE_BUILDER.write_manifest_file(
            manifest_directory_abs_path = self.sandboxed_home_abs_path,
            rule_dicts = [
                {"extension": ".py"},
                {"extension": ".md", "read": "~/docs/markdown.md"}
            ]
        )
        loaded_rule_records = required_reading._manifest.RequiredReadsManifestLoader.load_manifest_rule_records(
            manifest_abs_path = manifest_abs_path,

        )
        self.assertEqual(len(loaded_rule_records), 1)
        self.assertEqual(loaded_rule_records[0].match_extension_suffix, ".md")


    def test_rule_with_both_extension_and_filepath_is_skipped(self):

        manifest_abs_path = REQUIRED_READS_MANIFEST_FIXTURE_BUILDER.write_manifest_file(
            manifest_directory_abs_path = self.sandboxed_home_abs_path,
            rule_dicts = [
                {"extension": ".py", "filepath": "/server/", "read": "~/docs/both.md"},
                {"extension": ".md", "read": "~/docs/markdown.md"}
            ]
        )
        loaded_rule_records = required_reading._manifest.RequiredReadsManifestLoader.load_manifest_rule_records(
            manifest_abs_path = manifest_abs_path,

        )
        self.assertEqual(len(loaded_rule_records), 1)
        self.assertEqual(loaded_rule_records[0].match_extension_suffix, ".md")


    def test_filepath_rule_populates_only_filepath_field(self):

        manifest_abs_path = REQUIRED_READS_MANIFEST_FIXTURE_BUILDER.write_manifest_file(
            manifest_directory_abs_path = self.sandboxed_home_abs_path,
            rule_dicts = [
                {"filepath": "/server/", "read": "~/docs/backend.md"}
            ]
        )
        loaded_rule_records = required_reading._manifest.RequiredReadsManifestLoader.load_manifest_rule_records(
            manifest_abs_path = manifest_abs_path,

        )
        self.assertEqual(len(loaded_rule_records), 1)
        self.assertIsNone(loaded_rule_records[0].match_extension_suffix)
        self.assertEqual(loaded_rule_records[0].match_filepath_substring, "/server/")


    def test_match_field_values_are_lowercased_at_load_time(self):

        manifest_abs_path = REQUIRED_READS_MANIFEST_FIXTURE_BUILDER.write_manifest_file(
            manifest_directory_abs_path = self.sandboxed_home_abs_path,
            rule_dicts = [
                {"extension": ".PY", "read": "~/docs/python.md"},
                {"filepath": "/Server/", "read": "~/docs/backend.md"}
            ]
        )
        loaded_rule_records = required_reading._manifest.RequiredReadsManifestLoader.load_manifest_rule_records(
            manifest_abs_path = manifest_abs_path,

        )
        self.assertEqual(loaded_rule_records[0].match_extension_suffix, ".py")
        self.assertEqual(loaded_rule_records[1].match_filepath_substring, "/server/")


    def test_unknown_fields_including_comment_and_legacy_match_and_mode_are_ignored(self):

        manifest_abs_path = REQUIRED_READS_MANIFEST_FIXTURE_BUILDER.write_manifest_file(
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

        )
        self.assertEqual(len(loaded_rule_records), 1)
        self.assertEqual(loaded_rule_records[0].match_extension_suffix, ".py")


    def test_relative_read_path_resolved_against_project_root_not_manifest_directory(self):

        project_root_abs_path = os.path.join(self.sandboxed_home_abs_path, "some-project")
        os.makedirs(project_root_abs_path, exist_ok = True)
        manifest_abs_path = REQUIRED_READS_MANIFEST_FIXTURE_BUILDER.write_manifest_file(
            manifest_directory_abs_path = project_root_abs_path,
            rule_dicts = [
                {"extension": ".py", "read": "./docs/python.md"}
            ]
        )
        loaded_rule_records = required_reading._manifest.RequiredReadsManifestLoader.load_manifest_rule_records(
            manifest_abs_path = manifest_abs_path,

        )
        self.assertEqual(len(loaded_rule_records), 1)
        expected_read_abs_path_suffix = "/some-project/docs/python.md"
        self.assertTrue(loaded_rule_records[0].read_abs_path.endswith(expected_read_abs_path_suffix))
        self.assertNotIn("/.ai-sanity/docs/", loaded_rule_records[0].read_abs_path)


    def test_extension_list_expands_to_one_record_per_extension(self):

        manifest_abs_path = REQUIRED_READS_MANIFEST_FIXTURE_BUILDER.write_manifest_file(
            manifest_directory_abs_path = self.sandboxed_home_abs_path,
            rule_dicts = [
                {"extension": [".js", ".html"], "read": "~/docs/frontend.md"}
            ]
        )
        loaded_rule_records = required_reading._manifest.RequiredReadsManifestLoader.load_manifest_rule_records(
            manifest_abs_path = manifest_abs_path
        )
        self.assertEqual(len(loaded_rule_records), 2)
        extensions = {r.match_extension_suffix for r in loaded_rule_records}
        self.assertEqual(extensions, {".js", ".html"})


    def test_read_list_expands_to_one_record_per_read_path(self):

        manifest_abs_path = REQUIRED_READS_MANIFEST_FIXTURE_BUILDER.write_manifest_file(
            manifest_directory_abs_path = self.sandboxed_home_abs_path,
            rule_dicts = [
                {"extension": ".css", "read": ["~/docs/ux.md", "~/docs/mobile.md"]}
            ]
        )
        loaded_rule_records = required_reading._manifest.RequiredReadsManifestLoader.load_manifest_rule_records(
            manifest_abs_path = manifest_abs_path
        )
        self.assertEqual(len(loaded_rule_records), 2)
        self.assertTrue(all(r.match_extension_suffix == ".css" for r in loaded_rule_records))
        read_paths = {r.read_abs_path for r in loaded_rule_records}
        self.assertTrue(any("ux.md" in p for p in read_paths))
        self.assertTrue(any("mobile.md" in p for p in read_paths))


    def test_filepath_list_expands_to_one_record_per_filepath(self):

        manifest_abs_path = REQUIRED_READS_MANIFEST_FIXTURE_BUILDER.write_manifest_file(
            manifest_directory_abs_path = self.sandboxed_home_abs_path,
            rule_dicts = [
                {"filepath": ["test", "playwright"], "read": "~/docs/tests.md"}
            ]
        )
        loaded_rule_records = required_reading._manifest.RequiredReadsManifestLoader.load_manifest_rule_records(
            manifest_abs_path = manifest_abs_path
        )
        self.assertEqual(len(loaded_rule_records), 2)
        filepaths = {r.match_filepath_substring for r in loaded_rule_records}
        self.assertEqual(filepaths, {"test", "playwright"})


    def test_list_extension_and_list_read_produces_cross_product(self):

        manifest_abs_path = REQUIRED_READS_MANIFEST_FIXTURE_BUILDER.write_manifest_file(
            manifest_directory_abs_path = self.sandboxed_home_abs_path,
            rule_dicts = [
                {"extension": [".js", ".html"], "read": ["~/docs/frontend.md", "~/docs/ux.md"]}
            ]
        )
        loaded_rule_records = required_reading._manifest.RequiredReadsManifestLoader.load_manifest_rule_records(
            manifest_abs_path = manifest_abs_path
        )
        self.assertEqual(len(loaded_rule_records), 4)


    def test_note_field_is_ignored(self):

        manifest_abs_path = REQUIRED_READS_MANIFEST_FIXTURE_BUILDER.write_manifest_file(
            manifest_directory_abs_path = self.sandboxed_home_abs_path,
            rule_dicts = [
                {"extension": ".py", "read": "~/docs/python.md", "note": "this is ignored"}
            ]
        )
        loaded_rule_records = required_reading._manifest.RequiredReadsManifestLoader.load_manifest_rule_records(
            manifest_abs_path = manifest_abs_path
        )
        self.assertEqual(len(loaded_rule_records), 1)


class TestRequiredReadsManifestLoaderDiscovery(HOME_OVERRIDE_ENV_VAR_TEST_CASE_MIXIN, unittest.TestCase):

    def test_hooks_repo_global_manifest_is_discovered(self):

        project_directory_abs_path = os.path.join(self.sandboxed_home_abs_path, "some", "project")
        os.makedirs(project_directory_abs_path, exist_ok = True)
        edited_file_abs_path = os.path.join(project_directory_abs_path, "src", "foo.py")
        discovered_manifest_abs_paths = required_reading._manifest.RequiredReadsManifestLoader.discover_manifests(
            edited_file_abs_path = edited_file_abs_path
        )
        self.assertTrue(len(discovered_manifest_abs_paths) >= 1)
        self.assertTrue(any(
            path.endswith("/.ai-sanity/required-styleguides.json")
            for path in discovered_manifest_abs_paths
        ))


    def test_discovery_order_is_global_then_project(self):

        project_directory_abs_path = os.path.join(self.sandboxed_home_abs_path, "some", "project")
        os.makedirs(project_directory_abs_path, exist_ok = True)
        REQUIRED_READS_MANIFEST_FIXTURE_BUILDER.write_manifest_file(
            manifest_directory_abs_path = project_directory_abs_path,
            rule_dicts = []
        )
        edited_file_abs_path = os.path.join(project_directory_abs_path, "src", "foo.py")
        discovered_manifest_abs_paths = required_reading._manifest.RequiredReadsManifestLoader.discover_manifests(
            edited_file_abs_path = edited_file_abs_path
        )
        global_index = next(i for i, p in enumerate(discovered_manifest_abs_paths) if "required-styleguides.json" in p)
        project_index = next(i for i, p in enumerate(discovered_manifest_abs_paths) if "required-reading.json" in p)
        self.assertLess(global_index, project_index)


    def test_walk_passes_intermediate_directories_without_manifests(self):

        deep_directory_abs_path = os.path.join(self.sandboxed_home_abs_path, "a", "b", "c", "d")
        os.makedirs(deep_directory_abs_path, exist_ok = True)
        REQUIRED_READS_MANIFEST_FIXTURE_BUILDER.write_manifest_file(
            manifest_directory_abs_path = os.path.join(self.sandboxed_home_abs_path, "a", "b"),
            rule_dicts = []
        )
        edited_file_abs_path = os.path.join(deep_directory_abs_path, "foo.py")
        discovered_manifest_abs_paths = required_reading._manifest.RequiredReadsManifestLoader.discover_manifests(
            edited_file_abs_path = edited_file_abs_path
        )
        project_manifest_abs_paths = [
            p for p in discovered_manifest_abs_paths if "required-reading.json" in p
        ]
        self.assertEqual(len(project_manifest_abs_paths), 1)
        self.assertIn("/a/b/.ai-sanity/required-reading.json", project_manifest_abs_paths[0])


    def test_walk_stops_at_home_and_does_not_escape_above(self):

        grandparent_directory_abs_path = os.path.dirname(self.sandboxed_home_abs_path)
        REQUIRED_READS_MANIFEST_FIXTURE_BUILDER.write_manifest_file(
            manifest_directory_abs_path = grandparent_directory_abs_path,
            rule_dicts = []
        )
        edited_file_abs_path = os.path.join(self.sandboxed_home_abs_path, "project", "src", "foo.py")
        discovered_manifest_abs_paths = required_reading._manifest.RequiredReadsManifestLoader.discover_manifests(
            edited_file_abs_path = edited_file_abs_path
        )
        project_manifest_abs_paths = [
            p for p in discovered_manifest_abs_paths if "required-reading.json" in p
        ]
        self.assertEqual(project_manifest_abs_paths, [])


    def test_no_manifests_anywhere_returns_only_hooks_repo_global(self):

        edited_file_abs_path = os.path.join(self.sandboxed_home_abs_path, "a", "b", "foo.py")
        discovered_manifest_abs_paths = required_reading._manifest.RequiredReadsManifestLoader.discover_manifests(
            edited_file_abs_path = edited_file_abs_path
        )
        project_manifest_abs_paths = [
            p for p in discovered_manifest_abs_paths if "required-reading.json" in p
        ]
        self.assertEqual(project_manifest_abs_paths, [])


class TestRequiredReadsState(HOME_OVERRIDE_ENV_VAR_TEST_CASE_MIXIN, unittest.TestCase):

    def test_unmarked_read_path_is_not_satisfied(self):

        self.assertFalse(required_reading._state.RequiredReadsState.is_read_satisfied(
            claude_session_id_string = "session-unmarked",
            read_abs_path_string = "/fake/docs/unread.md"
        ))


    def test_marked_read_path_reads_back_as_satisfied(self):

        required_reading._state.RequiredReadsState.mark_read_satisfied(
            claude_session_id_string = "session-alpha",
            read_abs_path_string = "/fake/docs/python.md"
        )
        self.assertTrue(required_reading._state.RequiredReadsState.is_read_satisfied(
            claude_session_id_string = "session-alpha",
            read_abs_path_string = "/fake/docs/python.md"
        ))


    def test_second_mark_for_same_path_is_idempotent(self):

        required_reading._state.RequiredReadsState.mark_read_satisfied(
            claude_session_id_string = "session-beta",
            read_abs_path_string = "/fake/docs/style.md"
        )
        required_reading._state.RequiredReadsState.mark_read_satisfied(
            claude_session_id_string = "session-beta",
            read_abs_path_string = "/fake/docs/style.md"
        )
        self.assertTrue(required_reading._state.RequiredReadsState.is_read_satisfied(
            claude_session_id_string = "session-beta",
            read_abs_path_string = "/fake/docs/style.md"
        ))


    def test_different_sessions_do_not_share_flags(self):

        required_reading._state.RequiredReadsState.mark_read_satisfied(
            claude_session_id_string = "session-one",
            read_abs_path_string = "/fake/docs/shared.md"
        )
        self.assertFalse(required_reading._state.RequiredReadsState.is_read_satisfied(
            claude_session_id_string = "session-two",
            read_abs_path_string = "/fake/docs/shared.md"
        ))


    def test_clear_session_removes_all_flags_for_that_session(self):

        required_reading._state.RequiredReadsState.mark_read_satisfied(
            claude_session_id_string = "session-clear",
            read_abs_path_string = "/fake/docs/alpha.md"
        )
        required_reading._state.RequiredReadsState.mark_read_satisfied(
            claude_session_id_string = "session-clear",
            read_abs_path_string = "/fake/docs/bravo.md"
        )
        required_reading._state.RequiredReadsState.clear_session(claude_session_id_string = "session-clear")
        self.assertFalse(required_reading._state.RequiredReadsState.is_read_satisfied(
            claude_session_id_string = "session-clear",
            read_abs_path_string = "/fake/docs/alpha.md"
        ))
        self.assertFalse(required_reading._state.RequiredReadsState.is_read_satisfied(
            claude_session_id_string = "session-clear",
            read_abs_path_string = "/fake/docs/bravo.md"
        ))


    def test_clear_session_on_nonexistent_session_is_a_no_op(self):

        required_reading._state.RequiredReadsState.clear_session(claude_session_id_string = "session-never-existed")


    def test_sweep_stale_removes_old_session_directories_and_keeps_fresh_ones(self):

        required_reading._state.RequiredReadsState.mark_read_satisfied(
            claude_session_id_string = "session-old",
            read_abs_path_string = "/fake/docs/style.md"
        )
        required_reading._state.RequiredReadsState.mark_read_satisfied(
            claude_session_id_string = "session-new",
            read_abs_path_string = "/fake/docs/style.md"
        )
        old_session_directory_abs_path = required_reading._state.RequiredReadsState.get_session_directory_abs_path(
            claude_session_id_string = "session-old"
        )
        ten_days_ago_wall_clock_seconds = time.time() - (10 * 24 * 60 * 60)
        os.utime(old_session_directory_abs_path, (ten_days_ago_wall_clock_seconds, ten_days_ago_wall_clock_seconds))
        required_reading._state.RequiredReadsState.sweep_stale_session_directories()
        self.assertFalse(required_reading._state.RequiredReadsState.is_read_satisfied(
            claude_session_id_string = "session-old",
            read_abs_path_string = "/fake/docs/style.md"
        ))
        self.assertTrue(required_reading._state.RequiredReadsState.is_read_satisfied(
            claude_session_id_string = "session-new",
            read_abs_path_string = "/fake/docs/style.md"
        ))


    def test_sweep_stale_with_no_state_base_directory_is_a_no_op(self):

        required_reading._state.RequiredReadsState.sweep_stale_session_directories()


class PreToolUseRequiredReadsRuleRecordBuilder:

    @staticmethod
    def build_rule_record(rule_id = "manifest.json#0",
        manifest_abs_path = "/fake/manifest.json",
        match_extension_suffix = ".py",
        match_filepath_substring = None,
        read_abs_path = "/fake/docs/python.md",
    ):

        return required_reading._manifest.RequiredReadsRuleRecord(
            rule_id = rule_id,
            manifest_abs_path = manifest_abs_path,
            match_extension_suffix = match_extension_suffix,
            match_filepath_substring = match_filepath_substring,
            read_abs_path = read_abs_path,
        )


class TestExtractEditedFilePath(unittest.TestCase):

    def test_edit_payload_returns_normalized_file_path(self):

        edit_payload = tests._common.fixtures.PreToolUsePayloadFixtureBuilder.build_edit_payload(
            new_string_content = "x",
            file_path = "/tmp/foo.py"
        )
        extracted_abs_path = PRE_TOOL_USE_REQUIRED_READS_RULE_CHECKS.extract_edited_file_abs_path_or_none(
            pretooluse_payload = edit_payload
        )
        self.assertIsNotNone(extracted_abs_path)
        self.assertTrue(extracted_abs_path.endswith("/tmp/foo.py"))


    def test_write_payload_returns_normalized_file_path(self):

        write_payload = tests._common.fixtures.PreToolUsePayloadFixtureBuilder.build_write_payload(
            file_content = "x",
            file_path = "/tmp/bar.py"
        )
        extracted_abs_path = PRE_TOOL_USE_REQUIRED_READS_RULE_CHECKS.extract_edited_file_abs_path_or_none(
            pretooluse_payload = write_payload
        )
        self.assertIsNotNone(extracted_abs_path)
        self.assertTrue(extracted_abs_path.endswith("/tmp/bar.py"))


    def test_notebook_edit_payload_returns_notebook_path(self):

        notebook_edit_payload = tests._common.fixtures.PreToolUsePayloadFixtureBuilder.build_base_payload(
            tool_name = "NotebookEdit",
            tool_input = {"notebook_path": "/tmp/book.ipynb", "new_source": "x", "cell_id": "c"}
        )
        extracted_abs_path = PRE_TOOL_USE_REQUIRED_READS_RULE_CHECKS.extract_edited_file_abs_path_or_none(
            pretooluse_payload = notebook_edit_payload
        )
        self.assertIsNotNone(extracted_abs_path)
        self.assertTrue(extracted_abs_path.endswith("/tmp/book.ipynb"))


    def test_read_payload_returns_normalized_file_path(self):

        read_payload = tests._common.fixtures.PreToolUsePayloadFixtureBuilder.build_read_payload(
            file_path = "/tmp/foo.py"
        )
        extracted_abs_path = PRE_TOOL_USE_REQUIRED_READS_RULE_CHECKS.extract_edited_file_abs_path_or_none(
            pretooluse_payload = read_payload
        )
        self.assertIsNotNone(extracted_abs_path)
        self.assertTrue(extracted_abs_path.endswith("/tmp/foo.py"))


    def test_unknown_tool_returns_none(self):

        unrelated_payload = tests._common.fixtures.PreToolUsePayloadFixtureBuilder.build_bash_payload(
            bash_command_string = "echo hello"
        )
        extracted_abs_path = PRE_TOOL_USE_REQUIRED_READS_RULE_CHECKS.extract_edited_file_abs_path_or_none(
            pretooluse_payload = unrelated_payload
        )
        self.assertIsNone(extracted_abs_path)


    def test_missing_file_path_field_returns_none(self):

        empty_edit_payload = tests._common.fixtures.PreToolUsePayloadFixtureBuilder.build_base_payload(
            tool_name = "Edit",
            tool_input = {}
        )
        extracted_abs_path = PRE_TOOL_USE_REQUIRED_READS_RULE_CHECKS.extract_edited_file_abs_path_or_none(
            pretooluse_payload = empty_edit_payload
        )
        self.assertIsNone(extracted_abs_path)


class TestFilterRulesByMatchCriterion(unittest.TestCase):

    def test_wildcard_rule_matches_every_path(self):

        wildcard_rule_record = PreToolUseRequiredReadsRuleRecordBuilder.build_rule_record(
            match_extension_suffix = None,
            match_filepath_substring = None
        )
        match_passed_rule_records = PRE_TOOL_USE_REQUIRED_READS_RULE_CHECKS.filter_rules_by_match_criterion(
            rule_records = [wildcard_rule_record],
            candidate_file_abs_path = "/anywhere/foo.xyz"
        )
        self.assertEqual(len(match_passed_rule_records), 1)


    def test_extension_matches_when_path_ends_with_suffix(self):

        python_rule_record = PreToolUseRequiredReadsRuleRecordBuilder.build_rule_record(
            match_extension_suffix = ".py",
            match_filepath_substring = None
        )
        match_passed_rule_records = PRE_TOOL_USE_REQUIRED_READS_RULE_CHECKS.filter_rules_by_match_criterion(
            rule_records = [python_rule_record],
            candidate_file_abs_path = "/c/users/zachm/dev/ai-sanity/hooks/bar.py"
        )
        self.assertEqual(len(match_passed_rule_records), 1)


    def test_extension_rejects_when_path_does_not_end_with_suffix(self):

        python_rule_record = PreToolUseRequiredReadsRuleRecordBuilder.build_rule_record(
            match_extension_suffix = ".py",
            match_filepath_substring = None
        )
        match_passed_rule_records = PRE_TOOL_USE_REQUIRED_READS_RULE_CHECKS.filter_rules_by_match_criterion(
            rule_records = [python_rule_record],
            candidate_file_abs_path = "/c/users/zachm/dev/foo.md"
        )
        self.assertEqual(match_passed_rule_records, [])


    def test_filepath_matches_when_substring_appears_in_path(self):

        server_rule_record = PreToolUseRequiredReadsRuleRecordBuilder.build_rule_record(
            match_extension_suffix = None,
            match_filepath_substring = "/server/"
        )
        match_passed_rule_records = PRE_TOOL_USE_REQUIRED_READS_RULE_CHECKS.filter_rules_by_match_criterion(
            rule_records = [server_rule_record],
            candidate_file_abs_path = "/c/users/zachm/dev/project/server/api/foo.py"
        )
        self.assertEqual(len(match_passed_rule_records), 1)


    def test_filepath_rejects_when_substring_absent_from_path(self):

        server_rule_record = PreToolUseRequiredReadsRuleRecordBuilder.build_rule_record(
            match_extension_suffix = None,
            match_filepath_substring = "/server/"
        )
        match_passed_rule_records = PRE_TOOL_USE_REQUIRED_READS_RULE_CHECKS.filter_rules_by_match_criterion(
            rule_records = [server_rule_record],
            candidate_file_abs_path = "/c/users/zachm/dev/project/client/index.js"
        )
        self.assertEqual(match_passed_rule_records, [])


class TestIsReadOfAManifestListedDoc(HOME_OVERRIDE_ENV_VAR_TEST_CASE_MIXIN, unittest.TestCase):

    def test_read_of_self_target_doc_returns_true(self):

        markdown_doc_abs_path = os.path.join(self.sandboxed_home_abs_path, "markdown.md")
        with open(markdown_doc_abs_path, "w", encoding = "utf-8") as open_doc_file_handle:
            open_doc_file_handle.write("# md")
        REQUIRED_READS_MANIFEST_FIXTURE_BUILDER.write_manifest_file(
            manifest_directory_abs_path = self.sandboxed_home_abs_path,
            rule_dicts = [
                {"extension": ".md", "read": markdown_doc_abs_path}
            ]
        )
        normalized_candidate_abs_path = REQUIRED_READS_PATH_NORMALIZER.normalize_path(markdown_doc_abs_path)
        is_manifest_listed = PRE_TOOL_USE_REQUIRED_READS_RULE_CHECKS.is_read_of_a_manifest_listed_doc(
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
        REQUIRED_READS_MANIFEST_FIXTURE_BUILDER.write_manifest_file(
            manifest_directory_abs_path = self.sandboxed_home_abs_path,
            rule_dicts = [
                {"read": claude_md_abs_path},
                {"extension": ".py", "read": python_doc_abs_path}
            ]
        )
        normalized_candidate_abs_path = REQUIRED_READS_PATH_NORMALIZER.normalize_path(python_doc_abs_path)
        is_manifest_listed = PRE_TOOL_USE_REQUIRED_READS_RULE_CHECKS.is_read_of_a_manifest_listed_doc(
            tool_name_string = "Read",
            candidate_file_abs_path = normalized_candidate_abs_path,
            edited_file_abs_path = normalized_candidate_abs_path
        )
        self.assertTrue(is_manifest_listed)


    def test_read_of_unrelated_file_returns_false(self):

        markdown_doc_abs_path = os.path.join(self.sandboxed_home_abs_path, "markdown.md")
        with open(markdown_doc_abs_path, "w", encoding = "utf-8") as open_doc_file_handle:
            open_doc_file_handle.write("# md")
        REQUIRED_READS_MANIFEST_FIXTURE_BUILDER.write_manifest_file(
            manifest_directory_abs_path = self.sandboxed_home_abs_path,
            rule_dicts = [
                {"extension": ".md", "read": markdown_doc_abs_path}
            ]
        )
        unrelated_abs_path = REQUIRED_READS_PATH_NORMALIZER.normalize_path(
            os.path.join(self.sandboxed_home_abs_path, "project", "notes.md")
        )
        is_manifest_listed = PRE_TOOL_USE_REQUIRED_READS_RULE_CHECKS.is_read_of_a_manifest_listed_doc(
            tool_name_string = "Read",
            candidate_file_abs_path = unrelated_abs_path,
            edited_file_abs_path = unrelated_abs_path
        )
        self.assertFalse(is_manifest_listed)


    def test_edit_of_target_doc_returns_false(self):

        markdown_doc_abs_path = os.path.join(self.sandboxed_home_abs_path, "markdown.md")
        with open(markdown_doc_abs_path, "w", encoding = "utf-8") as open_doc_file_handle:
            open_doc_file_handle.write("# md")
        REQUIRED_READS_MANIFEST_FIXTURE_BUILDER.write_manifest_file(
            manifest_directory_abs_path = self.sandboxed_home_abs_path,
            rule_dicts = [
                {"extension": ".md", "read": markdown_doc_abs_path}
            ]
        )
        normalized_candidate_abs_path = REQUIRED_READS_PATH_NORMALIZER.normalize_path(markdown_doc_abs_path)
        is_manifest_listed = PRE_TOOL_USE_REQUIRED_READS_RULE_CHECKS.is_read_of_a_manifest_listed_doc(
            tool_name_string = "Edit",
            candidate_file_abs_path = normalized_candidate_abs_path,
            edited_file_abs_path = normalized_candidate_abs_path
        )
        self.assertFalse(is_manifest_listed)


class TestPartitionRulesIntoUnsatisfiedFireAndAlreadySatisfied(
    HOME_OVERRIDE_ENV_VAR_TEST_CASE_MIXIN,
    unittest.TestCase
):


    def test_no_flags_set_means_every_rule_fires(self):

        python_rule_record = PreToolUseRequiredReadsRuleRecordBuilder.build_rule_record(
            read_abs_path = "/fake/docs/python.md"
        )
        markdown_rule_record = PreToolUseRequiredReadsRuleRecordBuilder.build_rule_record(
            read_abs_path = "/fake/docs/markdown.md"
        )
        rules_to_fire_list, rules_already_satisfied_list = (
            PRE_TOOL_USE_REQUIRED_READS_RULE_CHECKS.partition_rules_into_unsatisfied_fire_and_already_satisfied(
                rule_records = [python_rule_record, markdown_rule_record],
                claude_session_id_string = "session-empty"
            )
        )
        self.assertEqual(len(rules_to_fire_list), 2)
        self.assertEqual(rules_already_satisfied_list, [])


    def test_flag_already_set_for_read_path_means_rule_is_skipped(self):

        python_rule_record = PreToolUseRequiredReadsRuleRecordBuilder.build_rule_record(
            read_abs_path = "/fake/docs/python.md"
        )
        required_reading._state.RequiredReadsState.mark_read_satisfied(
            claude_session_id_string = "session-partial",
            read_abs_path_string = "/fake/docs/python.md"
        )
        rules_to_fire_list, rules_already_satisfied_list = (
            PRE_TOOL_USE_REQUIRED_READS_RULE_CHECKS.partition_rules_into_unsatisfied_fire_and_already_satisfied(
                rule_records = [python_rule_record],
                claude_session_id_string = "session-partial"
            )
        )
        self.assertEqual(rules_to_fire_list, [])
        self.assertEqual(len(rules_already_satisfied_list), 1)


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
        deny_reason_string = PRE_TOOL_USE_REQUIRED_READS_RULE_CHECKS.build_deny_reason_string(
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
            PRE_TOOL_USE_REQUIRED_READS_RULE_CHECKS.partition_rules_by_missing_read_targets(
                rule_records = [present_rule_record, missing_rule_record]
            )
        )
        self.assertEqual(len(present_records), 1)
        self.assertEqual(present_records[0].rule_id, "m#present")
        self.assertEqual(len(required_missing_records), 1)
        self.assertEqual(required_missing_records[0].rule_id, "m#missing")


class TestIsFileInsideConfigDirectory(unittest.TestCase):

    def test_file_under_home_dot_claude_returns_true(self):

        self.assertTrue(PRE_TOOL_USE_REQUIRED_READS_RULE_CHECKS.is_file_inside_config_directory(
            edited_file_abs_path = "c:/users/zachm/.claude/plans/foo.md"
        ))


    def test_settings_json_under_home_dot_claude_returns_true(self):

        self.assertTrue(PRE_TOOL_USE_REQUIRED_READS_RULE_CHECKS.is_file_inside_config_directory(
            edited_file_abs_path = "c:/users/zachm/.claude/settings.json"
        ))


    def test_file_under_project_dot_claude_returns_true(self):

        self.assertTrue(PRE_TOOL_USE_REQUIRED_READS_RULE_CHECKS.is_file_inside_config_directory(
            edited_file_abs_path = "c:/users/zachm/dev/project/.claude/required-reads.json"
        ))


    def test_file_under_project_dot_ai_sanity_returns_true(self):

        self.assertTrue(PRE_TOOL_USE_REQUIRED_READS_RULE_CHECKS.is_file_inside_config_directory(
            edited_file_abs_path = "c:/users/zachm/dev/project/.ai-sanity/required-reading.json"
        ))


    def test_regular_project_file_returns_false(self):

        self.assertFalse(PRE_TOOL_USE_REQUIRED_READS_RULE_CHECKS.is_file_inside_config_directory(
            edited_file_abs_path = "c:/users/zachm/dev/project/src/foo.py"
        ))


    def test_partial_dot_claude_name_match_without_segment_boundary_returns_false(self):

        self.assertFalse(PRE_TOOL_USE_REQUIRED_READS_RULE_CHECKS.is_file_inside_config_directory(
            edited_file_abs_path = "c:/users/zachm/dev/project/src/.claude-config/foo.py"
        ))


    def test_partial_dot_ai_sanity_name_match_without_segment_boundary_returns_false(self):

        self.assertFalse(PRE_TOOL_USE_REQUIRED_READS_RULE_CHECKS.is_file_inside_config_directory(
            edited_file_abs_path = "c:/users/zachm/dev/project/src/.ai-sanity-extra/foo.py"
        ))


class TestIsReadOfClaudeConfigurationDoc(unittest.TestCase):

    def test_read_of_project_root_claude_md_returns_true(self):

        self.assertTrue(PRE_TOOL_USE_REQUIRED_READS_RULE_CHECKS.is_read_of_claude_configuration_doc(
            tool_name_string = "Read",
            edited_file_abs_path = "/users/zachm/dev/project/claude.md"
        ))


    def test_read_of_nested_claude_md_returns_true(self):

        self.assertTrue(PRE_TOOL_USE_REQUIRED_READS_RULE_CHECKS.is_read_of_claude_configuration_doc(
            tool_name_string = "Read",
            edited_file_abs_path = "/users/zachm/dev/project/src/claude.md"
        ))


    def test_read_of_agents_md_returns_true(self):

        self.assertTrue(PRE_TOOL_USE_REQUIRED_READS_RULE_CHECKS.is_read_of_claude_configuration_doc(
            tool_name_string = "Read",
            edited_file_abs_path = "/users/zachm/dev/project/agents.md"
        ))


    def test_edit_of_claude_md_returns_false(self):

        self.assertFalse(PRE_TOOL_USE_REQUIRED_READS_RULE_CHECKS.is_read_of_claude_configuration_doc(
            tool_name_string = "Edit",
            edited_file_abs_path = "/users/zachm/dev/project/claude.md"
        ))


    def test_write_of_agents_md_returns_false(self):

        self.assertFalse(PRE_TOOL_USE_REQUIRED_READS_RULE_CHECKS.is_read_of_claude_configuration_doc(
            tool_name_string = "Write",
            edited_file_abs_path = "/users/zachm/dev/project/agents.md"
        ))


    def test_read_of_unrelated_markdown_file_returns_false(self):

        self.assertFalse(PRE_TOOL_USE_REQUIRED_READS_RULE_CHECKS.is_read_of_claude_configuration_doc(
            tool_name_string = "Read",
            edited_file_abs_path = "/users/zachm/dev/project/readme.md"
        ))


    def test_read_of_file_with_claude_md_as_directory_component_returns_false(self):

        self.assertFalse(PRE_TOOL_USE_REQUIRED_READS_RULE_CHECKS.is_read_of_claude_configuration_doc(
            tool_name_string = "Read",
            edited_file_abs_path = "/users/zachm/dev/project/claude.md/something.txt"
        ))



if __name__ == "__main__":
    unittest.main()
