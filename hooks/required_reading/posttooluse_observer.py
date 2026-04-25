import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import _hook_io
from required_reading._manifest import RequiredReadsPathNormalizer, RequiredReadsManifestLoader
from required_reading._state import RequiredReadsState


class PostToolUseReadObserverRuleChecks:

    """Pure helpers for the PostToolUse Read observer. The observer does not deny; it translates a completed Read
    into zero or more satisfaction-flag writes. Each helper is independently unit-testable by passing synthetic
    payloads and RuleRecord lists."""

    @staticmethod
    def extract_read_file_abs_path_or_none(posttooluse_payload):

        """Returns the normalized absolute forward-slash path of the file Claude just Read, or None if the payload
        does not carry one (wrong tool_name, missing field, empty string)."""
        if posttooluse_payload.get("tool_name") != "Read":
            return None
        tool_input_dict = posttooluse_payload.get("tool_input") or {}
        raw_file_path_string = tool_input_dict.get("file_path")
        if not isinstance(raw_file_path_string, str) or not raw_file_path_string:
            return None
        return RequiredReadsPathNormalizer.normalize_path(raw_file_path_string)

    @staticmethod
    def collect_dedupe_keys_whose_read_target_matches(read_file_abs_path, cwd_abs_path):

        """Discovers every manifest reachable from the Read's absolute path (with `cwd_abs_path` as a fallback
        anchor when the Read target is outside the project tree, e.g. `~/.claude/CLAUDE.md`), loads their rules
        across both modes, and returns the set of dedupe_key strings for every rule whose normalized `read_abs_path`
        equals `read_file_abs_path`. Returns an empty set if no manifest is discoverable (fast path: zero cost when
        the feature is unused)."""
        discovered_manifest_abs_paths = RequiredReadsManifestLoader.discover_manifest_abs_paths(
            edited_file_abs_path = read_file_abs_path
        )
        if cwd_abs_path:
            cwd_manifest_abs_paths = RequiredReadsManifestLoader.discover_manifest_abs_paths(
                edited_file_abs_path = os.path.join(cwd_abs_path, "placeholder-filename")
            )
            seen = set(discovered_manifest_abs_paths)
            for cwd_manifest_abs_path in cwd_manifest_abs_paths:
                if cwd_manifest_abs_path not in seen:
                    discovered_manifest_abs_paths.append(cwd_manifest_abs_path)
        if not discovered_manifest_abs_paths:
            return set()
        global_manifest_abs_path = RequiredReadsPathNormalizer.normalize_path(
            os.path.join(RequiredReadsPathNormalizer.get_effective_home_abs_path(), ".claude/required-reads.json")
        )
        matching_dedupe_key_strings = set()
        for manifest_abs_path in discovered_manifest_abs_paths:
            is_global_manifest_bool = manifest_abs_path == global_manifest_abs_path
            loaded_rule_records = RequiredReadsManifestLoader.load_manifest_rule_records(
                manifest_abs_path = manifest_abs_path,
                is_global_manifest = is_global_manifest_bool
            )
            for candidate_rule_record in loaded_rule_records:
                if candidate_rule_record.read_abs_path == read_file_abs_path:
                    matching_dedupe_key_strings.add(candidate_rule_record.dedupe_key)
        return matching_dedupe_key_strings


class PostToolUseReadObserverEntry:

    """Orchestrates the Read-observer flow. Any error falls through to passthrough so that a bug in this hook cannot
    affect the user's Read tool call (which has already completed by the time this hook fires)."""

    @staticmethod
    def main():

        """Reads the payload, resolves the Read target, discovers applicable manifests, and writes a satisfaction
        flag for every matching rule's dedupe key. Always passthroughs; PostToolUse hooks cannot deny."""
        try:
            posttooluse_payload = _hook_io.PostToolUseHookIo.read_posttooluse_payload_from_stdin()
            read_file_abs_path = PostToolUseReadObserverRuleChecks.extract_read_file_abs_path_or_none(
                posttooluse_payload = posttooluse_payload
            )
            if read_file_abs_path is None:
                _hook_io.PostToolUseHookIo.emit_passthrough_and_exit()
                return
            cwd_abs_path_from_payload = posttooluse_payload.get("cwd") or ""
            matching_dedupe_key_strings = PostToolUseReadObserverRuleChecks.collect_dedupe_keys_whose_read_target_matches(
                read_file_abs_path = read_file_abs_path,
                cwd_abs_path = cwd_abs_path_from_payload
            )
            claude_session_id_string = posttooluse_payload.get("session_id") or "unknown-session"
            for dedupe_key_string in matching_dedupe_key_strings:
                RequiredReadsState.mark_dedupe_key_satisfied(
                    claude_session_id_string = claude_session_id_string,
                    dedupe_key_string = dedupe_key_string
                )
            _hook_io.PostToolUseHookIo.emit_passthrough_and_exit()
        except Exception:
            _hook_io.PostToolUseHookIo.emit_passthrough_and_exit()


if __name__ == "__main__":
    PostToolUseReadObserverEntry.main()
