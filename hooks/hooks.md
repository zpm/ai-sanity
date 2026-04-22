# Claude Code Hooks

> Enforces the rules in `~/.claude/CLAUDE.md` at tool-call time.

## Purpose

CLAUDE.md is guidance only: Claude reads it but the harness does not enforce it. Rules drift across long sessions, into subagents, and especially when another system prompt directly contradicts CLAUDE.md (the auto-memory system instructs Claude to write to a directory CLAUDE.md forbids). The PreToolUse hook contract lets a script inspect each tool call before it runs and deny outright with a message Claude reads back. Every CLAUDE.md rule that maps cleanly onto a deterministic, programmatic check lives here.

## Wiring

These scripts live outside `~/.claude/` so they can iterate under version control. They run because `~/.claude/settings.json` references them by absolute path (`$HOME/Dev/ai-common/hooks/pretooluse_*.py`). Moving or renaming any entry script requires updating `settings.json` to match. See the repo `README.md` for the installation pattern.

## Defense-in-depth: where to put each rule

`settings.json` deny rules are the primary enforcement layer and hold every rule that can be cleanly expressed as a glob match on the command string. That covers the obvious cases: every `*` install (pip install, npm install, uv pip install, python -m pip install, etc.), every git write subcommand (push, pull, fetch, merge, clone, gc, init, filter-branch, am, update-ref, etc.), every shell-out tool that should be replaced by a built-in (cat, grep, find, sed, awk).

The hooks are downstream and exist for two specific reasons:

- Coverage of cases `settings.json` globs cannot express. Examples: the dynamic `git ls-files` check on `mv` (depends on the runtime state of the repo), the content scan for em dashes (looks inside the new content payload, not at any glob-shaped command surface), the auto-memory directory path discrimination (path is dynamic per project), and mixed-mode git subcommand discrimination where the same subcommand has both read and write forms separated by positional vs flag argument structure (`git branch -v` is read but `git branch foo` is write).
- More nuance on allowed commands. For some mixed-mode subcommands, a broad `settings.json` deny would block legitimate read forms (`Bash(git tag *)` would block `git tag -l`, `Bash(git stash *)` would block `git stash list`). Removing the broad deny and adding hook discrimination carves out the specific safe forms while still blocking the writes.

Hook code should never duplicate logic that `settings.json` already handles. If a command is an obvious write or install that a glob can match, it belongs in `settings.json`, not in a hook check. Adding hook code that mirrors a `settings.json` deny is wasted work because the deny fires first regardless.

## Architecture

One entry script per Claude Code tool matcher. Each entry script holds a rule-checks class (the static methods) and an entry class (composes the checks in declaration order, runs them against the payload, denies on the first violation). The underscore-prefixed `_lib.py` is an imported helper module never executed directly; it holds the stdin/stdout protocol helpers and any low-level checkers shared across matchers.

A check method takes the full PreToolUse payload dict and returns either a string deny-reason on violation or None to pass. The deny-reason string must name the violated CLAUDE.md rule verbatim and tell Claude what to do instead, so Claude self-corrects without needing to re-read CLAUDE.md.

PostToolUse and PreCompact hooks follow the same two-class entry shape but emit no decision envelope. PostToolUse observes a completed tool call and writes external state if warranted (the required-reads Read observer is the in-repo example). PreCompact fires before context compaction and is used to reset per-session state so required reads are re-demanded after compaction. Neither event can block its originating action.

## Required-reads enforcement

The required-reads hook trio forces Claude to have specific documents (style guides, CLAUDE.md, settings.json, per-project docs) in context before modifying matching files. The PreToolUse enforcer lives at `./pretooluse_required_reads.py`, the PostToolUse Read observer at `./posttooluse_read_observer.py`, and the PreCompact state reset at `./precompact_required_reads.py`.

The manifest is a JSON file named `required-reads.json`. Discovery walks up from the edited file collecting any `./.claude/required-reads.json` encountered, then appends the global `~/.claude/required-reads.json` last. Project rules can silence a global rule by naming the global rule's `read` target in an `override` field; only project rules may override.

Every rule is block. An unsatisfied matched rule denies the edit until Claude Reads the target doc in the current session, batched into a single deny envelope listing every unsatisfied target so Claude can Read them all in one round and retry once. There is no inject mode; the previous two-mode design was dropped because the whole point of the feature is forcing the docs into the transcript rather than hiding them behind injected context that the model may or may not weight correctly.

Relative `read` paths in a manifest resolve against the project root (the directory that contains the `.claude/` subdirectory), not against the manifest's own directory. A project manifest at `<project>/.claude/required-reads.json` writes `./CLAUDE.md` to mean `<project>/CLAUDE.md` and `./.claude/settings.json` to mean `<project>/.claude/settings.json`.

Satisfaction state is per-session flag files under `~/.claude/hooks-state/required-reads/<session_id>/`, named `<sha1(dedupe_key)>.flag`. The default dedupe key is the normalised `read` target so rules pointing at the same doc share one satisfaction check. PreCompact removes the session subdirectory so required reads are re-demanded after compaction. A lazy 7-day sweep on PreToolUse entry ages out ended-session subdirectories.

A missing `read` target is a hard configuration error, not a soft failure. Any matched rule whose target does not exist on disk produces a dedicated config-error deny that refuses to proceed until the setup is fixed; there is no skip-if-missing escape hatch, because that would let a broken enforcement setup silently bypass the required reads.

Path canonicalisation in `_lib.py` expands `~`, absolutises, replaces backslashes with forward slashes, and lowercases the whole string. Universal lowercasing handles Windows filesystem case-insensitivity (Claude may call Read with `c:\...` while the manifest normalises to `C:\...`) at the cost of a theoretical Posix collision between files that differ only in case, which does not occur for documentation paths in practice.

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

Two layers using stdlib `unittest`. Unit tests import the rule classes directly. Subprocess integration tests pipe a synthetic payload to the entry script and assert on stdout JSON and exit code. Run via the repo-root wrappers: see the [repo README](../README.md) for commands. The wrappers `cd` into `hooks/` and hand off to `unittest discover tests/`.

## Windows notes

Hook commands resolve through Git Bash, which Claude Code locates via the `CLAUDE_CODE_GIT_BASH_PATH` env var in `settings.json`. Without that env var, `bash` may resolve to WSL bash, which has a different filesystem view. The Python interpreter must be on the PATH that Git Bash sees; `python --version` confirms this. Use `py` instead of `python` in the `settings.json` command if `python` is not on PATH but the Windows launcher is.

Hook stdin is raw UTF-8 bytes from Claude Code, but Python text-mode stdin defaults to the Windows locale (cp1252) and silently mojibakes multi-byte characters before JSON parsing. Entry scripts and subprocess tests must use the raw byte stream with explicit UTF-8 decoding; text-mode IO or ASCII-escaped JSON serialisation hides the bug by keeping the wire payload ASCII-only.