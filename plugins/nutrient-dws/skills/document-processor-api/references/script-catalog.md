# Script Catalog

## Core Document Operations

- `scripts/convert.py`
  - Method: `client.convert(input, target_format)`
  - Common use: office-to-pdf, pdf-to-markdown/html/image

- `scripts/merge.py`
  - Method: `client.merge(files)`
  - Common use: combine reports, append cover pages

- `scripts/split.py`
  - Method: `client.split(pdf, page_ranges)`
  - Common use: split sections into separate files

- `scripts/ocr.py`
  - Method: `client.ocr(file, language|language[])`
  - Common use: searchable text from scanned PDFs

- `scripts/extract-text.py`
  - Method: `client.extract_text(file, pages?)`
  - Common use: content indexing and summarization input

- `scripts/extract-table.py`
  - Method: `client.extract_table(file, pages?)`
  - Common use: analytics ingest from PDFs

- `scripts/extract-key-value-pairs.py`
  - Method: `client.extract_key_value_pairs(file, pages?)`
  - Common use: forms, invoices, claims data extraction

## PDF Editing and Security

- `scripts/watermark-text.py`
  - Method: `client.watermark_text(file, text, options?)`

- `scripts/redact-ai.py`
  - Method: `client.create_redactions_ai(pdf, criteria, redaction_state, pages?)`

- `scripts/rotate.py`
  - Method: `client.rotate(pdf, angle, pages?)`

- `scripts/sign.py`
  - Method: `client.sign(pdf, data?, options?)`
  - Note: input must be local file path

- `scripts/optimize.py`
  - Method: `client.optimize(pdf, options?)`

- `scripts/password-protect.py`
  - Method: `client.password_protect(file, user_password, owner_password, permissions?)`

- `scripts/add-pages.py`
  - Method: `client.add_page(pdf, count, index?)`

- `scripts/delete-pages.py`
  - Method: `client.delete_pages(pdf, page_indices)`

- `scripts/duplicate-pages.py`
  - Method: `client.duplicate_pages(pdf, page_indices)`

## Invocation

Run scripts with `uv run` from the plugin root:

```bash
uv run scripts/<script>.py --help
uv run scripts/convert.py --input doc.pdf --format docx --out out.docx
```

## Page Range Conventions

Use `start:end` and comma-separated lists for multi-range inputs.

Examples:
- `0:2` -> first three pages
- `-3:-1` -> last three pages
- `0:2,3:5` -> two segments
