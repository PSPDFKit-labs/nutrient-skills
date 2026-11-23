---
name: document-extraction-api
description: >-
  Use the Nutrient Data Extraction API to parse whole documents into Markdown or spatial
  elements, extract named fields such as invoice totals with source citations, classify
  documents against labels, or detect document boundaries in a merged packet.
license: MIT
metadata:
  author: nutrient-sdk
  version: "1.1"
  homepage: "https://www.nutrient.io/api/"
  repository: "https://github.com/PSPDFKit-labs/nutrient-skills"
  compatibility: "Requires Python 3.10+, uv, and internet. Works with Claude Code, Codex CLI, Gemini CLI, OpenCode, Cursor, Windsurf, GitHub Copilot, Amp, or any Agent Skills-compatible product."
  short-description: "Parse, extract cited fields, classify, or separate packets with Nutrient Data Extraction"
---

# Nutrient Data Extraction

Use this skill to build with the Data Extraction API. To process a file in chat, connect
the [hosted Nutrient MCP plugin](https://github.com/PSPDFKit/nutrient-mcp-plugins) for its
supported document tasks.

## Choose the operation

| Desired result | Use |
|---|---|
| Named fields, such as invoice number, total, and line items, with evidence | **`extract`** with a JSON Schema via `scripts/extract.py`. |
| Whole-document Markdown for RAG, search, or migration | **`parse`** with Markdown output via `scripts/parse.py`. |
| Document layout, bounding boxes, or every detected table | **`parse`** with spatial output via `scripts/parse.py`. |
| The likely document type, such as invoice, receipt, or contract | **`classify`** via the [Classify API](https://www.nutrient.io/guides/dws-data-extraction/classify.md). |
| Where the component documents start and end in a merged file | **`split`** via the [Split API](https://www.nutrient.io/guides/dws-data-extraction/split.md). |

For RAG *chunking* of a parsed document, see the sibling `grounded-rag-ingestion` skill. For
PDF generation, conversion, OCR, redaction, signing, or any `/build`-based workflow, use the
sibling `document-processor-api` skill.

### Classify or separate a packet

Follow the linked API examples for these operations. The bundled scripts cover parsing
and field extraction.

- Use `POST /extraction/classify` with at least two meaningful labels for a direct
  classification request. The result ranks labels with scores. Route ambiguous results to review.
- Use `POST /extraction/split` when the workspace has Split enabled. Read the one-based,
  inclusive page ranges and boundary confidence from `output.segments`. When you need
  one PDF per segment, the API can also return a ZIP download.
- For a mixed packet, review uncertain boundaries and classify the separated documents.
  Then extract against the right schema for each type. Keep each segment's original page
  range with the result so a citation can be traced back to the packet.
- When the user provides the page ranges and only wants pages cut out, use the
  `document-processor-api` skill instead.

## `/extraction/extract` — schema field extraction with citations

Define the fields you want in a JSON Schema (root `type: object`); `extract` returns
`output.data` with those values and `output.metadata` with per-field citation metadata
(`options.includeCitations` defaults on). Accepts a local file or a URL.

For a first run, save the schema from the [Extract API examples](https://www.nutrient.io/guides/dws-data-extraction/extract.md#request-formats)
as `fields.json` and use the [synthetic sample invoice](https://www.nutrient.io/downloads/pdf-to-json-review/invoice.pdf).
Look for invoice number `INV-DEMO-1042` and total `176.00` USD with citations on page 1.

```bash
# Pull schema-defined fields from a local invoice, with citations (default)
uv run scripts/extract.py --input invoice.pdf --schema fields.json --out result.json

# From the public sample URL
uv run scripts/extract.py --url https://www.nutrient.io/downloads/pdf-to-json-review/invoice.pdf \
  --schema fields.json --out result.json --mode understand
```

Use the [Data Extraction pricing guide](https://www.nutrient.io/guides/dws-data-extraction/pricing.md)
and the response's usage for current charges. The bundled script gates high local estimates
behind `--yes` and can display legacy credit-based estimates. See
`references/extract-output-and-citations.md` for the response shape. Include the source page
when reporting cited values, and flag missing or uncertain evidence for review.

## Setup

- Get an API key with Data Extraction access at <https://dashboard.nutrient.io/>.
- Export it as `NUTRIENT_EXTRACT_API_KEY`:
  ```bash
  export NUTRIENT_EXTRACT_API_KEY="pdf_live_..."
  ```
- Scripts live in `scripts/` relative to this SKILL.md. Use the directory containing this
  SKILL.md as the working directory:
  ```bash
  cd <directory containing this SKILL.md> && uv run scripts/<script>.py --help
  ```

The helpers prefer `NUTRIENT_EXTRACT_API_KEY` and can use a global key with Data Extraction
access via `NUTRIENT_API_KEY` when the first variable is unset.

## `/extraction/parse` — one primitive, two output shapes

One call returns a structural document model with typed elements, bounding boxes,
confidence scores, and reading order, or a whole-document Markdown string. The processing
mode determines which element types are available.

### Picking a mode

The [processing modes guide](https://www.nutrient.io/guides/dws-data-extraction/parsing/processing-modes.md)
recommends `auto` as a starting point for direct API integrations. It routes each page
to `structure`, `understand`, or `agentic`. The bundled `parse.py` helper takes explicit
modes and defaults to `structure` with spatial output.

| User intent | Mode | Output |
|---|---|---|
| Read an existing PDF text layer for search or RAG | `text` | Markdown |
| Read a scan or photo with OCR | `structure` | Markdown or spatial |
| Enumerate form regions or detect semantic layout | `understand` | Spatial |
| Describe figures or diagrams | `agentic` | Spatial |

For large runs, estimate the cost from the [current per-page prices](https://www.nutrient.io/guides/dws-data-extraction/pricing.md)
and the page count. When using a legacy credit estimate, confirm with the operator
before running above 200 extraction credits.

### Invocation

```bash
# Default: structure mode, spatial output
uv run scripts/parse.py --input doc.pdf --out out.json

# Markdown for RAG (text mode — cheapest)
uv run scripts/parse.py --input doc.pdf --out out.md --output-format markdown --mode text

# Enumerate all key-value regions of a form (understand mode) — for NAMED fields use extract
uv run scripts/parse.py --input doc.pdf --out out.json --mode understand

# Agentic (VLM alt text on pictures)
uv run scripts/parse.py --input doc.pdf --out out.json --mode agentic
```

The script reports legacy credit usage when present in the response. Use the API response
or dashboard to verify current charges.

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

`parse.py` accepts local file paths. For a document at a public URL, use the
[Parse API's documented JSON URL input](https://www.nutrient.io/guides/dws-data-extraction/parsing.md#json-body-with-url).
