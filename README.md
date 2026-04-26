# ai-sanity

Shared Claude Code hooks and style guides.

## Purpose

CLAUDE.md is guidance Claude reads but does not enforce, especially since Opus 4.7.

Every rule that can be a programmatic check lives here instead to force Claude into compliance.

## Setup

Copy [./settings.example.json](./settings.example.json) to `~/.claude/settings.json` and adjust paths.

The `permissions.allow` list should include the path to this repo (e.g., `Read(~/Dev/ai-sanity/**)`) so the required-reading hook can load styleguides from this repo without prompting.

## Required Reading

The `required_reading` hook forces Claude to Read specified documents before it can touch matching files.

The manifest filename is `.ai-sanity/required-reading.json` in all repos. Discovery checks two sources in order: the `ai-sanity` global list, and then project walk-up.

### Project repo (any repo Claude is working in)

| File | Required | Notes |
|---|---|---|
| `.ai-sanity/required-reading.json` | No | If present, its rules are loaded via directory walk-up from the edited file. If absent, silently skipped. |
| Any doc listed in that manifest | Yes | If the manifest exists and lists a doc, that doc must exist on disk. A missing target is a configuration error and blocks the edit. |

A project opts into required reading by creating `.ai-sanity/required-reading.json`. Once it does, every doc it references must be present. This is intentional: a project that declares a requirement and then deletes the target has a broken config, and silent degradation would bypass enforcement.

### This repo (ai-sanity)

| File | Required | Notes |
|---|---|---|
| `.ai-sanity/required-reading.global.json` | Yes | Always loaded. Contains extension-to-styleguide mappings. |
| `.ai-sanity/required-reading.json` | No | Project-level manifest for this repo. Currently requires `./README.md`. |

The global manifest is always present because it ships with this repo. Its styleguide targets are required.

## Playbook

The `playbook` hook auto-whitelists bash commands listed in a project's `.ai-sanity/playbook.json`. The first clause of a command is matched against playbook entries (exact or prefix). Pipes to safe output-filtering commands (`tail`, `head`, `grep`, `cat`, `wc`, `sort`, `uniq`, `tr`, `cut`, `column`) and descriptor merges (`2>&1`) are allowed. Sequential operators (`&&`, `||`, `;`) and file redirects (`>`, `<`) cause passthrough to normal permissions.

Each project that wants playbook support creates `.ai-sanity/playbook.json`:

```json
[
  {
    "bash": "python -m unittest discover -s tests -t . -v",
    "what": "Runs the full test suite",
    "when": "Run as a final step after all changes have landed"
  },
  {
    "bash": "python -m unittest *",
    "what": "Run targeted tests for a specific module",
    "when": "After modifying a specific hook, run its targeted tests"
  }
]
```

A trailing ` *` in the `bash` field enables prefix matching (token-level, not string). Without it, the match is exact.

To inject the playbook into Claude's context before file operations, add it to the project's `.ai-sanity/required-reading.json`.

## Permission Model

Hooks participate in a three-outcome decision chain:

| Outcome | Source | Effect |
|---|---|---|
| deny | bash_safety | Hard block. The command is rejected and Claude cannot proceed. |
| passthrough | bash_safety (default) | No opinion. Falls back to Claude Code's normal permission/prompt UI, where the user approves or rejects. |
| allow | playbook | Bypasses the normal permission prompt entirely. The command runs without user interaction. |

Execution order matters: bash_safety deny checks run before playbook allow checks, so a denied command can never be auto-allowed by the playbook.

## Other Hooks

- `bash_safety`: Deny-list for dangerous shell commands (git writes, package managers, system ops, shell spawning, text manipulation). Enforces `git mv` for tracked file moves. Unknown commands pass through to Claude Code's normal permission UI.
- `no_memory`: Blocks Claude from reading or writing to the auto-memory directory or any `MEMORY.md` file.

## Tests

Run from the repo root:

```sh
python -m unittest discover -s tests -t . -v
```

The primary test artifact is [./tests/command_tests.json](tests/command_tests.json). It is the e2e test suite for bash_safety: every entry runs the full hook entry script as a subprocess and asserts the outcome. When you encounter a new command in the wild that should be allowed, denied, or passed through, add it to the appropriate list.

```json
{
    "allow": ["git status", "..."],
    "deny":  ["pip install requests", "..."],
    "ask":   ["ls -la", "..."]
}
```

`allow` = hook auto-approves. `deny` = hook hard-blocks. `ask` = hook has no opinion, falls through to Claude Code's normal permission prompt.

Remaining hand-written tests cover cases that need filesystem fixtures (temp git repos for tracked-file detection, temp playbook files, required-reading manifests) or test non-command logic (the shell command parser).
