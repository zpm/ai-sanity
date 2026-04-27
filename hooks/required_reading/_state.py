########################################################################################################################
# hooks/required_reading/_state.py
#
# required-reading satisfaction state
########################################################################################################################


import hashlib
import os
import shutil
import time

import required_reading._manifest


class RequiredReadsState:

    """Per-session satisfaction flags used by the required-reads hook trio. A flag means that, within a single Claude
    Code session, a given rule's dedupe key has already been satisfied (either by a Read observed on its target doc or
    by an inline inject-mode injection). Flags live under `~/.ai-sanity/hooks-state/required-reads/<session_id>/` with
    filenames of `<sha1(dedupe_key)>.flag` containing the normalized key string for human debugging. The state
    directory base is overridable via the HOOK_TEST_STATE_DIR env var (test-only). Every operation swallows
    filesystem errors so that an unwritable state dir cannot crash an edit."""

    _state_directory_relative_path_from_home = ".ai-sanity/hooks-state/required-reads"


    @staticmethod
    def get_state_base_directory_abs_path():

        """Returns the absolute, forward-slash-normalized path of the root directory under which per-session
        subdirectories live. Honors HOOK_TEST_STATE_DIR when set, otherwise uses the effective home's
        `.ai-sanity/hooks-state/required-reads/`."""
        state_class = RequiredReadsState
        state_directory_override_abs_path = os.environ.get("HOOK_TEST_STATE_DIR")
        if state_directory_override_abs_path:
            return state_directory_override_abs_path.replace("\\", "/")
        effective_home_abs_path = required_reading._manifest.RequiredReadsPathNormalizer.get_effective_home_abs_path()
        return required_reading._manifest.RequiredReadsPathNormalizer.normalize_path(
            os.path.join(effective_home_abs_path, state_class._state_directory_relative_path_from_home)
        )


    @staticmethod
    def get_session_directory_abs_path(claude_session_id_string):

        """Returns the absolute path of `<state_base>/<session_id>/` without creating the directory. Callers that
        need to write inside it are responsible for `os.makedirs(exist_ok=True)`."""
        state_class = RequiredReadsState
        return os.path.join(
            state_class.get_state_base_directory_abs_path(),
            claude_session_id_string
        ).replace("\\", "/")


    @staticmethod
    def is_dedupe_key_satisfied(claude_session_id_string, dedupe_key_string):

        """Returns True if the flag file for the given dedupe key already exists under the session directory.
        Returns False on any filesystem error (effectively treats the key as not yet satisfied, which is the safe
        default: it re-fires the rule rather than silently suppressing it)."""
        state_class = RequiredReadsState
        try:
            flag_file_abs_path = state_class._get_flag_file_abs_path(
                claude_session_id_string = claude_session_id_string,
                dedupe_key_string = dedupe_key_string
            )
            return os.path.isfile(flag_file_abs_path)
        except OSError:
            return False


    @staticmethod
    def mark_dedupe_key_satisfied(claude_session_id_string, dedupe_key_string):

        """Writes a flag file for the given dedupe key under the session directory. The flag body is the normalized
        dedupe key (written only to aid human debugging; `is_dedupe_key_satisfied` checks existence, not contents).
        Creates the session directory if missing. Swallows any filesystem error so an unwritable state dir cannot
        crash an edit."""
        state_class = RequiredReadsState
        try:
            session_directory_abs_path = state_class.get_session_directory_abs_path(
                claude_session_id_string = claude_session_id_string
            )
            os.makedirs(session_directory_abs_path, exist_ok = True)
            flag_file_abs_path = state_class._get_flag_file_abs_path(
                claude_session_id_string = claude_session_id_string,
                dedupe_key_string = dedupe_key_string
            )
            with open(flag_file_abs_path, "w", encoding = "utf-8") as open_flag_file_handle:
                open_flag_file_handle.write(dedupe_key_string)
        except OSError:
            return


    @staticmethod
    def clear_session(claude_session_id_string):

        """Removes the session directory and every flag file inside it. Called by the PreCompact hook so that after
        context compaction the required reads are re-demanded. Swallows filesystem errors."""
        state_class = RequiredReadsState
        try:
            session_directory_abs_path = state_class.get_session_directory_abs_path(
                claude_session_id_string = claude_session_id_string
            )
            if os.path.isdir(session_directory_abs_path):
                shutil.rmtree(session_directory_abs_path, ignore_errors = True)
        except OSError:
            return


    @staticmethod
    def sweep_stale_session_directories(stale_age_seconds_threshold = 7 * 24 * 60 * 60):

        """Removes session subdirectories whose mtime is older than the threshold. Called lazily on PreToolUse entry
        so cleanup happens organically without a daemon. Default threshold is seven days. Swallows filesystem errors.
        Skips cleanly if the state base directory does not exist."""
        state_class = RequiredReadsState
        try:
            state_base_directory_abs_path = state_class.get_state_base_directory_abs_path()
            if not os.path.isdir(state_base_directory_abs_path):
                return
            current_wall_clock_seconds = time.time()
            for session_directory_name in os.listdir(state_base_directory_abs_path):
                candidate_session_directory_abs_path = os.path.join(
                    state_base_directory_abs_path,
                    session_directory_name
                )
                if not os.path.isdir(candidate_session_directory_abs_path):
                    continue
                try:
                    session_directory_mtime_seconds = os.path.getmtime(candidate_session_directory_abs_path)
                except OSError:
                    continue
                if current_wall_clock_seconds - session_directory_mtime_seconds > stale_age_seconds_threshold:
                    shutil.rmtree(candidate_session_directory_abs_path, ignore_errors = True)
        except OSError:
            return


    @staticmethod
    def _get_flag_file_abs_path(claude_session_id_string, dedupe_key_string):

        """Returns the absolute path of the flag file that represents satisfaction of the given dedupe key within the
        given session. The filename is `<sha1(dedupe_key)>.flag`; the hash avoids worrying about filesystem-illegal
        characters that might appear in a dedupe key derived from an arbitrary filesystem path."""
        state_class = RequiredReadsState
        dedupe_key_sha1_hex_digest = hashlib.sha1(dedupe_key_string.encode("utf-8")).hexdigest()
        session_directory_abs_path = state_class.get_session_directory_abs_path(
            claude_session_id_string = claude_session_id_string
        )
        return os.path.join(
            session_directory_abs_path,
            dedupe_key_sha1_hex_digest + ".flag"
        ).replace("\\", "/")
