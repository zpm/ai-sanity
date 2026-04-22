########################################################################################################################
# hooks/_lib.py
#
# IO helpers and the low-level memory-path checker shared by every PreToolUse entry script
########################################################################################################################
import collections
import hashlib
import json
import os
import re
import shutil
import sys
import time


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

class PostToolUseHookIo:

    """Stdin and stdout helpers for posttooluse_*.py entry scripts. Per the PostToolUse hook contract documented at
    https://code.claude.com/docs/en/hooks, PostToolUse hooks observe a completed tool call and cannot deny it; their
    usefulness comes from writing to external state (e.g. the required-reads satisfaction flags) based on what the
    tool did. The passthrough emit here is identical to PreToolUse passthrough: no stdout, exit 0."""

    @staticmethod
    def read_posttooluse_payload_from_stdin():

        """Reads and parses the PostToolUse JSON payload Claude Code pipes to stdin. Uses the raw UTF-8 byte buffer
        to match the PreToolUse sibling and avoid the Windows cp1252 mojibake regression."""
        return json.loads(sys.stdin.buffer.read().decode("utf-8"))

    @staticmethod
    def emit_passthrough_and_exit():

        """Writes nothing to stdout and exits 0. PostToolUse hooks have no per-decision envelope to emit; the
        observation they make (e.g. writing a satisfaction flag to disk) already happened before this call."""
        sys.exit(0)


class PreCompactHookIo:

    """Stdin and stdout helpers for precompact_*.py entry scripts. PreCompact fires when Claude Code is about to
    compress the conversation context. The hook has no decision envelope; any cleanup it performs (e.g. clearing
    required-reads satisfaction flags so docs are re-demanded after compaction) happens via external state writes."""

    @staticmethod
    def read_precompact_payload_from_stdin():

        """Reads and parses the PreCompact JSON payload Claude Code pipes to stdin. Uses the raw UTF-8 byte buffer
        for the same Windows cp1252 reason as the PreToolUse and PostToolUse siblings."""
        return json.loads(sys.stdin.buffer.read().decode("utf-8"))

    @staticmethod
    def emit_passthrough_and_exit():

        """Writes nothing to stdout and exits 0."""
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


RequiredReadsRuleRecord = collections.namedtuple(
    "RequiredReadsRuleRecord",
    [
        "rule_id",
        "manifest_abs_path",
        "is_global_manifest",
        "match_glob",
        "read_abs_path",
        "override_abs_path",
        "dedupe_key",
    ]
)


class RequiredReadsPathNormalizer:

    """Single canonicalization function for every path in the required-reads subsystem. All comparisons between paths
    (rule `read` targets, candidate edited-file paths, override targets) must go through this so Windows vs Posix and
    tilde-prefixed vs absolute forms collapse to the same string. Tilde expansion honors the test-only
    HOOK_TEST_HOME_OVERRIDE env var so tests can point at a sandboxed home without touching the real ~."""

    @staticmethod
    def normalize_path(raw_path_string, base_directory_abs_path = None):

        """Returns a forward-slash, lowercased absolute path. Tilde is expanded first (honoring
        HOOK_TEST_HOME_OVERRIDE), then relative paths are resolved against `base_directory_abs_path` if given, then
        `os.path.abspath`, then backslashes become forward slashes, then the whole string is lowercased. The lower
        call handles Windows filesystem case-insensitivity (the common real bug: manifest `C:/...` vs Read
        `c:/...`); it is technically lossy on Posix where `foo.md` and `FOO.md` can coexist, but case-colliding doc
        paths do not occur in any meaningful deployment of this hook, so universal lowercasing simplifies the
        canonicalization story."""
        home_expanded_path_string = RequiredReadsPathNormalizer._expand_home_honoring_test_override(raw_path_string)
        if base_directory_abs_path and not os.path.isabs(home_expanded_path_string):
            home_expanded_path_string = os.path.join(base_directory_abs_path, home_expanded_path_string)
        absolutised_path_string = os.path.abspath(home_expanded_path_string)
        return absolutised_path_string.replace("\\", "/").lower()

    @staticmethod
    def _expand_home_honoring_test_override(raw_path_string):

        """Expands a leading `~` using HOOK_TEST_HOME_OVERRIDE if set, otherwise `os.path.expanduser`. Non-tilde paths
        return unchanged."""
        home_override_abs_path = os.environ.get("HOOK_TEST_HOME_OVERRIDE")
        if home_override_abs_path and raw_path_string.startswith("~"):
            if raw_path_string == "~":
                return home_override_abs_path
            if raw_path_string[1] in ("/", "\\"):
                return home_override_abs_path + raw_path_string[1:]
        return os.path.expanduser(raw_path_string)

    @staticmethod
    def get_effective_home_abs_path():

        """Returns the home directory that the required-reads subsystem treats as ~. HOOK_TEST_HOME_OVERRIDE wins
        when set; otherwise `os.path.expanduser('~')`. Output is forward-slash-normalized and lowercased to match
        `normalize_path`'s canonicalization, so directory walk-up comparisons in the manifest discovery path do not
        miss on case differences."""
        home_override_abs_path = os.environ.get("HOOK_TEST_HOME_OVERRIDE")
        if home_override_abs_path:
            return home_override_abs_path.replace("\\", "/").lower()
        return os.path.expanduser("~").replace("\\", "/").lower()


class RequiredReadsState:

    """Per-session satisfaction flags used by the required-reads hook trio. A flag means that, within a single Claude
    Code session, a given rule's dedupe key has already been satisfied (either by a Read observed on its target doc or
    by an inline inject-mode injection). Flags live under `~/.claude/hooks-state/required-reads/<session_id>/` with
    filenames of `<sha1(dedupe_key)>.flag` containing the normalized key string for human debugging. The state
    directory base is overridable via the HOOK_TEST_STATE_DIR env var (test-only). Every operation swallows
    filesystem errors so that an unwritable state dir cannot crash an edit."""

    _state_directory_relative_path_from_home = ".claude/hooks-state/required-reads"

    @staticmethod
    def get_state_base_directory_abs_path():

        """Returns the absolute, forward-slash-normalized path of the root directory under which per-session
        subdirectories live. Honors HOOK_TEST_STATE_DIR when set, otherwise uses the effective home's
        `.claude/hooks-state/required-reads/`."""
        state_class = RequiredReadsState
        state_directory_override_abs_path = os.environ.get("HOOK_TEST_STATE_DIR")
        if state_directory_override_abs_path:
            return state_directory_override_abs_path.replace("\\", "/")
        effective_home_abs_path = RequiredReadsPathNormalizer.get_effective_home_abs_path()
        return RequiredReadsPathNormalizer.normalize_path(
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


class RequiredReadsManifestLoader:

    """Discovers and parses `.claude/required-reads.json` manifests. Project manifests live next to the edited file
    (walk up until home is reached). The global manifest lives at `~/.claude/required-reads.json`. Every failure mode
    (missing file, malformed JSON, wrong top-level shape, invalid rule) returns an empty list or skips the offending
    rule so that hook execution never crashes an edit."""

    _project_manifest_relative_path = ".claude/required-reads.json"
    _global_manifest_relative_path_from_home = ".claude/required-reads.json"

    @staticmethod
    def discover_manifest_abs_paths(edited_file_abs_path):

        """Walks up from `dirname(edited_file_abs_path)` collecting `.claude/required-reads.json` files. Stops when
        the walk reaches the effective home or the filesystem root. The global manifest is appended last if it
        exists. Return value is ordered nearest-project-manifest first, global last. A `visited` set on normalized
        paths guards against symlink loops."""
        loader_class = RequiredReadsManifestLoader
        discovered_manifest_abs_paths = []
        visited_directory_abs_paths = set()
        effective_home_abs_path = RequiredReadsPathNormalizer.get_effective_home_abs_path()
        current_directory_abs_path = RequiredReadsPathNormalizer.normalize_path(
            os.path.dirname(edited_file_abs_path)
        )
        while True:
            if current_directory_abs_path in visited_directory_abs_paths:
                break
            visited_directory_abs_paths.add(current_directory_abs_path)
            candidate_project_manifest_abs_path = RequiredReadsPathNormalizer.normalize_path(
                os.path.join(current_directory_abs_path, loader_class._project_manifest_relative_path)
            )
            if os.path.isfile(candidate_project_manifest_abs_path):
                discovered_manifest_abs_paths.append(candidate_project_manifest_abs_path)
            if current_directory_abs_path == effective_home_abs_path:
                break
            parent_directory_abs_path = RequiredReadsPathNormalizer.normalize_path(
                os.path.dirname(current_directory_abs_path)
            )
            if parent_directory_abs_path == current_directory_abs_path:
                break
            current_directory_abs_path = parent_directory_abs_path
        global_manifest_abs_path = RequiredReadsPathNormalizer.normalize_path(
            os.path.join(effective_home_abs_path, loader_class._global_manifest_relative_path_from_home)
        )
        if global_manifest_abs_path not in discovered_manifest_abs_paths and os.path.isfile(global_manifest_abs_path):
            discovered_manifest_abs_paths.append(global_manifest_abs_path)
        return discovered_manifest_abs_paths

    @staticmethod
    def load_manifest_rule_records(manifest_abs_path, is_global_manifest):

        """Parses a single manifest file and returns a list of `RequiredReadsRuleRecord`. Returns [] on any file or
        JSON parse error, and skips individual rules that are missing required fields or have invalid values. The
        `is_global_manifest` flag controls whether the rules produced are eligible to be silenced by a project-level
        `override`."""
        loader_class = RequiredReadsManifestLoader
        try:
            with open(manifest_abs_path, "r", encoding = "utf-8") as open_manifest_file_handle:
                parsed_manifest_object = json.load(open_manifest_file_handle)
        except (OSError, json.JSONDecodeError):
            return []
        if not isinstance(parsed_manifest_object, dict):
            return []
        raw_rule_objects = parsed_manifest_object.get("rules")
        if not isinstance(raw_rule_objects, list):
            return []
        project_root_abs_path = RequiredReadsPathNormalizer.normalize_path(
            os.path.dirname(os.path.dirname(manifest_abs_path))
        )
        produced_rule_records = []
        for raw_rule_object_index, raw_rule_object in enumerate(raw_rule_objects):
            if not isinstance(raw_rule_object, dict):
                continue
            rule_record_or_none = loader_class._build_rule_record_or_none(
                raw_rule_object = raw_rule_object,
                raw_rule_object_index = raw_rule_object_index,
                manifest_abs_path = manifest_abs_path,
                project_root_abs_path = project_root_abs_path,
                is_global_manifest = is_global_manifest
            )
            if rule_record_or_none is not None:
                produced_rule_records.append(rule_record_or_none)
        return produced_rule_records

    @staticmethod
    def _build_rule_record_or_none(raw_rule_object,
        raw_rule_object_index,
        manifest_abs_path,
        project_root_abs_path,
        is_global_manifest
    ):

        """Validates a single raw rule dict and returns a `RequiredReadsRuleRecord`, or None if the rule is invalid.
        Relative `read` paths resolve against the project root (the directory containing `.claude/`), not against the
        manifest's own directory; this keeps rules natural to write (`./CLAUDE.md`, `./docs/stack/backend.md`). The
        loader ignores unknown keys including any legacy `mode` field and the `comment` documentation field."""
        match_glob_string = raw_rule_object.get("match")
        read_path_string = raw_rule_object.get("read")
        if not isinstance(match_glob_string, str) or not match_glob_string:
            return None
        if not isinstance(read_path_string, str) or not read_path_string:
            return None
        read_abs_path = RequiredReadsPathNormalizer.normalize_path(
            read_path_string,
            base_directory_abs_path = project_root_abs_path
        )
        override_raw_value = raw_rule_object.get("override")
        override_abs_path = None
        if isinstance(override_raw_value, str) and override_raw_value:
            override_abs_path = RequiredReadsPathNormalizer.normalize_path(override_raw_value)
        dedupe_key_raw_value = raw_rule_object.get("dedupe_key")
        if isinstance(dedupe_key_raw_value, str) and dedupe_key_raw_value:
            dedupe_key_string = dedupe_key_raw_value
        else:
            dedupe_key_string = read_abs_path
        rule_id_string = f"{os.path.basename(manifest_abs_path)}#{raw_rule_object_index}"
        return RequiredReadsRuleRecord(
            rule_id = rule_id_string,
            manifest_abs_path = manifest_abs_path,
            is_global_manifest = is_global_manifest,
            match_glob = match_glob_string,
            read_abs_path = read_abs_path,
            override_abs_path = override_abs_path,
            dedupe_key = dedupe_key_string
        )


