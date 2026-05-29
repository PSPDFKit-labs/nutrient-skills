# Nutrient Skills

This repository contains AI agent skills for [Nutrient](https://www.nutrient.io/) APIs and SDKs.

Each skill lives under `plugins/<plugin-name>/skills/<skill-name>/SKILL.md`. Read the relevant SKILL.md for instructions on how to use a skill.

## Available Skills

- **nutrient-dws / document-processor-api** — Convert, transform, redact, sign, watermark, OCR, and secure documents via the Nutrient DWS Processor API (Python scripts via `uv`).
- **nutrient-dws / document-extraction-api** — Parse documents into a structural model (typed elements with bounds) or whole-document Markdown via the Nutrient DWS Data Extraction API (`/extraction/parse`). Use for RAG ingestion, layout analysis, and form/invoice extraction.
- **pdf-to-markdown / pdf-to-markdown** — Extract text from PDFs as structured, semantic Markdown. Use when converting a PDF to Markdown, extracting text from a PDF, or processing one or more PDFs into Markdown output.
