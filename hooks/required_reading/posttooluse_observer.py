########################################################################################################################
# hooks/required_reading/posttooluse_observer.py
#
# required-reading post-read observer hook
########################################################################################################################


import os
import sys

# hot patch so that imports work when script is invoked directly (how claude invokes hooks)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import _common._hook_io
import required_reading._manifest
import required_reading._state


class PostToolUseReadObserverRuleChecks:

    """Rule checks for the PostToolUse Read observer. Translates completed Reads into satisfaction flags."""


    @staticmethod
    def extract_read_file_abs_path_or_none(posttooluse_payload):

        """Returns the normalized absolute path of the file just Read, or None."""
        if posttooluse_payload.get("tool_name") != "Read":
            return None
        tool_input_dict = posttooluse_payload.get("tool_input") or {}
        raw_file_path_string = tool_input_dict.get("file_path")
        if not isinstance(raw_file_path_string, str) or not raw_file_path_string:
            return None
        return required_reading._manifest.RequiredReadsPathNormalizer.normalize_path(raw_file_path_string)


    @staticmethod
    def collect_dedupe_keys_whose_read_target_matches(read_file_abs_path, cwd_abs_path):

        """Returns dedupe keys for rules whose read target matches the file just Read."""
        discovered_manifests = required_reading._manifest.RequiredReadsManifestLoader.discover_manifests(
            edited_file_abs_path = read_file_abs_path
        )
        if cwd_abs_path:
            cwd_discovered_manifests = required_reading._manifest.RequiredReadsManifestLoader.discover_manifests(
                edited_file_abs_path = os.path.join(cwd_abs_path, "placeholder-filename")
            )
            seen_abs_paths = set(
                discovered_manifest.manifest_abs_path for discovered_manifest in discovered_manifests
            )
            for cwd_discovered_manifest in cwd_discovered_manifests:
                if cwd_discovered_manifest.manifest_abs_path not in seen_abs_paths:
                    discovered_manifests.append(cwd_discovered_manifest)
        if not discovered_manifests:
            return set()
        matching_dedupe_key_strings = set()
        for discovered_manifest in discovered_manifests:
            is_global_manifest_bool = not discovered_manifest.is_project_walkup_manifest
            loaded_rule_records = required_reading._manifest.RequiredReadsManifestLoader.load_manifest_rule_records(
                manifest_abs_path = discovered_manifest.manifest_abs_path,
                is_global_manifest = is_global_manifest_bool
            )
            for candidate_rule_record in loaded_rule_records:
                if candidate_rule_record.read_abs_path == read_file_abs_path:
                    matching_dedupe_key_strings.add(candidate_rule_record.dedupe_key)
        return matching_dedupe_key_strings


class PostToolUseReadObserverEntry:

    """Entry point. Errors fall through to passthrough so a bug cannot affect the completed Read."""


    @staticmethod
    def main():

        try:
            posttooluse_payload = _common._hook_io.PostToolUseHookIo.read_posttooluse_payload_from_stdin()
            read_file_abs_path = PostToolUseReadObserverRuleChecks.extract_read_file_abs_path_or_none(
                posttooluse_payload = posttooluse_payload
            )
            if read_file_abs_path is None:
                _common._hook_io.PostToolUseHookIo.emit_passthrough_and_exit()
                return
            cwd_abs_path_from_payload = posttooluse_payload.get("cwd") or ""
            matching_dedupe_key_strings = (
                PostToolUseReadObserverRuleChecks.collect_dedupe_keys_whose_read_target_matches(
                    read_file_abs_path = read_file_abs_path,
                    cwd_abs_path = cwd_abs_path_from_payload
                )
            )
            claude_session_id_string = posttooluse_payload.get("session_id") or "unknown-session"
            for dedupe_key_string in matching_dedupe_key_strings:
                required_reading._state.RequiredReadsState.mark_dedupe_key_satisfied(
                    claude_session_id_string = claude_session_id_string,
                    dedupe_key_string = dedupe_key_string
                )
            _common._hook_io.PostToolUseHookIo.emit_passthrough_and_exit()
        except Exception:
            _common._hook_io.PostToolUseHookIo.emit_passthrough_and_exit()


if __name__ == "__main__":
    PostToolUseReadObserverEntry.main()
