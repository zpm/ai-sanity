########################################################################################################################
# tests/instruction_repeater/test_state.py
#
# instruction-repeater state unit tests
########################################################################################################################


import os
import sys
import tempfile
import time
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "hooks"))

import instruction_repeater._state


class StateDirectoryOverrideTestCaseMixin:

    """Per-test setup/teardown that points HOOK_TEST_STATE_DIR at a fresh tempdir so the instruction-repeater state
    subsystem operates inside a sandbox. More targeted than HomeOverrideEnvVarTestCaseMixin because state unit tests
    only need to isolate the state directory, not the full home."""


    def setUp(self):

        self._previous_state_dir_value = os.environ.get("HOOK_TEST_STATE_DIR")
        self.sandboxed_state_dir_abs_path = tempfile.mkdtemp()
        os.environ["HOOK_TEST_STATE_DIR"] = self.sandboxed_state_dir_abs_path


    def tearDown(self):

        if self._previous_state_dir_value is None:
            os.environ.pop("HOOK_TEST_STATE_DIR", None)
        else:
            os.environ["HOOK_TEST_STATE_DIR"] = self._previous_state_dir_value


class TestInstructionRepeaterState(StateDirectoryOverrideTestCaseMixin, unittest.TestCase):


    def test_unset_flag_returns_false(self):

        self.assertFalse(instruction_repeater._state.InstructionRepeaterState.is_flag_set(
            claude_session_id_string = "session-never-set"
        ))


    def test_set_flag_then_is_flag_set_returns_true(self):

        instruction_repeater._state.InstructionRepeaterState.set_flag(
            claude_session_id_string = "session-alpha"
        )
        self.assertTrue(instruction_repeater._state.InstructionRepeaterState.is_flag_set(
            claude_session_id_string = "session-alpha"
        ))


    def test_set_flag_is_idempotent(self):

        instruction_repeater._state.InstructionRepeaterState.set_flag(
            claude_session_id_string = "session-beta"
        )
        instruction_repeater._state.InstructionRepeaterState.set_flag(
            claude_session_id_string = "session-beta"
        )
        self.assertTrue(instruction_repeater._state.InstructionRepeaterState.is_flag_set(
            claude_session_id_string = "session-beta"
        ))


    def test_different_sessions_do_not_share_flags(self):

        instruction_repeater._state.InstructionRepeaterState.set_flag(
            claude_session_id_string = "session-one"
        )
        self.assertFalse(instruction_repeater._state.InstructionRepeaterState.is_flag_set(
            claude_session_id_string = "session-two"
        ))


    def test_clear_flag_removes_the_flag(self):

        instruction_repeater._state.InstructionRepeaterState.set_flag(
            claude_session_id_string = "session-clear"
        )
        instruction_repeater._state.InstructionRepeaterState.clear_flag(
            claude_session_id_string = "session-clear"
        )
        self.assertFalse(instruction_repeater._state.InstructionRepeaterState.is_flag_set(
            claude_session_id_string = "session-clear"
        ))


    def test_clear_flag_on_nonexistent_session_is_a_no_op(self):

        instruction_repeater._state.InstructionRepeaterState.clear_flag(
            claude_session_id_string = "session-never-existed"
        )


    def test_sweep_stale_removes_old_flags_and_keeps_fresh(self):

        instruction_repeater._state.InstructionRepeaterState.set_flag(
            claude_session_id_string = "session-old"
        )
        instruction_repeater._state.InstructionRepeaterState.set_flag(
            claude_session_id_string = "session-new"
        )
        old_flag_file_abs_path = instruction_repeater._state.InstructionRepeaterState._get_flag_file_abs_path(
            claude_session_id_string = "session-old"
        )
        ten_days_ago_wall_clock_seconds = time.time() - (10 * 24 * 60 * 60)
        os.utime(old_flag_file_abs_path, (ten_days_ago_wall_clock_seconds, ten_days_ago_wall_clock_seconds))
        instruction_repeater._state.InstructionRepeaterState.sweep_stale_flag_files()
        self.assertFalse(instruction_repeater._state.InstructionRepeaterState.is_flag_set(
            claude_session_id_string = "session-old"
        ))
        self.assertTrue(instruction_repeater._state.InstructionRepeaterState.is_flag_set(
            claude_session_id_string = "session-new"
        ))


    def test_sweep_stale_with_no_state_base_directory_is_a_no_op(self):

        os.environ["HOOK_TEST_STATE_DIR"] = os.path.join(self.sandboxed_state_dir_abs_path, "nonexistent")
        instruction_repeater._state.InstructionRepeaterState.sweep_stale_flag_files()


if __name__ == "__main__":
    unittest.main()
