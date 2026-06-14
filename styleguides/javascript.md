# JavaScript Style Guide

> Covers JavaScript, CSS, HTML, and JSON style.

## Double Quotes Everywhere

ALWAYS use double quotes for strings. This is a strict, non-negotiable rule.

- JavaScript: `const x = "hello"`
- CSS: `font-family: "Roboto Slab"`
- HTML attributes: `class="btn"`

The rule applies to the primary (outer) quotes. Single quotes inside a double-quoted string are fine: `"it's ready"`, `"key='value'"`.

## Line Length

All lines wrap at 120 characters. When a string literal exceeds 120 chars, split it across lines using `+` between adjacent template literals. This produces a single runtime string with no embedded newlines, mirroring Python's implicit string concatenation. A single multi-line template literal embeds real `\n` characters into the result, which is almost never the intent for log or error strings.

```javascript
console.error(
    `main.js dashboard.load: failed to fetch items,`
    + ` retryCount=${retryCount}, lastError=${lastError}, timestamp=${timestamp}`
);
```

## Fully Descriptive Names

Brevity is the enemy of clarity.

Every name (variable, function, method, constant, class, CSS class, HTML id) must describe what it is, what it does, or what it's for. Avoid dropping concept words for brevity.

- Encode all concepts. If something is "safe user data," the name must say ALL of that. Not just "safe data" (safe what?) or "user info" (what makes it special?):
  - `apiGetSafeUserData()` (safe, user, data, all present)
- Variables and functions must read like helpful commentary:
  - `const currentAuthedUser = requireAuthedUserOrRedirect(request);`
  - `const sessionAuthedUserId = request.session.get("user_id");`
- Constants must describe their purpose and scope:
  - `UUID_PARAMS_ORDER` (what format, what entity, what it validates)
- Methods must describe the full action and context:
  - `apiGetOrderItems(uid)` (API method, gets order items, client-safe output)
  - `requireAuthedUserOrRedirect(request)` (requires auth, returns user, or redirects)
- Never sacrifice clarity for aesthetics. A clear name is always better than a short, ambiguous one.
- Concept-first naming. Lead with the concept so that related names sort together alphabetically in objects, JSON, and autocomplete. Put qualifiers like `total`, `count`, `max`, `min` at the end:
  - `wordCount`, `wordCountTotal`, `llmCostUsd`, `llmCostUsdTicks`
  - This applies equally to object/registry keys: `costPerMilTokensInput`, `costPerMilTokensOutput`, `costProvided`. All `cost*` keys group together when sorted.

Clarity does not mean expanding abbreviations. Common or technical abbreviations are encouraged as part of a broader descriptive name: `env`, `var`/`vars`, `config`, `db`, `api`, `url`, `id`, `uuid`, `llm`, `sdk`, etc.

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
- `console.log("dashboard.js loaded")`
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

## Load & Animation Timing

Sequence animations off `animationend`/`transitionend` events, never chained `setTimeout` delays. Timers drift and break under main-thread load or a cached reload; the event fires when the animation actually finishes, so each step waits for the real end of the previous one.

To run code after the page has painted, gate on the `load` event. `requestAnimationFrame` is not a reliable post-paint signal, and `document.fonts.load` can resolve before first paint on a cached refresh, so a sequence timed from either can run its gaps invisibly in the pre-paint window and land all at once.

For a reveal that must animate on load, prefer a `@keyframes` animation over a CSS transition. A transition needs a previously painted frame to interpolate from, which a cached load may never provide, so the element snaps straight to its end state; a keyframe animation always plays from its start whenever it is applied.

## Object and Array Literals

Object literals and array literals with multiple entries must be expanded with one key per line, even when entries are trivial (a single-key object, a short literal, or a one-element array). Blow them up anyway. Consistency with larger literals and scannability matter more than compactness; do not collapse for elegance. This applies to JS source the same way it applies to JSON files.

```javascript
const ROUTES = [
    {
        path: "/users",
        label: "Users"
    },
    {
        path: "/orders",
        label: "Orders"
    }
];
```

The exception is an object or array used as an inline config value where the entire literal stays under the line limit and never grows beyond a small fixed shape (e.g. a `{ x, y }` coordinate, an enum-like `{ type: "X" }` discriminator). When in doubt, blow it up.

## Columnar Alignment

Do not use columnar alignment for executable code syntax. Do not pad spaces to line up `:`, `=`, values, or related syntax across consecutive lines. One space after `:` in object literals, one space around `=`, always. Columnar alignment creates noisy diffs when any field is renamed or added (the whole block has to be reformatted) and rewards aesthetics over change-resilience. Inline comments may be aligned when a consecutive block uses them as a compact explanatory table and the alignment improves scanning.

## Whitespace

Max one blank line between sections. Never use two or more consecutive blank lines (triple newlines).

Function/method bodies are symmetric: every function, method, or arrow function that has a blank line after its opening `{` must also have a blank line before its closing `}`:
```javascript
someMethod() {

    doSomething();

},
```

This applies to function declarations, method definitions, and arrow callbacks at the function level. It does not apply to inner control-flow blocks (`if`, `for`, `try`/`catch`, `else`); those keep their braces tight.

## Ternary Operators

Only use ternary expressions (`condition ? a : b`) when the variable has exactly two possible values and no additional values could ever apply. If the variable can have more than two values anywhere in the program, even if the current branch narrows it to two, use explicit `if`/`else if` chains instead. A ternary that silently falls through to a default for an unexpected value is a bug waiting to happen.

## No Singletons

No singleton patterns. No IIFE-cached instance, no `getInstance()` with `if (!instance)` guards. The namespace pattern (`window.foo = { ... }`) is already a singleton by construction; reuse it instead.

```javascript
// bad
window.config = (function () {
    let instance = null;
    return {
        get() {
            if (instance === null) {
                instance = loadConfig();
            }
            return instance;
        }
    };
})();

// good
window.config = {
    settings: loadConfig(),

    get() {
        return config.settings;
    }
};
```

## No Trivial Wrapper Helpers

Don't create helpers that wrap a single expression for a single call site. Inline the expression directly. A wrapper earns its place when it is shared across multiple call sites; otherwise it is dead indirection.

```javascript
// bad: single call site, helper wraps one literal
function buildUserPayload(user) {
    return {
        userId: user.id,
        role: user.role
    };
}

await api.send(buildUserPayload(currentUser));

// good: inlined
await api.send({
    userId: currentUser.id,
    role: currentUser.role
});
```

When the same wrapper is called from multiple sites, keep it:

```javascript
window.users = {
    buildPayload(user) {
        return {
            userId: user.id,
            role: user.role
        };
    }
};

await api.send(users.buildPayload(currentUser));
await audit.log(users.buildPayload(actor));
await queue.enqueue(users.buildPayload(targetUser));
```

## No Implicit Defaults

In logging, audit, and observability code, no implicit defaults at all. No `= null`, `= 0`, `= false`, `= ""`, `= []` on parameters or destructured arguments. Every caller passes every value explicitly so that no field is silently dropped from the audit trail.

```javascript
// bad
window.audit = {
    logRequest({ userId, orderId = null, costBreakdown = null, latencyMs = 0 }) {

        // ...

    }
};

audit.logRequest({ userId: user.id });

// good
window.audit = {
    logRequest({ userId, orderId, costBreakdown, latencyMs }) {

        // ...

    }
};

audit.logRequest({
    userId: user.id,
    orderId: null,
    costBreakdown: null,
    latencyMs: 0
});
```

Outside logging and audit code, the same posture applies as a preference. Require explicit values rather than silently defaulting; implicit defaults make it easy to forget a field. When in doubt, require it.

## Third-Party API Responses

Never trust values from third-party APIs. Always coerce to the expected type explicitly, then validate. JS `Number(...)` returns `NaN` silently on bad input; follow numeric coercion with a `Number.isFinite(...)` check that throws on failure. The same posture applies to strings (`String(...)` plus a null/undefined check) and arrays (length check).

```javascript
// bad: raw access, trusts the shape
const usage = response.usage;
const inputTokens = usage.prompt_tokens;
const costTicks = usage.cost_in_usd_ticks;

// also bad: coerce but let NaN propagate
const inputTokens = Number(response.usage.prompt_tokens);
const costTicks = Number(response.usage.cost_in_usd_ticks);

// good: coerce, then validate
const usage = response.usage ?? {};
const inputTokens = Number(usage.prompt_tokens);
const costTicks = Number(usage.cost_in_usd_ticks);
if (!Number.isFinite(inputTokens) || !Number.isFinite(costTicks)) {
    throw new Error(`bad usage payload: ${JSON.stringify(usage)}`);
}
```

## Exception Handling

Always bind caught exceptions as `err`. No `error`, `e`, `exc`, `caughtErr`.

```javascript
try {
    await api.fetchUser(userId);
} catch (err) {
    console.error("fetch failed:", err);
}
```

The `try` block wraps only the statement(s) that can actually raise the caught exception. Validation, context building, and pure logic stay outside. A broad `try` hides bugs in setup logic that should fail loudly.

```javascript
// bad: guard, context, render all swallowed by the catch
try {
    if (!userEmail) {
        return;
    }
    const context = buildContext(user);
    const html = renderTemplate(context);
    await sendEmail(html);
} catch (err) {
    console.warn("email failed:", err);
}

// good: only the fallible I/O inside try
if (!userEmail) {
    return;
}
const context = buildContext(user);
const html = renderTemplate(context);
try {
    await sendEmail(html);
} catch (err) {
    console.warn("email failed:", err);
}
```
