---
name: make-pdf
description: Generate a finished PDF from Markdown or HTML via the Nutrient DWS Build API, with compliance-grade output options - accessible PDF/UA, archival PDF/A, and text watermarks. Use when the user asks to make, generate, or export a PDF from Markdown, HTML, notes, or a report, especially when the PDF must be accessible (PDF/UA, WCAG/ADA/EAA), archival (PDF/A), or watermarked. For processing an existing PDF (sign, redact, OCR, merge), use document-processor-api instead.
---

# Nutrient Make PDF

Turn a Markdown or HTML file into a finished PDF through the Nutrient DWS Build API. The differentiator over local `chromium --print-to-pdf` or Pandoc is the output stage: the same call can emit **tagged, accessible PDF/UA** or **archival PDF/A**, and stamp a diagonal text watermark — compliance work a plain HTML-to-PDF pipeline cannot do.

## Quick Start

All paths below are relative to this skill's directory (the directory containing `scripts/` and `assets/`).

1. Export the API key before generating (not needed for `--html-only` or the smoke test):
   - `export NUTRIENT_API_KEY="nutr_sk_..."` (the same variable the sibling `document-processor-api` scripts use; `NUTRIENT_DWS_API_KEY` is accepted as a fallback)
2. Generate:

```bash
uv run scripts/make-pdf.py --input report.md --out report.pdf
```

The `markdown-it-py` and `nutrient-dws` packages are fetched automatically on first use.

## Common Tasks

- Standard PDF from Markdown: `uv run scripts/make-pdf.py --input notes.md --out notes.pdf`
- Accessible PDF/UA (tagged, for WCAG/ADA/EAA requirements): add `--accessible`
- Archival PDF/A: add `--pdfa` (conformance via `--pdfa-level`, one of `pdfa-1a/1b/2a/2b/2u/3a/3u`, default `pdfa-2b`; only valid together with `--pdfa`)
- Draft watermark: add `--watermark DRAFT`
- Memo layout instead of the default document layout: `--template memo`
- Dark theme: `--theme dark`
- Title-page metadata: `--title`, `--subtitle`, `--author`, `--date` (or set them in Markdown frontmatter; CLI flags win)
- Inspect the rendered HTML without calling the API (offline, no key): `--html-only` (Markdown input only — errors on `.html` input, which already is the HTML)
- Debug layout alongside the PDF: `--output-html` writes the intermediate HTML next to the PDF

`--accessible` and `--pdfa` are mutually exclusive (one output type per build). Check exact arguments with `uv run scripts/make-pdf.py --help`.

## Input Rules

- `.md` input is converted to HTML with a CommonMark+GFM parser (tables, strikethrough, task lists), then wrapped in the selected template with the theme CSS inlined — one self-contained HTML file is uploaded.
- `.html` input is uploaded as-is; template, theme, and metadata flags do not apply and a warning names any that were passed. Use it when you already have styled HTML.
- YAML frontmatter in Markdown (`title`, `subtitle`, `author`, `date`, `template`, `theme`) controls the cover block; CLI flags override frontmatter. When no title is given anywhere, the first `#` heading (or the filename) becomes the document title, so accessible output always has a real title.
- External images require network fetches on the DWS side and referenced local images are not uploaded in v1 — embed images as `data:` URIs if they must appear.

## Layout Honesty (Chromium limits)

DWS renders HTML with headless Chromium (`printToPDF`). That means standard print CSS works (`@page` size and margins, `page-break-*`/`break-*` rules, `@media print`), but CSS Paged Media features Chromium does not implement will silently not render: `position: running()` running headers/footers, `counter(page)`, and `target-counter()` TOC page numbers. Do not promise page-numbered TOCs or running headers from CSS. If the user needs those, say so and offer the trade-offs (front-matter TOC without page numbers, or a different toolchain).

## Chaining Other Document Operations

Generation is one step. For operations on the produced PDF, chain the sibling `document-processor-api` skill scripts:

- Digitally sign the generated PDF: `document-processor-api/scripts/sign.py`
- Redact content: `document-processor-api/scripts/redact-ai.py`
- Merge with other documents: `document-processor-api/scripts/merge.py`

Run sibling scripts with `uv run` from their own skill directory. Example — "generate the report as PDF/A and sign it":

```bash
uv run scripts/make-pdf.py --input report.md --out report.pdf --pdfa
uv run ../document-processor-api/scripts/sign.py --input report.pdf --out report-signed.pdf
```

Both steps read the same `NUTRIENT_API_KEY` environment variable.

## Implementation Rules

- Fail fast with a clear message when `NUTRIENT_API_KEY` (or the `NUTRIENT_DWS_API_KEY` fallback) is missing (unless `--html-only`).
- Never log the API key or request headers.
- Write outputs to explicit paths and print created file paths on success (one path per line on stdout; progress on stderr).
- Non-zero exit on any failure; do not claim success unless the output file exists and is non-empty.

## Validation

Before calling this skill done after changes:

- `uv run scripts/smoke-test.py` — renders every template x theme combination offline (no network, no key) and checks Markdown features (headings, tables, code blocks) survive the pipeline.
- Generate one real PDF if a key is available, and verify it opens and is non-empty.
