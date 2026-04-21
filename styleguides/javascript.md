# JavaScript Style Guide

> Covers JavaScript and CSS code style across ALL PROJECTS.

## CRITICAL: Double Quotes Everywhere

ALWAYS use double quotes for strings in ALL languages. This is a strict, non-negotiable rule.

- JavaScript: `const x = "hello"` not `const x = 'hello'`
- CSS: `font-family: "Roboto Slab"` not `font-family: 'Roboto Slab'`
- HTML attributes: `class="btn"` not `class='btn'`

No exceptions. Single quotes are never acceptable for strings.

## Comments

Comment non-trivial blocks. Before any block of code where the intent isn't immediately obvious from the code itself, write a brief 1-2 line comment explaining what the block does and why. The reader should understand the purpose of the next 10-20 lines without reading every line. Don't comment self-explanatory code - only where the context helps.

All single-line comments should be lowercase (including section titles):
- Good: `// dom elements`
- Bad: `// DOM elements`

Sentence case (capital letters) is only used for full sentence/paragraph explanations.

## Console Output

All strings passed to `console.log`, `console.error`, `console.warn`, etc. should be lowercase:
- Good: `console.log("story.js loaded")`, `console.error("stream subscription failed:", err)`
- Bad: `console.log("Story.js loaded")`, `console.error("Stream subscription failed:", err)`

## File Headers

Every JavaScript file must have a standard header at the top (120 `/` chars for separator lines):
```javascript
////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
// /static/js/dashboard.js
//
// dashboard page interactive behavior
////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
```

Every CSS file uses `/*` to open, `*` for content lines, `*/` to close:
```css
/****************************************************************************************************************
* /static/css/main.css
*
* main stylesheet
****************************************************************************************************************/
```

File paths in headers must use the external serving path (e.g., `/static/js/dashboard.js`), not the internal filesystem path (e.g., `server/static/js/dashboard.js`). These files are served to the client - internal directory structure should never leak into client-facing code.

## Namespacing

All JavaScript files must organize their code into object namespaces on `window`. No top-level functions or scattered `window.*` globals - everything belongs to a namespace.

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
- Internal references always use the namespace name (e.g., `dashboard.container`, `dashboard.load()`), never `this` - avoids binding issues in callbacks
- DOM lookups go in `init()`, called immediately at the bottom of the file
- Framework event listeners and component registrations go inside `init()`

Exceptions:
- Universal utilities used on every page may stay as explicit `window.*` globals instead of belonging to a namespace

## CSS Units: rem not em

Always use `rem` for font sizes. Never use `em`, which compounds when elements are nested and causes inconsistent sizing. `rem` is always relative to the root font size.

- Good: `font-size: 0.875rem;`
- Bad: `font-size: 0.875em;`

## Whitespace

Max one blank line between sections. Never use two or more consecutive blank lines (triple newlines).

Function/method bodies are symmetric: every function, method, or arrow function that has a blank line after its opening `{` must also have a blank line before its closing `}`:
```javascript
// good - symmetric
someMethod() {

    doSomething();

},

// bad - asymmetric
someMethod() {

    doSomething();
},
```

This applies to function declarations, method definitions, and arrow callbacks at the function level. It does not apply to inner control-flow blocks (`if`, `for`, `try`/`catch`, `else`) - those keep their braces tight.