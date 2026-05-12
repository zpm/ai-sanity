########################################################################################################################
# hooks/instruction_repeater/_state.py
#
# instruction-repeater session flag state
########################################################################################################################


import os
import time


class InstructionRepeaterState:

    """Per-session flag tracking whether the instruction text has been injected in the current session. Flags live as
    flat files at `~/.ai-sanity/hooks-state/instruction-repeater/<session_id>.flag`. Unlike required_reading's state
    (which uses per-session directories holding multiple flag files), this hook has a single boolean flag per session
    so flat files are sufficient. The state directory base is overridable via HOOK_TEST_STATE_DIR (test-only). Every
    operation swallows filesystem errors so that an unwritable state dir cannot crash a prompt."""

    _state_directory_relative_path_from_home = ".ai-sanity/hooks-state/instruction-repeater"


    @staticmethod
    def _get_effective_home_abs_path():

        """Returns the effective home directory, honoring HOOK_TEST_HOME_OVERRIDE when set."""
        home_override_abs_path = os.environ.get("HOOK_TEST_HOME_OVERRIDE")
        if home_override_abs_path:
            return home_override_abs_path.replace("\\", "/")
        return os.path.expanduser("~").replace("\\", "/")


    @staticmethod
    def get_state_base_directory_abs_path():

        """Returns the absolute, forward-slash-normalized path of the directory holding per-session flag files.
        Honors HOOK_TEST_STATE_DIR when set, otherwise derives from the effective home directory."""
        state_class = InstructionRepeaterState
        state_directory_override_abs_path = os.environ.get("HOOK_TEST_STATE_DIR")
        if state_directory_override_abs_path:
            return state_directory_override_abs_path.replace("\\", "/")
        effective_home_abs_path = state_class._get_effective_home_abs_path()
        return os.path.join(
            effective_home_abs_path,
            state_class._state_directory_relative_path_from_home
        ).replace("\\", "/")


    @staticmethod
    def _get_flag_file_abs_path(claude_session_id_string):

        """Returns the absolute path of the flag file for the given session."""
        state_class = InstructionRepeaterState
        state_base_directory_abs_path = state_class.get_state_base_directory_abs_path()
        return os.path.join(
            state_base_directory_abs_path,
            claude_session_id_string + ".flag"
        ).replace("\\", "/")


    @staticmethod
    def is_flag_set(claude_session_id_string):

        """Returns True if the flag file for the given session exists. Returns False on any filesystem error
        (re-fires the injection rather than silently suppressing it)."""
        state_class = InstructionRepeaterState
        try:
            flag_file_abs_path = state_class._get_flag_file_abs_path(
                claude_session_id_string = claude_session_id_string
            )
            return os.path.isfile(flag_file_abs_path)
        except OSError:
            return False


    @staticmethod
    def set_flag(claude_session_id_string):

        """Writes a flag file for the given session. The flag body is the session id (written only to aid human
        debugging; is_flag_set checks existence, not contents). Creates the state directory if missing. Swallows
        any filesystem error so an unwritable state dir cannot crash a prompt."""
        state_class = InstructionRepeaterState
        try:
            state_base_directory_abs_path = state_class.get_state_base_directory_abs_path()
            os.makedirs(state_base_directory_abs_path, exist_ok = True)
            flag_file_abs_path = state_class._get_flag_file_abs_path(
                claude_session_id_string = claude_session_id_string
            )
            with open(flag_file_abs_path, "w", encoding = "utf-8") as open_flag_file_handle:
                open_flag_file_handle.write(claude_session_id_string)
        except OSError:
            return


    @staticmethod
    def clear_flag(claude_session_id_string):

        """Removes the flag file for the given session. Called by the PreCompact hook so that after context
        compaction the instruction is re-injected. Swallows filesystem errors."""
        state_class = InstructionRepeaterState
        try:
            flag_file_abs_path = state_class._get_flag_file_abs_path(
                claude_session_id_string = claude_session_id_string
            )
            if os.path.isfile(flag_file_abs_path):
                os.remove(flag_file_abs_path)
        except OSError:
            return


    @staticmethod
    def sweep_stale_flag_files(stale_age_seconds_threshold = 7 * 24 * 60 * 60):

        """Removes flag files whose mtime is older than the threshold. Called lazily on UserPromptSubmit entry so
        cleanup happens organically without a daemon. Default threshold is seven days. Swallows filesystem errors.
        Skips cleanly if the state base directory does not exist."""
        state_class = InstructionRepeaterState
        try:
            state_base_directory_abs_path = state_class.get_state_base_directory_abs_path()
            if not os.path.isdir(state_base_directory_abs_path):
                return
            current_wall_clock_seconds = time.time()
            for flag_file_name in os.listdir(state_base_directory_abs_path):
                if not flag_file_name.endswith(".flag"):
                    continue
                candidate_flag_file_abs_path = os.path.join(
                    state_base_directory_abs_path,
                    flag_file_name
                )
                if not os.path.isfile(candidate_flag_file_abs_path):
                    continue
                try:
                    flag_file_mtime_seconds = os.path.getmtime(candidate_flag_file_abs_path)
                except OSError:
                    continue
                if current_wall_clock_seconds - flag_file_mtime_seconds > stale_age_seconds_threshold:
                    try:
                        os.remove(candidate_flag_file_abs_path)
                    except OSError:
                        continue
        except OSError:
            return
