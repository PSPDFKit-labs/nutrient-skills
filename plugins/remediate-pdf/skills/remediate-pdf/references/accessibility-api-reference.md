# Nutrient Accessibility API Reference

Facts for `autotag.py` and `validate.py`. Auto-tagging behavior was confirmed by live probe on
2026-06-22; validation was confirmed by live calls on 2026-11-19 and 2026-11-25 and against the DWS
Accessibility validation guide.

## Authentication and keys

- `Authorization: Bearer <key>`. Keys use the **`pdf_live_` prefix**.
- On current plans (unified USD billing, from 2026-11-16), **one Nutrient account and key cover
  the Accessibility API and the Processor API**. The scripts read `NUTRIENT_ACCESSIBILITY_API_KEY`,
  falling back to `NUTRIENT_API_KEY`, and strip surrounding whitespace.
- Older accounts created before unified billing had separate per-product keys; on those, a
  Processor key returns `401` on `/accessibility/*` and an Accessibility key may not work on
  `/build`. If a call returns `401`, check which key the account issued for that API.

## Auto-tagging endpoint

- **`POST https://api.nutrient.io/accessibility/autotag`**
- **Input:** local file as `multipart/form-data`, field `file`.
- **Output:** the tagged PDF binary, `Content-Type: application/pdf`. The original file is not
  modified.
- **Max file size:** 150 MiB per request (enforced client-side before upload).

The response surfaces usage in the **`x-pspdfkit-build-stats`** header (JSON), for example:

```json
{"output":{"type":"pdfua","format":"pdf","page_count":1,"size_bytes":17728},
 "conversion_engine":"gdpicture",
 "required_license_features":{"pdf_to_pdfua_api":{"units":1}}}
```

`autotag.py` reads `output.page_count` and `required_license_features.pdf_to_pdfua_api.units`
for its usage note.

**Image-only scans:** auto-tagging doesn't add a text layer; it structures the text it finds. A
scan without OCR has no readable text to tag, and validation won't catch that, so run OCR first
(`document-processor-api`'s `ocr.py`). `autotag.py` exits 4 when the first pages have no text.

## Validation endpoint

- **`POST https://api.nutrient.io/accessibility/validate_pdfua`**
- **Input:** exactly one source, either a local file as multipart field `file` or a remote PDF as
  multipart field `url`. `validate.py` always uploads the file (it fetches `--url` client-side).
- **Password-protected PDFs:** send the password in the `pspdfkit-pdf-password` header, plain or
  as `base64:<encoded-password>`. `validate.py` always sends the base64 form, so spaces and
  non-ASCII characters can't break the header.
- **Profile:** PDF/UA-1 is the only supported profile.
- **Result:** a completed validation returns **HTTP 200 whether or not the PDF conforms**. Read
  `isValid` in the body.

Report fields:

- `isValid` — `true` if the PDF conforms to PDF/UA-1.
- `conformance` — `pdfua-1` if it conforms, otherwise `none`.
- `validationReport.profile` — the profile used (`{"conformance": "pdfua", "part": 1}`).
- `validationReport.result` — `isCompliant` and a `statement` summarizing the result.
- `validationReport.failureCount` — total failures across all failed checks.
- `validationReport.failedChecks` — one entry per failed requirement, with its `id`,
  `occurrenceCount`, and `occurrences`. Each occurrence has a `context` (`Document`, `Page`), the
  affected PDF object in `objectReference`, and a `statement` describing the failure. Empty when
  the PDF conforms. Check IDs are descriptive names such as `MissingDocumentTitle`,
  `InvalidLangEntry`, and `UnembeddedFont`, not PDF/UA clause numbers. Document-level failures
  carry a placeholder `objectReference` (`"None"` or `"0 obj"`).

A failing report for an untagged one-page PDF (live, 2026-11-25) is in
`tests/fixtures/validation-failing.json`: 8 failures across 7 checks, including a missing
structure tree, language, title, XMP metadata, MarkInfo, ViewerPreferences, and unembedded
fonts.

A passing report, as returned by the live API:

```json
{"conformance":"pdfua-1","isValid":true,
 "validationReport":{"failedChecks":[],"failureCount":0,
  "profile":{"conformance":"pdfua","part":1},
  "result":{"isCompliant":true,"statement":"PDF file is compliant with validation profile requirements."}}}
```

The API report checks what a machine can test. It confirms that an image has alternative text,
not that the text describes the image, so placeholder alt text such as "image" passes.
Accessibility Studio's validation warns about placeholder alt text.

### History

A June 2026 probe found no validation route (`/accessibility/validate` and `/accessibility/check`
returned the gateway's catch-all `403`), so version 1.0 of this skill shipped auto-tag-only.

## Preparation through the Processor API

Conversion and OCR run on `/build` through the `document-processor-api` skill (`convert.py`,
`ocr.py`), with the same key. On the free plan, Processor output is watermarked until the account
adds a wallet, and auto-tagging tags the watermark as page content.

## Errors

| Status | Meaning |
| --- | --- |
| 400 | No source, more than one source, or invalid parameters |
| 401 | The API key is missing or invalid |
| 402 | The account has no usage left (monthly usage and wallet) |
| 403 | Validation: the PDF password is missing or incorrect, or the key isn't enabled for the Accessibility API. Unknown routes also return `403` |
| 408 | The request timed out |
| 413 | The file exceeds the maximum upload size |
| 502 | The PDF couldn't be downloaded from the supplied URL |

Error bodies follow `{"error":{"details":"...","requestId":"...","status":403,"supportUrl":"..."}}`;
for validation `400`, `403`, and `502`, the body has a machine-readable `reason` (for example
`missing_source_file`, `password_required`) and a `description`. The scripts redact the API key
and PDF password from any error before printing.

## Pricing

Unified USD pricing from 2026-11-16: auto-tagging is billed per page and validation per
validation, from the account's monthly usage and then the prepay wallet. The free plan includes
$5 of usage a month. Editing tags in Accessibility Studio is free. Current rates:
<https://www.nutrient.io/api/pricing/>.

## Same engine as the Processor

The autotag build stats report `output.type: "pdfua"`, `conversion_engine: "gdpicture"`, and
`required_license_features.pdf_to_pdfua_api` — the same engine and license feature as the
Processor's `/build` PDF/UA output target. The difference between this skill and
`document-processor-api` is the API surface (auto-tagging plus validation), not tagging quality.

## Not documented

- Nutrient doesn't document a WCAG version or level that auto-tagged output aligns to. PDF/UA-1 is
  the validated target.
