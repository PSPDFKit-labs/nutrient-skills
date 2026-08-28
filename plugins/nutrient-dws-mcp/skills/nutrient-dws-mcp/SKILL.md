---
name: nutrient-dws-mcp
description: Process, convert, OCR, sign, redact, parse, or extract data from documents with the Nutrient DWS MCP tools. Use when the user wants cloud document processing through the installed Nutrient plugin.
---

# Nutrient DWS MCP

Use only the `nutrient-dws` MCP server bundled with this plugin. Do not invoke the DWS CLI, direct REST API, `curl`, or local helper scripts.

## Choose a tool

- `document_processor` — Convert documents, run OCR, watermark, rotate or rearrange pages, flatten annotations, and perform other Processor operations.
- `document_signer` — Apply a digital signature to a PDF.
- `ai_redactor` — Detect and permanently remove sensitive content with AI redaction.
- `parse_document` — Convert a PDF or Office document to Markdown or structured spatial JSON.
- `extract_fields` — Extract named fields into a requested JSON schema with citations.
- `check_credits` — Check the signed-in account and remaining Processor credits without uploading a document.
- `sandbox_file_tree` — Inspect files inside the configured sandbox without uploading them.
- `directory_tree` — Inspect an explicit local directory when sandbox mode is not configured.

## Workflow

1. Use explicit input and output paths. Prefer a configured sandbox and never scan unrelated directories.
2. Select the narrowest tool that completes the request. Use `document_processor` for combined processing workflows rather than chaining unnecessary calls.
3. Preserve the source file unless the user explicitly requests replacement. Write transformed documents to a distinct output path.
4. Report the created file path or structured extraction result and surface any DWS error directly.

The first API-backed tool call may open Nutrient browser OAuth. Let the user complete sign-in, then continue the same operation. Documents and processing instructions are sent to Nutrient only when an API-backed document tool is invoked; file-tree tools remain local.
