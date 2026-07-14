---
name: make-pdf
description: Generate finished PDFs from Markdown or HTML via the Nutrient DWS Build API - single files or whole directories - with compliance-grade output options (accessible PDF/UA, archival PDF/A, text watermarks) and built-in conformance verification. Use when the user asks to make, generate, export, or batch-convert PDFs from Markdown, HTML, notes, or reports, especially when PDFs must be accessible (PDF/UA, WCAG/ADA/EAA), archival (PDF/A), or watermarked - or to check whether an existing PDF carries valid PDF/UA or PDF/A markers. For processing an existing PDF (sign, redact, OCR, merge), use document-processor-api instead.
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
- Batch: point `--input` at a directory (with `--out <dir>`, required) to convert every `.md`/`.html` in it — see Batch Conversion below

`--accessible` and `--pdfa` are mutually exclusive (one output type per build). Check exact arguments with `uv run scripts/make-pdf.py --help`.

## Input Rules

- `.md` input is converted to HTML with a CommonMark+GFM parser (tables, strikethrough, task lists), then wrapped in the selected template with the theme CSS inlined — one self-contained HTML file is uploaded.
- `.html` input is uploaded as-is; template, theme, and metadata flags do not apply and a warning names any that were passed. Use it when you already have styled HTML.
- YAML frontmatter in Markdown (`title`, `subtitle`, `author`, `date`, `template`, `theme`) controls the cover block; CLI flags override frontmatter. When no title is given anywhere, the first `#` heading (or the filename) becomes the document title, so accessible output always has a real title.
- External images require network fetches on the DWS side and referenced local images are not uploaded in v1 — embed images as `data:` URIs if they must appear.

## Verification (built in)

Compliance outputs are verified, not just labeled. With `--accessible` or `--pdfa`, the generated PDF is automatically checked after the build (`--no-verify` opts out); exit code 3 means "generated but failed verification" — the PDF is kept on disk so you can inspect it. If the verifier itself cannot run, the build still exits 3 rather than silently passing; `--no-verify` is the explicit way to accept unverified output. Passing `--verify` without a compliance flag is rejected up front — a standard PDF has no conformance claim to check.

Two assurance levels, and be honest about which one ran:

- **Structural checks** (always available, via `scripts/verify-pdf.py`): the PDF/UA-1 claim marker (`pdfuaid` XMP part 1 — PDF/UA-2 documents are out of scope), tagged-structure signals (`MarkInfo`, `StructTreeRoot`), language, `DisplayDocTitle`, and a non-empty document title — or the PDF/A identification (`pdfaid` part + conformance, matched against the requested level). These catch real failures but are **not a full conformance audit**.
- **Full audit** (optional): if `verapdf` is installed on PATH, the verifier also runs veraPDF for a genuine conformance validation and reports its verdict. Recommend installing veraPDF when the user's requirement is regulatory (ADA/EAA deadlines, records retention).

The verifier also works standalone on any PDF, including ones this skill did not create:

```bash
uv run scripts/verify-pdf.py --input existing.pdf --profile pdfua
uv run scripts/verify-pdf.py --input archive-dir/ --profile pdfa --pdfa-level pdfa-2b
```

## Batch Conversion

`--input <directory>` converts every `.md`, `.markdown`, `.html`, and `.htm` file directly in that directory (non-recursive), up to 4 concurrently:

```bash
uv run scripts/make-pdf.py --input reports/ --out pdfs/ --accessible
```

- `--out <dir>` is required for directory input; outputs are named `<stem>.pdf`.
- Per-document metadata comes from each file's frontmatter, first `#` heading, or filename — global `--title`/`--subtitle` are rejected for directory input. Shared flags (`--template`, `--theme`, `--author`, `--date`, `--watermark`, compliance and verify flags) apply to every file.
- Failures don't stop the batch: a summary on stderr lists converted/verified/failed counts, stdout still prints only created file paths. Exit 0 = all good, 1 = at least one build failed, 3 = builds succeeded but at least one verification failed.
- Batch mode never overwrites existing outputs (and refuses inputs that would collide on the same output name) — point `--out` at a fresh directory or remove stale files when regenerating.

## Layout Honesty (Chromium limits)

DWS renders HTML with headless Chromium (`printToPDF`). That means standard print CSS works (`@page` size and margins, `page-break-*`/`break-*` rules, `@media print`), but CSS Paged Media features Chromium does not implement will silently not render: `position: running()` running headers/footers, `counter(page)`, and `target-counter()` TOC page numbers. Do not promise page-numbered TOCs or running headers from CSS. If the user needs those, say so and offer the trade-offs (front-matter TOC without page numbers, or a different toolchain).

## Chaining Other Document Operations

Generation is one step. Related operations live in sibling plugins from the same marketplace:

- Sign, redact, or merge the produced PDF: the `document-processor-api` skill — `/plugin install nutrient-dws@nutrient-skills`. Its scripts read the same `NUTRIENT_API_KEY`; run them from that skill's own directory, e.g. `uv run scripts/sign.py --input report.pdf --out report-signed.pdf`.
- Make an EXISTING PDF accessible (auto-tag for PDF/UA): the `remediate-pdf` skill — `/plugin install remediate-pdf@nutrient-skills`. This skill generates new PDFs; that one fixes old ones (and bundles the same `verify-pdf.py`).

## Implementation Rules

- Fail fast with a clear message when `NUTRIENT_API_KEY` (or the `NUTRIENT_DWS_API_KEY` fallback) is missing (unless `--html-only`).
- Never log the API key or request headers.
- Write outputs to explicit paths and print each created file path (one path per line on stdout; progress on stderr). A debug HTML path prints as soon as the file exists, even if a later build step fails.
- Non-zero exit on any failure; do not claim success unless the output file exists and is non-empty.

## Validation

Before calling this skill done after changes:

- `uv run scripts/smoke-test.py` — offline (no network, no key): every template x theme combination, Markdown feature survival (headings, tables, code blocks), verifier checks against constructed fixtures, and batch discovery.
- Generate one real PDF if a key is available; for compliance outputs let the built-in verification run (or run `verify-pdf.py` explicitly) rather than only checking the file is non-empty.
