########################################################################################################################
# tests/_common/fixtures.py
#
# Synthetic PreToolUse payload builders used by both unit and integration tests
########################################################################################################################


class PreToolUsePayloadFixtureBuilder:

    """Constructs synthetic PreToolUse payloads matching the contract documented at
    https://code.claude.com/docs/en/hooks. Keeps test bodies focused on the assertion rather than on JSON shape."""


    @staticmethod
    def build_base_payload(tool_name, tool_input, working_directory = "/tmp"):

        """Returns a complete PreToolUse payload dict with the given tool_name and tool_input populated."""
        return {
            "session_id": "test-session",
            "transcript_path": "/dev/null",
            "cwd": working_directory,
            "permission_mode": "default",
            "hook_event_name": "PreToolUse",
            "tool_name": tool_name,
            "tool_input": tool_input,
            "tool_use_id": "test-tool-use-id"
        }


    @staticmethod
    def build_write_payload(file_content, file_path = "/tmp/example.txt"):

        """Returns a Write PreToolUse payload with the given content and file_path."""
        builder_class = PreToolUsePayloadFixtureBuilder
        return builder_class.build_base_payload(
            tool_name = "Write",
            tool_input = {
                "file_path": file_path,
                "content": file_content
            }
        )


    @staticmethod
    def build_edit_payload(new_string_content, file_path = "/tmp/example.txt"):

        """Returns an Edit PreToolUse payload with the given new_string and file_path."""
        builder_class = PreToolUsePayloadFixtureBuilder
        return builder_class.build_base_payload(
            tool_name = "Edit",
            tool_input = {
                "file_path": file_path,
                "old_string": "previous-content-placeholder",
                "new_string": new_string_content
            }
        )


    @staticmethod
    def build_bash_payload(bash_command_string, working_directory = "/tmp"):

        """Returns a Bash PreToolUse payload with the given command and cwd."""
        builder_class = PreToolUsePayloadFixtureBuilder
        return builder_class.build_base_payload(
            tool_name = "Bash",
            tool_input = {
                "command": bash_command_string
            },
            working_directory = working_directory
        )


    @staticmethod
    def build_read_payload(file_path):

        """Returns a Read PreToolUse payload with the given file_path."""
        builder_class = PreToolUsePayloadFixtureBuilder
        return builder_class.build_base_payload(
            tool_name = "Read",
            tool_input = {
                "file_path": file_path
            }
        )


    @staticmethod
    def build_glob_payload(glob_pattern_string, glob_path = None):

        """Returns a Glob PreToolUse payload with the given pattern and optional path."""
        builder_class = PreToolUsePayloadFixtureBuilder
        glob_tool_input = {"pattern": glob_pattern_string}
        if glob_path is not None:
            glob_tool_input["path"] = glob_path
        return builder_class.build_base_payload(
            tool_name = "Glob",
            tool_input = glob_tool_input
        )


    @staticmethod
    def build_grep_payload(grep_pattern, grep_path = None):

        """Returns a Grep PreToolUse payload with the given regex pattern and optional path."""
        builder_class = PreToolUsePayloadFixtureBuilder
        grep_tool_input = {"pattern": grep_pattern}
        if grep_path is not None:
            grep_tool_input["path"] = grep_path
        return builder_class.build_base_payload(
            tool_name = "Grep",
            tool_input = grep_tool_input
        )


    @staticmethod
    def build_ask_user_question_payload(questions = None):

        """Returns an AskUserQuestion PreToolUse payload with the given questions list."""
        builder_class = PreToolUsePayloadFixtureBuilder
        return builder_class.build_base_payload(
            tool_name = "AskUserQuestion",
            tool_input = {
                "questions": questions or []
            }
        )


    @staticmethod
    def build_posttooluse_read_payload(file_path, working_directory = "/tmp", session_id = "test-session"):

        """Returns a synthetic PostToolUse payload for a completed Read tool call. Matches the PreToolUse shape with
        `hook_event_name` switched to `PostToolUse` and a minimal `tool_response` object; the required-reads
        observer only consumes `tool_name`, `tool_input.file_path`, `cwd`, and `session_id`."""
        return {
            "session_id": session_id,
            "transcript_path": "/dev/null",
            "cwd": working_directory,
            "permission_mode": "default",
            "hook_event_name": "PostToolUse",
            "tool_name": "Read",
            "tool_input": {"file_path": file_path},
            "tool_response": {"success": True},
            "tool_use_id": "test-tool-use-id"
        }


    @staticmethod
    def build_precompact_payload(session_id = "test-session"):

        """Returns a synthetic PreCompact payload. Only `session_id` is load-bearing for the required-reads
        precompact hook; other fields mirror the standard shape."""
        return {
            "session_id": session_id,
            "transcript_path": "/dev/null",
            "cwd": "/tmp",
            "permission_mode": "default",
            "hook_event_name": "PreCompact"
        }
