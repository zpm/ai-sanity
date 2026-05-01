# Shell Scripts Style Guide

> Covers shell script conventions across ALL PROJECTS.

## Fully Descriptive Names

Brevity is the enemy of clarity.

Every name (variable, function, constant) must describe what it is, what it does, or what it's for. Avoid dropping concept words for brevity.

- Encode all concepts. If something is "safe user data," the name must say ALL of that. Not just "safe data" (safe what?) or "user info" (what makes it special?):
  - `get_safe_user_data_file_path()` (safe, user, data, all present)
- Variables and functions must read like helpful commentary:
  - `current_branch_name="$(git rev-parse --abbrev-ref HEAD)"`
  - `requirements_lock_file="$ROOT_DIR/requirements.lock"`
- Constants (SCREAMING_SNAKE_CASE) must describe their purpose and scope:
  - `MAX_RETRY_ATTEMPTS_HTTP` (what it's for, what it limits)
- Functions must describe the full action and context:
  - `ensure_venv_activated()` (ensures venv is active, idempotent)
  - `require_git_clean_working_tree()` (requires clean tree, errors if dirty)
- Never sacrifice clarity for aesthetics. A clear name is always better than a short, ambiguous one.
- Concept-first naming. Lead with the concept so that related names sort together alphabetically in env vars, config files, and autocomplete. Put qualifiers like `total`, `count`, `max`, `min` at the end:
  - `PYTHON_VERSION_MIN`, `PYTHON_VERSION_MAX`, `PYTHON_VERSION_REQUIRED`
  - This applies equally to environment variable groups: `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`. All `DB_*` vars group together when sorted.

Clarity does not mean expanding abbreviations. Common or technical abbreviations are encouraged as part of a broader descriptive name: `env`, `var`/`vars`, `config`, `db`, `api`, `url`, `id`, `uuid`, `llm`, `sdk`, etc.

Note: the double-quote rule that applies in Python and JavaScript does not apply to shell, which has semantic differences between `'` and `"` (variable expansion, command substitution).

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

Exception: a script that only operates inside its own directory (e.g. a test runner that `cd`s to `$PSScriptRoot` / `$(dirname "$0")` and hands off to `pytest` or `unittest discover` in the same directory) does not need the walk-up. The walk-up exists to resolve paths elsewhere in the repo; a self-contained script has no such paths to resolve.
