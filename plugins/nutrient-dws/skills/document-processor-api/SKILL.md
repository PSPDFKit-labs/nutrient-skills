---
name: document-processor-api
description: >-
  Process documents with Nutrient DWS. Use when the user wants to generate PDFs from HTML or URLs,
  convert Office/images/PDFs, assemble or split packets, OCR scans, extract text/tables/key-value
  pairs, redact PII, watermark, sign, fill forms, optimize PDFs, or produce compliance outputs like
  PDF/A or PDF/UA. Triggers include convert to PDF, merge these PDFs, OCR this scan, extract tables,
  redact PII, sign this PDF, make this PDF/A, or linearize for web delivery.
license: MIT
metadata:
  author: nutrient-sdk
  version: "2.0"
  homepage: "https://www.nutrient.io/api/"
  repository: "https://github.com/PSPDFKit-labs/nutrient-skills"
  compatibility: "Requires Python 3.10+, uv, and internet. Works with Claude Code, Codex CLI, Gemini CLI, OpenCode, Cursor, Windsurf, GitHub Copilot, Amp, or any Agent Skills-compatible product."
  short-description: "Generate, convert, assemble, OCR, redact, sign, archive, and optimize documents"
---

# Nutrient Document Processing

Use Nutrient DWS for managed document workflows where fidelity, compliance, or multi-step processing matters more than local-tool convenience.

## Setup
- Get a Nutrient DWS API key at <https://dashboard.nutrient.io/sign_up/?product=processor>.
- Direct API calls use `Authorization: Bearer $NUTRIENT_API_KEY`.
  ```bash
  export NUTRIENT_API_KEY="nutr_sk_..."
  ```
- MCP setups commonly use `@nutrient-sdk/dws-mcp-server` with `NUTRIENT_DWS_API_KEY`.
- Scripts live in `scripts/` relative to this SKILL.md. Use the directory containing this SKILL.md as the working directory:
  ```bash
  cd <directory containing this SKILL.md> && uv run scripts/<script>.py --help
  ```
- Page ranges use `start:end` with 0-based indexes and end-exclusive semantics. Negative indexes count from the end.

## When to use
- Generate PDFs from HTML templates, uploaded assets, or remote URLs.
- Convert Office, HTML, image, and PDF files between supported formats.
- OCR scans and extract text, tables, or key-value pairs.
- Redact PII, watermark, sign, fill forms, merge, split, rotate, flatten, or encrypt PDFs.
- Produce delivery targets like PDF/A, PDF/UA, optimized PDFs, or linearized PDFs.
- Check credits before large, batch, or AI-heavy runs.

## Tool preference
1. Prefer `scripts/*.py` for covered single-operation workflows.
2. Use `assets/templates/custom-workflow-template.py` for multi-step jobs that should still run through the Python client.
3. Use the modular `references/` docs and direct API payloads for capabilities that do not yet have a dedicated helper script, especially HTML/URL generation and compliance tuning.
4. Use local PDF utilities only for lightweight inspection. Use Nutrient when output fidelity or compliance matters.

## Single-operation scripts
- `convert.py` -> convert between `pdf`, `pdfa`, `pdfua`, `docx`, `xlsx`, `pptx`, `png`, `jpeg`, `webp`, `html`, and `markdown`
- `merge.py` -> merge multiple files into one PDF
- `split.py` -> split one PDF into multiple PDFs by page ranges
- `add-pages.py` -> append blank pages
- `delete-pages.py` -> remove specific pages
- `duplicate-pages.py` -> reorder or duplicate pages into a new PDF
- `rotate.py` -> rotate selected pages
- `ocr.py` -> OCR scanned PDFs or images
- `extract-text.py` -> extract text to JSON
- `extract-table.py` -> extract tables
- `extract-key-value-pairs.py` -> extract key-value pairs
- `watermark-text.py` -> apply a text watermark
- `redact-ai.py` -> detect and apply AI-powered redactions
- `sign.py` -> digitally sign a local PDF
- `password-protect.py` -> write encrypted output PDFs
- `optimize.py` -> apply optimization and linearization-style options via JSON

## Multi-Step Workflow Rule
Do not add new committed pipeline scripts under `scripts/`.

When the user asks for multiple operations in one run:
1. Copy `assets/templates/custom-workflow-template.py` to a temporary location such as `/tmp/ndp-workflow-<task>.py`.
2. Implement the combined workflow in that temporary script.
3. Run it with `uv run /tmp/ndp-workflow-<task>.py ...`.
4. Return generated output files.
5. Delete the temporary script unless the user explicitly asks to keep it.

## PDF Requirements
- `split.py` requires a multi-page PDF and cannot extract ranges from a single-page document.
- `delete-pages.py` must retain at least one page and cannot delete the entire document.
- `sign.py` only accepts local file paths for the main PDF.

## Decision rules
- Prefer a helper script when one already covers the requested operation cleanly.
- If you control the source markup, prefer HTML generation over browser print workflows.
- Use remote `file.url` inputs when the source already lives at a stable URL and you want to avoid local uploads.
- Use `output.type` for conversion and finalization targets. Use `actions` for transformations when building direct API payloads.
- OCR before text extraction, key-value extraction, or semantic redaction on scans.
- Prefer preset or regex redaction when the target is explicit. Use AI redaction only for contextual or natural-language requests.
- Use the PDF manipulation reference for merge, split, rotate, flatten, and page-range workflows instead of inferring those payloads from conversion examples.
- Treat PDF/A and PDF/UA as compliance targets, not cosmetic export formats. Choose the target up front and validate final artifacts when requirements are contractual.
- For PDF/UA, clean born-digital inputs and structured HTML usually tag better than rasterized or flattened source PDFs.
- For delivery optimization, linearize or optimize unsigned output artifacts instead of mutating already signed files.
- When the user asks for multiple steps, keep destructive or final steps late in the sequence. Use the workflow recipes when ordering is ambiguous.

## Anti-patterns
- Do not OCR born-digital PDFs just because the task mentions extraction. Extract first and OCR only if the text layer is missing.
- Do not flatten forms or annotations until the user confirms the artifact no longer needs to stay editable.
- Do not sign, archive, or linearize intermediate working files. Keep those as final-delivery steps.
- Do not promise PDF/A or PDF/UA compliance without a validation step when the requirement is contractual.
- Do not commit temporary workflow scripts under `scripts/`.

## Reference map
Read only what you need:

- `references/request-basics.md` -> endpoint model, auth, multipart vs JSON, credits, limits, and errors
- `references/generation-and-conversion.md` -> HTML/URL generation and format conversion
- `references/pdf-manipulation.md` -> merge, split, page-range, rotate, and flatten workflows
- `references/extraction-and-ocr.md` -> OCR, text extraction, tables, and key-value workflows
- `references/security-signing-and-forms.md` -> redaction, watermarking, signatures, forms, and passwords
- `references/compliance-and-optimization.md` -> PDF/A, PDF/UA, optimization, and linearization
- `references/workflow-recipes.md` -> end-to-end sequencing patterns for common business document workflows

## Rules
- Fail fast when required arguments are missing.
- Write outputs to explicit paths and print created files.
- Do not log secrets.
- All client methods are async and should run via `asyncio.run(main())`.
- If import fails, install dependency with `uv add nutrient-dws`.

## Security Hardening Addendum

- Prefer a pinned, preinstalled MCP server binary over runtime package fetches.
  - Preferred: `npm i -g @nutrient-sdk/dws-mcp-server@<pinned-version>`
  - Avoid unpinned runtime fetch in production paths.
- Never store `NUTRIENT_DWS_API_KEY` in committed JSON config files.
  - Use process env injection at runtime (shell/export, secrets manager, or host env).
- Restrict file access with `SANDBOX_PATH` to the minimum required working directory.
- Before enabling MCP mode in production, verify package provenance and lock version.

