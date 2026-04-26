import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import _common._hook_io
import required_reading._manifest
import required_reading._state


class PreToolUseRequiredReadsRuleChecks:

    """Rule checks for the required-reads PreToolUse hook."""

    _file_path_tool_input_field_name_by_tool_name = {
        "Write": "file_path",
        "Edit": "file_path",
        "NotebookEdit": "notebook_path",
        "Read": "file_path"
    }

    @staticmethod
    def extract_edited_file_abs_path_or_none(pretooluse_payload):

        """Returns the normalized absolute path of the file being touched, or None."""
        rule_checks_class = PreToolUseRequiredReadsRuleChecks
        tool_name_string = pretooluse_payload.get("tool_name", "")
        file_path_field_name = rule_checks_class._file_path_tool_input_field_name_by_tool_name.get(tool_name_string)
        if file_path_field_name is None:
            return None
        tool_input_dict = pretooluse_payload.get("tool_input") or {}
        raw_file_path_string = tool_input_dict.get(file_path_field_name)
        if not isinstance(raw_file_path_string, str) or not raw_file_path_string:
            return None
        return required_reading._manifest.RequiredReadsPathNormalizer.normalize_path(raw_file_path_string)

    @staticmethod
    def is_file_inside_config_directory(edited_file_abs_path):

        """Files in `.claude/` or `.ai-sanity/` are operational space where style guide enforcement does not apply."""
        return "/.claude/" in edited_file_abs_path or "/.ai-sanity/" in edited_file_abs_path

    _claude_configuration_doc_basenames = frozenset(("claude.md", "agents.md"))

    @staticmethod
    def is_read_of_claude_configuration_doc(tool_name_string, edited_file_abs_path):

        """CLAUDE.md and agents.md can always be read without styleguide enforcement. Edits still require it."""
        if tool_name_string != "Read":
            return False
        basename_string = os.path.basename(edited_file_abs_path)
        return basename_string in PreToolUseRequiredReadsRuleChecks._claude_configuration_doc_basenames

    @staticmethod
    def collect_applicable_rule_records(edited_file_abs_path):

        """Loads all manifests, applies overrides, and returns rules matching the edited file."""
        rule_checks_class = PreToolUseRequiredReadsRuleChecks
        discovered_manifests = required_reading._manifest.RequiredReadsManifestLoader.discover_manifests(
            edited_file_abs_path = edited_file_abs_path
        )
        flattened_rule_records = []
        for discovered_manifest in discovered_manifests:
            is_global_manifest_bool = not discovered_manifest.is_project_walkup_manifest
            flattened_rule_records.extend(required_reading._manifest.RequiredReadsManifestLoader.load_manifest_rule_records(
                manifest_abs_path = discovered_manifest.manifest_abs_path,
                is_global_manifest = is_global_manifest_bool
            ))
        override_applied_rule_records = rule_checks_class.apply_project_overrides_against_global_rules(
            rule_records = flattened_rule_records
        )
        return rule_checks_class.filter_rules_by_match_criterion(
            rule_records = override_applied_rule_records,
            candidate_file_abs_path = edited_file_abs_path
        )

    @staticmethod
    def apply_project_overrides_against_global_rules(rule_records):

        """Drops global rules whose read target is claimed by a project rule's `override` field."""
        override_abs_paths_from_project_rules = set()
        for candidate_rule_record in rule_records:
            if candidate_rule_record.is_global_manifest:
                continue
            if candidate_rule_record.override_abs_path is None:
                continue
            override_abs_paths_from_project_rules.add(candidate_rule_record.override_abs_path)
        surviving_rule_records = []
        for candidate_rule_record in rule_records:
            if (
                candidate_rule_record.is_global_manifest
                and candidate_rule_record.read_abs_path in override_abs_paths_from_project_rules
            ):
                continue
            surviving_rule_records.append(candidate_rule_record)
        return surviving_rule_records

    @staticmethod
    def filter_rules_by_match_criterion(rule_records, candidate_file_abs_path):

        """Returns rules matching the file by extension suffix, filepath substring, or wildcard (neither set)."""
        match_passed_rule_records = []
        for candidate_rule_record in rule_records:
            if candidate_rule_record.match_extension_suffix is None and candidate_rule_record.match_filepath_substring is None:
                match_passed_rule_records.append(candidate_rule_record)
                continue
            if candidate_rule_record.match_extension_suffix is not None:
                if candidate_file_abs_path.endswith(candidate_rule_record.match_extension_suffix):
                    match_passed_rule_records.append(candidate_rule_record)
                continue
            if candidate_rule_record.match_filepath_substring in candidate_file_abs_path:
                match_passed_rule_records.append(candidate_rule_record)
        return match_passed_rule_records

    @staticmethod
    def is_read_of_a_manifest_listed_doc(tool_name_string, candidate_file_abs_path, edited_file_abs_path):

        """Reads of required docs always passthrough to break circular deadlocks."""
        if tool_name_string != "Read":
            return False
        discovered_manifests = required_reading._manifest.RequiredReadsManifestLoader.discover_manifests(
            edited_file_abs_path = edited_file_abs_path
        )
        for discovered_manifest in discovered_manifests:
            loaded_rule_records = required_reading._manifest.RequiredReadsManifestLoader.load_manifest_rule_records(
                manifest_abs_path = discovered_manifest.manifest_abs_path,
                is_global_manifest = False
            )
            for candidate_rule_record in loaded_rule_records:
                if candidate_rule_record.read_abs_path == candidate_file_abs_path:
                    return True
        return False

    @staticmethod
    def partition_rules_into_unsatisfied_fire_and_already_satisfied(rule_records, claude_session_id_string):

        """Splits rules into unsatisfied (need to fire) and already-satisfied (skip) lists."""
        rules_to_fire_list = []
        rules_already_satisfied_list = []
        for candidate_rule_record in rule_records:
            is_satisfied_bool = required_reading._state.RequiredReadsState.is_dedupe_key_satisfied(
                claude_session_id_string = claude_session_id_string,
                dedupe_key_string = candidate_rule_record.dedupe_key
            )
            if is_satisfied_bool:
                rules_already_satisfied_list.append(candidate_rule_record)
            else:
                rules_to_fire_list.append(candidate_rule_record)
        return rules_to_fire_list, rules_already_satisfied_list

    @staticmethod
    def partition_rules_by_missing_read_targets(rule_records):

        """Returns (present, required_missing)."""
        present_rule_records = []
        required_missing_rule_records = []
        for candidate_rule_record in rule_records:
            if os.path.isfile(candidate_rule_record.read_abs_path):
                present_rule_records.append(candidate_rule_record)
            else:
                required_missing_rule_records.append(candidate_rule_record)
        return present_rule_records, required_missing_rule_records

    @staticmethod
    def build_missing_target_deny_reason_string(rules_with_missing_targets, edited_file_abs_path):

        """Returns a deny-reason string for required docs missing on disk."""
        missing_target_description_lines = [
            f"  - `{candidate_rule_record.read_abs_path}` (rule {candidate_rule_record.rule_id}"
            f" from {candidate_rule_record.manifest_abs_path})"
            for candidate_rule_record in rules_with_missing_targets
        ]
        joined_missing_target_description_string = "\n".join(missing_target_description_lines)
        return (
            f"Required-reads configuration error: `{edited_file_abs_path}` requires documents that are missing on"
            f" disk:\n{joined_missing_target_description_string}\n"
            f"Fix the setup (clone the missing repo, correct the manifest path, or remove the offending rule) before"
            f" retrying. Do not proceed without the required context."
        )

    @staticmethod
    def build_deny_reason_string(unsatisfied_rule_records, edited_file_abs_path):

        """Returns the deny-reason string listing every unsatisfied rule's `read` target so Claude can Read them all
        in one batch before retrying the edit. Only called after all targets have been verified to exist."""
        required_read_description_lines = [
            f"  - `{candidate_rule_record.read_abs_path}` (rule {candidate_rule_record.rule_id}"
            f" from {candidate_rule_record.manifest_abs_path})"
            for candidate_rule_record in unsatisfied_rule_records
        ]
        joined_required_read_description_string = "\n".join(required_read_description_lines)
        return (
            f"Required-reads block: `{edited_file_abs_path}` requires the following documents to be in context"
            f" first:\n{joined_required_read_description_string}\n"
            f"Use the Read tool to load each one, then retry."
        )


class PreToolUseRequiredReadsHookEntry:

    """Entry point. Errors fall through to passthrough so a bug in this hook cannot crash an edit."""

    @staticmethod
    def main():

        rule_checks_class = PreToolUseRequiredReadsRuleChecks
        try:
            pretooluse_payload = _common._hook_io.PreToolUseHookIo.read_pretooluse_payload_from_stdin()
            try:
                required_reading._state.RequiredReadsState.sweep_stale_session_directories()
            except OSError:
                pass
            claude_session_id_string = pretooluse_payload.get("session_id") or "unknown-session"
            edited_file_abs_path = rule_checks_class.extract_edited_file_abs_path_or_none(
                pretooluse_payload = pretooluse_payload
            )
            if edited_file_abs_path is None:
                _common._hook_io.PreToolUseHookIo.emit_passthrough_and_exit()
                return
            if rule_checks_class.is_file_inside_config_directory(
                edited_file_abs_path = edited_file_abs_path
            ):
                _common._hook_io.PreToolUseHookIo.emit_passthrough_and_exit()
                return
            if rule_checks_class.is_read_of_claude_configuration_doc(
                tool_name_string = pretooluse_payload.get("tool_name", ""),
                edited_file_abs_path = edited_file_abs_path
            ):
                _common._hook_io.PreToolUseHookIo.emit_passthrough_and_exit()
                return
            if rule_checks_class.is_read_of_a_manifest_listed_doc(
                tool_name_string = pretooluse_payload.get("tool_name", ""),
                candidate_file_abs_path = edited_file_abs_path,
                edited_file_abs_path = edited_file_abs_path
            ):
                _common._hook_io.PreToolUseHookIo.emit_passthrough_and_exit()
                return
            applicable_rule_records = rule_checks_class.collect_applicable_rule_records(
                edited_file_abs_path = edited_file_abs_path
            )
            rules_to_fire_list, _ = rule_checks_class.partition_rules_into_unsatisfied_fire_and_already_satisfied(
                rule_records = applicable_rule_records,
                claude_session_id_string = claude_session_id_string
            )
            if not rules_to_fire_list:
                _common._hook_io.PreToolUseHookIo.emit_passthrough_and_exit()
                return
            rules_to_fire_list, required_missing_rule_records = (
                rule_checks_class.partition_rules_by_missing_read_targets(
                    rule_records = rules_to_fire_list
                )
            )
            if required_missing_rule_records:
                missing_target_deny_reason_string = rule_checks_class.build_missing_target_deny_reason_string(
                    rules_with_missing_targets = required_missing_rule_records,
                    edited_file_abs_path = edited_file_abs_path
                )
                _common._hook_io.PreToolUseHookIo.emit_deny_decision_and_exit(missing_target_deny_reason_string)
                return
            if not rules_to_fire_list:
                _common._hook_io.PreToolUseHookIo.emit_passthrough_and_exit()
                return
            deny_reason_string = rule_checks_class.build_deny_reason_string(
                unsatisfied_rule_records = rules_to_fire_list,
                edited_file_abs_path = edited_file_abs_path
            )
            _common._hook_io.PreToolUseHookIo.emit_deny_decision_and_exit(deny_reason_string)
        except Exception:
            _common._hook_io.PreToolUseHookIo.emit_passthrough_and_exit()


if __name__ == "__main__":
    PreToolUseRequiredReadsHookEntry.main()
