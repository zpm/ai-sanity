# Scripts Style Guide

> Covers script conventions across ALL PROJECTS.

## Fully Descriptive Names

Brevity is the enemy of clarity.

Every name (variable, function, constant) must describe what it is, what it does, or what it's for. Avoid dropping concept words for brevity.

- Encode all concepts. If something is "safe user data," the name must say ALL of that. Not just "safe data" (safe what?) or "user info" (what makes it special?):
  - `get_safe_user_data_file_path()` (safe, user, data, all present)
- Variables and functions must read like helpful commentary:
  - `current_branch_name = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], ...)`
  - `requirements_lock_file = root_dir / "requirements.lock"`
- Constants (SCREAMING_SNAKE_CASE) must describe their purpose and scope:
  - `MAX_RETRY_ATTEMPTS_HTTP` (what it's for, what it limits)
- Functions must describe the full action and context:
  - `ensure_docker_running()` (ensures docker is up, errors if not)
  - `require_git_clean_working_tree()` (requires clean tree, errors if dirty)
- Never sacrifice clarity for aesthetics. A clear name is always better than a short, ambiguous one.
- Concept-first naming. Lead with the concept so that related names sort together alphabetically in env vars, config files, and autocomplete. Put qualifiers like `total`, `count`, `max`, `min` at the end:
  - `PYTHON_VERSION_MIN`, `PYTHON_VERSION_MAX`, `PYTHON_VERSION_REQUIRED`
  - This applies equally to environment variable groups: `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`. All `DB_*` vars group together when sorted.

Clarity does not mean expanding abbreviations. Common or technical abbreviations are encouraged as part of a broader descriptive name: `env`, `var`/`vars`, `config`, `db`, `api`, `url`, `id`, `uuid`, `llm`, `sdk`, etc.

## Structure

Scripts are Python by default. `.py` is the standard format for all scripts: it matches the codebase language, is platform-independent, and is testable. Dev machines and prod operators have the venv active in their terminal. No shell wrapper is needed to run a Python script.

`.sh` and `.ps1` files exist only for two cases:

- Agent entry points. Agents (Claude Code) run in sandboxed environments without venv. `.sh`/`.ps1` thin pairs activate the venv and call `python <script>.py` immediately. No logic beyond venv activation and arg passthrough lives in these files. Each is natively written for its platform (`.sh` for macOS/Linux, `.ps1` for Windows); neither delegates to the other. A `.ps1` whose body invokes `bash.exe` on the sibling `.sh` is not allowed.
- Bootstrap scripts. Scripts that create the Python environment itself (e.g., `bootstrap-venv.sh` on a prod server). Python/venv does not exist yet, so shell is the only option. `.sh` only because bootstrapping targets Linux.

All `.py` scripts require tests with a goal of 100% coverage. Mock external boundaries (`subprocess.run`, `subprocess.Popen`, file I/O, network calls, `input()` prompts) and test argument parsing, logic flow, and error handling paths.

### Agent wrapper naming convention

When `.sh`/`.ps1` agent entry points call a `.py` script, the `.py` lives in a `run/` (or `common/`) subdirectory and shares the same base name as the wrapper. `all-fast.sh` calls `run/all_fast.py`. `pytest.ps1` calls `run\pytest.py`. The name mapping is: strip the extension, convert hyphens to underscores for the `.py` filename. No prefix differences, no `run_` prefix on the Python file.

### No duplicated functions

Shared logic lives in one place. If multiple scripts need the same helper (SSH wrappers, output teeing, path builders), extract it into a shared module that all callers import. Environment wrappers call shared scripts in a sibling `common/` directory.

### Path resolution

Scripts use `pathlib.Path(__file__).resolve().parents[N]` to hardcode the project root based on their fixed depth in the directory tree. No `find_project_root()` walk-up function. Scripts do not move, so the depth is stable.

## Finding the Project Root

Scripts use `pathlib.Path(__file__).resolve().parents[N]` to resolve the project root, where N is the script's fixed depth in the directory tree. Never write a walk-up function; the directory structure is static and the depth is known at authoring time.

```python
import pathlib

# scripts/setup/install.py -> parents[2] = project root
PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[2]

# scripts/tests/run/check.py -> parents[3] = project root
PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[3]
```

Then use `PROJECT_ROOT` to build all absolute paths: `PROJECT_ROOT / "src"`, `PROJECT_ROOT / "config"`, etc. Never use relative `../../` navigation from the script location.

For agent entry points that remain as `.sh`/`.ps1`, the shell root-finding patterns are:

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

Note: the double-quote rule that applies in Python and JavaScript does not apply to shell, which has semantic differences between `'` and `"` (variable expansion, command substitution).
