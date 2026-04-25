# CLAUDE.md

## Tests

Run the hook suite through the wrapper scripts only. Do not invoke `python -m unittest` (or `pytest`, etc.) directly. The wrappers own platform setup (venv activation on future work, `cd` to the test directory, `ErrorActionPreference` on PowerShell) and keep that logic in one place.

| Platform | Command |
|---|---|
| Unix | `./test_hooks.sh` |
| Windows | `pwsh ./test_hooks.ps1` |

Run from the repo root.
