########################################################################################################################
# hooks/tests/fixtures_required_reads.py
#
# Manifest fixture builders used by the required-reads hook tests
########################################################################################################################


import json
import os
import tempfile


class RequiredReadsManifestFixtureBuilder:

    """Writes `.claude/required-reads.json` manifests into tempdirs for loader and discovery tests. Keeps test bodies
    focused on the assertion rather than on filesystem plumbing. Every write creates parent directories as needed and
    returns the absolute path of the written manifest so tests can read it back or register it as the home override."""

    @staticmethod
    def write_manifest_file(manifest_directory_abs_path, rule_dicts):

        """Writes a manifest with the given list of rule dicts to
        `<manifest_directory_abs_path>/.claude/required-reads.json`. Returns the absolute path of the written file.
        Rule dicts are serialized verbatim so tests can include invalid rules to exercise loader error handling."""
        claude_sub_directory_abs_path = os.path.join(manifest_directory_abs_path, ".claude")
        os.makedirs(claude_sub_directory_abs_path, exist_ok = True)
        manifest_abs_path = os.path.join(claude_sub_directory_abs_path, "required-reads.json")
        with open(manifest_abs_path, "w", encoding = "utf-8") as open_manifest_file_handle:
            json.dump({"rules": rule_dicts}, open_manifest_file_handle)
        return manifest_abs_path

    @staticmethod
    def write_raw_manifest_body(manifest_directory_abs_path, raw_manifest_body_string):

        """Writes an arbitrary byte body to `<manifest_directory_abs_path>/.claude/required-reads.json`. Used by
        loader tests that need to exercise malformed JSON, non-object top-level shapes, or other invalid bodies that
        cannot be produced by `write_manifest_file`. Returns the absolute path of the written file."""
        claude_sub_directory_abs_path = os.path.join(manifest_directory_abs_path, ".claude")
        os.makedirs(claude_sub_directory_abs_path, exist_ok = True)
        manifest_abs_path = os.path.join(claude_sub_directory_abs_path, "required-reads.json")
        with open(manifest_abs_path, "w", encoding = "utf-8") as open_manifest_file_handle:
            open_manifest_file_handle.write(raw_manifest_body_string)
        return manifest_abs_path


class HomeOverrideEnvVarTestCaseMixin:

    """Per-test setup/teardown that points `HOOK_TEST_HOME_OVERRIDE` at a fresh tempdir so the required-reads
    path-normalizer, manifest-discovery, and state subsystems operate inside a sandbox instead of the real home.
    Used by both the unit tests (direct method calls) and the subprocess tests (where the child Python process
    inherits the parent's env). Subclasses read `self.sandboxed_home_abs_path` to place fixture files."""

    def setUp(self):

        self._previous_home_override_value = os.environ.get("HOOK_TEST_HOME_OVERRIDE")
        self.sandboxed_home_abs_path = tempfile.mkdtemp()
        os.environ["HOOK_TEST_HOME_OVERRIDE"] = self.sandboxed_home_abs_path

    def tearDown(self):

        if self._previous_home_override_value is None:
            os.environ.pop("HOOK_TEST_HOME_OVERRIDE", None)
        else:
            os.environ["HOOK_TEST_HOME_OVERRIDE"] = self._previous_home_override_value
