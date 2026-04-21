# Shell Scripts Style Guide

> Covers shell script conventions across ALL PROJECTS.

## Structure

Non-trivial logic lives in a shared `.py` file, or in the wrapped tool call itself (`pytest`, `npm test`, etc.).

`.ps1` and `.sh` are parallel per-platform entry points; each is natively written for its platform and neither delegates to the other. Both `.ps1` and `.sh` always exist, even when the body is a one-liner. Their role is limited to platform-specific setup (venv activation, system locks on test sentinel files, etc.) before handing off to the `.py` or tool command. Any shared logic that can live in the common call must live there. The shell scripts should hand off to Python or the tool command as early as possible.

Venv paths are the canonical case for per-platform scripts:
- Windows: `venv\Scripts\Activate.ps1`
- Unix: `venv/bin/activate`

A `.ps1` whose body invokes `bash.exe` on the sibling `.sh` is not allowed.

## Finding the Project Root

Scripts must work when invoked from any working directory. All path references use a root directory variable, resolved at startup by walking up the directory tree until a `.git` directory is found.

`.sh`:

```sh
ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
while [ ! -d "$ROOT_DIR/.git" ]; do
    ROOT_DIR="$(dirname "$ROOT_DIR")"
    if [ "$ROOT_DIR" = "/" ]; then
        echo "ERROR: could not find project root (.git directory)" >&2
        exit 1
    fi
done
```

`.ps1`:

```powershell
$RootDir = $PSScriptRoot
while (-not (Test-Path "$RootDir\.git")) {
    $RootDir = Split-Path $RootDir -Parent
    if (-not $RootDir) {
        Write-Error "ERROR: could not find project root (.git directory)"
        exit 1
    }
}
```

Then use `$ROOT_DIR` (`.sh`) or `$RootDir` (`.ps1`) to build all absolute paths: `$ROOT_DIR/server`, `$ROOT_DIR/venv/bin/activate`, etc. Never use relative `../../` navigation from the script location.
