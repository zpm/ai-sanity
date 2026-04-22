# CLAUDE.md

You MUST read `~/.claude/CLAUDE.md` for user-level instructions that apply across all projects.

## Only use allowed commands

You MUST only use commands from the `allow` key in `settings.json`. All other usage will be denied.

| Doc |
|---|
| [`~/.claude/settings.json`](~/.claude/settings.json) |
| [./.claude/settings.json](./.claude/settings.json) |

## Tests

Run the hook suite through the wrapper scripts only. Do not invoke `python -m unittest` (or `pytest`, etc.) directly. The wrappers own platform setup (venv activation on future work, `cd` to the test directory, `ErrorActionPreference` on PowerShell) and keep that logic in one place.

| Platform | Command |
|---|---|
| Unix | `./hooks/test_hooks.sh` |
| Windows | `pwsh ./hooks/test_hooks.ps1` |

Run from the repo root.
