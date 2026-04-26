# Markdown

> Covers markdown style and formatting.

## Line Breaks

Do not introduce line breaks within a paragraph. Each paragraph is a single unbroken line. Blank lines separate block elements (headings, paragraphs, lists, code blocks, tables).

## Headings

`#` for the document title, `##` for sections, `###` when needed. No `####` or deeper. Most sub-topics work fine as a new paragraph; don't use a heading when a paragraph break will do.

## Formatting

No bold or italic. No `**text**`, `*text*`, `__text__`, or `_text_`.

Inline backticks are only for code - class names, functions, file paths, commands, values. Not for emphasis.

## Blockquotes

`>` only at the very top of the file to describe scope. Never used elsewhere.

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

The display path is the visible link text. It always starts with `./` for files inside the project, such as `[./styleguides/python.md](python.md)`.

The link target is the hyperlink destination. It is relative to the current document's location so the link works when clicked, such as `(python.md)` from `./styleguides/markdown.md` to `./styleguides/python.md`, or `(../README.md)` from `./styleguides/markdown.md` to `./README.md`.

## Paths

All displayed file references must use dot-prefix paths. Within a project, display paths from the project root with `./` (e.g., `./docs/stack/backend.md`). For user-level files in `~/.claude/`, always use the home path `~/` (e.g., `~/.claude/styleguides/python.md`). Never display absolute paths (`/Users/...`) or naked paths without a dot prefix (`docs/stack/backend.md`).
