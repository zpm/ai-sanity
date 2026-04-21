# Claude Code PreToolUse Hooks

> Enforces the rules in `~/.claude/CLAUDE.md` at tool-call time.

## Purpose

CLAUDE.md is guidance only: Claude reads it but the harness does not enforce it. Rules drift across long sessions, into subagents, and especially when another system prompt directly contradicts CLAUDE.md (the auto-memory system instructs Claude to write to a directory CLAUDE.md forbids). The PreToolUse hook contract lets a script inspect each tool call before it runs and deny outright with a message Claude reads back. Every CLAUDE.md rule that maps cleanly onto a deterministic, programmatic check lives here.

## Defense-in-depth: where to put each rule

`settings.json` deny rules are the primary enforcement layer and hold every rule that can be cleanly expressed as a glob match on the command string. That covers the obvious cases: every `*` install (pip install, npm install, uv pip install, python -m pip install, etc.), every git write subcommand (push, pull, fetch, merge, clone, gc, init, filter-branch, am, update-ref, etc.), every shell-out tool that should be replaced by a built-in (cat, grep, find, sed, awk).

The hooks are downstream and exist for two specific reasons:

- Coverage of cases `settings.json` globs cannot express. Examples: the dynamic `git ls-files` check on `mv` (depends on the runtime state of the repo), the content scan for em dashes (looks inside the new content payload, not at any glob-shaped command surface), the auto-memory directory path discrimination (path is dynamic per project), and mixed-mode git subcommand discrimination where the same subcommand has both read and write forms separated by positional vs flag argument structure (`git branch -v` is read but `git branch foo` is write).
- More nuance on allowed commands. For some mixed-mode subcommands, a broad `settings.json` deny would block legitimate read forms (`Bash(git tag *)` would block `git tag -l`, `Bash(git stash *)` would block `git stash list`). Removing the broad deny and adding hook discrimination carves out the specific safe forms while still blocking the writes.

Hook code should never duplicate logic that `settings.json` already handles. If a command is an obvious write or install that a glob can match, it belongs in `settings.json`, not in a hook check. Adding hook code that mirrors a `settings.json` deny is wasted work because the deny fires first regardless.

## Architecture

One entry script per Claude Code tool matcher. Each entry script holds a rule-checks class (the static methods) and an entry class (composes the checks in declaration order, runs them against the payload, denies on the first violation). The underscore-prefixed `_lib.py` is an imported helper module never executed directly; it holds the stdin/stdout protocol helpers and any low-level checkers shared across matchers.

A check method takes the full PreToolUse payload dict and returns either a string deny-reason on violation or None to pass. The deny-reason string must name the violated CLAUDE.md rule verbatim and tell Claude what to do instead, so Claude self-corrects without needing to re-read CLAUDE.md.

## Naming conventions

| Element | Convention |
|---|---|
| Entry script | `pretooluse_<matcher>.py` where `<matcher>` is the tool family name (write, bash, read) |
| Rule-checks class | `PreToolUse<Matcher>RuleChecks` |
| Entry class | `PreToolUse<Matcher>HookEntry` |
| Check method | `check_<rule_name>`, returning a deny-reason string or None |
| Shared helper class | Lives in `_lib.py`, named for what it checks rather than for which matchers use it |

## Adding a new rule

1. Identify which matcher the rule applies to.
2. Add a `check_<rule>` static method to that matcher's rule-checks class.
3. Register it in the entry class's tuple of methods to run, ordered so the most specific check fires first (it produces the most useful deny message).
4. Add unit tests covering both block and pass cases, including edge cases such as wrapper invocations, malformed inputs, and false-positive temptations (content fields that contain path-like substrings but are not paths).
5. Add a subprocess test so the wiring is covered too.
6. If the rule has a `settings.json` glob equivalent, leave the existing deny rule in place. Defense in depth.

If the rule applies to more than one matcher, factor the comparison logic into a helper class in `_lib.py` and call it from each matcher-specific check. The matcher-specific check extracts the right field from the payload (file_path vs notebook_path vs tokenised command) so the helper only sees path-shaped strings, never arbitrary content fields.

## Adding a new matcher

1. Create `pretooluse_<matcher>.py` following the same two-class pattern.
2. Add a `hooks.PreToolUse` entry to `~/.claude/settings.json` with the matcher pattern and the python invocation.
3. Add subprocess tests for the new entry script.

## Tests

Two layers using stdlib `unittest`. Unit tests import the rule classes directly. Subprocess integration tests pipe a synthetic payload to the entry script and assert on stdout JSON and exit code. Run via `./test_hooks.sh` or `./test_hooks.ps1` from anywhere; both walk up to find the `.git` directory before running.

## Windows notes

Hook commands resolve through Git Bash, which Claude Code locates via the `CLAUDE_CODE_GIT_BASH_PATH` env var in `settings.json`. Without that env var, `bash` may resolve to WSL bash, which has a different filesystem view. The Python interpreter must be on the PATH that Git Bash sees; `python --version` confirms this. Use `py` instead of `python` in the `settings.json` command if `python` is not on PATH but the Windows launcher is.

Hook stdin is raw UTF-8 bytes from Claude Code, but Python text-mode stdin defaults to the Windows locale (cp1252) and silently mojibakes multi-byte characters before JSON parsing. Entry scripts and subprocess tests must use the raw byte stream with explicit UTF-8 decoding; text-mode IO or ASCII-escaped JSON serialisation hides the bug by keeping the wire payload ASCII-only.