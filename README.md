# ai-sanity

Shared Claude Code hooks and style guides.

## Purpose

`./CLAUDE.md` is guidance claude reads but does not enforce. Especially since Anthropic nerfed Opus 4.6 and then trainwrecked Opus 4.7.

So... every rule that can be a programmatic check lives here instead to force claude into compliance.

Built for Claude Code in VS Code on Windows and macOS. Hooks may behave differently in other contexts (terminal CLI, other IDEs, other platforms), wouldn't know, haven't tested.

## Fail Closed

All hooks fail closed. If a hook crashes for any reason, the tool call is denied with the error message, not silently passed through. A bug in a hook must be loud and visible so it gets fixed.

## Setup

Copy [./settings.example.json](settings.example.json) to `~/.claude/settings.json` and adjust paths.

The `permissions.allow` list should include the path to this repo (e.g., `Read(~/Dev/ai-sanity/**)`) so the required-reading hook can load styleguides from this repo without prompting.

## 1. Bash Playbook

Keeps claude from invoking dangerous shell commands, auto-allows the safe ones it commonly uses, and auto-allows commands listed in a project's playbook.

Works by implementing a deny-list for dangerous shell commands (git writes, package managers, system ops, shell spawning, text manipulation). Commands matching a project's `./.ai-sanity/playbook.json` are auto-allowed. Unknown commands pass through to Claude Code's normal permission UI.

### Security Model

The threat model is "keep claude from doing stupid shit," not "protect against nation-state actors." These hooks catch the mistakes claude commonly makes, not crafted bypass attempts. The command parser handles well-formed, whitespace-separated commands because that is what claude produces. Commands outside that shape are not part of the safety guarantee.

The rough goals of the rules are:

1. All changes must show up in git. claude can freely use the Edit tool because those changes appear in the diff. Destructive commands (`git push`, `git reset`, `rm`) and environment-mutating commands (`pip install`, `npm install`, `brew install`) leave no trace in the diff, so they are denied or deferred to the user.

2. No third-party code execution without the user in the loop. Package installs, shell spawning, and running downloaded scripts all require explicit user approval. claude should never silently pull in or execute code the user hasn't reviewed.

3. File edits are not a concern, as claude already has general edit permissions.

Deny checks compose in a fixed order. The raw-path checks (Windows backslash paths, tilde paths) run first on the unparsed command and are absolute: that syntax would corrupt the hook's own tokenizer and path matching, so no playbook entry bypasses them. Every other check runs per-segment after the playbook match, so a playbook entry bypasses it. A check earns absolute status only when the syntax it catches breaks the hook's parsing; otherwise it belongs in the per-segment pipeline.

### Playbook

The playbook is a per-project registry of entrypoint commands (test runners, build scripts, task scripts) that claude runs to do common tasks. A command matching `./.ai-sanity/playbook.json` is auto-allowed, bypassing every deny check except the absolute raw-path checks above. The command is tokenized and matched against playbook entries (exact or prefix). If claude submits a compound command, the compounded part is evaluated independently against the bash rules.

Each project that wants playbook support creates `./.ai-sanity/playbook.json`. It includes metadata to help Claude understand when to run the commands:

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

A `*/` prefix on any token marks it as a path relative to the project root (the directory containing `.ai-sanity/playbook.json`). At match time, both the entry path and the command path are resolved to absolute paths via `os.path.realpath` and compared. This allows scripts to match regardless of the working directory or relative path used to invoke them. `*/` can appear on any token position (e.g., `*/server/scripts/test.sh *` or `pwsh */server/scripts/test.ps1 *`).

## 2. No Questions

Blocks the `AskUserQuestion` tool so claude asks questions in plain chat text instead of rendering interactive dialog widgets.

Works by unconditionally denying any `AskUserQuestion` tool call with a message redirecting claude to use plain text.

## 3. No Memory

Prevents claude from using its built-in auto-memory system, as it sits outside version control.

Works by blocking reads and writes to the auto-memory directory and any `MEMORY.md` file.

## 4a. Required Reading

Makes claude read project documentation and style guides before it can edit matching files.

Works by forcing claude to Read specified documents before it can touch matching files. The manifest filename is `./.ai-sanity/required-reading.json` in all repos.

| File | Required | Notes |
|---|---|---|
| `./.ai-sanity/required-reading.json` | No | If present, its rules are loaded via directory walk-up from the edited file. If absent, silently skipped. |
| Any doc listed in that manifest | Yes | If the manifest exists and lists a doc, that doc must exist on disk. A missing target is a configuration error and blocks the edit. |

## 4b. Required Styleguides

Make claude read global styleguides contained in this repo before it can edit matching files.

Ships a global set of style guides that claude must read before editing files of a given type. The global manifest (`./.ai-sanity/required-styleguides.json`) maps file extensions to styleguides in `./styleguides/`. Any project that uses ai-sanity gets these enforced automatically.

Note that these are my personal styles. They are not idiomatic, and if you're copying this repo, you'll probably want to delete this hook or update the styles to match your own.

| File | Required | Notes |
|---|---|---|
| `./.ai-sanity/required-styleguides.json` | Yes | Always loaded. Contains extension-to-styleguide mappings. |

The global manifest is always present because it ships with this repo. Its styleguide targets are required.

## 5. Instruction Repeater

Injects a fixed instruction message into context on the first user message of each conversation, then goes silent until compaction resets it.

Works by handling `UserPromptSubmit` to check a per-session flag file. On first fire (no flag), it writes the instruction text to stdout (which Claude Code injects as visible context) and sets the flag. On subsequent fires (flag exists), it emits nothing. A `PreCompact` handler clears the flag so the instruction is re-injected after context compaction.

## 6. Context Alarm

Warns the user in chat when context exceeds a token threshold so they can manually run `/compact` at a natural stopping point.

Works by handling `UserPromptSubmit` to read the transcript JSONL file and extract the total context token count from the most recent assistant message. If the count exceeds the threshold (200k tokens), it injects a system reminder instructing claude to relay the warning to the user. Fires on every turn the context is over the limit.

## Tests

Run from the repo root:

```sh
python -m unittest discover -s tests -t . -v
```

An important test is [./tests/command_tests.json](tests/command_tests.json). It is the e2e black-box test suite for bash_safety. Every entry runs the full hook entry script as a subprocess and asserts the outcome. It does not care about internal implementation; it matches opaque behavior against real commands seen in the wild. Every entry must be a syntactically valid shell command. If you encounter a new command in the wild that should be allowed, denied, or passed through, add it here to ensure behavior never regresses.

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
