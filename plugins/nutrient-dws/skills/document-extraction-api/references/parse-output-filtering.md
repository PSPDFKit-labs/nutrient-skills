# Parse Output — Filtering and Downstream Patterns

The response shape of `/extraction/parse` — element types, field-by-field
schemas, coordinate spaces, per-mode field availability — is documented
upstream. Use those pages as the source of truth; this reference only
suggests which tools to reach for when slicing and reshaping the response.

## Official documentation

- [Document element extraction (spatial output)](https://www.nutrient.io/guides/dws-data-extraction/parsing/extract-document-elements/) —
  schema for `output.elements`, element types, bounding-box conventions.
- [Markdown extraction](https://www.nutrient.io/guides/dws-data-extraction/parsing/extract-markdown/) —
  shape of `output.markdown`.
- [Processing modes](https://www.nutrient.io/guides/dws-data-extraction/parsing/processing-modes/) —
  which fields each mode populates (e.g. `altDescription` only with
  `agentic`; `keyValueRegion` and `formula` only with `understand` or
  higher).
- [Coordinate spaces](https://www.nutrient.io/guides/dws-data-extraction/parsing/coordinate-spaces/) —
  how `bounds` relate to `page.width` / `page.height`.

## Suggested tools

| Task | Tool | Why |
|---|---|---|
| Filter or project the spatial JSON response | `jq` | Discriminate on `type` (`paragraph`, `table`, `picture`, …), select by `page.pageIndex` / `readingOrder`, or pull nested fields without writing code. |
| Walk the response programmatically | the standard `json` module | The response is plain JSON; a recursive walk over `output.elements` is enough for type filtering, reading-order sort, and bounds extraction. |
| Project tables into rows / columns | `pandas` | Tables come as a flat `cells[]` list with `row` / `column` indices; `pd.DataFrame` reshapes them cleanly. |
| Render formulas | any LaTeX renderer (MathJax, KaTeX, matplotlib) | `formula` elements carry `latex` strings ready to feed a renderer. |
| Post-process markdown output (chunk on headings, strip tables, etc.) | `markdown-it-py`, `mistune`, or a regex on `#` lines | `output.markdown` uses standard heading hierarchy. |

For the per-call extraction-credit cost, read `usage.data_extraction_credits.cost`
directly from the response — no tool needed.
