########################################################################################################################
# hooks/required_reading/_manifest.py
#
# required-reading manifest loading and path matching
########################################################################################################################


import collections
import json
import os


RequiredReadsRuleRecord = collections.namedtuple(
    "RequiredReadsRuleRecord",
    [
        "rule_id",
        "manifest_abs_path",
        "match_extension_suffix",
        "match_filepath_substring",
        "read_abs_path",
    ]
)



class RequiredReadsPathNormalizer:

    """Canonicalizes every path in the required-reads subsystem to forward-slash, lowercased absolute form."""


    @staticmethod
    def normalize_path(raw_path_string, base_directory_abs_path = None):

        """Returns a forward-slash, lowercased absolute path."""
        home_expanded_path_string = RequiredReadsPathNormalizer._expand_home_honoring_test_override(raw_path_string)
        if base_directory_abs_path and not os.path.isabs(home_expanded_path_string):
            home_expanded_path_string = os.path.join(base_directory_abs_path, home_expanded_path_string)
        absolutised_path_string = os.path.abspath(home_expanded_path_string)
        # lowercasing handles Windows case-insensitivity; harmless on Posix for doc paths
        return absolutised_path_string.replace("\\", "/").lower()


    @staticmethod
    def _expand_home_honoring_test_override(raw_path_string):

        """Expands a leading `~` using HOOK_TEST_HOME_OVERRIDE if set, otherwise `os.path.expanduser`."""
        home_override_abs_path = os.environ.get("HOOK_TEST_HOME_OVERRIDE")
        if home_override_abs_path and raw_path_string.startswith("~"):
            if raw_path_string == "~":
                return home_override_abs_path
            if raw_path_string[1] in ("/", "\\"):
                return home_override_abs_path + raw_path_string[1:]
        return os.path.expanduser(raw_path_string)


    @staticmethod
    def get_effective_home_abs_path():

        """Returns the normalized home directory. HOOK_TEST_HOME_OVERRIDE wins when set."""
        home_override_abs_path = os.environ.get("HOOK_TEST_HOME_OVERRIDE")
        if home_override_abs_path:
            return home_override_abs_path.replace("\\", "/").lower()
        return os.path.expanduser("~").replace("\\", "/").lower()


class RequiredReadsManifestLoader:

    """Discovers and loads required-reading manifests. Failure modes (missing file, bad JSON, invalid rules) return
    empty lists or skip the offending rule so hook execution never crashes an edit."""

    _project_manifest_relative_path = ".ai-sanity/required-reading.json"
    _global_manifest_relative_path_from_repo_root = ".ai-sanity/required-styleguides.json"


    @staticmethod
    def get_hooks_repo_root_abs_path():

        """Two directory levels up from `hooks/required_reading/`."""
        return RequiredReadsPathNormalizer.normalize_path(
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
        )


    @staticmethod
    def discover_manifests(edited_file_abs_path):

        """Returns discovered manifest absolute paths in order: hooks-repo global, project walk-up."""
        loader_class = RequiredReadsManifestLoader
        discovered_manifest_abs_paths = []

        # hooks-repo global (.ai-sanity/required-styleguides.json resolved via __file__)
        global_manifest_abs_path = RequiredReadsPathNormalizer.normalize_path(
            os.path.join(
                loader_class.get_hooks_repo_root_abs_path(),
                loader_class._global_manifest_relative_path_from_repo_root
            )
        )
        if os.path.isfile(global_manifest_abs_path):
            discovered_manifest_abs_paths.append(global_manifest_abs_path)

        # project walk-up (stops at $HOME after checking it, visited set guards against symlink loops)
        effective_home_abs_path = RequiredReadsPathNormalizer.get_effective_home_abs_path()
        visited_directory_abs_paths = set()
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
        return discovered_manifest_abs_paths


    @staticmethod
    def load_manifest_rule_records(manifest_abs_path):

        """Parses a manifest file into rule records. Returns [] on any file or JSON error, skips invalid rules."""
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
        # .ai-sanity/ manifests resolve relative paths against the project root (parent of .ai-sanity/),
        # other manifests resolve against their own directory
        manifest_parent_directory_basename = os.path.basename(os.path.dirname(manifest_abs_path))
        if manifest_parent_directory_basename == ".ai-sanity":
            base_directory_abs_path_for_relative_reads = RequiredReadsPathNormalizer.normalize_path(
                os.path.dirname(os.path.dirname(manifest_abs_path))
            )
        else:
            base_directory_abs_path_for_relative_reads = RequiredReadsPathNormalizer.normalize_path(
                os.path.dirname(manifest_abs_path)
            )
        produced_rule_records = []
        for raw_rule_object_index, raw_rule_object in enumerate(raw_rule_objects):
            if not isinstance(raw_rule_object, dict):
                continue
            expanded_rule_records = loader_class._build_rule_records(
                raw_rule_object = raw_rule_object,
                raw_rule_object_index = raw_rule_object_index,
                manifest_abs_path = manifest_abs_path,
                base_directory_abs_path_for_relative_reads = base_directory_abs_path_for_relative_reads
            )
            produced_rule_records.extend(expanded_rule_records)
        return produced_rule_records


    @staticmethod
    def _normalize_string_or_list_field(raw_value):

        """Accepts a string or list of strings. Returns a list of non-empty strings, or []."""
        if isinstance(raw_value, str):
            return [raw_value] if raw_value else []
        if isinstance(raw_value, list):
            return [v for v in raw_value if isinstance(v, str) and v]
        return []


    @staticmethod
    def _build_rule_records(raw_rule_object,
        raw_rule_object_index,
        manifest_abs_path,
        base_directory_abs_path_for_relative_reads
    ):

        """Expands one manifest rule into flat RequiredReadsRuleRecords. Accepts string or list for extension,
        filepath, and read fields. Returns [] if the rule is invalid."""
        loader_class = RequiredReadsManifestLoader
        read_values = loader_class._normalize_string_or_list_field(raw_rule_object.get("read"))
        if not read_values:
            return []
        extension_values = [
            v.lower() for v in loader_class._normalize_string_or_list_field(raw_rule_object.get("extension"))
        ]
        filepath_values = [
            v.lower() for v in loader_class._normalize_string_or_list_field(raw_rule_object.get("filepath"))
        ]
        if extension_values and filepath_values:
            return []
        if extension_values:
            match_criteria_pairs = [(ext, None) for ext in extension_values]
        elif filepath_values:
            match_criteria_pairs = [(None, fp) for fp in filepath_values]
        else:
            match_criteria_pairs = [(None, None)]
        rule_id_string = f"{os.path.basename(manifest_abs_path)}#{raw_rule_object_index}"
        produced_rule_records = []
        for match_extension_suffix, match_filepath_substring in match_criteria_pairs:
            for read_path_string in read_values:
                read_abs_path = RequiredReadsPathNormalizer.normalize_path(
                    read_path_string,
                    base_directory_abs_path = base_directory_abs_path_for_relative_reads
                )
                produced_rule_records.append(RequiredReadsRuleRecord(
                    rule_id = rule_id_string,
                    manifest_abs_path = manifest_abs_path,
                    match_extension_suffix = match_extension_suffix,
                    match_filepath_substring = match_filepath_substring,
                    read_abs_path = read_abs_path,
                ))
        return produced_rule_records
