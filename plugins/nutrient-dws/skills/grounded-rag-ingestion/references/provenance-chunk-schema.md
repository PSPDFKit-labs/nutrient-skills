# Provenance Chunk Schema

Authoritative specification for the chunks `chunk.py` emits. Both the SKILL.md and `chunk.py`
implement against this document.

## 1. Chunk schema

One JSONL line per chunk. Every chunk carries:

| Field | Type | Source field (spatial output) | Notes |
|-------|------|-------------------------------|-------|
| `chunk_id` | string | derived | deterministic — see §2 |
| `doc_id` | string | `--doc-id` or content hash | stable document identity; never the basename |
| `source_doc` | string | input basename | **display-only**; may encode PII — sanitize via `--doc-id` for sensitive corpora |
| `element_type` | string | `element.type` (normalized) | `paragraph`, `table`, `table_row`, `key_value_pair`, `formula`, `picture`, `handwriting`, `reading_order_window` |
| `page_index` | int | `element.page.pageIndex` | 0-based |
| `reading_order` | int \| null | `element.readingOrder` | null sorts last on its page |
| `bbox` | object | `element.bounds` | normalized to `{x, y, width, height}` — see §4 / OQ-1 |
| `confidence` | float \| null | `element.confidence` (0–1) | for key-value pairs, `relationshipConfidence` with element-level fallback |
| `text` | string | per type-dispatch (§3, §5, §6) | the chunk's textual content |
| `chunking_warning` | string (optional) | — | present **only** on table span-expansion fallback chunks; declared in the schema so strict validators do not break on the dense-table case |

## 2. `chunk_id` derivation

```
{doc_id}__p{page_index}_r{reading_order}_e{element_index}{disc}
```

- **`doc_id`** — caller `--doc-id`, else the first 12 hex of SHA-256 over the input bytes.
  **Never the filename basename**, so `a/invoice.pdf` and `b/invoice.pdf` get disjoint IDs and
  vector-DB upsert stays idempotent and tenant/corpus-safe (cross-document collision avoidance).
- **`_e{element_index}`** — the element's stable position in the `(page_index, reading_order)`
  sort. This guarantees **inter-element** uniqueness even when `reading_order` is `null` (missing
  `readingOrder`, sorted last) or shared by two elements — a collision the bare `_r` segment
  cannot prevent on the default `--strategy element` path.
- **`{disc}`** — the **intra-element** discriminator for elements that emit more than one chunk:
  - `_tr{row}` — table-row chunks (`--strategy table-row`)
  - `_kv{pair_index}` — key-value pairs
  - `_w{window_index}` — reading-order windows
  - empty — single-chunk elements (paragraph, handwriting, formula, picture, whole-table default)

There is **no `_c{row}_{col}` per-cell discriminator**: no strategy emits per-cell chunks, so
cells are never standalone chunks. The whole-table default emits one chunk and needs only `_e`.

Three collision dimensions are covered: **cross-document** (`doc_id`), **inter-element**
(`_e{element_index}`, incl. null/duplicate `reading_order`), and **intra-element** (`{disc}`).

## 3. Chunking strategies

| Strategy | Flag | Behavior |
|----------|------|----------|
| Element (default) | `--strategy element` | One chunk per typed spatial element. A `table` becomes one whole-table TSV chunk. |
| Reading-order window | `--strategy reading-order-window` | Sliding window over reading-order-sorted text elements (`paragraph`, `handwriting`); `--window-size` in approximate tokens; window bbox is the union of member bboxes. Trades some provenance precision for retrieval coherence. |
| Table-row | `--strategy table-row` | Each table row becomes its own chunk (`element_type=table_row`, `_tr{row}`). Better precision on wide financial tables. |

## 4. Table span expansion

`table` elements carry `cells[]` with `row`, `column`, `rowSpan`, `colSpan`, `text`. Before
rendering, expand spans into a rectangular grid:

1. Compute `max_row` / `max_col` from `row + rowSpan - 1` and `column + colSpan - 1`.
2. Fill an `(max_row+1) × (max_col+1)` grid; a spanning cell writes its text into every covered
   cell that is still empty.
3. Render rows as tab-joined lines.

If expansion produces an inconsistent grid (e.g. malformed span metadata), do **not** crash:
emit the whole table as a single chunk with a flat cell join and set `chunking_warning`. Dense
financial schedules with multi-level headers and merged cells are the known hard case.

`bbox` normalization (OQ-1): the element-extraction guide shows `bounds` as
`{x, y, width, height}`; the API landing page shows `[x1, y1, x2, y2]`. The canonical form here
is `{x, y, width, height}`; `chunk.py` normalizes either shape at runtime. **Confirmed at the
U2 smoke test (2026-06-22): the live `/extraction/parse` response returns the object form
`{x, y, width, height}`.** The array-form normalization is retained defensively.

## 5. Key-value region mapping

Each `pair` in a `keyValueRegion` element becomes one chunk:

- `text = "{key.value}: {value.value}"` — `key` and `value` are **nested objects** exposing a
  `.value` string field, not bare strings. Formatting the objects directly would emit dict reprs
  into the chunk text.
- `element_type = "key_value_pair"`, `chunk_id` suffix `_kv{pair_index}`.
- `bbox` = union of the pair's key and value bounds.
- `confidence` = the pair's `relationshipConfidence` when present, else the parent element's
  `confidence`.

**Mode-gated:** `keyValueRegion` (and `formula`) elements are only populated by `understand`
mode or higher. Under the default `structure` mode they are absent and these chunks are empty;
`chunk.py` warns on stderr.

## 6. Element-type passthrough

| Element type | Included by default | Text source | Notes |
|--------------|---------------------|-------------|-------|
| `paragraph` | yes | `text` | — |
| `handwriting` | yes | `text` | — |
| `table` | yes | TSV of cells (§4) | or per-row under `--strategy table-row` |
| `keyValueRegion` | yes (understand+) | `key.value: value.value` (§5) | one chunk per pair |
| `formula` | yes (understand+) | `[formula] {latex}` | — |
| `picture` | configurable | `altDescription` (agentic) | skipped if empty or `--skip-pictures` |

`--min-confidence` drops chunks below the threshold after assembly (null confidence is kept);
the dropped count is logged to stderr.
