# Python Style Guide

> Covers Python code style: imports, spacing, naming, quotes, file headers, and comments.

## Double Quotes Everywhere

ALWAYS use double quotes for strings. This is a strict, non-negotiable rule.

- `mode = "json"`, `role = "system"`

No exceptions. Single quotes are never acceptable for strings.

## Fully Descriptive Names

Brevity is the enemy of clarity. Every name (variable, function, method, constant, class) must fully describe what it is, what it does, or what it's for. Never shorten, abbreviate, or drop words for brevity. If a name has multiple concepts, every concept must be present. A reader should understand the name's full meaning without looking at the implementation.

- Encode all concepts. If something is "safe user data," the name must say ALL of that. Not just "safe data" (safe what?) or "user info" (what makes it special?):
  - `api_get_safe_user_data()` (safe, user, data, all present)
- Variables must read like helpful commentary. The reader should understand what a variable holds and where it came from without checking the right side of the assignment:
  - `current_authed_user = require_authed_user_or_redirect(request)`
  - `session_authed_user_id = request.session.get("user_id")`
- Constants must describe their purpose and scope:
  - `UUID_PARAMS_STORY` (what format, what entity, what it validates)
- Methods must describe the full action and context:
  - `api_get_story_sections(uid)` (API method, gets story sections, client-safe output)
  - `require_authed_user_or_redirect(request)` (requires auth, returns user, or redirects)
- Never sacrifice clarity for aesthetics. A long, clear name is always better than a short, ambiguous one. If a name feels "too long," that's a sign it's doing its job.
- Concept-first naming. Lead with the concept so that related names sort together alphabetically in dicts, JSON, and autocomplete. Put qualifiers like `total`, `count`, `max`, `min` at the end:
  - `word_count`, `word_count_total`, `llm_cost_usd`, `llm_cost_usd_ticks`
  - This applies equally to dict/registry keys: `cost_per_mil_tokens_input`, `cost_per_mil_tokens_output`, `cost_provided`. All `cost_*` keys group together when sorted.

Explicit exception: caught exceptions are always bound as `e` (see Exception Handling). This is the single deliberate deviation from the naming rule, chosen for ubiquity and muscle memory, not because the name is descriptive.

## Imports

Use `import x` instead of `from x import y`. Reference with full module path for clarity:
- `import fastapi` then `app = fastapi.FastAPI()`
- Exception: Standard library modules with very long paths can use `from` imports if it improves readability

All imports must be at the top of the file. Never use `__import__()` or place `import` statements inside functions, methods, or conditional blocks. If a top-level import would create a circular dependency, that is a structural problem. Fix the dependency graph instead of hiding the cycle with a late import.

Never use quoted/string type annotations (e.g. `"MyClass"`, `"module.MyClass | None"`). Always import the module and use the real type. Never use `TYPE_CHECKING` or `from __future__ import annotations`.

Import spacing: Separate third-party imports from project imports with one empty line:
```python
import uuid
import os
import fastapi

import myapp.models.user
import myapp.services.config
```

## Line Length

All lines must wrap at 120 characters. When a string literal (including f-strings, log messages, error messages) exceeds 120 characters, split it using implicit string concatenation:

```python
myapp.services.logging.critical(
    f"main.py my_function: database health check failed,"
    f" consecutive_failures={consecutive_failures}, down_since={down_since}, {exc}"
)
```

## Spacing

- Between major code blocks: Use three newlines (two empty lines) between module-level classes. For large files with distinct logical sections (e.g., base/model classes vs. service classes vs. router setup), use a `########` separator line (120 `#` chars). Do not add a label comment after the separator; the class name below is label enough:
  ```python
  class UserService:
      def __init__(self):

          pass


  ########################################################################################################################


  class AuditLogger:
      def __init__(self):

          pass

  class Config:
      def __init__(self):

          pass


  class SubConfig(Config):
      def __init__(self):

          pass
  ```
- Always include an empty newline after every function/method definition (between the `def` line and the function body). This applies to every `def`, including single-line bodies, `pass` stubs, and docstring-only bodies. The cost of one blank line is trivial, and consistency with real function bodies matters more than visual density on stubs. Do not collapse for elegance.

## Method Signatures

When a method definition wraps across multiple lines, keep `self` (or `cls`) on the same line as `def`, not on its own line:
```python
class SampleGenerator:
    async def generate_sample(self,
        sections: list[myapp.models.story.Section],
        user_id: str
    ) -> str:
```

Never use the keyword-only separator `*` in a function signature. The separate "Keyword Arguments and Formatting" rule already requires callers to pass by keyword for 2+ args, so `*` is redundant enforcement. It adds visual noise, creates a positional-vs-keyword-only class distinction that has no real semantic, and makes signatures harder to scan. Write every argument as a normal positional-or-keyword parameter and trust the kwargs rule.
```python
class InkTrialService:
    async def xsvc_add_ink_trial_daily(self,
        user: infinite.models.user.User,
        generating_id: str,
        require_cron_eligibility: bool = False,
    ) -> bool:
```

## Keyword Arguments and Formatting

- When a function call has 2+ arguments, always use keyword arguments for clarity:
  ```python
  myapp.services.logging.write(
      logging_group_key = logging_group_key,
      filename_suffix = "api-response",
      data = response.model_dump()
  )
  ```
- Always include exactly one space around `=` and other operators, even inside function calls. Never columnar-align `=` across consecutive kwargs; it creates noisy diffs when any field is renamed or added, and the whole block has to be reformatted. One space, always. The same rule applies to dict literals: exactly one space after the colon, never pad values to line up vertically.
  - `Field(default_factory = datetime.utcnow)`
  - Example:
    ```python
    call(
        event_id = event_id,
        event_type = event_type,
        event_payload = event_payload,
    )

    row = {
        "event_id": row["event_id"],
        "event_type": row["event_type"],
        "event_payload": row["event_payload"],
    }
    ```
  - Note: the space-around-`=` rule explicitly overrides PEP 8 (which says no spaces around `=` in keyword arguments) and will fight auto-formatters like black and ruff's default profile. Configure the formatter to respect this rule, or disable formatting on conflicting regions. PEP 8 does not win here.
- Never use columnar alignment. Do not pad spaces to line up `=`, `:`, values, comments, or related syntax across consecutive lines.
- For function calls with multiple arguments, use JSON-style indenting with each argument on its own line. This applies even when arguments are trivial (a single-key dict, a one-element list, a short literal). Blow them up anyway. Consistency with larger calls and scannability matter more than compactness; do not collapse for elegance. Exception: Decorators (`@app.get`, `@app.post`, etc.) stay on one line:
  ```python
  return templates.TemplateResponse(
      name = "index.html",
      context = {
          "request": request
      }
  )
  ```

## API Response Dict Formatting

Dict literals returned as API responses must be formatted with one key per line, JSON-style. Keys should be alphabetized when there's no semantic reason for a different order.

```python
return {
    "name": user.name,
    "role": user.role,
    "user_id": user.user_id
}
```

## Required Subclass Configuration

Per-subclass configuration (provider tag, env var name, timeout, etc.) goes through `__init__` parameters on the base class. Each subclass passes concrete values up via `super().__init__()`. A missing kwarg raises `TypeError` at construction: the loud, immediate failure you want.

```python
class WebhookIngest:
    def __init__(self,
        storage,
        provider_tag: str,
        webhook_secret_env: str,
        signature_max_age_seconds: int,
    ):
        self._storage = storage
        self.provider_tag = provider_tag
        self.webhook_secret_env = webhook_secret_env
        self.signature_max_age_seconds = signature_max_age_seconds


class StripeWebhookIngest(WebhookIngest):
    def __init__(self, storage):
        super().__init__(
            storage = storage,
            provider_tag = "stripe",
            webhook_secret_env = "STRIPE_WEBHOOK_SECRET",
            signature_max_age_seconds = 300,
        )
```

## No Top-Level Functions

All functions must live inside a class. No bare `def` at module level. If a function doesn't need instance state, make it a `@staticmethod` on the most relevant class. This keeps every function discoverable via its class and avoids orphaned helpers drifting around at module scope.

Note: this explicitly overrides typical Python convention. Top-level functions are idiomatic in most Python code and no linter or formatter enforces this rule out of the box. Rationale: in complex projects, scattered module-level helpers are error-prone, hard to discover, and drift without a clear home. This convention mirrors Java/C#-style organization where every callable has a class home. Third-party libraries will not follow this rule; it applies only to code you own.

```python
class CostCalculator:
    @staticmethod
    def calculate_total(items):

        return sum(i.price for i in items)
```

## Third-Party API Responses

Never trust values from third-party APIs. Always coerce to the expected type explicitly. If it's not our code, assume anything could happen: wrong types, missing fields, unexpected nulls. Defensive coercion costs nothing and prevents silent corruption.

```python
class ApiUsageParser:
    @staticmethod
    def parse_usage(usage):

        input_tokens = int(usage.get("prompt_tokens"))
        cost_usd_ticks = int(usage.get("cost_in_usd_ticks"))
```

## Enum Values at External Boundaries

Always call `.value` explicitly when passing an enum to anything outside Python: SQL statements, JSON serialization, logging strings, third-party API payloads. `StrEnum` subclasses `str` so the implicit form happens to work today, but the explicit form is the rule.

Three reasons:
1. Intent is visible at the call site. A reader sees `enum.value` and knows "this leaves Python as a string now." Without `.value`, the reader has to know the enum type is a `StrEnum`.
2. It's symmetric with the read side. DB reads always coerce back via `MyEnum(row["column"])`; the write side should show the same symmetric coercion out.
3. It's forward-compatible. If an enum later changes from `StrEnum` to plain `Enum` (or gains non-string values), the implicit pattern breaks silently and every call site must be audited. `.value` keeps working.

```python
sqlalchemy.insert(table).values(status = record.status.value)
json.dumps({"role": message.role.value})
logger.info(f"tier={user.tier.value}")
```

Inside Python this does not apply. Enum comparisons (`if status == MyEnum.ACTIVE:`), dict keys, and attribute access stay as enums.

## Anti-Patterns

- No implicit defaults in logging and audit code. Every parameter must be required (no `= None`, no `= 0`, no `= False`). Call sites must pass every value explicitly so that every field is visibly accounted for. Silent defaults make it too easy to forget a field and silently lose audit data:
  ```python
  class AuditLogger:
      def log_request(self,
          user_id: str,
          story_id: str | None,
          cost_stream: dict | None,
      ) -> None:

          ...

  class RequestHandler:
      async def handle_request(self, service, user):

          await service.log_request(
              user_id = user.user_id,
              story_id = None,
              cost_stream = None,
          )
  ```
- No singleton patterns: Don't use `__new__` with instance checking (`if cls._instance is None`). Just use normal `__init__` and instantiate when needed:
  ```python
  class Config:
      def __init__(self):

          # load config here
          pass
  ```
- No nested functions. Never define a function inside another function. Extract it as a private method on the class instead. If you need a callable for `asyncio.to_thread`, pass a method reference and its arguments.
- No trivial wrapper helpers. Don't create helper functions that just wrap a single expression like dict construction or simple transforms. Inline the expression directly at the call site; it's easier to read and grep for:
  ```python
  class TemplateContextBuilder:
      @staticmethod
      def render_index(templates, request):

          return templates.TemplateResponse(
              name = "index.html",
              context = {
                  "request": request
              }
          )
  ```

## Exception Handling

- Always bind caught exceptions as `e`. No other names (`exc`, `err`, `error`, `caught_exc`, etc.).
  ```python
  try:
      ...
  except Exception as e:
      logger.warning(f"failed: {e}")
  ```

## File Headers

Every Python file must have a standard header at the top (120 `#` chars for separator lines):
```python
########################################################################################################################
# myapp/services/config.py
#
# configuration service
########################################################################################################################
```

## Comments

- Comment non-trivial blocks. Before any block of code where the intent isn't immediately obvious from the code itself, write a brief 1-2 line comment explaining what the block does and why. The reader should understand the purpose of the next 10-20 lines without reading every line. Don't comment self-explanatory code; only where the context helps.
- Three capitalization tiers for comments:
  1. Class-level section breakpoints (full-width `########` separators): ALL CAPS.
     - `# STORY SUMMARY SERVICE`
  2. Function-level section headings (indented `####` separators inside classes): first word capitalized, sentence case after colon. Acronyms like API and DEBUG stay all caps.
     - `# API: Methods`, `# DEBUG: Model dumps`, `# Internal: Linking`
  3. Normal inline comments: all lowercase.
     - `return uid  # hex format without dashes`
- Docstrings use sentence case (leading capital). Keep docstrings to 1-2 sentences, wrap close to the 120-column max instead of wrapping early, and never exceed 5 physical lines under any circumstances.
  ```python
  class LiveMemoryBufferManager:
      def _init_live_memory_buffers(self):

          """Live memory buffers remain instantiated on the class and allow for keeping state on long-running background
          tasks, in this case LLM streaming requests. This is to avoid clobbering this status to the database."""
  ```
