# DWS Viewer API — product decision matrix & routing

This is the **single source of truth** for disambiguating the three Nutrient products that show
documents in a browser. The SKILL.md inline summary, the `AGENTS.md` bullet, and the `README.md`
row are one-line pointers to this file — when positioning shifts, change it here.

## The three products

| Dimension | DWS Viewer API (this skill) | Nutrient Web SDK (`nutrient-web-sdk`) | Document Engine (`nutrient-document-engine`) |
|---|---|---|---|
| Infrastructure hosting | Nutrient cloud | Developer (browser WASM) | Developer's server |
| Document storage | Nutrient cloud or app-provided | Developer's server / CDN | Developer's database |
| Real-time collaboration | Built in | Via Document Engine only | Yes (self-hosted) |
| Offline / air-gap | No | Yes (standalone WASM mode) | Partial |
| Auth model | API key (server) + session JWT (browser) | License key (client) | Custom (server-managed) |
| Pricing model | Session quota + storage limits | SDK license | Server license |
| Setup time | Minutes (3 API calls) | Hours (WASM bundle + CDN config) | Days (server deploy + DB) |
| When to use | Cloud-first; no server infra; collab fast | Full control; offline capable; existing server | Self-hosted persistence; custom auth; regulatory |

## Routing rules

- **DWS Viewer API (this skill)** — the user wants a cloud-backed viewer fast, does **not** want to
  run servers, needs annotation persistence or real-time collaboration out of the box, or is
  prototyping a cloud document workflow. Signals: "no server infra", "cloud viewer", "mint a viewer
  session", "session JWT/token to the browser", `POST /viewer/sessions`, `POST /viewer/documents`.
- **`nutrient-web-sdk`** — self-hosted WASM viewer the developer hosts and keys themselves. Signals:
  `@nutrient-sdk/viewer`, `NutrientViewer.load()` **without** a DWS `session:`, license key, offline
  capability, React/Vue/Angular/Next.js embed wiring, "standalone WASM mode". The client embed of a
  DWS Viewer session JWT also uses `NutrientViewer.load({ session })` — but the **server-side** work
  (upload + session mint) is this skill; the **framework embed recipe** is `nutrient-web-sdk`.
- **`nutrient-document-engine`** — self-hosted backend for annotation persistence, team
  collaboration with custom auth, or data-residency / regulatory constraints requiring you to own
  the server and database.

## Confirmed API contract (delete/teardown gate — U6, probed live 2026-06-23)

The document delete/teardown contract was resolved as a blocking gate before any live upload smoke.
**Result: delete is confirmed.** v1 ships in delete-confirmed mode with required, verified teardown
of every uploaded document.

| Operation | Endpoint | Notes |
|---|---|---|
| Upload | `POST https://api.nutrient.io/viewer/documents` | Binary body (`Content-Type: application/octet-stream`) preferred; multipart `file` field also works. Response: `{"data": {"document_id", "title", "createdAt", "sourcePdfSha256", ...}}`. |
| List | `GET https://api.nutrient.io/viewer/documents` | `{"data": [{"id", "title", "created_at"}], "next_cursor", "prev_cursor", "document_count"}`. **List item key is `id`, not `document_id`.** |
| Delete | `DELETE https://api.nutrient.io/viewer/documents/{id}` | `200 "OK"` (plain text). **Hard and synchronous.** |
| Session | `POST https://api.nutrient.io/viewer/sessions` | Body `{allowed_documents: [{document_id, permissions}], exp}` (DWS-managed) or `{}` (app-provided). Response: `201 {"jwt": "<3-segment token>"}`. |

### Teardown verification — what is and isn't a liveness signal

- **Authoritative:** a document's **absence from `GET /viewer/documents`** (no list item whose `id`
  equals the `document_id`). Corroborated by a re-`DELETE` returning `404 "Document not found"`.
- **NOT a signal — `GET /viewer/documents/{id}`:** returns `404` **unconditionally**, even for a
  live document (there is no GET-by-id read route). Using GET-by-id → 404 as a delete check
  false-passes every teardown. Do not use it. *(This corrects the assumption in the original plan,
  which proposed verifying deletion by a direct GET → 404.)*
- **NOT a signal — session mint:** `POST /viewer/sessions` mints a JWT for an already-deleted
  `document_id` without existence-checking, so a successful session does not prove the document
  exists.

### Quota (free tier)

100 documents / 500 MiB storage / 100 uploads per month; 1,000 sessions per month. Every uploaded
document draws down storage/upload quota and carries data-retention exposure — tear it down when
done. Sessions are minted even in app-provided mode, and each consumes session quota; rate-limit
per-commit CI smoke runs.

## Official docs

- DWS Viewer API overview: <https://www.nutrient.io/api/viewer-api/>
- Guides (llms.txt): <https://www.nutrient.io/guides/dws-viewer/llms.txt>
- Web SDK: <https://www.nutrient.io/guides/web/llms.txt>
- Document Engine: <https://www.nutrient.io/guides/document-engine/>
- Cross-product index: <https://www.nutrient.io/llms.txt>
