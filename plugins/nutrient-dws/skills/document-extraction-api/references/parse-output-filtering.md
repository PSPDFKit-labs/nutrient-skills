# Parse Output — Filtering and Downstream Patterns

`/extraction/parse` returns a single document model in one call. You always receive all
element types at once — there is no per-type call. This document shows how to slice the
response into the shapes that downstream pipelines commonly need.

All examples below assume you have already run `parse.py` with `--output-format spatial`
and saved the response to `out.json`.

---

## Response structure

```
ParseResponse
├── output
│   ├── elements[]          (spatial mode)  — typed element list
│   └── markdown            (markdown mode) — whole-document Markdown string
├── metrics
│   ├── pagesProcessed
│   └── processingTimeMs
└── usage
    └── data_extraction_credits
        ├── cost            — extraction credits used by this call
        └── remainingCredits
```

### Element types (discriminated on `type`)

| type             | Key fields                                                      | Modes that produce it         |
|------------------|-----------------------------------------------------------------|-------------------------------|
| `paragraph`      | `text`, `role`, `words[]`, `bounds`, `readingOrder`             | all                           |
| `table`          | `rowCount`, `columnCount`, `cells[]`, `bounds`, `readingOrder`  | structure / understand / agentic |
| `formula`        | `latex`, `bounds`                                               | understand / agentic          |
| `picture`        | `classification`, `altDescription`, `bounds`                    | all (agentic adds VLM alt text) |
| `keyValueRegion` | `pairs[]` (each with `key`/`value` entities + bounds)           | understand / agentic          |
| `handwriting`    | `text`, `words[]`, `bounds`                                     | understand / agentic          |

---

## Reading-order plain text

Walk elements in `(page.pageIndex, readingOrder)` order, collect `text` from
`paragraph` and `handwriting` elements, join with newlines.

```python
import json

with open("out.json") as f:
    response = json.load(f)

elements = response["output"]["elements"]

text_elements = [
    e for e in elements
    if e.get("type") in ("paragraph", "handwriting") and e.get("text")
]

text_elements.sort(
    key=lambda e: (e.get("page", {}).get("pageIndex", 0), e.get("readingOrder", 0))
)

plain_text = "\n\n".join(e["text"] for e in text_elements)
print(plain_text)
```

### jq equivalent

```bash
jq -r '
  [.output.elements[]
   | select(.type == "paragraph" or .type == "handwriting")
   | select(.text != null)
  ]
  | sort_by([.page.pageIndex // 0, .readingOrder // 0])
  | .[].text
' out.json | paste -sd '\n\n' /dev/stdin
```

---

## Tables — rows and columns dict

Each `TableElement` carries a flat `cells[]` list. Reconstruct rows/columns by grouping
on `row` and `column` (both 0-indexed). Multi-span cells span `rowSpan` rows and
`colSpan` columns.

```python
def table_to_grid(table: dict) -> list[list[str]]:
    """Return a list-of-rows, each row a list of cell text values."""
    rows = table.get("rowCount", 0)
    cols = table.get("columnCount", 0)
    grid = [[""] * cols for _ in range(rows)]
    for cell in table.get("cells") or []:
        r, c = cell.get("row", 0), cell.get("column", 0)
        if r < rows and c < cols:
            grid[r][c] = cell.get("text", "")
    return grid


tables = [e for e in elements if e.get("type") == "table"]
for i, table in enumerate(tables):
    print(f"Table {i} (page {table.get('page', {}).get('pageIndex', 0)}):")
    for row in table_to_grid(table):
        print(" | ".join(row))
```

### jq — extract all table cells as JSON

```bash
jq '[
  .output.elements[]
  | select(.type == "table")
  | {
      page: .page.pageIndex,
      readingOrder,
      rowCount,
      columnCount,
      rows: (
        [ .cells[]? | {row, col: .column, text} ]
        | group_by(.row)
        | map(sort_by(.col) | map(.text))
      )
    }
]' out.json
```

---

## Key-value regions — key/value dict

`keyValueRegion` elements carry a `pairs[]` list. Each pair has a `key` entity and a
`value` entity, both with a `value` string field.

```python
kv_regions = [e for e in elements if e.get("type") == "keyValueRegion"]
for region in kv_regions:
    for pair in region.get("pairs") or []:
        key_text = pair.get("key", {}).get("value", "")
        val_text = pair.get("value", {}).get("value", "")
        confidence = pair.get("relationshipConfidence")
        print(f"{key_text!r}: {val_text!r}  (confidence={confidence})")
```

### jq equivalent

```bash
jq '[
  .output.elements[]
  | select(.type == "keyValueRegion")
  | .pairs[]?
  | { key: .key.value, value: .value.value, confidence: .relationshipConfidence }
]' out.json
```

---

## Filtering by element type

```python
from typing import Literal

def filter_elements(elements: list[dict], type_: str) -> list[dict]:
    return [e for e in elements if e.get("type") == type_]

paragraphs   = filter_elements(elements, "paragraph")
tables       = filter_elements(elements, "table")
formulas     = filter_elements(elements, "formula")
pictures     = filter_elements(elements, "picture")
kv_regions   = filter_elements(elements, "keyValueRegion")
handwriting  = filter_elements(elements, "handwriting")
```

### jq

```bash
# Count by type
jq '.output.elements | group_by(.type) | map({(.[0].type): length}) | add' out.json

# All tables on page 0
jq '[.output.elements[] | select(.type == "table" and .page.pageIndex == 0)]' out.json
```

---

## Formulas (LaTeX)

```python
formulas = [e for e in elements if e.get("type") == "formula" and e.get("latex")]
for f in formulas:
    print(f["latex"])
```

---

## Pictures with alt descriptions (agentic mode)

`agentic` mode uses a vision language model to generate `altDescription` on every
`picture` element. Other modes leave `altDescription` absent or empty.

```python
pictures = [e for e in elements if e.get("type") == "picture"]
for pic in pictures:
    print(f"[{pic.get('classification', 'unknown')}] {pic.get('altDescription', '')}")
```

---

## Checking extraction-credit cost

```python
usage = response.get("usage", {})
credits = usage.get("data_extraction_credits", {})
print(f"Cost: {credits.get('cost')} extraction credits")
print(f"Remaining: {credits.get('remainingCredits')}")
```

Note: `data_extraction_credits` reflects charges from the **extraction credits** bucket,
which is separate from the **processor API credits** bucket used by `/build`, `/sign`,
OCR, and other Processor API endpoints.

---

## Mode selection guide

| Intent | Recommended mode | Cost | Why |
|--------|-----------------|------|-----|
| RAG / search indexing / content migration — born-digital PDF | `text` + `markdown` output | 1 cr/pg | No OCR needed; fastest path to a Markdown string |
| RAG / search indexing — scanned or image PDF | `structure` + `markdown` output | 1.5 cr/pg | OCR required before Markdown assembly |
| Form / invoice extraction | `understand` + `spatial` output | 9 cr/pg | AI classification needed for reliable key-value and table detection |
| Layout-aware document understanding | `understand` + `spatial` output | 9 cr/pg | Semantic classification of paragraphs (Title, SectionHeader, etc.) |
| Deep visual understanding (charts, diagrams) | `agentic` + `spatial` output | 18 cr/pg | VLM generates alt descriptions on every picture element |
| Default / unknown intent | `structure` + `spatial` output | 1.5 cr/pg | Good balance: spatial elements with OCR, low cost |

All costs are **extraction credits per page** — a separate billing bucket from
processor API credits.
