# Markdown

> Covers markdown style and formatting across ALL PROJECTS.

## Line Breaks

Do not introduce line breaks within a paragraph. Each paragraph is a single unbroken line. Blank lines separate block elements (headings, paragraphs, lists, code blocks, tables).

## Headings

`#` for the document title, `##` for sections, `###` only when truly needed. No `####` or deeper. Most sub-topics work fine as a new paragraph - don't reach for a heading when a paragraph break will do.

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

Prefer tables over lists unless the data is flat (single column, no attributes).

## Links

Use relative paths from the doc's location.

## Paths

All file references must use dot-prefix paths. Within a project, use `./` (e.g., `./docs/stack/backend.md`). For user-level files in `~/.claude/`, always use the home path `~/` (e.g., `~/.claude/styleguides/python.md`). Never use absolute paths (`/Users/...`) or naked paths without a dot prefix (`docs/stack/backend.md`).