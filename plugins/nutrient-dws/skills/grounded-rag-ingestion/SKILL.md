---
name: grounded-rag-ingestion
description: >-
  Chunk a document into provenance-carrying JSONL ready for embedding via the Nutrient Data
  Extraction API (`/extraction/parse`, spatial output). Every chunk carries element type, page
  index, bounding box, confidence, and reading order, traceable to a specific page region. Use
  for grounded or auditable RAG, cited retrieval, confidence-aware ingestion, or any pipeline
  that must prove which document region a retrieved answer came from. Triggers include grounded
  RAG, auditable RAG, RAG with provenance, chunk with bounding box, cite page, provenance-carrying
  chunks, confidence-aware chunking, or embedding pipeline. Not for cheap Markdown — use
  document-extraction-api with `--output-format markdown` for that.
license: MIT
metadata:
  author: nutrient-sdk
  version: "1.0"
  homepage: "https://www.nutrient.io/api/data-extraction-api/"
  repository: "https://github.com/PSPDFKit-labs/nutrient-skills"
  compatibility: "Requires Python 3.10+, uv, and internet. Works with Claude Code, Codex CLI, Gemini CLI, OpenCode, Cursor, Windsurf, GitHub Copilot, Amp, or any Agent Skills-compatible product."
  short-description: "Chunk documents into provenance-carrying JSONL for grounded, auditable RAG"
---

# Grounded RAG Ingestion

Turn a document into a stream of **provenance-carrying chunks** — one JSONL line per chunk,
each tagged with its element type, page index, bounding box, confidence score, and
reading-order index, all traceable back to a specific region of the source page.

The differentiator is provenance, a capability frontier-LLM Markdown extraction structurally
cannot supply: a downstream system can highlight the exact region of the source document a
retrieval result came from. That is the compliance-grade requirement for RAG in finance,
healthcare, and legal workflows where "the model said so" is not an acceptable citation. This
skill does not relitigate raw Markdown quality (see the `pdf-to-markdown` skill for that) — it
adds the provenance layer on top of Nutrient extraction.

This is a **doer skill**: a bundled `uv`-runnable Python script (`chunk.py`) drives the pipeline
end to end and emits JSONL to stdout or a file. It is **embedding-agnostic** — it stops at the
chunk boundary. No vector DB client, no embedding provider import.

## When to use

- **Grounded / cited RAG**: retrieval results include `page_index` and `bbox` so the UI can draw
  a highlight box on the source document.
- **Confidence-aware ingestion**: gate on `confidence >= threshold` to suppress low-confidence
  chunks before they reach the index.
- **Reading-order-aware chunking**: preserve `reading_order` so sliding-window chunking respects
  the document's logical sequence.
- **Auditable pipelines**: regulated workflows that must prove which page region a retrieved
  answer came from — the `bbox` + `page_index` tuple is the audit trail.

**Not for** cheap whole-document Markdown — that stays in `document-extraction-api` with
`--output-format markdown`. Not for vector-store upsert or embedding generation — this skill
stops at the chunk JSONL.

## Dependency: `document-extraction-api`

This skill calls `document-extraction-api` under the hood. **Read that skill first** for mode
selection, key setup, and credit-cost guidance. `chunk.py` reuses its `create_client()` helper
and `client.parse(..., output_format="spatial")` call — it does not re-implement the API call.

The extraction skill must be present in the same plugin at
`../document-extraction-api/scripts/`. If it lives elsewhere, set `PARSE_SCRIPT_PATH` to its
`scripts/` directory; `chunk.py` fails fast with a clear message if it cannot find it.

## Setup

DWS Extract is a separate product from DWS Processor and has its own API key.

- Get a Nutrient DWS Extract API key at <https://dashboard.nutrient.io/>.
- Export it as `NUTRIENT_EXTRACT_API_KEY`:
  ```bash
  export NUTRIENT_EXTRACT_API_KEY="pdf_live_..."
  ```
- Run from the directory containing this SKILL.md:
  ```bash
  cd <directory containing this SKILL.md> && uv run scripts/chunk.py --help
  ```

If your tenant has migrated to global DWS API keys, a single key set as either
`NUTRIENT_EXTRACT_API_KEY` or `NUTRIENT_API_KEY` works for both products.

## Mode selection

Mode selection for this skill follows the **same rules as `document-extraction-api`** (mode →
cost → when to use). Pass `--mode` through to the parse call; the default is `structure`.

| Mode | Cost (cr/pg) | When |
|------|--------------|------|
| `text` | 1 | Cheapest; incompatible with spatial — **not usable here** (this skill requires spatial) |
| `structure` | 1.5 | **Default.** OCR + spatial typed elements with bounds and tables |
| `understand` | 9 | AI layout: **required for `keyValueRegion` and `formula` elements** |
| `agentic` | 18 | VLM: adds `altDescription` on pictures |

> **Mode-gating — important.** `keyValueRegion` and `formula` elements are **only populated by
> `understand` mode or higher**. Under the default `structure` mode the key-value and formula
> chunk paths produce **nothing**. `chunk.py` warns on stderr when KV/formula content would be
> expected but the mode is too low. To exercise key-value chunking, pass `--mode understand`.

## Invocation

```bash
uv run scripts/chunk.py --input doc.pdf --out chunks.jsonl \
  [--doc-id ID] [--mode structure] \
  [--strategy element|reading-order-window|table-row] [--window-size 512] \
  [--min-confidence 0.0] [--skip-pictures] [--yes]
```

- `--out -` writes JSONL to stdout; otherwise to the named file (created with `0600`
  permissions — the JSONL carries extracted document text).
- Credit usage is printed to **stderr** after the parse call.

## Provenance chunk schema

Each JSONL line is one chunk:

| Field | Type | Source |
|-------|------|--------|
| `chunk_id` | string | deterministic — see below |
| `doc_id` | string | `--doc-id` or content hash of input bytes (never the basename) |
| `source_doc` | string | input basename, **display-only** |
| `element_type` | string | `paragraph`, `table`, `table_row`, `key_value_pair`, `formula`, `picture`, `handwriting` |
| `page_index` | int\|null | `element.page.pageIndex` (null when the element carries no page — never fabricated `0`) |
| `reading_order` | int\|null | `element.readingOrder` (null sorts last) |
| `bbox` | object\|null | `{x, y, width, height}` (normalized at runtime — see OQ-1; null when bounds are missing, never `{0,0,0,0}`) |
| `confidence` | float\|null | element-level `confidence` (0–1); null when unknown |
| `text` | string | element text per type-dispatch rules |
| `chunking_warning` | string? | present **only** on table span-expansion fallback chunks |

**`chunk_id`** is deterministic: `{doc_id}__p{page_index}_r{reading_order}_e{element_index}{disc}`.

- `_e{element_index}` (the element's position in the `(page_index, reading_order)` sort)
  guarantees **inter-element** uniqueness even when `reading_order` is `null` or shared by two
  elements.
- `{disc}` is the **intra-element** discriminator for elements that emit multiple chunks:
  `_tr{row}` (table-row), `_kv{pair_index}` (key-value pairs), `_w{window_index}`
  (reading-order windows); empty for single-chunk elements.
- `doc_id` is `--doc-id` if supplied, else a short content hash of the input bytes — **never the
  basename**, so two same-named files in different directories get disjoint IDs and upsert stays
  idempotent and tenant-safe.

Full spec: `references/provenance-chunk-schema.md`.

## Chunking strategies

- `--strategy element` (**default**): one chunk per typed spatial element — the purest expression
  of the grounding value prop. A `table` becomes one whole-table TSV chunk.
- `--strategy table-row`: each table row becomes its own chunk (`_tr{row}`) — better precision on
  wide financial tables.
- `--strategy reading-order-window`: sliding window over reading-order-sorted text elements
  (`--window-size` in tokens, `_w{window_index}`) — better retrieval coherence for prose, at some
  provenance precision (a window may span two elements' bboxes).

## Cost gate

`chunk.py` runs its **own** preflight before the network call: it counts the input PDF's pages
locally and estimates `pages × mode-cost`. If the estimate exceeds **200 credits** (or the API's
`remainingCredits` when known), it refuses to proceed unless `--yes` is passed or interactive
confirmation is given. (The extraction skill's 200-credit rule is an agent instruction, not
enforceable code — this gate is real code here.) For non-PDF inputs where local page count is
unavailable, the gate requires `--yes` for `understand`/`agentic` runs.

## Illustrative: passing chunks to an embedder

The boundary is the chunk schema. See `examples/embed-chunks-illustrative.py` for a minimal,
**illustrative-only** example of loading the JSONL and passing `text` to an embedder while
keeping `chunk_id` + `bbox` + `page_index` provenance attached to each embedding record. Swap the
provider import for your stack — no embedding library is a dependency of this skill.

## Anti-patterns

- Do **not** use this skill when raw Markdown is sufficient — use `document-extraction-api` with
  `--output-format markdown`.
- Do **not** bundle vector-DB or embedding-provider logic into `chunk.py` — the boundary is the
  chunk JSONL.
- Do **not** expect key-value or formula chunks under the default `structure` mode — they require
  `--mode understand`.
- Do **not** derive `doc_id` from the filename basename — it breaks cross-document collision
  safety (R15).

## Security Hardening Addendum

- Never store `NUTRIENT_EXTRACT_API_KEY` in committed files. Use process env injection at runtime
  (shell/export, secrets manager, or host env).
- The output JSONL carries extracted document text (potentially finance/health/legal content) and
  is written with `0600` permissions. Treat it as sensitive; do not commit it.
- `source_doc` carries the input basename, which may encode PII (e.g. `patient-jsmith.pdf`). For
  sensitive corpora, supply a sanitized `--doc-id` and be deliberate about what reaches the index.
- The script prints credit usage (the numeric cost only) to stderr and never logs the API key.

## Rules

- Always require spatial output — Markdown output loses provenance and is rejected.
- Preserve the printed credit-usage summary so the operator can observe per-call cost.
- Reuse `document-extraction-api`'s `create_client()` and `client.parse()`; do not re-implement
  the API call or mode-selection logic.

## Reference map

- `references/provenance-chunk-schema.md` — authoritative chunk schema, `chunk_id` derivation,
  chunking strategies, table span-expansion, key-value mapping.
- `examples/embed-chunks-illustrative.py` — illustrative embedding snippet (not a supported script).
- Sibling `document-extraction-api/SKILL.md` — mode selection, credit costs, key setup.
