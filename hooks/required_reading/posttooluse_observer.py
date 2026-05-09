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
    def collect_satisfied_read_abs_paths(read_file_abs_path, cwd_abs_path):

        """Returns read_abs_path values for rules whose read target matches the file just Read."""
        discovered_manifest_abs_paths = required_reading._manifest.RequiredReadsManifestLoader.discover_manifests(
            edited_file_abs_path = read_file_abs_path
        )
        if cwd_abs_path:
            cwd_manifest_abs_paths = required_reading._manifest.RequiredReadsManifestLoader.discover_manifests(
                edited_file_abs_path = os.path.join(cwd_abs_path, "placeholder-filename")
            )
            seen_abs_paths = set(discovered_manifest_abs_paths)
            for cwd_manifest_abs_path in cwd_manifest_abs_paths:
                if cwd_manifest_abs_path not in seen_abs_paths:
                    discovered_manifest_abs_paths.append(cwd_manifest_abs_path)
        if not discovered_manifest_abs_paths:
            return set()
        matching_read_abs_paths = set()
        for manifest_abs_path in discovered_manifest_abs_paths:
            loaded_rule_records = required_reading._manifest.RequiredReadsManifestLoader.load_manifest_rule_records(
                manifest_abs_path = manifest_abs_path
            )
            for candidate_rule_record in loaded_rule_records:
                if candidate_rule_record.read_abs_path == read_file_abs_path:
                    matching_read_abs_paths.add(candidate_rule_record.read_abs_path)
        return matching_read_abs_paths


class PostToolUseReadObserverEntry:

    """Entry point."""


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
            satisfied_read_abs_paths = (
                PostToolUseReadObserverRuleChecks.collect_satisfied_read_abs_paths(
                    read_file_abs_path = read_file_abs_path,
                    cwd_abs_path = cwd_abs_path_from_payload
                )
            )
            claude_session_id_string = posttooluse_payload.get("session_id") or "unknown-session"
            for read_abs_path in satisfied_read_abs_paths:
                required_reading._state.RequiredReadsState.mark_read_satisfied(
                    claude_session_id_string = claude_session_id_string,
                    read_abs_path_string = read_abs_path
                )
            _common._hook_io.PostToolUseHookIo.emit_passthrough_and_exit()
        except Exception:
            raise


if __name__ == "__main__":
    PostToolUseReadObserverEntry.main()
