# ai-common

Shared Claude Code hooks and style guides.

## Purpose

CLAUDE.md is guidance only: Claude reads it but the harness does not enforce it. Rules drift across long sessions, into subagents, and especially when another system prompt directly contradicts CLAUDE.md. The PreToolUse hook contract lets a script inspect each tool call before it runs and deny outright with a message Claude reads back. Every CLAUDE.md rule that maps cleanly onto a deterministic, programmatic check lives here.

## Wiring

Copy [settings.example.json](settings.example.json) to `~/.claude/settings.json` and adjust paths if your clone lives somewhere other than `~/Dev/ai-common`. On Windows, `CLAUDE_CODE_GIT_BASH_PATH` must point to Git Bash. Personal preferences (model, effort, view) are omitted from the example; add your own.

## Where rules live

Hooks are the primary enforcement layer for Bash command policy. The `bash_commands` hook handles both allow and deny decisions with informative messages. `settings.json` is reserved for tool-level allows (Read, Write, Edit, etc.) which hooks cannot express without per-call subprocess overhead, non-Bash tool denies (e.g. `Skill(update-config)`), and ask-mode rules (e.g. `Bash(rm *)`).

## Hook architecture

One directory per functional domain under `hooks/`. Each domain holds its own entry scripts, rule-check classes, and internal library modules. The shared `_hook_io.py` provides the stdin/stdout protocol helpers.

Each entry script follows a two-class pattern: a rule-checks class (static methods returning deny-reason or None) and an entry class that composes checks, reads the payload, and denies on first violation. Every entry script wraps `main()` in try/except with passthrough fallback so a bug never blocks an edit.

## no_memory

Blocks Claude from reading or writing to the auto-memory directory or any `MEMORY.md` file. The auto-memory system prompt directly contradicts CLAUDE.md; this hook makes CLAUDE.md win that conflict. Covers Write, Edit, NotebookEdit, Read, Glob, Grep, and Bash tool calls with per-matcher path extraction so content fields are never overblocked.

## required_reading

Forces Claude to Read required documents before touching a matching file. Uses a three-hook trio: PreToolUse denies until docs are read, PostToolUse observes Reads and writes per-session satisfaction flags, PreCompact clears flags on context compaction so docs are re-demanded.

Manifests live at `~/.claude/required-reads.json` (global) and `<project>/.claude/required-reads.json` (project-scoped). Discovery walks up from the edited file collecting manifests, then appends the global manifest last. Project rules can silence a global rule via `override`.

A rule carries zero or one match criterion via two mutually exclusive fields: `extension` (suffix test) or `filepath` (substring test). A rule with neither is a wildcard. Both on one rule is a validation error and the rule is skipped.

Reads of any manifest-listed target always passthrough regardless of other rules, breaking self-target deadlocks.

Satisfaction state is per-session flag files under `~/.claude/hooks-state/required-reads/<session_id>/`. PreCompact clears the session directory. A lazy 7-day sweep ages out ended sessions. A missing `read` target is a hard configuration error.

Path canonicalisation expands `~`, absolutises, replaces backslashes with forward slashes, and lowercases.

## git_safety

Denies all git write commands with an informative message listing allowed read-only commands. Also enforces `git mv` for tracked file moves by running `git ls-files` to detect when `mv` targets tracked content.

## bash_commands

Handles both allow and deny decisions for Bash tool calls. Deny checks run first (package managers, system ops, shell spawning, gh api, text manipulation, builtin tool bypass, taskkill), then the allow check auto-permits known-safe commands (echo, cp, mkdir, git diff, etc.) without prompting. Unknown commands pass through to the default permission mode. The command parser tokenises and splits on clause separators (`|`, `&&`, `||`, `;`), so piped commands are caught.

## Adding a new rule

1. Identify which domain the rule belongs to.
2. Add a static check method to that domain's rule-checks class.
3. Register it in the entry class's tuple.
4. Add unit tests covering both block and pass cases.
5. Add a subprocess test.

## Adding a new domain

1. Create `<domain>/` with `__init__.py` and entry script(s).
2. Add `hooks.PreToolUse` entries to `~/.claude/settings.json`.
3. Create `tests/<domain>/` with test files.

## Tests

Two layers: unit tests import rule classes directly, subprocess integration tests pipe payloads to entry scripts and assert on stdout JSON. Run from the repo root:

```sh
./hooks/test_hooks.sh       # unix/mac
pwsh ./hooks/test_hooks.ps1 # windows
```

## Windows

Hook commands resolve through Git Bash via `CLAUDE_CODE_GIT_BASH_PATH`. Hook stdin is raw bytes; entry scripts read from `sys.stdin.buffer` and pass bytes to `json.loads` for encoding auto-detection, bypassing the Windows cp1252 text-mode default.
