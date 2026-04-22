# ai-common

> Shared Claude Code configuration pulled out of `~/.claude/` so it can iterate under version control.

## Contents

| Path | Purpose |
|---|---|
| [./hooks/](./hooks/) | PreToolUse Python hooks that enforce `~/.claude/CLAUDE.md` rules at tool-call time |
| [./styleguides/](./styleguides/) | Language style guides referenced from `~/.claude/CLAUDE.md` |

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
      }
    ]
  }
}
```

Absolute paths are mandatory because the scripts live outside `~/.claude/`. Renaming or moving any entry script requires a matching edit here.

On Windows, `CLAUDE_CODE_GIT_BASH_PATH` is set so the harness resolves `bash` to Git Bash rather than WSL. See [./hooks/hooks.md](./hooks/hooks.md) for the stdin encoding constraint that depends on this.

### `~/.claude/CLAUDE.md`

The Style Guides table links each guide by home-relative path so the reader has one click to the full rules.

```markdown
| Doc | When to read |
|---|---|
| [~/Dev/ai-common/styleguides/javascript.md](~/Dev/ai-common/styleguides/javascript.md) | Editing any `.js` or `.css` file |
| [~/Dev/ai-common/styleguides/markdown.md](~/Dev/ai-common/styleguides/markdown.md) | Editing any `.md` file |
| [~/Dev/ai-common/styleguides/python.md](~/Dev/ai-common/styleguides/python.md) | Editing any `.py` file |
| [~/Dev/ai-common/styleguides/scripts.md](~/Dev/ai-common/styleguides/scripts.md) | Editing any `.sh` or `.ps1` file |
```

## Tests

The hooks ship with a unittest suite covering every rule check and each entry script end-to-end.

```sh
./hooks/test_hooks.sh       # unix
pwsh ./hooks/test_hooks.ps1 # windows
```

Run from the repo root. The runners `cd` into `./hooks/` and invoke `python -m unittest discover tests/`. They intentionally do not walk up to the repo root (see the self-contained exception in [./styleguides/scripts.md](./styleguides/scripts.md)). The allowlist in [./.claude/settings.json](./.claude/settings.json) matches these exact command forms so Claude Code can run them without a permission prompt.
