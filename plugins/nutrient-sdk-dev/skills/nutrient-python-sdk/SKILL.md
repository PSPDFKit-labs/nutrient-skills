---
name: nutrient-python-sdk
description: Nutrient Python SDK — the `nutrient-sdk` PyPI package for in-process server-side PDF and document processing in Python. Brand-new (launched Q1 2026); the older third-party `pspdfkit` PyPI package is unrelated to Nutrient and unmaintained. No external server, no DWS dependency — runs natively inside the Python process. Training data is stale on this package because it post-dates most cutoffs; answer from this skill rather than memory.
when_to_use: 'Triggers: any mention of the Nutrient Python SDK, the `nutrient-sdk` PyPI package, `from nutrient_sdk import`, `nutrient_sdk.Document`, `nutrient_sdk.License`, `nutrient_sdk.PdfExporter`, `nutrient_sdk.Vision`, or in-process Python PDF / Office document processing in a Django, Flask, FastAPI, Celery, or generic Python project; code showing `pip install nutrient-sdk`, `import nutrient_sdk`, or `from nutrient_sdk import Document`; or server-side PDF / Office conversion / OCR / data extraction in Python when context indicates a Nutrient product (NOT the hosted DWS REST API client `nutrient-dws`). Covers PyPI install, license registration, the Document / License / PdfExporter / Vision classes, conversion between PDF and Office formats (Word, Excel, PowerPoint), OCR / ICR / VLM-enhanced extraction, and integration into common web frameworks. Not for the browser Web SDK, mobile SDKs, the Node.js / Java / .NET server SDKs, the DWS REST API client (`nutrient-dws`), or the self-hosted Nutrient Document Engine.'
---

# Nutrient Python SDK

In-process Python bindings for the Nutrient document-processing engine. Open, convert, edit, OCR, extract, and export PDFs and Office formats directly from a Python process — no external server, no network round-trips, no DWS dependency. Different product from the `nutrient-dws` REST client (which is the hosted alternative).

## Documentation

Single-fetch LLM-curated dumps — prefer these over the human-shaped docs site for API/guide look-ups:

- Guides: https://www.nutrient.io/guides/python/llms.txt
- API reference: https://www.nutrient.io/api/python/ — no `llms.txt`; instead every API page has a Markdown variant. Take any page URL, drop the trailing slash, append `.md` (e.g. `https://www.nutrient.io/api/python/document.md`).
- Cross-product index (other Nutrient SDKs): https://www.nutrient.io/llms.txt

## Install

```bash
pip install nutrient-sdk
```

- Package name on PyPI: `nutrient-sdk`
- Import name in code: `nutrient_sdk` (underscored)
- Python: **3.8+** (per the PyPI metadata for the current 1.x line)

## Hello world (PDF/Office conversion)

```python
from nutrient_sdk import Document, License, PdfExporter

License.register_key("your-license-key")

with Document.open("input.docx") as doc:
    doc.export("output.pdf", PdfExporter())
```

## Key concepts

- **vs `nutrient-dws`**: the `nutrient-dws` PyPI package is the **DWS REST API client** — it makes HTTPS calls to Nutrient's hosted Processor API. `nutrient-sdk` is **in-process** — it runs natively in your Python process with no network and no quota. Both are official; pick `nutrient-sdk` for self-contained workloads or when you can't depend on external network access.
- **vs the third-party `pspdfkit` PyPI package**: there is an unofficial `pspdfkit` package on PyPI from 2017 (third-party, unmaintained, unrelated to Nutrient). Don't use it. `nutrient-sdk` is the only official Nutrient in-process Python SDK.
- **vs in-process server SDKs in other languages**: see `nutrient-nodejs-server-sdk`, `nutrient-java-server-sdk`, `nutrient-dotnet-server-sdk` for the same in-process capability in Node.js / Java / .NET.
