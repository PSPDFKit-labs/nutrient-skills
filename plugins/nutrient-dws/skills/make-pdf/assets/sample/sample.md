---
title: Quarterly Operating Review
subtitle: Markdown to DWS PDF sample
author: Nutrient Solutions Team
date: 2026-07-09
template: document
theme: dark
---

# Quarterly Operating Review

This sample exercises the make-pdf pipeline with [Nutrient DWS](https://www.nutrient.io/).
It includes headings, a table, code, task lists, and quoted notes.

## Performance Summary

| Area | Status | Notes |
| --- | --- | --- |
| Pipeline | Green | Markdown renders into template HTML. |
| Compliance | Ready | PDF/UA and PDF/A are output options. |
| Review | Pending | Watermark output is available for drafts. |

### Key Actions

- [x] Confirm the Markdown parser handles GFM tables.
- [x] Keep generated HTML self-contained.
- [ ] Run a live DWS build when an API key is available.

> Draft reviews should use a watermark before external circulation.

## Implementation Note

```python
def build_message(title: str) -> str:
    return f"Generated PDF: {title}"
```

### Distribution

The generated PDF can be archived as PDF/A, remediated as PDF/UA, or passed to
the document-processor-api skill for signing, redaction, OCR, or merging.

For layout debugging, run the script with `--html-only` and inspect the HTML.
