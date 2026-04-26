# ai-sanity

Shared Claude Code hooks and style guides.

## Purpose

CLAUDE.md is guidance Claude reads but does not enforce, especially since Opus 4.7.

Every rule that can be a programmatic check lives here instead to force Claude into compliance.

## Setup

Copy [./settings.example.json](./settings.example.json) to `~/.claude/settings.json` and adjust paths.

On Windows, `CLAUDE_CODE_GIT_BASH_PATH` must point to Git Bash (which it should by default).

## Hooks

- `bash_commands`: Deny-list for dangerous shell commands (package managers, system ops, shell spawning) and allow-list for safe ones (echo, cp, mkdir). Unknown commands fall through to the default permission mode.
- `git_safety`: Restricts Claude to read-only git commands and enforces `git mv` for tracked file moves.
- `no_memory`: Blocks Claude from reading or writing to the auto-memory directory or any `MEMORY.md` file, enforcing the CLAUDE.md preference for version-controlled persistence.
- `required_reading`: Forces Claude to Read specified documents before it can touch matching files. Rules are declared in `~/.claude/required-reads.json` (global) and `<project>/.claude/required-reads.json` (project-scoped).

## Tests

Run from the repo root:

```sh
./test_hooks.sh         # unix/mac
pwsh ./test_hooks.ps1   # windows
```
