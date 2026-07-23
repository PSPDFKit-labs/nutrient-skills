---
name: document-extraction-api
description: >-
  Two primitives of the Nutrient Data Extraction API. `parse` (`/extraction/parse`) returns
  the whole-document model — a structural JSON of typed elements with bounding boxes, or
  whole-document Markdown — for RAG ingestion, search indexing, content migration, or
  layout-aware understanding. `extract` (`/extraction/extract`) returns just the fields you
  define in a JSON Schema, each with a per-field citation grounding it to a page region. Route
  to `extract` for "pull the invoice number and total", "extract these fields", "map to my
  schema", or "with citations"; route to `parse` for "parse this document", "whole-document
  Markdown", "chunk for embeddings", or "extract every table/element" (no target schema).
  Triggers include parse this document, extract layout, RAG pipeline, schema extraction, field
  extraction, cited fields, invoice/form field extraction, document understanding.
license: MIT
metadata:
  author: nutrient-sdk
  version: "1.1"
  homepage: "https://www.nutrient.io/api/"
  repository: "https://github.com/PSPDFKit-labs/nutrient-skills"
  compatibility: "Requires Python 3.10+, uv, and internet. Works with Claude Code, Codex CLI, Gemini CLI, OpenCode, Cursor, Windsurf, GitHub Copilot, Amp, or any Agent Skills-compatible product."
  short-description: "Parse whole documents, or extract schema-defined fields with citations, via Nutrient Data Extraction"
---

# Nutrient Data Extraction

Two GA primitives, two scripts. **`parse`** (`scripts/parse.py`) returns the whole-document
model — typed elements (paragraphs, tables, formulas, pictures, key-value regions,
handwriting) with bounding boxes, or clean whole-document Markdown. **`extract`**
(`scripts/extract.py`) returns just the fields you define in a JSON Schema, each grounded to a
page region by a per-field citation.

## Choosing parse vs extract

| The request is about… | Use | Why |
|---|---|---|
| Named target fields — "the invoice number and total", "these fields", "map to my schema", "with citations" | **`extract`** | One call returns your fields, cited — no need to walk every element |
| The whole document — "parse this", "whole-document Markdown", "chunk for embeddings", RAG, search indexing, migration | **`parse`** | Whole-document model / Markdown for open-ended retrieval |
| Every table / all key-value regions (no target schema) | **`parse`** (spatial) | Enumerate all elements; `extract` needs a schema of what to pull |

For RAG *chunking* of a parsed document, see the sibling `grounded-rag-ingestion` skill. For
PDF generation, conversion, OCR, redaction, signing, or any `/build`-based workflow, use the
sibling `document-processor-api` skill.

## When to use

- Extract known fields with citations (invoice number, totals, dates, parties) → **`extract`**.
- Build a RAG ingestion pipeline: PDF -> Markdown -> chunks -> embeddings → **`parse`**.
- Index content for search or migrate documents into a new CMS → **`parse`**.
- Reconstruct page layout, or run layout-aware understanding (semantic roles, table cell
  spans, formulas in LaTeX, picture alt descriptions) → **`parse`**.

<!-- Roadmap: /extraction/generate_schema, /classify, and /form exist but are internal preview
     (data_extraction_preview flag; 404 for public tenants) — not surfaced here yet. -->

## `/extraction/extract` — schema field extraction with citations

Define the fields you want in a JSON Schema (root `type: object`); `extract` returns
`output.data` with those values and `output.metadata` with a per-field citation grounding each
to a page region (`options.includeCitations` defaults on). Accepts a local file **or a URL**.

```bash
# Pull schema-defined fields from a local invoice, with citations (default)
uv run scripts/extract.py --input invoice.pdf --schema fields.json --out result.json

# From a URL, higher-accuracy mode, persist the run
uv run scripts/extract.py --url https://example.com/form.pdf --schema fields.json \
  --out result.json --mode understand --store-run
```

Cost: `extract` bills the chosen parse mode **plus a flat +6 credits/page** (text 7,
structure 7.5, understand 15, agentic 24 cr/page). The script prints the server's authoritative
usage after the call and gates high estimates behind `--yes`. See
`references/extract-output-and-citations.md` for the response shape and citation structure.

For PDF generation, conversion, OCR, redaction, signing, watermarking, or any `/build`-based
workflow, use the sibling `document-processor-api` skill.

## Setup

DWS Extract is a separate product from DWS Processor and has its own API key.

- Get a Nutrient DWS Extract API key at <https://dashboard.nutrient.io/>.
- Export it as `NUTRIENT_EXTRACT_API_KEY`:
  ```bash
  export NUTRIENT_EXTRACT_API_KEY="pdf_live_..."
  ```
- Scripts live in `scripts/` relative to this SKILL.md. Use the directory containing this
  SKILL.md as the working directory:
  ```bash
  cd <directory containing this SKILL.md> && uv run scripts/<script>.py --help
  ```

Calling `/extraction/parse` with a DWS Processor key returns `403`. If your tenant has been
migrated to global DWS API keys, a single key set as either `NUTRIENT_EXTRACT_API_KEY` or
`NUTRIENT_API_KEY` will work for both products.

## `/extraction/parse` — one primitive, two output shapes

One call returns the full structural document model — typed elements with bounding boxes,
confidence scores, and reading order — or a whole-document Markdown string. You always
receive all element types in a single call.

### Picking a mode

Choose based on the user's intent and acceptable credit cost. All costs are
**extraction credits per page** — a separate billing bucket from the processor API
credits consumed by `/build`, `/sign`, OCR, and other DWS Processor endpoints.

**Principle — decide from the request alone; do not ask the user clarifying questions.**
Walk the checks below in order. Each rule that fires sets a minimum mode — the final
pick is the highest minimum across all rules that fired. If none fired, use the default
(rule 5).

1. **Explicit features named in the request** are non-negotiable.
   - Key-value pairs, form fields, semantic role classification (Title / SectionHeader /
     etc.), formulas, or handwriting → at minimum `understand` (9 cr/pg).
   - Alt text on pictures, charts, or diagrams → `agentic` (18 cr/pg).
2. **Document type implied by the request or filename.**
   - `form`, `invoice`, `receipt`, `application`, `claim` → likely contains key-value
     pairs → `understand`.
   - `chart`, `infographic`, or diagram-heavy doc + the user wants descriptions →
     `agentic`.
3. **OCR signal from filename or request** (`scanned`, `image-based`, `photographed`,
   `handwritten`, `screenshot`) → `structure` minimum; `text` mode silently fails on
   image-only input.
4. **Output format from intent.** RAG, search indexing, embeddings, or content migration
   → `markdown`. Layout overlay, per-element processing, or bounded extraction →
   `spatial`.
5. **No cues match anything above** → documented default `structure` + `spatial`
   (1.5 cr/pg). Handles both born-digital and scanned, gives bounded typed elements
   with table cells, never silently drops content.

| User intent | Mode | Output format | Cost | Notes |
|-------------|------|---------------|------|-------|
| RAG / search indexing / content migration — born-digital PDF | `text` | `markdown` | 1 cr/pg | Cheapest path; no OCR or AI needed |
| RAG / search indexing — scanned or image-based PDF | `structure` | `markdown` | 1.5 cr/pg | OCR required before Markdown assembly |
| Form / invoice extraction | `understand` | `spatial` | 9 cr/pg | AI classification for reliable key-value and table detection |
| Layout-aware document understanding | `understand` | `spatial` | 9 cr/pg | Semantic paragraph roles (Title, SectionHeader, etc.) |
| Deep visual understanding (charts, diagrams, alt text) | `agentic` | `spatial` | 18 cr/pg | VLM adds alt descriptions on every picture element |
| **Default / ambiguous intent** | **`structure`** | **`spatial`** | **1.5 cr/pg** | Good balance: OCR + spatial elements, low cost |

**Confirm before running when the estimated cost exceeds 200 extraction credits** —
roughly 11 pages of `agentic`, 22 of `understand`, 133 of `structure`, or 200 of `text`.
Surface the estimate (`pages × cost_per_page`) and ask the operator to confirm before
invoking. Under that threshold, just run.

`mode='text'` is incompatible with `output_format='spatial'`; the client rejects the
combination before the network call.

### Invocation

```bash
# Default: structure mode, spatial output
uv run scripts/parse.py --input doc.pdf --out out.json

# Markdown for RAG (text mode — cheapest)
uv run scripts/parse.py --input doc.pdf --out out.md --output-format markdown --mode text

# Form extraction (understand mode)
uv run scripts/parse.py --input doc.pdf --out out.json --mode understand

# Agentic (VLM alt text on pictures)
uv run scripts/parse.py --input doc.pdf --out out.json --mode agentic
```

The script prints extraction-credit usage after each run so you can verify the cost.

### Downstream consumption

After a single `/parse` call, slice the response for common needs:

- **Reading-order plain text**: walk `output.elements` sorted by `(page.pageIndex, readingOrder)`, join `paragraph` and `handwriting` `text` fields
- **Tables**: project `cells[]` on each `table` element into rows/columns using `cell.row` and `cell.column`
- **Key-value pairs**: read `pairs[]` on each `keyValueRegion` element — each pair has `.key.value` and `.value.value`
- **Formulas**: read `latex` on each `formula` element
- **Pictures**: read `classification` and `altDescription` (populated by `agentic` mode) on each `picture` element
- **Markdown output**: call with `--output-format markdown`; the script writes the Markdown string directly

For the canonical response schema and per-mode field availability, see the official docs linked from `references/parse-output-filtering.md`; that file also lists the tools we suggest for filtering and reshaping the response.

### Input constraint

`parse.py` only accepts **local file paths** — the underlying API endpoint is
multipart-only. For remote inputs, download the file first.

## Rules

- Always preserve the printed credit-usage summary in script output so the operator can
  observe per-call cost.
- Do not add a URL-fetch shortcut; the endpoint is multipart-only.
