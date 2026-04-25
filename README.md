# ai-common

Shared claude hooks and style guides.

## no_memory

Blocks Claude from reading or writing to the auto-memory directory or any `MEMORY.md` file. Overrides the auto-memory system prompt so `CLAUDE.md` wins the conflict.

| File | Purpose |
|---|---|
| `hooks/no_memory/_checker.py` | `MemoryPathChecker` regex matcher for auto-memory directory and MEMORY.md paths |
| `hooks/no_memory/pretooluse_write.py` | PreToolUse entry for Write, Edit, NotebookEdit |
| `hooks/no_memory/pretooluse_bash.py` | PreToolUse entry for Bash (per-token memory path scan) |
| `hooks/no_memory/pretooluse_read.py` | PreToolUse entry for Read, Glob, Grep |

## required_reading

Forces Claude to Read required documents (style guides, CLAUDE.md, settings.json, project docs) before touching a matching file. Uses a three-hook setup: PreToolUse denies until docs are read, PostToolUse observes Reads and writes satisfaction flags, PreCompact clears flags on context compaction so docs are re-demanded.

| File | Purpose |
|---|---|
| `hooks/required_reading/_manifest.py` | Rule record type, path normalizer, manifest discovery and parsing |
| `hooks/required_reading/_state.py` | Per-session satisfaction flag management |
| `hooks/required_reading/pretooluse.py` | PreToolUse entry for Write, Edit, NotebookEdit, Read |
| `hooks/required_reading/posttooluse_observer.py` | PostToolUse entry for Read (writes satisfaction flags) |
| `hooks/required_reading/precompact.py` | PreCompact entry (clears satisfaction flags before compaction) |

Manifests live at `~/.claude/required-reads.json` (global) and `<project>/.claude/required-reads.json` (project-scoped). See [hooks/hooks.md](hooks/hooks.md) for schema.

## git_safety

Enforces `git mv` for tracked file moves. Rejects Bash `mv` commands when any source argument is tracked by git or is a directory containing tracked files.

| File | Purpose |
|---|---|
| `hooks/git_safety/pretooluse_bash.py` | PreToolUse entry for Bash (dynamic `git ls-files` check on `mv`) |

## Shared

| File | Purpose |
|---|---|
| `hooks/_hook_io.py` | Stdin/stdout protocol helpers for PreToolUse, PostToolUse, PreCompact payloads |
| `styleguides/` | Language style guides referenced from the required-reads manifest |

## Wiring

`~/.claude/settings.json` registers each hook by absolute path using `$HOME`. Moving or renaming any entry script requires a matching edit there. On Windows, `CLAUDE_CODE_GIT_BASH_PATH` must point to Git Bash so hook commands resolve correctly.

## Tests

```sh
./hooks/test_hooks.sh       # unix
pwsh ./hooks/test_hooks.ps1 # windows
```

Run from the repo root.
