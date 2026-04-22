########################################################################################################################
# hooks/_lib.py
#
# IO helpers and the low-level memory-path checker shared by every PreToolUse entry script
########################################################################################################################
import json
import os
import re
import sys


class PreToolUseHookIo:

    """Stdin and stdout helpers shared by every pretooluse_*.py entry script. The PreToolUse hook contract is documented
    at https://code.claude.com/docs/en/hooks: read a JSON payload from stdin, then either exit 0 with a hookSpecificOutput
    JSON object on stdout to deny/allow/ask, or exit 0 with no stdout to pass through to normal permission rules."""

    @staticmethod
    def read_pretooluse_payload_from_stdin():

        """Reads and parses the PreToolUse JSON payload Claude Code pipes to stdin and returns it as a dict. Uses the
        raw byte buffer with explicit UTF-8 decoding because text-mode stdin on Windows defaults to the cp1252 locale
        and silently mojibakes multi-byte characters before JSON parsing, erasing the em dash rule check."""
        return json.loads(sys.stdin.buffer.read().decode("utf-8"))

    @staticmethod
    def emit_deny_decision_and_exit(deny_reason_shown_to_claude):

        """Writes a deny-decision hookSpecificOutput JSON object to stdout and exits, which blocks the in-flight tool
        call. The deny_reason_shown_to_claude argument is surfaced verbatim to Claude so the message must explain which
        CLAUDE.md rule was violated and what Claude should do instead."""
        json.dump(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": deny_reason_shown_to_claude
                }
            },
            sys.stdout
        )
        sys.exit(0)

    @staticmethod
    def emit_passthrough_and_exit():

        """Writes nothing to stdout and exits cleanly, which lets the tool call proceed to the normal settings.json
        permission rule evaluation pipeline."""
        sys.exit(0)


class MemoryPathChecker:

    """Low-level check for whether a given path string references the auto-memory directory or a MEMORY.md file. Each
    matcher's entry script extracts the path arguments appropriate to its tool and passes them in. This avoids the
    'scan every text field' anti-pattern that would overblock legitimate searches for the literal string 'MEMORY.md'
    inside Grep regex patterns or the unrelated body of a Bash command."""

    _auto_memory_directory_path_pattern = re.compile(
        r"\.claude[/\\]projects[/\\][^/\\]+[/\\]memory(?:[/\\]|$)",
        re.IGNORECASE
    )
    _memory_md_filename_pattern = re.compile(
        r"(?:^|[/\\])MEMORY\.md\b",
        re.IGNORECASE
    )

    @staticmethod
    def assert_paths_are_not_memory_locations(*candidate_path_strings):

        """Returns a deny reason string if any candidate path string references the auto-memory directory layout
        (`<dir>/.claude/projects/<hash>/memory/...`) or a `MEMORY.md` filename. Returns None when all candidates pass.
        Empty/None candidates are skipped. The rule comes from CLAUDE.md ('YOU ARE NOT ALLOWED TO USE MEMORY.md or the
        external memory directory'). This is the losing side of a direct system-prompt conflict with the auto-memory
        system, so this hook is what makes CLAUDE.md actually win."""
        rule_check_class = MemoryPathChecker
        for candidate_path_string in candidate_path_strings:
            if not candidate_path_string:
                continue
            if rule_check_class._auto_memory_directory_path_pattern.search(candidate_path_string):
                return (
                    f"Refused: path `{candidate_path_string}` is inside the auto-memory directory. CLAUDE.md forbids"
                    f" using the external memory directory; the auto-memory system prompt is explicitly overridden."
                    f" Persistent rules must go in version-controlled CLAUDE.md files."
                )
            if rule_check_class._memory_md_filename_pattern.search(candidate_path_string):
                return (
                    f"Refused: path `{candidate_path_string}` references MEMORY.md. CLAUDE.md forbids using MEMORY.md;"
                    f" the auto-memory system prompt is explicitly overridden. Persistent rules must go in"
                    f" version-controlled CLAUDE.md files."
                )
        return None


class GlobToRegexConverter:

    """Converts a manifest-style glob pattern (as used in the `match` field of a required-reads rule) into a compiled
    regex suitable for `fullmatch` against a normalized forward-slash absolute path. Supported tokens: `**` matches any
    characters including path separators, `*` matches any characters except `/`, `?` matches one character except `/`,
    `{a,b,c}` expands to an alternation group (brace nesting is unsupported), `[abc]` is passed through to regex as a
    character class, and every other regex metacharacter is escaped so it matches literally. Matching is case
    insensitive on Windows (os.name == 'nt') and case sensitive elsewhere."""

    @staticmethod
    def convert_glob_to_compiled_regex(glob_pattern_string):

        """Returns a compiled `re.Pattern` equivalent to the given glob. Callers use `pattern.fullmatch(normalized_path)`
        to test a candidate path. Normalization (tilde expansion, absolutising, forward-slash separators) is the
        caller's responsibility and is shared with the manifest loader."""
        regex_part_strings = []
        character_index = 0
        glob_length = len(glob_pattern_string)
        while character_index < glob_length:
            current_character = glob_pattern_string[character_index]
            # ** must be checked before single *
            if (
                current_character == "*"
                and character_index + 1 < glob_length
                and glob_pattern_string[character_index + 1] == "*"
            ):
                regex_part_strings.append(".*")
                character_index += 2
                continue
            if current_character == "*":
                regex_part_strings.append("[^/]*")
                character_index += 1
                continue
            if current_character == "?":
                regex_part_strings.append("[^/]")
                character_index += 1
                continue
            if current_character == "{":
                # flat brace alternation only; nesting is unsupported and the '{' is treated literally if unterminated
                close_brace_index = glob_pattern_string.find("}", character_index + 1)
                if close_brace_index == -1:
                    regex_part_strings.append(re.escape(current_character))
                    character_index += 1
                    continue
                brace_body_string = glob_pattern_string[character_index + 1:close_brace_index]
                brace_alternative_strings = brace_body_string.split(",")
                escaped_brace_alternative_strings = [
                    re.escape(brace_alternative_string) for brace_alternative_string in brace_alternative_strings
                ]
                regex_part_strings.append("(?:" + "|".join(escaped_brace_alternative_strings) + ")")
                character_index = close_brace_index + 1
                continue
            if current_character == "[":
                # character class passthrough; if unterminated, treat '[' literally
                close_bracket_index = glob_pattern_string.find("]", character_index + 1)
                if close_bracket_index == -1:
                    regex_part_strings.append(re.escape(current_character))
                    character_index += 1
                    continue
                regex_part_strings.append(glob_pattern_string[character_index:close_bracket_index + 1])
                character_index = close_bracket_index + 1
                continue
            regex_part_strings.append(re.escape(current_character))
            character_index += 1
        combined_regex_string = "".join(regex_part_strings)
        compile_flags = re.IGNORECASE if os.name == "nt" else 0
        return re.compile(combined_regex_string, compile_flags)