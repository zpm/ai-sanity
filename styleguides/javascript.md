# JavaScript Style Guide

> Covers JavaScript, CSS, HTML, and JSON style.

## Double Quotes Everywhere

ALWAYS use double quotes for strings. This is a strict, non-negotiable rule.

- JavaScript: `const x = "hello"`
- CSS: `font-family: "Roboto Slab"`
- HTML attributes: `class="btn"`

No exceptions. Single quotes are never acceptable for strings.

## Fully Descriptive Names

Brevity is the enemy of clarity. Every name (variable, function, method, constant, class, CSS class, HTML id) must fully describe what it is, what it does, or what it's for. Never shorten, abbreviate, or drop words for brevity. If a name has multiple concepts, every concept must be present. A reader should understand the name's full meaning without looking at the implementation.

- Encode all concepts. If something is "safe user data," the name must say ALL of that. Not just "safe data" (safe what?) or "user info" (what makes it special?):
  - `apiGetSafeUserData()` (safe, user, data, all present)
- Variables must read like helpful commentary. The reader should understand what a variable holds and where it came from without checking the right side of the assignment:
  - `const currentAuthedUser = requireAuthedUserOrRedirect(request);`
  - `const sessionAuthedUserId = request.session.get("user_id");`
- Constants must describe their purpose and scope:
  - `UUID_PARAMS_STORY` (what format, what entity, what it validates)
- Methods must describe the full action and context:
  - `apiGetStorySections(uid)` (API method, gets story sections, client-safe output)
  - `requireAuthedUserOrRedirect(request)` (requires auth, returns user, or redirects)
- Never sacrifice clarity for aesthetics. A long, clear name is always better than a short, ambiguous one. If a name feels "too long," that's a sign it's doing its job.
- Concept-first naming. Lead with the concept so that related names sort together alphabetically in objects, JSON, and autocomplete. Put qualifiers like `total`, `count`, `max`, `min` at the end:
  - `wordCount`, `wordCountTotal`, `llmCostUsd`, `llmCostUsdTicks`
  - This applies equally to object/registry keys: `costPerMilTokensInput`, `costPerMilTokensOutput`, `costProvided`. All `cost*` keys group together when sorted.

## JSON Formatting

JSON files are always expanded (pretty-printed) with every field on its own line. No collapsed single-line or collapsed-single-object forms. Nested objects and arrays indent one level. This applies to configuration, fixtures, manifests, and hand-authored payloads alike. Editor-generated minification is fine at the build boundary but never committed.

Example:

```json
{
  "rules": [
    {
      "extension": ".py",
      "read": "~/docs/python.md"
    }
  ]
}
```

## Comments

Comment non-trivial blocks. Before any block of code where the intent isn't immediately obvious from the code itself, write a brief 1-2 line comment explaining what the block does and why. The reader should understand the purpose of the next 10-20 lines without reading every line. Don't comment self-explanatory code; only where the context helps.

All single-line comments should be lowercase (including section titles):
- `// dom elements`

Sentence case (capital letters) is only used for full sentence/paragraph explanations.

## Console Output

All strings passed to `console.log`, `console.error`, `console.warn`, etc. should be lowercase:
- `console.log("story.js loaded")`
- `console.error("stream subscription failed:", err)`

## File Headers

Every JavaScript file must have a standard header at the top (120 `/` chars for separator lines):
```javascript
////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
// /static/js/dashboard.js
//
// dashboard page interactive behavior
////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
```

Every CSS file uses `/*` to open, `*` for content lines, `*/` to close. CSS header separator lines are exactly 120 chars wide, including the opening or closing comment syntax:
```css
/***********************************************************************************************************************
* /static/css/main.css
*
* main stylesheet
***********************************************************************************************************************/
```

File paths in headers must use the external serving path (e.g., `/static/js/dashboard.js`), not the internal filesystem path (e.g., `server/static/js/dashboard.js`). These files are served to the client; internal directory structure should never leak into client-facing code.

## Namespacing

All JavaScript files must organize their code into object namespaces on `window`. No top-level functions or scattered `window.*` globals; everything belongs to a namespace.

Shared scripts use the domain as the namespace name (e.g., `window.api`, `window.utils`, `window.STRINGS`).

Page scripts use the page name as the namespace, with an `init()` method:
```javascript
window.dashboard = {
    // constants
    POLL_INTERVAL_MS: 5000,

    // state (dom refs populated in init)
    container: null,
    pollIntervalId: null,

    // methods
    createCard(item) { ... },
    async load() { ... },

    init() {
        dashboard.container = document.getElementById("dashboard-items");
        // event listeners, framework registrations, initial load
        dashboard.load();
    }
};

dashboard.init();
```

Rules:
- Internal references always use the namespace name (e.g., `dashboard.container`, `dashboard.load()`), never `this` (avoids binding issues in callbacks)
- DOM lookups go in `init()`, called immediately at the bottom of the file
- Framework event listeners and component registrations go inside `init()`

Exceptions:
- Universal utilities used on every page may stay as explicit `window.*` globals instead of belonging to a namespace

## CSS Units: rem not em

Always use `rem` for font sizes. Never use `em`, which compounds when elements are nested and causes inconsistent sizing. `rem` is always relative to the root font size.

- `font-size: 0.875rem;`

## Whitespace

Max one blank line between sections. Never use two or more consecutive blank lines (triple newlines).

Function/method bodies are symmetric: every function, method, or arrow function that has a blank line after its opening `{` must also have a blank line before its closing `}`:
```javascript
someMethod() {

    doSomething();

},
```

This applies to function declarations, method definitions, and arrow callbacks at the function level. It does not apply to inner control-flow blocks (`if`, `for`, `try`/`catch`, `else`); those keep their braces tight.
