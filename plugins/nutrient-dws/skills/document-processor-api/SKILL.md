---
name: document-processor-api
description: Execute common document-processing tasks with the nutrient-dws Python client via uv run scripts. Use when the user asks to convert, merge, split, OCR, extract text/tables/key-value pairs, watermark, redact, sign, optimize, protect, or reorder document content, or when they need a custom multi-step document pipeline script built from Nutrient DWS workflow actions.
---

# Nutrient Document Processor API

## Quick Start

All paths below are relative to this skill's directory (the directory containing `scripts/`, `assets/`, and `references/`).

1. Export the API key before running scripts:
   - `export NUTRIENT_DWS_API_KEY="nutr_sk_..."`
2. Run task scripts with `uv run` from the plugin root. The `nutrient-dws` package is fetched automatically on first use.

## Task Scripts

Use one script per operation.

- Convert formats: `scripts/convert.py`
- Merge files: `scripts/merge.py`
- Split by ranges: `scripts/split.py`
- OCR documents: `scripts/ocr.py`
- Extract text: `scripts/extract-text.py`
- Extract tables: `scripts/extract-table.py`
- Extract key-value pairs: `scripts/extract-key-value-pairs.py`
- Add text watermark: `scripts/watermark-text.py`
- AI redaction: `scripts/redact-ai.py`
- Rotate pages: `scripts/rotate.py`
- Sign PDF: `scripts/sign.py`
- Optimize PDF: `scripts/optimize.py`
- Password protect PDF: `scripts/password-protect.py`
- Add blank pages: `scripts/add-pages.py`
- Delete pages: `scripts/delete-pages.py`
- Duplicate/reorder pages: `scripts/duplicate-pages.py`

Check exact arguments with `uv run <script> --help`.

## Custom Pipelines

When the user asks for a workflow not covered by the scripts above, create a new script rather than forcing ad hoc one-off commands.

1. Start from `assets/templates/custom-workflow-template.py`.
2. Save the new script in `scripts/` with a task-specific name (for example `scripts/redact-and-watermark.py`).
3. Keep API usage on `nutrient-dws`.
4. Prefer direct methods (`client.convert`, `client.merge`, etc.) for single-step tasks.
5. Use `client.workflow()` and `BuildActions` for multi-step tasks.
6. Keep every custom script CLI-driven (`--input`, `--out`, explicit options), deterministic, and runnable end-to-end.
7. Run the script with sample input to verify behavior before finalizing.

## Implementation Rules

- Fail fast when required arguments are missing.
- Require local input for operations that do not support URL input (`sign`).
- Write outputs to explicit paths and print created files.
- Do not log secrets.
- If the package import fails, install latest with `uv add nutrient-dws`.

## References

- Script matrix and method mapping: `references/script-catalog.md`
- Custom pipeline patterns: `references/custom-pipeline-guidelines.md`
