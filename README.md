# ai-common

> Shared Claude Code configuration pulled out of `~/.claude/` so it can iterate under version control.

## Contents

| Path | Purpose |
|---|---|
| [./hooks/](./hooks/) | PreToolUse/PostToolUse/PreCompact Python hooks that enforce `~/.claude/CLAUDE.md` rules and required-reads at tool-call time |
| [./styleguides/](./styleguides/) | Language style guides referenced from the required-reads manifest |

The hooks and style guides live here rather than in `~/.claude/` because the claude harness does not track `~/.claude/` under git. Keeping them in a normal repo gives change history, tests, and cross-machine sync.

## Wiring

Two files in `~/.claude/` reference this repo by absolute path: `settings.json` registers the hooks, and `CLAUDE.md` links the style guides.

### `~/.claude/settings.json`

Each PreToolUse matcher points at the corresponding entry script in `./hooks/`. The `$HOME` variable resolves before the Python interpreter is invoked.

```json
{
  "env": {
    "CLAUDE_CODE_GIT_BASH_PATH": "C:\\Program Files\\Git\\bin\\bash.exe"
  },
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Write|Edit|NotebookEdit",
        "hooks": [
          {
            "type": "command",
            "command": "python $HOME/Dev/ai-common/hooks/pretooluse_write.py"
          }
        ]
      },
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "python $HOME/Dev/ai-common/hooks/pretooluse_bash.py"
          }
        ]
      },
      {
        "matcher": "Read|Glob|Grep",
        "hooks": [
          {
            "type": "command",
            "command": "python $HOME/Dev/ai-common/hooks/pretooluse_read.py"
          }
        ]
      },
      {
        "matcher": "Write|Edit|NotebookEdit",
        "hooks": [
          {
            "type": "command",
            "command": "python $HOME/Dev/ai-common/hooks/pretooluse_required_reads.py"
          }
        ]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Read",
        "hooks": [
          {
            "type": "command",
            "command": "python $HOME/Dev/ai-common/hooks/posttooluse_read_observer.py"
          }
        ]
      }
    ],
    "PreCompact": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python $HOME/Dev/ai-common/hooks/precompact_required_reads.py"
          }
        ]
      }
    ]
  }
}
```

Absolute paths are mandatory because the scripts live outside `~/.claude/`. Renaming or moving any entry script requires a matching edit here. The required-reads trio is a sibling of the existing `Write|Edit|NotebookEdit` entry, not a replacement; the harness runs both in parallel and the first to deny wins.

On Windows, `CLAUDE_CODE_GIT_BASH_PATH` is set so the harness resolves `bash` to Git Bash rather than WSL. See [./hooks/hooks.md](./hooks/hooks.md) for the stdin encoding constraint that depends on this.

### `~/.claude/CLAUDE.md`

The `Required Reads` section points readers at the manifest rather than enumerating rules. The manifest is the source of truth; the prose here just tells the model what to do when a required-read deny fires.

```markdown
# Required Reads

Style guides and other mandatory context are enforced by a PreToolUse hook. The source of truth is the global `~/.claude/required-reads.json` plus any per-project `.claude/required-reads.json` discovered by walking up from the edited file. Every rule denies the edit until Claude has Read the target doc in the current session. When a deny fires, Read the cited docs and retry. Do not ask the user to disable the hook. A missing `read` target is a hard configuration error, not an escape hatch.
```

### `~/.claude/required-reads.json`

The global manifest maps file-path globs to documents Claude must have in context before editing. It lives in `~/.claude/` (not in this repo) because the targets it references are user-configurable and machine-specific. Project-scoped manifests live at `<project>/.claude/required-reads.json` and layer on top via walk-up discovery. Relative `read` paths in a project manifest resolve against the project root (the parent of `.claude/`), not against the manifest directory. See [./hooks/hooks.md](./hooks/hooks.md) for the manifest schema and state-directory location.

## Tests

The hooks ship with a unittest suite covering every rule check and each entry script end-to-end.

```sh
./hooks/test_hooks.sh       # unix
pwsh ./hooks/test_hooks.ps1 # windows
```

Run from the repo root. The runners `cd` into `./hooks/` and invoke `python -m unittest discover tests/`. They intentionally do not walk up to the repo root (see the self-contained exception in [./styleguides/scripts.md](./styleguides/scripts.md)). The allowlist in [./.claude/settings.json](./.claude/settings.json) matches these exact command forms so Claude Code can run them without a permission prompt.
