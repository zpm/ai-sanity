# Required-Reads Enforcement Hooks

## Context

Claude Opus 4.7 routinely skips "must read" documents listed in `CLAUDE.md` (styleguides, product docs, stack docs) despite explicit instructions. Instructions in `CLAUDE.md` are not enforced by the harness — they are suggestions the model can ignore. Hooks are the only mechanism the harness actually enforces.

This plan builds a system that forces required documents into the model's working context before it is allowed to edit files. It covers global style guides (from `~/.claude/styleguides/`), per-project docs (product/stack/architecture docs in individual repos), `CLAUDE.md` itself (both global and project scope), and `settings.json` at both scopes (so the model understands the active hooks, permissions, and env vars governing the session before it starts making changes).

The intended outcome: the model cannot modify any file without either (a) having the relevant docs already in context via a recorded `Read` tool call in this session, or (b) having had them auto-injected by the hook on the first matching edit. Compaction resets this state, so after context compression the model is re-required to process the docs.

**Scope decision for "start of every conversation" enforcement (CLAUDE.md and settings.json):** these are enforced as `block`-mode rules matching `**/*`, which fires on the first `Edit`, `Write`, or `NotebookEdit` of the session. Read-only conversations (question answering, file exploration without edits) do not trigger enforcement. If the intent is stricter (force Read before any tool call of any kind, including Read/Grep/Bash), the hook's PreToolUse matcher would need to expand from `Edit|Write|NotebookEdit` to `*`, adding an `on_tools` field to the rule schema so other rules remain scoped to edits only. Flag this back to the user before implementation if the current scope is insufficient; the design is extensible for it.

## Architecture

Three coordinating hooks plus a manifest discovery system:

| Hook | Event | File | Role |
|---|---|---|---|
| `pretooluse_required_reads.py` | PreToolUse on `Edit\|Write\|NotebookEdit` | New | Discovers rules, dedupes by session state, injects or blocks |
| `posttooluse_read_observer.py` | PostToolUse on `Read` | New | Writes satisfaction flags when the model Reads a required doc |
| `precompact_required_reads.py` | PreCompact | New | Clears this session's satisfaction flags on context compaction |

**Manifest discovery**: walk-up from the edited file collecting any `.claude/required-reads.json` files, append the global manifest last. Rules are unioned; project rules can silence specific global rules via an explicit `override` key.

**Single hook, distributed manifests**: the mechanism lives once at `~/.claude/hooks/`; content lives in per-project manifest files that travel with the repo.

**State**: per-session satisfaction flags in `~/.claude/hooks/.state/required-reads/<session_id>/<sha1(dedupe_key)>.flag`. Flags written by either (a) the Read observer when the model Reads a required doc, or (b) the PreToolUse hook when it injects a doc inline. Cleared by PreCompact. Aged out by a lazy 7-day TTL sweep on PreToolUse entry.

## Manifest format

**JSON.** Justification: matches the convention already established in `~/.claude/settings.json` and `.claude/settings.json`. Stdlib `json` is already used by the existing hooks for stdin/stdout payloads — zero new parsing surface. YAML would require `pyyaml` (forbidden by `CLAUDE.md`). TOML is a stdlib option but nothing else in the repo uses it, and introducing a second config format is gratuitous.

JSON's lack of inline comments is addressed via an optional per-rule `"comment"` field (the loader ignores it).

Filename: `required-reads.json` at both scopes. No other formats supported.

### Rule schema

Top-level shape: an object with a `"rules"` array. The wrapper allows non-breaking additions later (schema version, defaults block) without changing existing manifests.

```json
{
  "rules": [ { ... }, { ... } ]
}
```

Each rule is an object with these fields:

| Field | Type | Required | Default | Notes |
|---|---|---|---|---|
| `match` | string | yes | — | Glob against absolute, forward-slash-normalized file path. Supports `**`, `*`, `?`, `{a,b}`. |
| `read` | string | yes | — | Path to the required doc. `~` expanded. Relative resolved against manifest dir. |
| `mode` | string | no | `"inject"` | `"inject"` or `"block"`. |
| `override` | string | no | `null` | Normalized path of a global rule's `read` to silence. Only project rules can override global rules. |
| `dedupe_key` | string | no | normalized `read` path | Rules with the same dedupe key share satisfaction state. |
| `comment` | string | no | `null` | Loader ignores this. Exists so users can document rules inline despite JSON's lack of comments. |

**Path normalization** (one canonicalization point): `os.path.expanduser` → `os.path.abspath` → `.replace("\\", "/")`. All comparisons happen on the normalized form. Essential on Windows.

### Default global manifest

Shipped at `~/.claude/required-reads.json` as part of this work:

```json
{
  "rules": [
    {
      "comment": "CLAUDE.md is required context for any file-modifying tool call.",
      "match": "**/*",
      "read": "~/.claude/CLAUDE.md",
      "mode": "block"
    },
    {
      "comment": "Global settings.json defines active hooks, permissions, and env vars.",
      "match": "**/*",
      "read": "~/.claude/settings.json",
      "mode": "block"
    },
    {
      "match": "**/*.py",
      "read": "~/.claude/styleguides/python.md",
      "mode": "block"
    },
    {
      "match": "**/*.{js,css}",
      "read": "~/.claude/styleguides/javascript.md",
      "mode": "block"
    },
    {
      "comment": "Short doc; inject is lighter than a round-trip.",
      "match": "**/*.md",
      "read": "~/.claude/styleguides/markdown.md",
      "mode": "inject"
    },
    {
      "match": "**/*.{sh,ps1}",
      "read": "~/.claude/styleguides/scripts.md",
      "mode": "inject"
    }
  ]
}
```

Rationale for mode choices: long docs (python.md is 426 lines, CLAUDE.md is large) use `block` so they enter context via a single Read that's transcript-visible and benefits from prompt-cache placement. Short docs (markdown.md 44 lines, scripts.md 47 lines) use `inject` to skip a round-trip.

### Project manifest example

A project such as `/infinite-art/` would ship `.claude/required-reads.json`:

```json
{
  "rules": [
    {
      "comment": "Project settings.json defines project-scoped hooks and permissions.",
      "match": "**/*",
      "read": "./.claude/settings.json",
      "mode": "block"
    },
    {
      "comment": "Project CLAUDE.md is required for any edit in this project.",
      "match": "**/*",
      "read": "./CLAUDE.md",
      "mode": "block"
    },
    {
      "comment": "Product docs are required for any edit in this project.",
      "match": "**/*",
      "read": "./docs/product.md",
      "mode": "block"
    },
    {
      "comment": "Stack docs — required when touching infra or API code.",
      "match": "src/{api,infra}/**/*",
      "read": "./docs/stack.md",
      "mode": "block"
    },
    {
      "comment": "Project uses its own Python style — silence the global one.",
      "match": "**/*.py",
      "read": "./docs/project-python-style.md",
      "mode": "block",
      "override": "~/.claude/styleguides/python.md"
    }
  ]
}
```

## Files to create

| Path | Purpose |
|---|---|
| `~/.claude/hooks/pretooluse_required_reads.py` | PreToolUse entry for Edit/Write/NotebookEdit |
| `~/.claude/hooks/posttooluse_read_observer.py` | PostToolUse entry for Read |
| `~/.claude/hooks/precompact_required_reads.py` | PreCompact entry |
| `~/.claude/required-reads.json` | Default global manifest (five rules above) |
| `~/.claude/hooks/tests/test_required_reads_units.py` | Unit tests for shared logic |
| `~/.claude/hooks/tests/test_required_reads_subprocess.py` | Subprocess integration tests for all three hooks |
| `~/.claude/hooks/tests/fixtures_required_reads.py` | Manifest fixture builders |

## Files to modify

| Path | Changes |
|---|---|
| `~/.claude/hooks/_lib.py` | Append: `RequiredReadsManifestLoader`, `GlobToRegexConverter`, `RequiredReadsState` (flag read/write/clear), `PreToolUseHookIo.emit_inject_additional_context_and_exit()`, `PostToolUseHookIo` (new class for the Read observer). Plus test hook for `HOME` override via env var. |
| `~/.claude/settings.json` | Add three hook entries (diff below). |

### settings.json diff

Add to existing `hooks` block:

```json
{
  "PreToolUse": [
    // ...existing three entries unchanged...
    {
      "matcher": "Edit|Write|NotebookEdit",
      "hooks": [
        { "type": "command", "command": "python $HOME/.claude/hooks/pretooluse_required_reads.py" }
      ]
    }
  ],
  "PostToolUse": [
    {
      "matcher": "Read",
      "hooks": [
        { "type": "command", "command": "python $HOME/.claude/hooks/posttooluse_read_observer.py" }
      ]
    }
  ],
  "PreCompact": [
    {
      "hooks": [
        { "type": "command", "command": "python $HOME/.claude/hooks/precompact_required_reads.py" }
      ]
    }
  ]
}
```

The `Edit|Write|NotebookEdit` entry is a *sibling* of the existing `pretooluse_write.py` entry, not a replacement. Claude Code runs both hooks in parallel; if the memory-path hook denies, its deny wins and required-reads output is dropped — correct behavior. Exact PreCompact event name and matcher structure needs verification against current Claude Code docs during implementation; fallback if the event name differs is to hook `Stop` or `SessionEnd` and accept that mid-session compaction won't reset state.

## Module design

### Shared additions to `_lib.py`

```
GlobToRegexConverter
├── convert(glob: str) -> re.Pattern
│   # ** → .*, * → [^/]*, ? → [^/], {a,b} → (a|b), else literal-escaped.
│   # Case-insensitive when os.name == "nt", else case-sensitive.
│   # Brace nesting unsupported (documented).

RequiredReadsManifestLoader
├── discover_manifest_paths(file_path_abs: str, home_override: str | None) -> list[str]
│   # Walk up from dirname(file_path); append global last; dedupe; stop at home.
├── load_manifest(manifest_path: str) -> list[RuleRecord]
│   # Parse JSON; require top-level object with "rules" array; validate
│   # per-rule; skip invalid rules; ignore unknown fields (incl. "comment");
│   # never raise.
├── normalize_path(path: str, base_dir: str | None) -> str
│   # The single canonicalization function. Used everywhere.

RequiredReadsState
├── state_dir_for_session(session_id: str) -> str
│   # ~/.claude/hooks/.state/required-reads/<session_id>/
├── is_satisfied(session_id: str, dedupe_key: str) -> bool
├── mark_satisfied(session_id: str, dedupe_key: str) -> None
│   # Writes a flag file named sha1(dedupe_key).flag containing the key.
├── clear_session(session_id: str) -> None
│   # shutil.rmtree the session dir; swallow errors.
├── sweep_stale(ttl_days: int = 7) -> None
│   # Lazy TTL sweep; swallow errors.

PreToolUseHookIo
├── emit_inject_additional_context_and_exit(additional_context: str) -> NoReturn
│   # stdout: {"hookSpecificOutput": {"hookEventName": "PreToolUse", "additionalContext": "..."}}
│   # exit 0.

PostToolUseHookIo                                        # new class
├── read_posttooluse_payload_from_stdin() -> dict
├── emit_passthrough_and_exit() -> NoReturn
```

`RuleRecord` = `namedtuple("RuleRecord", ["rule_id", "manifest_abs_path", "is_global_manifest", "match_glob", "read_abs_path", "mode", "override_abs_path", "dedupe_key"])`.

### `pretooluse_required_reads.py`

Two-class pattern matching existing hooks.

```
PreToolUseRequiredReadsRuleChecks
├── extract_file_path(payload: dict) -> str | None
│   # Edit/Write → tool_input.file_path; NotebookEdit → tool_input.notebook_path.
├── collect_applicable_rules(file_path_abs: str, home: str) -> list[RuleRecord]
│   # Discover manifests, load, flatten, apply_overrides, glob-match.
├── apply_overrides(rules: list[RuleRecord]) -> list[RuleRecord]
│   # Project rules' override set filters global rules.
├── filter_satisfied(rules, session_id) -> (list[RuleRecord], list[RuleRecord])
│   # Returns (rules_to_fire, rules_already_satisfied).
├── partition_by_mode(rules) -> (block_rules, inject_rules)
├── build_deny_reason(block_rule: RuleRecord, file_path_abs: str) -> str
├── build_inject_context(inject_rules: list[RuleRecord]) -> str
│   # Reads each doc from disk; emits preamble + fenced body per rule,
│   # separated by blank lines. Missing files → preamble only with
│   # "<file not found on disk>" marker. Still marks satisfied.

PreToolUseRequiredReadsHookEntry
├── main() — control flow:
│   1. read payload (stdin)
│   2. outer try/except → passthrough on any error (never fail an edit)
│   3. RequiredReadsState.sweep_stale() (own try/except)
│   4. file_path = extract_file_path(payload); None → passthrough
│   5. file_path_abs = normalize_path(file_path)
│   6. rules = collect_applicable_rules(file_path_abs, home)
│   7. rules_to_fire, already_satisfied = filter_satisfied(rules, session_id)
│   8. block_rules, inject_rules = partition_by_mode(rules_to_fire)
│   9. if block_rules:
│        emit deny envelope with build_deny_reason(block_rules[0])
│        do NOT mark satisfied (satisfaction comes from Read, not deny)
│        exit 0
│     elif inject_rules:
│        ctx = build_inject_context(inject_rules)
│        for rule in inject_rules: mark_satisfied(session_id, rule.dedupe_key)
│        emit inject envelope
│        exit 0
│     else:
│        passthrough
```

### `posttooluse_read_observer.py`

```
PostToolUseReadObserverChecks
├── extract_read_path(payload: dict) -> str | None
├── load_all_rule_targets(file_path_abs: str, home: str) -> set[str]
│   # Returns set of normalized read_abs_path for all rules from all
│   # manifests discoverable from the Read's path (or cwd).
│   # Includes rules of all modes; satisfaction applies to both.
├── rule_dedupe_keys_for_target(target_abs: str, rules) -> list[str]
│   # All rules whose read_abs_path equals target get satisfied.

PostToolUseReadObserverEntry
├── main():
│   1. read payload (stdin)
│   2. outer try/except → passthrough on any error
│   3. read_path = extract_read_path(payload); None → passthrough
│   4. read_path_abs = normalize_path(read_path)
│   5. Discover manifests from read_path_abs (or cwd if read_path_abs
│      is outside the project tree).
│   6. For each rule whose read_abs_path == read_path_abs:
│        mark_satisfied(session_id, rule.dedupe_key)
│   7. emit_passthrough_and_exit()
```

Fast path: if `~/.claude/required-reads.json` doesn't exist and no project manifest is discoverable, exit immediately. Zero cost when the feature is unused.

### `precompact_required_reads.py`

```
PreCompactRequiredReadsEntry
├── main():
│   1. read payload (stdin) — expect session_id
│   2. outer try/except → exit 0 silently
│   3. RequiredReadsState.clear_session(session_id)
│   4. exit 0 with no stdout
```

Under 30 lines.

## Injection and deny envelopes

### Inject mode stdout

```json
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "additionalContext": "<formatted body>"
  }
}
```

`<formatted body>` per rule:

```
REQUIRED READ (rule <id> from <manifest_path>):
Editing <file_path> matches `<glob>`. The following doc must be in context:

--- BEGIN <read_path> ---
<full doc body>
--- END <read_path> ---
```

Multiple rules concatenated with `\n\n` between them.

### Block mode stdout

```json
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "Required-reads block: editing `<file_path>` requires `<read_path>` in context (rule <id> from <manifest_path>). Use the Read tool to load `<read_path>`, then retry this edit."
  }
}
```

First matching block rule wins; remaining block and inject rules are skipped (their satisfaction state unchanged — the Read observer will flag them as the model Reads each one).

## Glob matching

Small converter in `_lib.py`, ~40 lines, stdlib only. Rules:

- `**` → `.*`
- `*` → `[^/]*`
- `?` → `[^/]`
- `{a,b,c}` → `(a|b|c)` (no nested braces; document the limit)
- `[abc]` → passthrough
- All other regex metachars escaped
- `re.fullmatch` semantics
- `re.IGNORECASE` when `os.name == "nt"`

Caller normalizes path before matching.

## State file layout

```
~/.claude/hooks/.state/required-reads/
├── <session_id_1>/
│   ├── <sha1(dedupe_key_a)>.flag    # content: normalized dedupe_key (human-debug only)
│   └── <sha1(dedupe_key_b)>.flag
├── <session_id_2>/
│   └── ...
```

- **Created by**: PostToolUse Read observer (preferred path — model actually Read the doc) OR PreToolUse inject mode (immediate, because injection provides the context without a Read).
- **Read by**: PreToolUse hook's `filter_satisfied`.
- **Cleared by**: PreCompact hook (whole session subdir) + lazy 7-day TTL sweep on PreToolUse entry.
- **Session dir only**: no global state. No LRU, no count cap, no locks.

## Failure-mode handling

Every path must degrade to "passthrough, emit nothing, do not crash an edit."

| # | Failure | Handling |
|---|---|---|
| 1 | Manifest unreadable | Skip that manifest, continue. |
| 2 | Malformed JSON (`json.JSONDecodeError`) or top-level shape wrong (not an object, missing `rules`, `rules` not a list) | Skip that manifest, continue. |
| 3 | Rule missing required field | Skip that rule, keep siblings. |
| 4 | Rule has invalid `mode` | Skip that rule. |
| 5 | Read-target file doesn't exist | Inject: emit preamble with `<file not found on disk>`, still mark satisfied. Block: include "missing" note in deny reason, do not retry loop. |
| 6 | State dir unwritable | Swallow. Proceed without flag write. May re-inject next edit. |
| 7 | Session ID missing from payload | Use `"unknown-session"`. Dedupe works within one invocation only. |
| 8 | Symlink loop in walk-up | `visited` set of normalized paths. |
| 9 | Glob regex compile fails | Skip that rule. |
| 10 | Memory-path hook denies alongside us | Harness merges; memory deny wins. Our output dropped. Correct. |
| 11 | No `~/.claude/required-reads.json` yet | Empty rule list → passthrough. Zero-config install is a no-op. |
| 12 | PreCompact event name differs in current Claude Code docs | Verified during implementation; fall back to Stop/SessionEnd if PreCompact absent, and document limitation. |

## Test plan

### `tests/test_required_reads_units.py`

Unit classes (direct method calls, no subprocess):

- **TestGlobToRegex**: `**` across separators, `*` not across, `?` single char, braces, metachar escaping, case handling on `nt` vs `posix`.
- **TestManifestLoader**: well-formed load, malformed JSON → `[]`, top-level not an object → `[]`, missing `rules` key → `[]`, `rules` not a list → `[]`, missing file → `[]`, rule missing `match`/`read` skipped, invalid `mode` skipped, unknown fields (including `comment`) ignored without error, tilde expansion, relative `read` resolved against manifest dir, dedupe_key default.
- **TestDiscoverManifests**: tempdir-based, home override. Cases: only-global, project manifest in nearest `.claude/`, walk past intermediate dirs, stops at home, global always appended last, empty → empty list.
- **TestApplyOverrides**: project overrides global, project cannot override project, tilde/abs normalization for override comparison.
- **TestRequiredReadsState**: first write + read, second write idempotent, clear_session removes dir, sweep_stale removes old dirs only.
- **TestFilterSatisfied**: no flags → all fire, flag present → skip, two rules sharing dedupe_key collapse to one satisfaction.
- **TestBuildInjectContext**: single rule preamble+fences, missing file marker, multi-rule concat with blank line.
- **TestBuildDenyReason**: first block rule wins, reason contains file_path + read_path + rule_id.

### `tests/test_required_reads_subprocess.py`

Subprocess integration via existing `HookEntryScriptInvocationHelper`. Each test sets `HOOK_TEST_HOME_OVERRIDE` and `HOOK_TEST_STATE_DIR` env vars to point at a tempdir.

- **TestPreToolUseRequiredReadsEntry**:
  - Edit `.py` with global python rule → deny with reason mentioning python.md
  - Edit unmatched file → passthrough
  - Write matching inject rule → inject envelope with preamble+fences
  - Second Edit same session same rule → no re-inject
  - Different session → re-injects
  - Malformed project manifest → global rules still apply
  - Unwritable state dir → passthrough, no crash
  - NotebookEdit on `.ipynb` with matching rule → inject
  - Payload missing file_path → passthrough
  - Project override silences global rule end-to-end
  - Both block and inject rules match → deny wins, inject skipped
- **TestPostToolUseReadObserver**:
  - Read on required doc → next PreToolUse does not deny that rule
  - Read on unrelated doc → no flag written
  - Read path normalized (tilde) matches rule with abs path
  - Missing manifest → fast-path no-op
- **TestPreCompactClear**:
  - Flags exist in session dir → after PreCompact, dir empty / removed
  - Non-existent session dir → no-op no error
  - Malformed payload (missing session_id) → no error

### New test infrastructure

- Extend `_lib` to read `os.environ.get("HOOK_TEST_HOME_OVERRIDE") or os.path.expanduser("~")` and `os.environ.get("HOOK_TEST_STATE_DIR")` (falls back to default). Document as test-only.
- Extend `fixtures.py` with `build_read_payload` (may already exist — confirm and reuse), add `build_precompact_payload`.
- Add `fixtures_required_reads.py` with `ManifestFixtureBuilder` that writes JSON manifests to tempdirs.

## Verification end-to-end

After implementation:

1. Run existing unittest suite from `hooks/test_hooks.sh`. All pre-existing tests must pass unchanged.
2. Run new suites: `python -m unittest hooks.tests.test_required_reads_units hooks.tests.test_required_reads_subprocess -v`.
3. Manual smoke: in a fresh Claude Code session, try to Edit a `.py` file. Expect deny citing `python.md`. Claude Reads `python.md`. Retry Edit. Expect success.
4. Second Edit on a different `.py` file in the same session. Expect success without deny (dedupe).
5. Trigger `/compact`. Then Edit another `.py` file. Expect deny again (state cleared). If PreCompact event wiring turned out to not exist in the current Claude Code version, this step verifies the fallback instead.
6. Drop a `required-reads.json` into a test project's `.claude/` with a rule for `**/*.py` pointing at a local doc. Edit a `.py` in that project. Expect both global python.md rule and project rule to fire (union).
7. Add `override = "~/.claude/styleguides/python.md"` to the project rule. Edit a `.py`. Expect only project rule fires.

## Documentation check

Per `CLAUDE.md` rules, every change ends with a docs pass. After implementation, update:

- `~/.claude/CLAUDE.md` — replace the "Style Guides" table's wording. Current table frames style-guide reading as a manual must-do. After this feature, it is hook-enforced; the table should note this (one line) and point at `~/.claude/required-reads.json` as the source of truth. Do NOT list rules in CLAUDE.md (docs must not duplicate code/config).
- `~/.claude/CLAUDE.md` — add a short section (3-5 lines) under "ALWAYS SEEK USER INPUT" or similar: if a required-read deny fires, Read the doc then retry the edit; don't ask the user to disable the hook.
- `~/.claude/hooks/` — if there's a README, update the hook inventory. If none exists, do not create one (CLAUDE.md rule: no new docs unless requested).
- No new user-facing docs for the manifest format. The shipped default global manifest uses `"comment"` fields on rules to document itself by example.
