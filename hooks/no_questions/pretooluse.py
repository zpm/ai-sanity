########################################################################################################################
# hooks/no_questions/pretooluse.py
#
# blocks AskUserQuestion tool calls, forcing claude to ask questions in plain chat text
########################################################################################################################


import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import _common._hook_io


_DENY_MESSAGE = "AskUserQuestion is disabled. Ask your questions in plain chat text instead of using interactive dialogs."


class PreToolUseNoQuestionsHookEntry:

    """Unconditionally denies AskUserQuestion."""


    @staticmethod
    def main():

        try:
            _common._hook_io.PreToolUseHookIo.read_pretooluse_payload_from_stdin()
            _common._hook_io.PreToolUseHookIo.emit_deny_decision_and_exit(_DENY_MESSAGE)
        except Exception as e:
            _common._hook_io.PreToolUseHookIo.emit_deny_decision_and_exit(f"no_questions hook crashed: {e}")


if __name__ == "__main__":
    PreToolUseNoQuestionsHookEntry.main()
