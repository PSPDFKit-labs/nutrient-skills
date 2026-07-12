# DWS Accessibility API Reference

Confirmed facts and probe findings for the Nutrient DWS Accessibility API, as used by
`autotag.py`. Endpoint behavior below was confirmed by live probe on 2026-06-22.

## Auto-tagging endpoint (confirmed)

- **`POST https://api.nutrient.io/accessibility/autotag`**
- **Auth:** `Authorization: Bearer <key>`. The key is product-specific
  (`NUTRIENT_ACCESSIBILITY_API_KEY`) and uses the **`pdf_live_` prefix** (OQ1, confirmed). A
  missing/empty key → `401`; a wrong-product (Processor/Extraction) key → `401`.
- **Input:** local file as `multipart/form-data` with field name `file`; or a remote PDF as a
  JSON body `{"file": {"url": "https://..."}}`.
- **Output:** the remediated PDF binary, `Content-Type: application/pdf`.
- **Max file size:** 150 MiB per request (enforced client-side before upload).

### Quota / usage (R14, OQ2 — resolved)

The response surfaces usage in the **`x-pspdfkit-build-stats`** response header (JSON), e.g.:

```json
{"output":{"type":"pdfua","format":"pdf","page_count":1,"size_bytes":17728},
 "conversion_engine":"gdpicture",
 "required_license_features":{"pdf_to_pdfua_api":{"units":1}}}
```

`autotag.py` reads `output.page_count` and `required_license_features.pdf_to_pdfua_api.units`
for its quota-consumption note. Quota model: auto-tagging draws from the monthly
auto-tagged-pages bucket (Free tier = 20 pages/month; no rollover; the API blocks at the limit).

### Error envelope (OQ4 — resolved)

Non-2xx responses return:

```json
{"error":{"details":"Forbidden","requestId":"...","status":403,"supportUrl":"https://www.nutrient.io/api/support/"}}
```

Observed status codes: `200` success (`application/pdf`); `401` missing/invalid auth; `403`
forbidden — **also the gateway's catch-all for unrecognized POST routes** (see below).
`autotag.py` redacts the API key from any error body before printing.

## Validation endpoint (OQ3 — resolved: does not exist yet)

A live probe on 2026-06-22 found **no dedicated accessibility conformance-validation endpoint**:

- `POST /accessibility/validate` → `403`, **byte-identical to a nonsense path**
  (`POST /accessibility/definitely-not-real-xyz` → the same `403`). The gateway returns `403`
  (not `404`) for unrecognized POST routes, so the `403` means *route-absent*, not an auth/scope
  problem — the same key auto-tags successfully, and a no-auth call returns `401`, not `403`.
- `POST /accessibility/check` → same `403`.
- Validation is **not a mode of autotag**: `validate=true`, `mode=validate`, `output_type=report`
  form fields and `Accept: application/json` all still return `200 application/pdf`.
- The Processor's `validate_pdfa` is a different product/key, not the Accessibility API.

**Decision (R17):** the skill ships **auto-tag-only**; conformance validation is marked "coming
soon." When a validation endpoint ships, add `validate.py` and re-enable validation routing.

## Premise note (P1) — same engine as the Processor

The autotag response's `x-pspdfkit-build-stats` reports `output.type: "pdfua"`,
`conversion_engine: "gdpicture"`, and `required_license_features.pdf_to_pdfua_api` — the same
engine and license feature the Processor's `/build` PDF/UA output target uses. So
`/accessibility/autotag` is the **Accessibility-product surface over the same `pdf_to_pdfua`
engine**, not a distinct capability. Disambiguation between this skill and `document-processor-api`
is therefore about **product / key / quota / dashboard** (and the forthcoming validator), not
about which one "can auto-tag." The SKILL.md disambiguation reflects this.

## Open questions remaining

- **OQ5** — PDF/UA-1 (ISO 14289-1) vs PDF/UA-2 target version: the build stats report
  `type: "pdfua"` without a version; not resolved. See `pdf-ua-wcag-compliance-notes.md`.
- **OQ6** — WCAG version/level the output aligns to: not resolved.
