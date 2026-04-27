# ai-sanity

Shared Claude Code hooks and style guides.

## Purpose

`./CLAUDE.md` is guidance claude reads but does not enforce, especially since Opus 4.7.

Every rule that can be a programmatic check lives here instead to force claude into compliance.

## Setup

Copy [./settings.example.json](settings.example.json) to `~/.claude/settings.json` and adjust paths.

The `permissions.allow` list should include the path to this repo (e.g., `Read(~/Dev/ai-sanity/**)`) so the required-reading hook can load styleguides from this repo without prompting.

## 1. Bash Safety

Keeps claude from invoking dangerous shell commands, auto-allows the safe ones it commonly uses, and auto-allows commands listed in a project's playbook.

Works by implementing a deny-list for dangerous shell commands (git writes, package managers, system ops, shell spawning, text manipulation). Commands matching a project's `./.ai-sanity/playbook.json` bypass all deny checks. Unknown commands pass through to Claude Code's normal permission UI.

### Security Rules

The threat model is "keep claude from doing stupid shit," not "protect against nation-state actors." These hooks catch the mistakes claude commonly makes, not crafted bypass attempts. The command parser handles well-formed, whitespace-separated commands because that is what claude produces. Commands outside that shape are not part of the safety guarantee.

1. All changes must show up in git. claude can freely use the Edit tool because those changes appear in the diff. Destructive commands (`git push`, `git reset`, `rm`) and environment-mutating commands (`pip install`, `npm install`, `brew install`) leave no trace in the diff, so they are denied or deferred to the user.
2. No third-party code execution without the user in the loop. Package installs, shell spawning, and running downloaded scripts all require explicit user approval. claude should never silently pull in or execute code the user hasn't reviewed.
3. File edits are not the concern, as claude already has elevated Edit permissions. The hooks protect against unintentional catastrophes and invisible side effects.

### Playbook

Commands matching a project's `./.ai-sanity/playbook.json` bypass all deny checks. The full command is tokenized and matched against playbook entries (exact or prefix). If it's in the playbook, it's allowed, including commands with `&&`, pipes, redirects, or any other shell syntax.

Each project that wants playbook support creates `./.ai-sanity/playbook.json`:

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

## 2. No Memory

Prevents claude from using its built-in auto-memory system, as it sits outside version control.

Works by blocking reads and writes to the auto-memory directory and any `MEMORY.md` file.

## 3a. Required Reading

Makes claude read project documentation and style guides before it can edit matching files.

Works by forcing claude to Read specified documents before it can touch matching files. The manifest filename is `./.ai-sanity/required-reading.json` in all repos.

| File | Required | Notes |
|---|---|---|
| `./.ai-sanity/required-reading.json` | No | If present, its rules are loaded via directory walk-up from the edited file. If absent, silently skipped. |
| Any doc listed in that manifest | Yes | If the manifest exists and lists a doc, that doc must exist on disk. A missing target is a configuration error and blocks the edit. |

## 3b. Required Styleguides

Make claude read global styleguides contained in this repo before it can edit matching files.

Ships a global set of style guides that claude must read before editing files of a given type. The global manifest (`./.ai-sanity/required-styleguides.json`) maps file extensions to styleguides in `./styleguides/`. Any project that uses ai-sanity gets these enforced automatically.

| File | Required | Notes |
|---|---|---|
| `./.ai-sanity/required-styleguides.json` | Yes | Always loaded. Contains extension-to-styleguide mappings. |

The global manifest is always present because it ships with this repo. Its styleguide targets are required.

## Tests

Run from the repo root:

```sh
python -m unittest discover -s tests -t . -v
```

An important test is [./tests/command_tests.json](tests/command_tests.json). It is the e2e black-box test suite for bash_safety. Every entry runs the full hook entry script as a subprocess and asserts the outcome. It does not care about internal implementation; it matches opaque behavior against real commands seen in the wild. Every entry must be a syntactically valid shell command.

If you encounter a new command in the wild that should be allowed, denied, or passed through, add it here to ensure behavior never regresses:

```json
{
    "allow": ["git status", "..."],
    "deny":  ["pip install requests", "..."],
    "ask":   ["ls -la", "..."]
}
```

Each list is alphabetized (case-insensitive). A test enforces this; add new entries in sorted order.

`allow` = hook auto-approves. `deny` = hook hard-blocks. `ask` = falls through to claude code's normal permission prompt.

Remaining tests cover cases that need filesystem fixtures (temp git repos for tracked-file detection, temp playbook files, required-reading manifests), malformed input (empty strings, unbalanced quotes), or non-command logic (the shell command parser).
