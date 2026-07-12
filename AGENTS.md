# Nutrient Skills

This repository contains AI agent skills for [Nutrient](https://www.nutrient.io/) APIs and SDKs.

Each skill lives under `plugins/<plugin-name>/skills/<skill-name>/SKILL.md`. Read the relevant SKILL.md for instructions on how to use a skill.

## Available Skills

- **nutrient-dws / document-processor-api** — Convert, transform, redact, sign, watermark, OCR, and secure documents via the Nutrient DWS Processor API (Python scripts via `uv`).
- **nutrient-dws / document-extraction-api** — Parse documents into a structural model (typed elements with bounds) or whole-document Markdown via the Nutrient DWS Data Extraction API (`/extraction/parse`). Use for RAG ingestion, layout analysis, and form/invoice extraction.
- **nutrient-dws / make-pdf** — Generate PDFs from Markdown or HTML via DWS, single files or whole directories, with accessible PDF/UA, archival PDF/A, and watermark outputs plus built-in conformance verification (structural checks, optional veraPDF audit).
- **pdf-to-markdown / pdf-to-markdown** — Extract text from PDFs as structured, semantic Markdown. Use when converting a PDF to Markdown, extracting text from a PDF, or processing one or more PDFs into Markdown output.
- **pdf-to-text / pdf-to-text** — Extract text from PDFs as layout-preserving plain text. Use when the consumer wants raw text only, when columns and tables must stay spatially aligned, or when downstream tooling can't parse Markdown. Prefer `pdf-to-markdown` when the consumer benefits from semantic structure.
- **query / query** — Find the most relevant passages in an already-extracted document (the output of `pdf-to-markdown` / `pdf-to-text`) with ranked BM-25 search that returns only the top line windows. Use to answer a question or pull a section from a large converted file without reading it all back into context.
- **nutrient-sdk-dev** — Building with a Nutrient SDK. 13 skills, one per SDK family: `nutrient-web-sdk`, `nutrient-document-authoring`, `nutrient-ios-sdk`, `nutrient-android-sdk`, `nutrient-react-native-sdk`, `nutrient-flutter-sdk`, `nutrient-maui-sdk`, `nutrient-python-sdk`, `nutrient-java-server-sdk`, `nutrient-nodejs-server-sdk`, `nutrient-dotnet-server-sdk`, `nutrient-document-engine`, `nutrient-ai-assistant`. Each points to the right nutrient.io API/guide URLs and example repos for that SDK.
