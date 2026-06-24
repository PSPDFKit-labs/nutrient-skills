---
name: remediate-pdf
description: >-
  Auto-tag existing PDFs with PDF/UA semantic structure (headings, lists, tables, reading order)
  for accessibility remediation via the Nutrient DWS Accessibility API. Use when the user wants to
  make an existing PDF accessible, auto-tag for screen readers, remediate for PDF/UA, or prepare a
  document for Section 508. Triggers include auto-tag PDF, make this PDF accessible, tag for screen
  readers, remediate accessibility, PDF/UA remediation, or Section 508 remediation. Auto-tag only:
  check tagged output with the sibling make-pdf skill's verify-pdf.py. To generate a NEW accessible
  PDF from Markdown or HTML, use make-pdf instead. Converting to PDF/A, producing a PDF/UA output
  target via /build, merging, or signing go to document-processor-api.
license: MIT
metadata:
  author: nutrient-sdk
  version: "1.0"
  homepage: "https://www.nutrient.io/api/accessibility-api/"
  repository: "https://github.com/PSPDFKit-labs/nutrient-skills"
  compatibility: "Requires Python 3.10+, uv, and internet. Works with Claude Code, Codex CLI, Gemini CLI, OpenCode, Cursor, Windsurf, GitHub Copilot, Amp, or any Agent Skills-compatible product."
  short-description: "Remediate existing PDFs: auto-tag for PDF/UA accessibility via the Nutrient DWS Accessibility API"
---

# Nutrient Remediate PDF

Remediate an existing PDF by auto-tagging it with PDF/UA semantic structure — headings (H1–H6),
lists, tables (TR/TD/TH), reading order, and artifact marking — via the dedicated Nutrient DWS
Accessibility API. The script uploads a PDF and writes back the remediated, tagged PDF.

> **This skill ships auto-tag only.** The DWS Accessibility API does not currently expose a
> separate accessibility conformance *validation* endpoint (confirmed by live probe — see
> `references/accessibility-api-reference.md`). To check tagged output today, use the sibling
> `make-pdf` skill's standalone verifier — `uv run ../make-pdf/scripts/verify-pdf.py --input
> doc-tagged.pdf --profile pdfua` — which checks structural PDF/UA-1 signals and escalates to a
> full veraPDF audit when veraPDF is installed. It is not a certification.

## When to use

- "Make this PDF accessible" / "auto-tag for screen readers"
- "Tag this PDF for PDF/UA" / "remediate accessibility"
- "Prepare this document for Section 508" (the tagging step)

## Disambiguation from sibling skills

Existing PDF vs. new PDF is the first fork:

- **Use this skill (`remediate-pdf`)** to fix a PDF that already exists — auto-tag it for
  accessibility.
- **Use `make-pdf`** to generate a NEW compliant PDF from Markdown or HTML (PDF/UA or PDF/A
  output with built-in verification). Its `verify-pdf.py` is also the way to check this skill's
  tagged output.

Both `document-processor-api` and this skill perform **PDF/UA auto-tagging using the same
underlying engine** (the `pdf_to_pdfua` capability — confirmed from the live response's build
stats). The distinction is **product and account surface, not capability**:

- **Use this skill (`remediate-pdf`)** when the user wants the dedicated DWS **Accessibility
  product**: its own API key (`NUTRIENT_ACCESSIBILITY_API_KEY`), its own monthly auto-tagged-pages
  quota and dashboard.
- **Use `document-processor-api`** when the user is already doing `/build` work and wants PDF/UA
  as one of several output targets with their Processor key, or wants `convert to PDF/A`, `produce
  PDF/UA` via `/build`, `merge`, or `sign`.

Do **not** claim the Processor "cannot auto-tag" — it can. Route on which product/key/quota the
user wants, not on a capability difference. Cross-link the Processor's `pdfua` output target.

## Setup

The DWS Accessibility API is a **separate product** with its own API key (distinct from the
Processor key `NUTRIENT_API_KEY` and the Extraction key `NUTRIENT_EXTRACT_API_KEY`). Calling the
Accessibility endpoint with the wrong product key returns `401` (malformed/unknown key) or `403`
(valid key for a different DWS product — observed live).

- Get a DWS Accessibility API key at <https://dashboard.nutrient.io/>.
- Export it as `NUTRIENT_ACCESSIBILITY_API_KEY` (the key uses the `pdf_live_` prefix):
  ```bash
  export NUTRIENT_ACCESSIBILITY_API_KEY="pdf_live_..."
  ```
- Run from the directory containing this SKILL.md:
  ```bash
  cd <directory containing this SKILL.md> && uv run scripts/autotag.py --help
  ```

## Operations

### `autotag.py` — remediate a PDF with PDF/UA tags

```bash
uv run scripts/autotag.py --input doc.pdf --output doc-tagged.pdf
uv run scripts/autotag.py --url https://example.com/doc.pdf --output doc-tagged.pdf
```

- `POST https://api.nutrient.io/accessibility/autotag`, `Authorization: Bearer <key>`, always as
  `multipart/form-data` (field `file`). `--url` is validated (https-only, must resolve to a public
  address) then **downloaded client-side** and uploaded as bytes — the Nutrient backend never
  fetches the URL, so there is no backend SSRF surface (redirects are not followed).
- On success the remediated PDF is written to `--output` (default `<input-stem>-tagged.pdf`).
- The script prints the pages-processed and quota-unit count from the response build stats.

## Decision rules

- **Quota gate.** Auto-tagging consumes from the monthly auto-tagged-pages quota (Free tier = 20
  pages/month; quotas do not roll over and the API blocks at the limit). `autotag.py` estimates
  the page count and **requires confirmation before any run exceeding remaining quota** (when the
  account surfaces it) **or exceeding `--confirm-over` (default 20)** when remaining is unknown.
  Pass `--yes` to bypass for known-safe runs.
- **Max file size** is 150 MiB per request; the script enforces this client-side before upload.
  For larger documents, split first with `document-processor-api/split.py`.
- **Do not auto-retry on a 2xx response** — each call consumes quota.

## Anti-patterns

- Do **not** represent auto-tagged output as guaranteed PDF/UA-compliant. Auto-tagging improves
  but does not guarantee conformance (Nutrient's benchmark cites ~96.5% PDF/UA conformance, not
  100%). Check output with the sibling `make-pdf` skill's `verify-pdf.py` (and veraPDF for a full
  audit); treat the output as remediated, not certified.
- Do **not** route `convert to PDF/A`, `produce PDF/UA` via `/build`, `merge`, or `sign` here —
  those belong to `document-processor-api`.
- Do **not** use a Processor or Extraction key against this endpoint — it returns `401`.

## Security Hardening Addendum

- Never store `NUTRIENT_ACCESSIBILITY_API_KEY` in committed files. Use process env injection at
  runtime (shell/export, secrets manager, or host env).
- The script never prints or logs the API key, and redacts the key from any error response body
  before printing it.
- `--url` inputs are validated (https-only; the host must resolve to a globally-routable public
  address) and then fetched **client-side** with redirects disabled, so the Nutrient backend never
  fetches the URL — there is no backend SSRF surface. The client fetch is still operator-scoped
  egress: do not pass unsanitized user-controlled strings to `--url`.

## Reference map

- `references/accessibility-api-reference.md` — confirmed endpoint, request/response shape, quota
  model, error envelope, and the validation-endpoint probe findings.
- `references/pdf-ua-wcag-compliance-notes.md` — what PDF/UA auto-tagging does, PDF/UA vs WCAG,
  Section 508 relationship.
- Sibling `document-processor-api/SKILL.md` — `/build` PDF/UA output target and the same
  underlying auto-tagging engine.
- Sibling `make-pdf/SKILL.md` — generate NEW compliant PDFs from Markdown/HTML, and
  `make-pdf/scripts/verify-pdf.py` — the standalone structural checker for this skill's tagged
  output.
