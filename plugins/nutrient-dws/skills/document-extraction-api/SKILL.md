---
name: document-extraction-api
description: >-
  Parse documents into a structural model or whole-document Markdown via the Nutrient Data
  Extraction API (`/extraction/parse`). Use when the user wants to extract layout, tables,
  key-value pairs, formulas, or images with bounding boxes; build a RAG ingestion pipeline;
  produce Markdown for search indexing or content migration; or run layout-aware document
  understanding. Triggers include parse this document, extract layout, RAG pipeline, document
  understanding, form/invoice extraction, layout analysis, or whole-document Markdown.
license: MIT
metadata:
  author: nutrient-sdk
  version: "1.0"
  homepage: "https://www.nutrient.io/api/"
  repository: "https://github.com/PSPDFKit-labs/nutrient-skills"
  compatibility: "Requires Python 3.10+, uv, and internet. Works with Claude Code, Codex CLI, Gemini CLI, OpenCode, Cursor, Windsurf, GitHub Copilot, Amp, or any Agent Skills-compatible product."
  short-description: "Parse documents into a structural model or Markdown via Nutrient Data Extraction"
---

# Nutrient Data Extraction

Use Nutrient DWS Extract for document-understanding workflows where you need typed
elements (paragraphs, tables, formulas, pictures, key-value regions, handwriting) with
bounding boxes — or a clean Markdown representation of the whole document.

## When to use

- Build a RAG ingestion pipeline: PDF -> Markdown -> chunks -> embeddings.
- Index content for search or migrate documents into a new CMS.
- Extract structured fields from forms and invoices (key/value pairs, tables, semantic regions).
- Reconstruct page layout for downstream rendering or comparison.
- Run layout-aware document understanding (semantic paragraph roles, table cell spans,
  formulas in LaTeX, picture classification and alt descriptions).

This skill is **only** for `/extraction/parse`. For PDF generation, conversion, OCR,
redaction, signing, watermarking, or any `/build`-based workflow, use the sibling
`document-processor-api` skill.

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

Full patterns with Python snippets and jq one-liners: `references/parse-output-filtering.md`

### Input constraint

`parse.py` only accepts **local file paths** — the underlying API endpoint is
multipart-only. For remote inputs, download the file first.

## Rules

- One script per skill: `scripts/parse.py`. Do not add new committed scripts for /build
  workflows here — those belong in the sibling `document-processor-api` skill.
- Always preserve the printed credit-usage summary in script output so the operator can
  observe per-call cost.
- Do not add a URL-fetch shortcut; the endpoint is multipart-only.
