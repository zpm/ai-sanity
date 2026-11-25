# Markdown

> Covers markdown style and formatting.

## Line Breaks

Do not introduce line breaks within a paragraph. Each paragraph is a single unbroken line. Blank lines separate block elements (headings, paragraphs, lists, code blocks, tables).

## Headings

`#` for the document title, `##` for sections, `###` when needed. No `####` or deeper. Most sub-topics work fine as a new paragraph; don't use a heading when a paragraph break will do.

Every `##` section heading has three blank lines above it. `###` subheadings keep a single blank line above.

A doc that numbers its sections writes `## 1. Name` for a section and `### 1.1. Name` for a subsection.

## Formatting

Bold and italic are both available when the user asks for them. Never add bold or italic on your own initiative. The rule exists because you overuse both as headings and for emphasis in running text when left to your own devices.

Inline backticks are only for code - class names, functions, file paths, commands, values. Not for emphasis.

## Blockquotes

Never add a blockquote. A user can ask for one.

## Horizontal Rules

No `---` or `***`.

## Lists

`-` for unordered lists. Numbered lists (`1.`) only for sequential steps. No `*` bullets.

## Code Blocks

Fenced code blocks must have a language tag.

## Tables

Prefer tables over lists when presenting records with multiple attributes, such as commands by platform or options with descriptions. Use lists for flat items, ordered steps, and examples where each item is a short label plus a code example.

## Links

Use project-root-relative display paths and document-relative link targets.

The display path is the visible link text. It always starts with `./` for files inside the project, such as `[./styleguides/python.md](python.md)`, with `../` for files in a sibling repo, such as `[../zpm-llc/PROD.md](../zpm-llc/PROD.md)`, and with `~/` only for global files.

The link target is the hyperlink destination. It is relative to the current document's location so the link works when clicked, such as `(python.md)` from `./styleguides/markdown.md` to `./styleguides/python.md`, `(../README.md)` from `./styleguides/markdown.md` to `./README.md`, or `(../../zpm-llc/PROD.md)` from `./styleguides/markdown.md` to `../zpm-llc/PROD.md`.

## Paths

Every displayed path to a file in the project or in a sibling repo is relative to the project root. A path inside the project starts with `./` (e.g., `./docs/stack/backend.md`), and a path in a sibling repo starts with `../` (e.g., `../zpm-llc/PROD.md`). Use the tilde path `~/` only for global files, which are the user-level files under the home directory (e.g., `~/.claude/settings.json`). Never display absolute paths (`/Users/...`) or naked paths without a dot prefix (`docs/stack/backend.md`).



## File Names

A doc at a repo's root has a name in capitals, and so does a README in any folder. Every other doc has a lowercase name with hyphens between words.
