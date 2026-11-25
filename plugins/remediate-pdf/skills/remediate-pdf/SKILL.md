---
name: remediate-pdf
description: >-
  Make existing documents accessible with the Nutrient Accessibility API: auto-tag PDFs with
  PDF/UA semantic structure (headings, lists, tables, reading order), validate PDFs against
  PDF/UA-1 with a JSON report of every failed check, and prepare Word, Excel, PowerPoint, image,
  and scanned files with conversion and OCR first. Use when the user wants to make a PDF accessible,
  auto-tag for screen readers, remediate for PDF/UA or Section 508, check whether a PDF passes
  PDF/UA, or make a Word file or scan accessible. Triggers include auto-tag PDF, make this PDF
  accessible, tag for screen readers, remediate accessibility, PDF/UA remediation, validate PDF/UA,
  check PDF/UA, or Section 508 remediation. To generate a NEW accessible PDF from Markdown or HTML,
  use make-pdf instead. Converting to PDF/A, merging, or signing go to document-processor-api.
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
- **Prepare** files the Accessibility API can't take directly: convert Word, Excel, PowerPoint,
  text, and image files to PDF, and run OCR on scans, through the Processor API.

## When to use

- "Make this PDF accessible" / "auto-tag for screen readers" / "tag this PDF for PDF/UA"
- "Does this PDF pass PDF/UA?" / "validate this PDF for accessibility"
- "Make this Word document accessible" / "make this scanned PDF accessible"
- "Prepare this document for Section 508" (the tagging and PDF/UA checking steps)

## Which path to take

Start from what the user has:

| Input | Path |
|---|---|
| PDF without tags | `autotag.py`, then optionally `validate.py` for a report |
| PDF that already has tags | `validate.py` first. If it fails, re-tag with `autotag.py` and validate again |
| Scanned PDF (no text layer) | `prepare.py --ocr <language>`, then `autotag.py` |
| Word, Excel, PowerPoint, text, or image file | `prepare.py` (add `--ocr` for images of text), then `autotag.py` |

Auto-tagging is built to produce PDF/UA-1 conformant output, so validating every auto-tagged file
is optional at volume. Validate when the user wants a report, when the input already had tags, or
after any manual edits.

## Disambiguation from sibling skills

- **Use `make-pdf`** (its own plugin: `/plugin install make-pdf@nutrient-skills`) to generate a NEW
  compliant PDF from Markdown or HTML.
- **Use `document-processor-api`** to convert to PDF/A, merge, sign, or produce PDF/UA as one
  output target of a wider `/build` job. Both that skill and this one use the same auto-tagging
  engine (`pdf_to_pdfua`); this skill is the Accessibility API surface with validation.

## Setup

- Get an API key at <https://dashboard.nutrient.io/>. One Nutrient account and key cover the
  Accessibility API and the Processor API that `prepare.py` uses.
- Export it as `NUTRIENT_ACCESSIBILITY_API_KEY` (`prepare.py` also accepts `NUTRIENT_API_KEY`):
  ```bash
  export NUTRIENT_ACCESSIBILITY_API_KEY="pdf_live_..."
  ```
- Run from the directory containing this SKILL.md:
  ```bash
  cd <directory containing this SKILL.md> && uv run scripts/autotag.py --help
  ```

## Operations

### `autotag.py` — auto-tag a PDF

```bash
uv run scripts/autotag.py --input doc.pdf --output doc-tagged.pdf
uv run scripts/autotag.py --url https://example.com/doc.pdf --output doc-tagged.pdf
```

- `POST https://api.nutrient.io/accessibility/autotag`, multipart field `file`. `--url` is
  validated (https-only, public address) and downloaded client-side; redirects are not followed.
- Writes the tagged PDF to `--output` (default `<input-stem>-tagged.pdf`) and prints the pages
  processed. Warns when the PDF has no text layer, which means it needs OCR first.

### `validate.py` — check a PDF against PDF/UA-1

```bash
uv run scripts/validate.py --input doc.pdf
uv run scripts/validate.py --input protected.pdf --password-env PDF_PASSWORD
```

- `POST https://api.nutrient.io/accessibility/validate_pdfua`, multipart field `file`.
- A completed validation returns HTTP 200 whether or not the PDF conforms. The script reads
  `isValid`, writes the report to `--report` (default `<input-stem>-validation.json`), and prints
  each failed check with its occurrences. Exit code 0 = conforms, 3 = does not conform, 1 = error.
- Pass a PDF password through an environment variable named with `--password-env`; it is sent in
  the `pspdfkit-pdf-password` header. A `403` means the password is missing or wrong.

### `prepare.py` — convert and OCR before auto-tagging

```bash
uv run scripts/prepare.py --input report.docx             # writes report.pdf
uv run scripts/prepare.py --input scan.pdf --ocr english  # writes scan-ocr.pdf
uv run scripts/prepare.py --input photo.jpg --ocr english,german
```

- `POST https://api.nutrient.io/build` with the file as the only part, plus an `ocr` action when
  `--ocr` is set. Accepts Word, Excel, PowerPoint, RTF, ODT, text, and image files, and PDFs for
  OCR. CSV, Markdown, and HTML are not supported.

## Decision rules

- **Cost.** Auto-tagging is billed per page and validation per validation; conversion and OCR are
  billed at the Processor API's rates (<https://www.nutrient.io/api/pricing/>). Everything draws
  from the account's monthly usage, then the wallet. `autotag.py` and `prepare.py --ocr`
  ask for confirmation above `--confirm-over` pages (default 20); pass `--yes` for known-safe runs.
- **Free-plan watermark.** On the free plan, `prepare.py` output carries an evaluation watermark,
  and auto-tagging tags it as page content. Tell the user before preparing documents to publish.
- **Max file size** is 150 MiB per request. For larger documents, split first with
  `document-processor-api/split.py`.
- **Do not auto-retry on a 2xx response** — each call is billed.

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

- Do **not** claim WCAG, ADA, or Section 508 compliance. PDF/UA-1 is the technical standard; the
  wider regulations depend on the content, such as whether alt text describes an image, and need
  human review. Auto-tagging is built to produce PDF/UA-1 conformant output (96.5 percent passed
  in Nutrient's March 2026 benchmark).
- Do **not** read an HTTP 200 from validation as a pass. Check `isValid`.
- Do **not** auto-tag an image-only scan without OCR. Auto-tagging doesn't add a text layer, so
  the result has no readable text.
- Do **not** route PDF/A conversion, merging, or signing here — those belong to
  `document-processor-api`.

## Security Hardening Addendum

- Never store `NUTRIENT_ACCESSIBILITY_API_KEY` or PDF passwords in committed files. Use process env
  injection at runtime (shell/export, secrets manager, or host env).
- The scripts never print or log the API key, and redact it from any error response body.
- `--url` inputs are validated (https-only; the host must resolve to a globally-routable public
  address) and fetched **client-side** with redirects disabled, so the Nutrient backend never
  fetches the URL. Do not pass unsanitized user-controlled strings to `--url`.
- Outputs (tagged PDFs, prepared PDFs, reports) are written with `0600` permissions and never
  through a symlink.

## Reference map

- `references/accessibility-api-reference.md` — endpoints, request and response shapes, report
  schema, error codes, and pricing model.
- `references/pdf-ua-wcag-compliance-notes.md` — what PDF/UA auto-tagging does, PDF/UA vs WCAG,
  Section 508 relationship.
- `scripts/verify-pdf.py` — the bundled offline structural checker (the identical file ships in the
  `make-pdf` plugin; keep them in sync). Use it when no API key is available or for a free local
  check; `validate.py` is the authoritative PDF/UA-1 validation.
- Sibling `document-processor-api/SKILL.md` — `/build` PDF/UA output target and the same
  underlying auto-tagging engine.
- The `make-pdf` skill (separate plugin: `make-pdf@nutrient-skills`) — generate NEW compliant
  PDFs from Markdown/HTML.
