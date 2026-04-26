# ai-sanity

Shared Claude Code hooks and style guides.

## Purpose

CLAUDE.md is guidance Claude reads but does not enforce, especially since Opus 4.7.

Every rule that can be a programmatic check lives here instead to force Claude into compliance.

## Setup

Copy [./settings.example.json](./settings.example.json) to `~/.claude/settings.json` and adjust paths.

On Windows, `CLAUDE_CODE_GIT_BASH_PATH` must point to Git Bash (which it should by default).

## Required Reading

The `required_reading` hook forces Claude to Read specified documents before it can touch matching files.

The manifest filename is `.claude/required-reading.json` in all repos, including `~/.claude/`. Discovery checks three sources in order: hooks-repo global, `~/.claude/`, then project walk-up.

### `~/.claude/` (user home)

| File | Required | Notes |
|---|---|---|
| `~/.claude/required-reading.json` | No | Hardcoded path, always checked. If absent, silently skipped. Not discovered via walk-up. |

`~/.claude/` is a hardcoded location, not a project directory. The walk-up stops before reaching `$HOME`. Any rule that points at a missing file under `~/.claude/` is silently dropped because the user may not have created it. This applies regardless of which manifest declared the rule.

### Project repo (any repo Claude is working in)

| File | Required | Notes |
|---|---|---|
| `.claude/required-reading.json` | No | If present, its rules are loaded via directory walk-up from the edited file. If absent, silently skipped. |
| Any doc listed in that manifest | Yes | If the manifest exists and lists a doc, that doc must exist on disk. A missing target is a configuration error and blocks the edit. |

A project opts into required reading by creating `.claude/required-reading.json`. Once it does, every doc it references must be present. This is intentional: a project that declares a requirement and then deletes the target has a broken config, and silent degradation would bypass enforcement.

### This repo (ai-sanity)

| File | Required | Notes |
|---|---|---|
| `.claude/required-reading.global.json` | Yes | Always loaded. Contains global wildcard rules and extension-to-styleguide mappings. |
| `.claude/required-reading.json` | No | Project-level manifest for this repo. Currently requires `./README.md`. |

The global manifest is always present because it ships with this repo. Its styleguide targets are required.

## Other Hooks

- `bash_commands`: Deny-list for dangerous shell commands (package managers, system ops, shell spawning) and allow-list for safe ones (echo, cp, mkdir). Unknown commands fall through to the default permission mode.
- `git_safety`: Restricts Claude to read-only git commands and enforces `git mv` for tracked file moves.
- `no_memory`: Blocks Claude from reading or writing to the auto-memory directory or any `MEMORY.md` file, enforcing the CLAUDE.md preference for version-controlled persistence.

## Tests

Run from the repo root:

```sh
./test_hooks.sh         # unix/mac
pwsh ./test_hooks.ps1   # windows
```
