import collections
import json
import os


RequiredReadsRuleRecord = collections.namedtuple(
    "RequiredReadsRuleRecord",
    [
        "rule_id",
        "manifest_abs_path",
        "is_global_manifest",
        "match_extension_suffix",
        "match_filepath_substring",
        "read_abs_path",
        "override_abs_path",
        "dedupe_key",
    ]
)


class RequiredReadsPathNormalizer:

    """Single canonicalization function for every path in the required-reads subsystem. All comparisons between paths
    (rule `read` targets, candidate edited-file paths, override targets) must go through this so Windows vs Posix and
    tilde-prefixed vs absolute forms collapse to the same string. Tilde expansion honors the test-only
    HOOK_TEST_HOME_OVERRIDE env var so tests can point at a sandboxed home without touching the real ~."""

    @staticmethod
    def normalize_path(raw_path_string, base_directory_abs_path = None):

        """Returns a forward-slash, lowercased absolute path. Tilde is expanded first (honoring
        HOOK_TEST_HOME_OVERRIDE), then relative paths are resolved against `base_directory_abs_path` if given, then
        `os.path.abspath`, then backslashes become forward slashes, then the whole string is lowercased. The lower
        call handles Windows filesystem case-insensitivity (the common real bug: manifest `C:/...` vs Read
        `c:/...`); it is technically lossy on Posix where `foo.md` and `FOO.md` can coexist, but case-colliding doc
        paths do not occur in any meaningful deployment of this hook, so universal lowercasing simplifies the
        canonicalization story."""
        home_expanded_path_string = RequiredReadsPathNormalizer._expand_home_honoring_test_override(raw_path_string)
        if base_directory_abs_path and not os.path.isabs(home_expanded_path_string):
            home_expanded_path_string = os.path.join(base_directory_abs_path, home_expanded_path_string)
        absolutised_path_string = os.path.abspath(home_expanded_path_string)
        return absolutised_path_string.replace("\\", "/").lower()

    @staticmethod
    def _expand_home_honoring_test_override(raw_path_string):

        """Expands a leading `~` using HOOK_TEST_HOME_OVERRIDE if set, otherwise `os.path.expanduser`. Non-tilde paths
        return unchanged."""
        home_override_abs_path = os.environ.get("HOOK_TEST_HOME_OVERRIDE")
        if home_override_abs_path and raw_path_string.startswith("~"):
            if raw_path_string == "~":
                return home_override_abs_path
            if raw_path_string[1] in ("/", "\\"):
                return home_override_abs_path + raw_path_string[1:]
        return os.path.expanduser(raw_path_string)

    @staticmethod
    def get_effective_home_abs_path():

        """Returns the home directory that the required-reads subsystem treats as ~. HOOK_TEST_HOME_OVERRIDE wins
        when set; otherwise `os.path.expanduser('~')`. Output is forward-slash-normalized and lowercased to match
        `normalize_path`'s canonicalization, so directory walk-up comparisons in the manifest discovery path do not
        miss on case differences."""
        home_override_abs_path = os.environ.get("HOOK_TEST_HOME_OVERRIDE")
        if home_override_abs_path:
            return home_override_abs_path.replace("\\", "/").lower()
        return os.path.expanduser("~").replace("\\", "/").lower()


class RequiredReadsManifestLoader:

    """Discovers and parses `.claude/required-reads.json` manifests. Project manifests live next to the edited file
    (walk up until home is reached). The global manifest lives at `~/.claude/required-reads.json`. Every failure mode
    (missing file, malformed JSON, wrong top-level shape, invalid rule) returns an empty list or skips the offending
    rule so that hook execution never crashes an edit."""

    _project_manifest_relative_path = ".claude/required-reads.json"
    _global_manifest_relative_path_from_home = ".claude/required-reads.json"

    @staticmethod
    def discover_manifest_abs_paths(edited_file_abs_path):

        """Walks up from `dirname(edited_file_abs_path)` collecting `.claude/required-reads.json` files. Stops when
        the walk reaches the effective home or the filesystem root. The global manifest is appended last if it
        exists. Return value is ordered nearest-project-manifest first, global last. A `visited` set on normalized
        paths guards against symlink loops."""
        loader_class = RequiredReadsManifestLoader
        discovered_manifest_abs_paths = []
        visited_directory_abs_paths = set()
        effective_home_abs_path = RequiredReadsPathNormalizer.get_effective_home_abs_path()
        current_directory_abs_path = RequiredReadsPathNormalizer.normalize_path(
            os.path.dirname(edited_file_abs_path)
        )
        while True:
            if current_directory_abs_path in visited_directory_abs_paths:
                break
            visited_directory_abs_paths.add(current_directory_abs_path)
            candidate_project_manifest_abs_path = RequiredReadsPathNormalizer.normalize_path(
                os.path.join(current_directory_abs_path, loader_class._project_manifest_relative_path)
            )
            if os.path.isfile(candidate_project_manifest_abs_path):
                discovered_manifest_abs_paths.append(candidate_project_manifest_abs_path)
            if current_directory_abs_path == effective_home_abs_path:
                break
            parent_directory_abs_path = RequiredReadsPathNormalizer.normalize_path(
                os.path.dirname(current_directory_abs_path)
            )
            if parent_directory_abs_path == current_directory_abs_path:
                break
            current_directory_abs_path = parent_directory_abs_path
        global_manifest_abs_path = RequiredReadsPathNormalizer.normalize_path(
            os.path.join(effective_home_abs_path, loader_class._global_manifest_relative_path_from_home)
        )
        if global_manifest_abs_path not in discovered_manifest_abs_paths and os.path.isfile(global_manifest_abs_path):
            discovered_manifest_abs_paths.append(global_manifest_abs_path)
        return discovered_manifest_abs_paths

    @staticmethod
    def load_manifest_rule_records(manifest_abs_path, is_global_manifest):

        """Parses a single manifest file and returns a list of `RequiredReadsRuleRecord`. Returns [] on any file or
        JSON parse error, and skips individual rules that are missing required fields or have invalid values. The
        `is_global_manifest` flag controls whether the rules produced are eligible to be silenced by a project-level
        `override`."""
        loader_class = RequiredReadsManifestLoader
        try:
            with open(manifest_abs_path, "r", encoding = "utf-8") as open_manifest_file_handle:
                parsed_manifest_object = json.load(open_manifest_file_handle)
        except (OSError, json.JSONDecodeError):
            return []
        if not isinstance(parsed_manifest_object, dict):
            return []
        raw_rule_objects = parsed_manifest_object.get("rules")
        if not isinstance(raw_rule_objects, list):
            return []
        project_root_abs_path = RequiredReadsPathNormalizer.normalize_path(
            os.path.dirname(os.path.dirname(manifest_abs_path))
        )
        produced_rule_records = []
        for raw_rule_object_index, raw_rule_object in enumerate(raw_rule_objects):
            if not isinstance(raw_rule_object, dict):
                continue
            rule_record_or_none = loader_class._build_rule_record_or_none(
                raw_rule_object = raw_rule_object,
                raw_rule_object_index = raw_rule_object_index,
                manifest_abs_path = manifest_abs_path,
                project_root_abs_path = project_root_abs_path,
                is_global_manifest = is_global_manifest
            )
            if rule_record_or_none is not None:
                produced_rule_records.append(rule_record_or_none)
        return produced_rule_records

    @staticmethod
    def _build_rule_record_or_none(raw_rule_object,
        raw_rule_object_index,
        manifest_abs_path,
        project_root_abs_path,
        is_global_manifest
    ):

        """Validates a single raw rule dict and returns a `RequiredReadsRuleRecord`, or None if the rule is invalid.
        Relative `read` paths resolve against the project root (the directory containing `.claude/`), not against the
        manifest's own directory; this keeps rules natural to write (`./CLAUDE.md`, `./docs/stack/backend.md`). The
        two match fields `extension` and `filepath` are mutually exclusive; both present is a validation error and the
        rule is skipped. A rule with neither is a wildcard that matches every file. All unknown keys (including legacy
        `mode`, `match`, and the `comment` documentation field) are ignored."""
        read_path_string = raw_rule_object.get("read")
        if not isinstance(read_path_string, str) or not read_path_string:
            return None
        extension_raw_value = raw_rule_object.get("extension")
        filepath_raw_value = raw_rule_object.get("filepath")
        match_extension_suffix = None
        match_filepath_substring = None
        if isinstance(extension_raw_value, str) and extension_raw_value:
            match_extension_suffix = extension_raw_value.lower()
        if isinstance(filepath_raw_value, str) and filepath_raw_value:
            match_filepath_substring = filepath_raw_value.lower()
        if match_extension_suffix is not None and match_filepath_substring is not None:
            return None
        read_abs_path = RequiredReadsPathNormalizer.normalize_path(
            read_path_string,
            base_directory_abs_path = project_root_abs_path
        )
        override_raw_value = raw_rule_object.get("override")
        override_abs_path = None
        if isinstance(override_raw_value, str) and override_raw_value:
            override_abs_path = RequiredReadsPathNormalizer.normalize_path(override_raw_value)
        dedupe_key_raw_value = raw_rule_object.get("dedupe_key")
        if isinstance(dedupe_key_raw_value, str) and dedupe_key_raw_value:
            dedupe_key_string = dedupe_key_raw_value
        else:
            dedupe_key_string = read_abs_path
        rule_id_string = f"{os.path.basename(manifest_abs_path)}#{raw_rule_object_index}"
        return RequiredReadsRuleRecord(
            rule_id = rule_id_string,
            manifest_abs_path = manifest_abs_path,
            is_global_manifest = is_global_manifest,
            match_extension_suffix = match_extension_suffix,
            match_filepath_substring = match_filepath_substring,
            read_abs_path = read_abs_path,
            override_abs_path = override_abs_path,
            dedupe_key = dedupe_key_string
        )
