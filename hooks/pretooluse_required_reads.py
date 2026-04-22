########################################################################################################################
# hooks/pretooluse_required_reads.py
#
# PreToolUse entry script for the Write|Edit|NotebookEdit matcher that forces required reading of style guides, global
# and project CLAUDE.md, settings.json, and project-specific docs before a file-modifying tool call is allowed to run
########################################################################################################################
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import _lib


class PreToolUseRequiredReadsRuleChecks:

    """Pure helpers composing the required-reads PreToolUse flow. Every rule is block-mode: an unsatisfied rule denies
    the edit until Claude has Read the target doc in the current session. Each helper is independently unit-testable
    by passing synthetic RequiredReadsRuleRecord instances."""

    _file_path_tool_input_field_name_by_tool_name = {
        "Write": "file_path",
        "Edit": "file_path",
        "NotebookEdit": "notebook_path"
    }

    @staticmethod
    def extract_edited_file_abs_path_or_none(pretooluse_payload):

        """Returns the normalized absolute forward-slash path of the file being edited, or None if the payload does
        not carry one. Edit and Write read `tool_input.file_path`; NotebookEdit reads `tool_input.notebook_path`."""
        rule_checks_class = PreToolUseRequiredReadsRuleChecks
        tool_name_string = pretooluse_payload.get("tool_name", "")
        file_path_field_name = rule_checks_class._file_path_tool_input_field_name_by_tool_name.get(tool_name_string)
        if file_path_field_name is None:
            return None
        tool_input_dict = pretooluse_payload.get("tool_input") or {}
        raw_file_path_string = tool_input_dict.get(file_path_field_name)
        if not isinstance(raw_file_path_string, str) or not raw_file_path_string:
            return None
        return _lib.RequiredReadsPathNormalizer.normalize_path(raw_file_path_string)

    @staticmethod
    def collect_applicable_rule_records(edited_file_abs_path):

        """Discovers every manifest applicable to the edited file, loads and flattens their rules, applies project
        overrides against global rules, and filters to only those whose match criterion (extension suffix, filepath
        substring, or wildcard) matches the edited file path. Returns a list of RequiredReadsRuleRecord in
        manifest-discovery order (nearest project rules first, global rules last)."""
        rule_checks_class = PreToolUseRequiredReadsRuleChecks
        discovered_manifest_abs_paths = _lib.RequiredReadsManifestLoader.discover_manifest_abs_paths(
            edited_file_abs_path = edited_file_abs_path
        )
        global_manifest_abs_path = _lib.RequiredReadsPathNormalizer.normalize_path(
            os.path.join(_lib.RequiredReadsPathNormalizer.get_effective_home_abs_path(), ".claude/required-reads.json")
        )
        flattened_rule_records = []
        for manifest_abs_path in discovered_manifest_abs_paths:
            is_global_manifest_bool = manifest_abs_path == global_manifest_abs_path
            flattened_rule_records.extend(_lib.RequiredReadsManifestLoader.load_manifest_rule_records(
                manifest_abs_path = manifest_abs_path,
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

        """Returns a new rule list with global rules dropped if any project rule's normalized `override_abs_path`
        matches their `read_abs_path`. Project rules cannot override other project rules; override has effect only
        against global rules (is_global_manifest == True)."""
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

        """Returns only the rules that match the candidate file absolute path. A rule matches when: (a) it has neither
        `match_extension_suffix` nor `match_filepath_substring` (wildcard), or (b) its `match_extension_suffix` is a
        suffix of the path, or (c) its `match_filepath_substring` appears anywhere in the path. Both match fields on a
        single rule is rejected at manifest load time, so this function never sees a rule with both set."""
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
    def partition_rules_into_unsatisfied_fire_and_already_satisfied(rule_records, claude_session_id_string):

        """Splits rules into two lists: those whose dedupe key is not yet satisfied within the session (fire list)
        and those already satisfied (skip list). Ties between rules that share a dedupe key collapse to one
        satisfaction check. Preserves the relative order of the input."""
        rules_to_fire_list = []
        rules_already_satisfied_list = []
        for candidate_rule_record in rule_records:
            is_satisfied_bool = _lib.RequiredReadsState.is_dedupe_key_satisfied(
                claude_session_id_string = claude_session_id_string,
                dedupe_key_string = candidate_rule_record.dedupe_key
            )
            if is_satisfied_bool:
                rules_already_satisfied_list.append(candidate_rule_record)
            else:
                rules_to_fire_list.append(candidate_rule_record)
        return rules_to_fire_list, rules_already_satisfied_list

    @staticmethod
    def find_rules_with_missing_read_targets(rule_records):

        """Returns the sub-list of rules whose `read_abs_path` does not exist on disk. A missing target indicates a
        setup problem (e.g. the repo containing the required doc was not cloned on this machine, or a path was
        renamed and the manifest was not updated). The caller hard-fails on any non-empty result rather than
        silently degrading; silent degradation would let an unsatisfied required-read bypass enforcement."""
        return [
            candidate_rule_record for candidate_rule_record in rule_records
            if not os.path.isfile(candidate_rule_record.read_abs_path)
        ]

    @staticmethod
    def build_missing_target_deny_reason_string(rules_with_missing_targets, edited_file_abs_path):

        """Returns a deny-reason string for the configuration-broken case. The message lists every missing doc so
        the user can fix the setup in one pass. No escape hatch is offered; a missing required doc is a hard error
        until the target exists on disk."""
        missing_target_description_lines = [
            f"  - `{candidate_rule_record.read_abs_path}` (rule {candidate_rule_record.rule_id}"
            f" from {candidate_rule_record.manifest_abs_path})"
            for candidate_rule_record in rules_with_missing_targets
        ]
        joined_missing_target_description_string = "\n".join(missing_target_description_lines)
        return (
            f"Required-reads configuration error: editing `{edited_file_abs_path}` requires documents that are"
            f" missing on disk:\n{joined_missing_target_description_string}\n"
            f"Fix the setup (clone the missing repo, correct the manifest path, or remove the offending rule) before"
            f" retrying this edit. Do not proceed without the required context."
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
            f"Required-reads block: editing `{edited_file_abs_path}` requires the following documents to be in"
            f" context first:\n{joined_required_read_description_string}\n"
            f"Use the Read tool to load each one, then retry this edit."
        )


class PreToolUseRequiredReadsHookEntry:

    """Orchestrates the required-reads checks against an incoming PreToolUse payload. Any unexpected error inside
    the main control flow falls through to passthrough so that a bug in this hook cannot crash a user edit."""

    @staticmethod
    def main():

        """Reads the payload and emits one of three envelopes: a configuration-error deny if any unsatisfied rule's
        target is missing on disk, a block deny listing every unsatisfied rule otherwise, or passthrough when nothing
        fires. Sweeps stale session directories lazily on entry so cleanup happens without a daemon."""
        rule_checks_class = PreToolUseRequiredReadsRuleChecks
        try:
            pretooluse_payload = _lib.PreToolUseHookIo.read_pretooluse_payload_from_stdin()
            try:
                _lib.RequiredReadsState.sweep_stale_session_directories()
            except OSError:
                pass
            claude_session_id_string = pretooluse_payload.get("session_id") or "unknown-session"
            edited_file_abs_path = rule_checks_class.extract_edited_file_abs_path_or_none(
                pretooluse_payload = pretooluse_payload
            )
            if edited_file_abs_path is None:
                _lib.PreToolUseHookIo.emit_passthrough_and_exit()
                return
            applicable_rule_records = rule_checks_class.collect_applicable_rule_records(
                edited_file_abs_path = edited_file_abs_path
            )
            rules_to_fire_list, _ = rule_checks_class.partition_rules_into_unsatisfied_fire_and_already_satisfied(
                rule_records = applicable_rule_records,
                claude_session_id_string = claude_session_id_string
            )
            if not rules_to_fire_list:
                _lib.PreToolUseHookIo.emit_passthrough_and_exit()
                return
            rules_with_missing_targets = rule_checks_class.find_rules_with_missing_read_targets(
                rule_records = rules_to_fire_list
            )
            if rules_with_missing_targets:
                missing_target_deny_reason_string = rule_checks_class.build_missing_target_deny_reason_string(
                    rules_with_missing_targets = rules_with_missing_targets,
                    edited_file_abs_path = edited_file_abs_path
                )
                _lib.PreToolUseHookIo.emit_deny_decision_and_exit(missing_target_deny_reason_string)
                return
            deny_reason_string = rule_checks_class.build_deny_reason_string(
                unsatisfied_rule_records = rules_to_fire_list,
                edited_file_abs_path = edited_file_abs_path
            )
            _lib.PreToolUseHookIo.emit_deny_decision_and_exit(deny_reason_string)
        except Exception:
            _lib.PreToolUseHookIo.emit_passthrough_and_exit()


if __name__ == "__main__":
    PreToolUseRequiredReadsHookEntry.main()
