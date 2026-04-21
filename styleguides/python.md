# Python Style Guide

> Covers Python code style: imports, spacing, naming, quotes, file headers, and comments. Project-agnostic - applies across projects.

## CRITICAL: Double Quotes Everywhere

ALWAYS use double quotes for strings. This is a strict, non-negotiable rule.

- Good: `mode = "json"`, `role = "system"`
- Bad: `mode = 'json'`, `role = 'system'`

No exceptions. Single quotes are never acceptable for strings.

## CRITICAL: Fully Descriptive Names - Brevity Is the Enemy

Every name - variable, function, method, constant, class - must fully describe what it is, what it does, or what it's for. Never shorten, abbreviate, or drop words for brevity. If a name has multiple concepts, every concept must be present. A reader should understand the name's full meaning without looking at the implementation.

- Encode all concepts.
  If something is "safe user data," the name must say ALL of that - not just "safe data" (safe what?) or "user info" (what makes it special?):
  - Good: `api_get_safe_user_data()` - safe, user, data, all present
  - Bad: `api_get_data()` - drops "safe" and "user"
  - Bad: `api_get_safe_info()` - drops what entity it's for
  - Bad: `get_info()` - says nothing useful
- Variables must read like helpful commentary. The reader should understand what a variable holds and where it came from without checking the right side of the assignment:
  - Good: `current_authed_user = require_authed_user_or_redirect(request)`
  - Bad: `user = require_authed_user_or_redirect(request)`
  - Good: `session_authed_user_id = request.session.get("user_id")`
  - Bad: `uid = request.session.get("user_id")`
- Constants must describe their purpose and scope:
  - Good: `UUID_PARAMS_STORY` - what format, what entity, what it validates
  - Bad: `UID_PARAMS` - which UID? params for what?
- Methods must describe the full action and context:
  - Good: `api_get_story_sections(uid)` - API method, gets story sections, client-safe output
  - Good: `require_authed_user_or_redirect(request)` - requires auth, returns user, or redirects
  - Bad: `get_sections(uid)` - which sections? for whom? filtered how?
  - Bad: `check_auth(request)` - checks auth and then what?
- Never sacrifice clarity for aesthetics. A long, clear name is always better than a short, ambiguous one. If a name feels "too long," that's a sign it's doing its job.
- Concept-first naming. Lead with the concept so that related names sort together alphabetically in dicts, JSON, and autocomplete. Put qualifiers like `total`, `count`, `max`, `min` at the end:
  - Good: `word_count`, `word_count_total`, `llm_cost_usd`, `llm_cost_usd_ticks`
  - Bad: `total_word_count`, `total_llm_cost`
  - This applies equally to dict/registry keys: `cost_per_mil_tokens_input`, `cost_per_mil_tokens_output`, `cost_provided` - all `cost_*` keys group together when sorted.

This rule applies across all languages (Python, JavaScript, CSS class names, HTML IDs, etc.).

## Imports

Use `import x` instead of `from x import y`. Reference with full module path for clarity:
- Good: `import fastapi` then `app = fastapi.FastAPI()`
- Bad: `from fastapi import FastAPI` then `app = FastAPI()`
- Exception: Standard library modules with very long paths can use `from` imports if it improves readability

All imports must be at the top of the file. Never use `__import__()` or place `import` statements inside functions, methods, or conditional blocks. If a top-level import would create a circular dependency, that is a structural problem - fix the dependency graph instead of hiding the cycle with a late import.

Never use quoted/string type annotations (e.g. `"MyClass"`, `"module.MyClass | None"`). Always import the module and use the real type. Never use `TYPE_CHECKING` or `from __future__ import annotations`.

Import spacing: Separate third-party imports from project imports with one empty line:
```python
# Good
import uuid
import os
import fastapi

import myapp.models.user
import myapp.services.config

# Bad
import uuid
import os
import fastapi
import myapp.models.user
```

## Line Length

All lines must wrap at 120 characters. When a string literal (including f-strings, log messages, error messages) exceeds 120 characters, split it using implicit string concatenation:

```python
# Good - split at 120 chars
myapp.services.logging.critical(
    f"main.py my_function: database health check failed,"
    f" consecutive_failures={consecutive_failures}, down_since={down_since}, {exc}"
)

# Bad - single line exceeds 120 chars
myapp.services.logging.critical(
    f"main.py my_function: database health check failed, consecutive_failures={consecutive_failures}, down_since={down_since}, {exc}"
)
```

## Spacing

- Between major code blocks: Use three newlines (two empty lines) between module-level classes and functions. For large files with distinct logical sections (e.g., base classes vs. standalone functions vs. router), use a `########` separator line (120 `#` chars) with an ALL CAPS label (see comment capitalization tiers in Comments section):
  ```python
  # Good - separator between major sections
  class Service:
      def __init__(self):
          pass


  ########################################################################################################################


  def standalone_helper():
      pass

  # Good - blank lines between closely related classes
  class Config:
      def __init__(self):
          pass


  class SubConfig(Config):
      def __init__(self):
          pass

  # Bad - comment label after separator (the class/function name is label enough)
  ########################################################################################################################
  # helpers

  def standalone_helper():
      pass

  # Bad - only one empty line between module-level blocks
  class Config:
      def __init__(self):
          pass

  class Service:
      def __init__(self):
          pass
  ```
- Always include an empty newline after every function/method definition (between the `def` line and the function body).

## Method Signatures

When a method definition wraps across multiple lines, keep `self` (or `cls`) on the same line as `def`, not on its own line:
```python
# Good
async def generate_sample(self,
    sections: list[myapp.models.story.Section],
    user_id: str
) -> str:

# Bad
async def generate_sample(
    self,
    sections: list[myapp.models.story.Section],
    user_id: str
) -> str:
```

Never use the keyword-only separator `*` in a function signature. The separate "Keyword Arguments and Formatting" rule already requires callers to pass by keyword for 2+ args, so `*` is redundant enforcement. It adds visual noise, creates a positional-vs-keyword-only class distinction that has no real semantic, and makes signatures harder to scan. Write every argument as a normal positional-or-keyword parameter and trust the kwargs rule.
```python
# Good
async def xsvc_add_ink_trial_daily(self,
    user: infinite.models.user.User,
    generating_id: str,
    require_cron_eligibility: bool = False,
) -> bool:

# Bad - keyword-only separator
async def xsvc_add_ink_trial_daily(self,
    user: infinite.models.user.User,
    *,
    generating_id: str,
    require_cron_eligibility: bool = False,
) -> bool:
```

## Keyword Arguments and Formatting

- When a function call has 2+ arguments, always use keyword arguments for clarity:
  ```python
  # Good
  myapp.services.logging.write(
      logging_group_key = logging_group_key,
      filename_suffix = "api-response",
      data = response.model_dump()
  )

  # Bad
  myapp.services.logging.write(logging_group_key, "api-response", response.model_dump())
  ```
- Always include exactly one space around `=` and other operators, even inside function calls. Never columnar-align `=` across consecutive kwargs - it creates noisy diffs when any field is renamed or added, and the whole block has to be reformatted. One space, always. The same rule applies to dict literals: exactly one space after the colon, never pad values to line up vertically.
  - Good: `Field(default_factory = datetime.utcnow)`
  - Bad: `Field(default_factory=datetime.utcnow)`
  - Good:
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
  - Bad (columnar alignment):
    ```python
    call(
        event_id      = event_id,
        event_type    = event_type,
        event_payload = event_payload,
    )

    row = {
        "event_id":      row["event_id"],
        "event_type":    row["event_type"],
        "event_payload": row["event_payload"],
    }
    ```
- For function calls with multiple arguments, use JSON-style indenting with each argument on its own line. Exception: Decorators (`@app.get`, `@app.post`, etc.) stay on one line:
  ```python
  # Good
  return templates.TemplateResponse(
      "index.html",
      {
          "request": request
      }
  )

  # Bad
  return templates.TemplateResponse("index.html", {"request": request})
  ```

## API Response Dict Formatting

Dict literals returned as API responses must be formatted with one key per line, JSON-style. Keys should be alphabetized when there's no semantic reason for a different order.

```python
# Good - multi-line, alphabetized keys
return {
    "name": user.name,
    "role": user.role,
    "user_id": user.user_id
}

# Bad - inline
return {"name": user.name, "role": user.role, "user_id": user.user_id}
```

## Required Subclass Configuration

Per-subclass configuration (provider tag, env var name, timeout, etc.) goes through `__init__` parameters on the base class. Each subclass passes concrete values up via `super().__init__()`. A missing kwarg raises `TypeError` at construction - the loud, immediate failure you want.

```python
class WebhookIngest:
    def __init__(self,
        storage,
        provider_tag: str,
        webhook_secret_env: str,
        signature_max_age_seconds: int,
    ):
        self._storage                  = storage
        self.provider_tag              = provider_tag
        self.webhook_secret_env        = webhook_secret_env
        self.signature_max_age_seconds = signature_max_age_seconds


class StripeWebhookIngest(WebhookIngest):
    def __init__(self, storage):
        super().__init__(
            storage                   = storage,
            provider_tag              = "stripe",
            webhook_secret_env        = "STRIPE_WEBHOOK_SECRET",
            signature_max_age_seconds = 300,
        )
```

## No Top-Level Functions

All functions must live inside a class. No bare `def` at module level. If a function doesn't need instance state, make it a `@staticmethod` on the most relevant class. This keeps every function discoverable via its class and avoids orphaned helpers drifting around at module scope.

```python
# Good - static method on a class
class CostCalculator:
    @staticmethod
    def calculate_total(items):
        return sum(i.price for i in items)

# Bad - top-level function
def calculate_total(items):
    return sum(i.price for i in items)
```

## Third-Party API Responses

Never trust values from third-party APIs. Always coerce to the expected type explicitly. If it's not our code, assume anything could happen - wrong types, missing fields, unexpected nulls. Defensive coercion costs nothing and prevents silent corruption.

```python
# Good - coerce to int
input_tokens = int(usage.get("prompt_tokens"))
cost_usd_ticks = int(usage.get("cost_in_usd_ticks"))

# Bad - trusting the API to return the right type
input_tokens = usage.get("prompt_tokens")
cost_usd_ticks = usage.get("cost_in_usd_ticks")
```

## Enum Values at External Boundaries

Always call `.value` explicitly when passing an enum to anything outside Python: SQL statements, JSON serialization, logging strings, third-party API payloads. `StrEnum` subclasses `str` so the implicit form happens to work today, but the explicit form is the rule.

Three reasons:
1. Intent is visible at the call site. A reader sees `enum.value` and knows "this leaves Python as a string now." Without `.value`, the reader has to know the enum type is a `StrEnum`.
2. It's symmetric with the read side. DB reads always coerce back via `MyEnum(row["column"])`; the write side should show the same symmetric coercion out.
3. It's forward-compatible. If an enum later changes from `StrEnum` to plain `Enum` (or gains non-string values), the implicit pattern breaks silently and every call site must be audited. `.value` keeps working.

```python
# Good - explicit at every external boundary
sqlalchemy.insert(table).values(status = record.status.value)
json.dumps({"role": message.role.value})
logger.info(f"tier={user.tier.value}")

# Bad - relies on StrEnum subclassing str
sqlalchemy.insert(table).values(status = record.status)
json.dumps({"role": message.role})
logger.info(f"tier={user.tier}")
```

Inside Python this does not apply. Enum comparisons (`if status == MyEnum.ACTIVE:`), dict keys, and attribute access stay as enums.

## Anti-Patterns

- No implicit defaults in logging and audit code. Every parameter must be required (no `= None`, no `= 0`, no `= False`). Call sites must pass every value explicitly so that every field is visibly accounted for. Silent defaults make it too easy to forget a field and silently lose audit data:
  ```python
  # Good - caller explicitly passes None
  def log_request(self,
      user_id: str,
      story_id: str | None,
      cost_stream: dict | None,
  ) -> None:
      ...

  await service.log_request(
      user_id = user.user_id,
      story_id = None,
      cost_stream = None,
  )

  # Bad - caller silently omits nullable fields
  def log_request(self,
      user_id: str,
      story_id: str | None = None,
      cost_stream: dict = None,
  ) -> None:
      ...

  await service.log_request(user_id = user.user_id)
  ```
- No singleton patterns: Don't use `__new__` with instance checking (`if cls._instance is None`). Just use normal `__init__` and instantiate when needed:
  ```python
  # Good
  class Config:
      def __init__(self):
          # load config here
          pass

  # Bad
  class Config:
      _instance = None
      def __new__(cls):
          if cls._instance is None:
              cls._instance = super().__new__(cls)
          return cls._instance
  ```
- No nested functions. Never define a function inside another function. Extract it as a private method on the class instead. If you need a callable for `asyncio.to_thread`, pass a method reference and its arguments.
- No trivial wrapper helpers. Don't create helper functions that just wrap a single expression like dict construction or simple transforms. Inline the expression directly at the call site - it's easier to read and grep for:
  ```python
  # Good
  return templates.TemplateResponse("index.html", {"request": request})

  # Bad
  def make_context(request, **extra):
      ctx = {"request": request}
      ctx.update(extra)
      return ctx
  return templates.TemplateResponse("index.html", make_context(request))
  ```

## Exception Handling

- Always bind caught exceptions as `e`. No other names (`exc`, `err`, `error`, `caught_exc`, etc.).
  ```python
  # Good
  try:
      ...
  except Exception as e:
      logger.warning(f"failed: {e}")

  # Bad
  try:
      ...
  except Exception as exc:
      logger.warning(f"failed: {exc}")
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

- Comment non-trivial blocks. Before any block of code where the intent isn't immediately obvious from the code itself, write a brief 1-2 line comment explaining what the block does and why. The reader should understand the purpose of the next 10-20 lines without reading every line. Don't comment self-explanatory code - only where the context helps.
- Three capitalization tiers for comments:
  1. Class-level section breakpoints (full-width `########` separators): ALL CAPS.
     - Good: `# STORY SUMMARY SERVICE`
     - Bad: `# Story Summary Service`
  2. Function-level section headings (indented `####` separators inside classes): first word capitalized, sentence case after colon. Acronyms like API and DEBUG stay all caps.
     - Good: `# API: Methods`, `# DEBUG: Model dumps`, `# Internal: Linking`
     - Bad: `# api methods`, `# DEBUG: Model Dumps`, `# INTERNAL: Statistics calculation`
  3. Normal inline comments: all lowercase.
     - Good: `return uid  # hex format without dashes`
     - Bad: `return uid  # Hex format without dashes`
- Docstrings use sentence case (leading capital) and should fill lines to the 120-column max rather than wrapping early:
  ```python
  # Good - sentence case, fills to 120 cols
  def _init_live_memory_buffers(self):

      """Live memory buffers remain instantiated on the class and allow for keeping state on long-running background
      tasks, in this case LLM streaming requests. This is to avoid clobbering this status to the database."""

  # Bad - lowercase start
  def _init_live_memory_buffers(self):

      """live memory buffers remain instantiated on the class..."""

  # Bad - wraps too early when there is room on the line
  def _init_live_memory_buffers(self):

      """Live memory buffers remain instantiated on the class
      and allow for keeping state on long-running background tasks..."""
  ```
- Keep docstrings to 1-2 sentences. A docstring is a one-line description of what the thing does.
