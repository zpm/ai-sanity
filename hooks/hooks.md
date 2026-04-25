# Claude Code Hooks

> Enforces the rules in `~/.claude/CLAUDE.md` at tool-call time.

## Purpose

CLAUDE.md is guidance only: Claude reads it but the harness does not enforce it. Rules drift across long sessions, into subagents, and especially when another system prompt directly contradicts CLAUDE.md (the auto-memory system instructs Claude to write to a directory CLAUDE.md forbids). The PreToolUse hook contract lets a script inspect each tool call before it runs and deny outright with a message Claude reads back. Every CLAUDE.md rule that maps cleanly onto a deterministic, programmatic check lives here.

## Wiring

These scripts live outside `~/.claude/` so they can iterate under version control. They run because `~/.claude/settings.json` references them by absolute path (`$HOME/Dev/ai-common/hooks/<domain>/pretooluse_*.py`). Moving or renaming any entry script requires updating `settings.json` to match. See the repo `README.md` for the installation pattern.

## Defense-in-depth: where to put each rule

`settings.json` deny rules are the primary enforcement layer and hold every rule that can be cleanly expressed as a glob match on the command string. The hooks are downstream and exist for cases globs cannot express: dynamic checks (git ls-files on mv), content-level path discrimination (auto-memory directory detection), and the required-reads manifest system.

Hook code should never duplicate logic that `settings.json` already handles.

## Architecture

One directory per functional domain. Each domain directory holds its own entry scripts, rule-check classes, and internal library modules. The shared `_hook_io.py` at the hooks root provides the stdin/stdout protocol helpers used by every entry script.

| Domain | Directory | What it does |
|---|---|---|
| no_memory | `no_memory/` | Blocks access to auto-memory directory and MEMORY.md |
| required_reading | `required_reading/` | Forces required docs into context before file operations |
| git_safety | `git_safety/` | Enforces `git mv` for tracked file moves |

Each entry script follows a two-class pattern: a rule-checks class (static methods returning deny-reason or None) and an entry class (composes checks, reads payload, denies on first violation). Every entry script wraps its `main()` in try/except with passthrough fallback so a bug in the hook never blocks an edit.

PostToolUse and PreCompact hooks follow the same shape but emit no decision envelope.

## Required-reads enforcement

The required-reads hook trio forces Claude to have specific documents in context before any Read, Write, Edit, or NotebookEdit tool call that touches a matching file. The PreToolUse enforcer lives at `required_reading/pretooluse.py`, the PostToolUse Read observer at `required_reading/posttooluse_observer.py`, and the PreCompact state reset at `required_reading/precompact.py`.

The manifest is a JSON file named `required-reads.json`. Discovery walks up from the edited file collecting any `./.claude/required-reads.json` encountered, then appends the global `~/.claude/required-reads.json` last. Project rules can silence a global rule by naming the global rule's `read` target in an `override` field; only project rules may override.

A rule carries zero or one match criterion via two mutually exclusive fields. `extension` is a suffix test against the normalised path. `filepath` is a substring test. A rule with neither is a wildcard. Both on one rule is a load-time validation error and the rule is skipped. Match values are lowercased at load time.

Every rule is block-mode. An unsatisfied matched rule denies the tool call until Claude Reads the target doc.

Reads of any manifest-listed `read` target always passthrough regardless of other rules. This breaks self-target deadlocks and ensures loading required context is never gated on other required context.

Satisfaction state is per-session flag files under `~/.claude/hooks-state/required-reads/<session_id>/`, named `<sha1(dedupe_key)>.flag`. PreCompact removes the session subdirectory. A lazy 7-day sweep ages out ended sessions.

A missing `read` target is a hard configuration error with no skip-if-missing escape hatch.

Path canonicalisation expands `~`, absolutises, replaces backslashes with forward slashes, and lowercases.

## Adding a new rule

1. Identify which domain the rule belongs to.
2. Add a `check_<rule>` static method to that domain's rule-checks class.
3. Register it in the entry class's tuple.
4. Add unit tests covering both block and pass cases.
5. Add a subprocess test.

If the rule applies across domains, factor the comparison logic into the domain's internal library module and import from other entry scripts.

## Adding a new domain

1. Create `<domain>/` with `__init__.py` and entry script(s).
2. Add `hooks.PreToolUse` entries to `~/.claude/settings.json`.
3. Create `tests/<domain>/` with `__init__.py` and test files.
4. Add subprocess tests.

## Tests

Two layers using stdlib `unittest`. Unit tests import rule classes directly. Subprocess integration tests pipe payloads to entry scripts and assert on stdout JSON and exit code. Run via `test_hooks.sh` or `test_hooks.ps1` from the repo root. The runners `cd` into `hooks/` and invoke `python -m unittest discover -s tests -t .`.

## Windows notes

Hook commands resolve through Git Bash via `CLAUDE_CODE_GIT_BASH_PATH` in `settings.json`. Hook stdin is raw bytes from Claude Code; entry scripts read from `sys.stdin.buffer` and pass bytes directly to `json.loads` for encoding auto-detection, bypassing the Windows cp1252 text-mode default.
