---
name: remediate-pdf
description: >-
  Make existing documents accessible with the Nutrient Accessibility API: auto-tag PDFs with
  PDF/UA semantic structure (headings, lists, tables, reading order) and validate PDFs against
  PDF/UA-1 with a JSON report of every failed check. Routes Word, image, and scanned files through
  conversion and OCR first. Use when the user wants to make a PDF accessible, auto-tag for screen
  readers, remediate for PDF/UA as part of Section 508 work, check whether a PDF passes PDF/UA, or
  make a Word file or scan accessible. Triggers include auto-tag PDF, make this PDF accessible,
  tag for screen readers, remediate accessibility, PDF/UA remediation, validate PDF/UA, or check
  PDF/UA. Hand edits to reading order, alt text, or tags go to Accessibility Studio. To generate a
  NEW accessible PDF from Markdown or HTML, use make-pdf instead. Converting to PDF/A, merging, or
  signing go to document-processor-api.
license: MIT
metadata:
  author: nutrient-sdk
  version: "1.1"
  homepage: "https://www.nutrient.io/api/accessibility-api/"
  repository: "https://github.com/PSPDFKit-labs/nutrient-skills"
  compatibility: "Requires Python 3.10+, uv, and internet. Works with Claude Code, Codex CLI, Gemini CLI, OpenCode, Cursor, Windsurf, GitHub Copilot, Amp, or any Agent Skills-compatible product."
  short-description: "Make existing documents accessible: auto-tag and validate PDF/UA via the Nutrient Accessibility API"
---

# Nutrient Remediate PDF

Make an existing document accessible with the Nutrient Accessibility API:

- **Auto-tag** a PDF with PDF/UA semantic structure: headings (H1–H6), lists, tables (TR/TD/TH),
  reading order, and artifact marking. Writes a tagged copy; the original is untouched.
- **Validate** a PDF against PDF/UA-1. Writes the JSON report and summarizes every failed check.

Files the Accessibility API can't take directly (Word, Excel, PowerPoint, images, scans without a
text layer) are converted or OCR'd first with the `document-processor-api` skill.

## When to use

- "Make this PDF accessible" / "auto-tag for screen readers" / "tag this PDF for PDF/UA"
- "Does this PDF pass PDF/UA?" / "validate this PDF for accessibility"
- "Make this Word document accessible" / "make this scanned PDF accessible"
- "Prepare this document for Section 508" (the tagging and PDF/UA checking steps)

## Which path to take

Start from what the user has:

| Input | Path |
|---|---|
| PDF without tags | `autotag.py`, then `validate.py` |
| PDF that already has tags | `validate.py` first. If it fails, suggest Accessibility Studio's Repair, which keeps the existing tags. Re-tag with `autotag.py` only when the tags are unusable, and warn the user that re-tagging replaces the existing structure and alt text |
| Scanned PDF (no text layer) | OCR with `document-processor-api`'s `ocr.py`, then `autotag.py`, then `validate.py` |
| Word, Excel, or PowerPoint file | Best: fix it in the source (heading styles, alt text, title, language) and export a tagged PDF (Word: Save as PDF with "Document structure tags for accessibility"), then `validate.py`. Otherwise convert with `document-processor-api`'s `convert.py`, then `autotag.py` and `validate.py` |
| Image of a document | `document-processor-api`'s `ocr.py`, then `autotag.py` and `validate.py` |

Validate before the user publishes or shares a file. Auto-tagging is built to produce PDF/UA-1
conformant output, but not every file passes (see Anti-patterns). Skip validation only for
internal drafts the user doesn't plan to publish.

`document-processor-api` is part of the `nutrient-dws` plugin
(`/plugin install nutrient-dws@nutrient-skills`). Its scripts read `NUTRIENT_API_KEY`, for example
`uv run scripts/ocr.py --input scan.pdf --languages english --out scan-ocr.pdf` and
`uv run scripts/convert.py --input report.docx --format pdf --out report.pdf` (check its SKILL.md
for current flags).

## Disambiguation from sibling skills

- **Use `make-pdf`** (its own plugin: `/plugin install make-pdf@nutrient-skills`) to generate a NEW
  compliant PDF from Markdown or HTML.
- **Use `document-processor-api`** to convert to PDF/A, merge, sign, or produce PDF/UA as one
  output target of a wider `/build` job. Both that skill and this one use the same auto-tagging
  engine (`pdf_to_pdfua`); this skill is the Accessibility API surface with validation.

## Setup

- Get an API key at <https://dashboard.nutrient.io/>. On current plans, one Nutrient account and
  key cover the Accessibility API and the Processor API.
- Export it as `NUTRIENT_ACCESSIBILITY_API_KEY` (the scripts also accept `NUTRIENT_API_KEY`):
  ```bash
  export NUTRIENT_ACCESSIBILITY_API_KEY="pdf_live_..."
  ```
- Run the scripts by their path in this skill directory and pass **absolute** paths for
  `--input`, `--output`, and `--report`, so the user's files resolve from any working directory:
  ```bash
  uv run <skill-dir>/scripts/autotag.py --help
  ```

## Operations

### `autotag.py` — auto-tag a PDF

```bash
uv run <skill-dir>/scripts/autotag.py --input /abs/doc.pdf --output /abs/doc-tagged.pdf
uv run <skill-dir>/scripts/autotag.py --url https://example.com/doc.pdf --output /abs/doc-tagged.pdf
```

- `POST https://api.nutrient.io/accessibility/autotag`, multipart field `file`. `--url` is
  downloaded client-side (https on port 443, public addresses only, no redirects).
- Writes the tagged PDF to `--output` (default `<input-stem>-tagged.pdf`) and prints the pages
  processed. Refuses to replace an existing file unless `--overwrite` is passed.
- Exit codes: 0 = written; 1 = error; 2 = stopped at the cost gate; 4 = the PDF has no text layer,
  so OCR it first (`--allow-no-text` overrides).

### `validate.py` — check a PDF against PDF/UA-1

```bash
uv run <skill-dir>/scripts/validate.py --input /abs/doc.pdf
NUTRIENT_PDF_PASSWORD="..." uv run <skill-dir>/scripts/validate.py --input /abs/protected.pdf --with-password
```

- `POST https://api.nutrient.io/accessibility/validate_pdfua`, multipart field `file`.
- A completed validation returns HTTP 200 whether or not the PDF passes. The script reads
  `isValid`, writes the report to `--report` (default `<input-stem>-validation.json`), and prints
  each failed check with its occurrences.
- Exit codes: 0 = passed machine validation; 3 = failed; 1 = error.
- `--with-password` sends the password from `NUTRIENT_PDF_PASSWORD` in the
  `pspdfkit-pdf-password` header. A `403` means the password is missing or wrong, or the key isn't
  enabled for the Accessibility API.

## Decision rules

- **Cost.** Auto-tagging is billed per page and validation per validation, from the account's
  monthly usage, then the wallet (rates: <https://www.nutrient.io/api/pricing/>). `autotag.py`
  stops with exit 2 above `--confirm-over` pages (default 10) or when the page count is unknown,
  as with every `--url`. Tell the user the page count and re-run with `--yes` only after they
  confirm.
- **Watermark.** On the free plan, Processor output (`convert.py`, `ocr.py`) is watermarked until
  the account adds a wallet, and auto-tagging tags the watermark as page content. Tell the user
  before preparing documents to publish.
- **Max file size** is 150 MiB per request. For larger documents, split first with
  `document-processor-api`'s `split.py`.
- **Do not auto-retry on a 2xx response**: each call is billed.

## What a person still has to check

A pass from `validate.py` covers the machine-testable PDF/UA-1 requirements. Before calling a
document accessible, ask the user to have someone check:

- that alt text describes each image (the API passes placeholder text such as "image")
- that the reading order is logical and tag types are right (for example, a heading not tagged as
  a paragraph), with heading levels that make sense
- that table headers belong to the right cells, and link text makes sense on its own
- that the document title and language are correct, not just present
- color contrast and meaning conveyed by color alone (not checked by PDF/UA validation)

## What the API can't do: send people to Accessibility Studio

Some fixes need a person and a visual editor, and have no API. When a validation report or the
user's request calls for them, point the user to Accessibility Studio in the Nutrient dashboard
(<https://dashboard.nutrient.io/>):

- **Repair**: fix the existing tags of a failing PDF without re-tagging it.
- **Remediation**: edit tag types, alternative text, actual text, and language on the page, with
  one-click fixes for common structure, table, list, heading, and form issues.
- **Reading order**: drag blocks into the order a screen reader should follow.
- **Placeholder alternative text**: Studio's validation warns about figures whose alt text is a
  placeholder. The API report passes placeholder text such as "image".

Editing tags in Studio is free; only validation is billed. Manual edits can break conformance (for
example, changing the first heading from H1 to H3), so validate again after editing.

## Anti-patterns

- Do **not** claim WCAG, ADA, or Section 508 compliance. Section 508 requires WCAG 2.0 AA for
  documents; PDF/UA-1 conformance supports many of those criteria but doesn't establish
  conformance on its own. Auto-tagged files passed PDF/UA-1 validation 96.5 percent of the time
  in Nutrient's March 2026 benchmark of 3,157 files checked with veraPDF
  (<https://www.nutrient.io/blog/pdf-ua-compliance-guide/>), so not every file passes.
- Do **not** report a pass as "accessible" or "fully conformant". Say it passed PDF/UA-1 machine
  validation, and list the human checks above.
- Do **not** read an HTTP 200 from validation as a pass. Check `isValid`.
- Do **not** auto-tag an image-only scan without OCR. Auto-tagging doesn't add a text layer, so
  the result has no readable text.
- Do **not** add `--yes` by default. It skips the cost gate.
- Do **not** route PDF/A conversion, merging, or signing here — those belong to
  `document-processor-api`.

## Security Hardening Addendum

- Never store the API key or PDF passwords in committed files. Use process env injection at
  runtime (shell/export, secrets manager, or host env).
- The scripts never print the API key or PDF password, and redact both from any error output.
  The PDF password is read only from `NUTRIENT_PDF_PASSWORD`.
- `--url` inputs must be https on port 443 and resolve to public addresses; the address actually
  connected to is checked again, redirects are not followed, and the download is capped at
  150 MiB and 300 seconds. The Nutrient backend never fetches the URL. Do not pass unsanitized
  user-controlled strings to `--url`.
- Outputs (tagged PDFs, reports) are written with `0600` permissions, never through a symlink,
  never over the input, and never over an existing file without `--overwrite`.

## Reference map

- `references/accessibility-api-reference.md` — endpoints, request and response shapes, report
  schema, error codes, and pricing model.
- `references/pdf-ua-wcag-compliance-notes.md` — what auto-tagging and validation cover, PDF/UA vs
  WCAG, Section 508 relationship.
- `scripts/verify-pdf.py` — the bundled offline structural checker (the identical file ships in the
  `make-pdf` plugin; keep them in sync). Use it when no API key is available or for a free local
  check; `validate.py` is the authoritative PDF/UA-1 validation.
- Sibling `document-processor-api/SKILL.md` — conversion, OCR, splitting, the `/build` PDF/UA
  output target, and the same underlying auto-tagging engine.
- The `make-pdf` skill (separate plugin: `make-pdf@nutrient-skills`) — generate NEW compliant
  PDFs from Markdown/HTML.
