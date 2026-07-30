---
name: dws-viewer-api
description: >-
  Upload documents to Nutrient-managed cloud storage and mint browser viewer session JWTs via the
  Nutrient DWS Viewer API (cloud-hosted document viewing). Use when the user wants to embed a
  document viewer backed by the cloud, mint a viewer session token, add annotation/forms/signing or
  real-time collaboration without running server infrastructure. Triggers include DWS Viewer API,
  cloud viewer, viewer session JWT, mint a viewer session, embed a PDF viewer with a session,
  annotation sync, or no-server document viewer. Not for the self-hosted Web SDK
  (`@nutrient-sdk/viewer` / `NutrientViewer.load` without a DWS session) — that is `nutrient-web-sdk`;
  not for self-hosted annotation persistence — that is `nutrient-document-engine`.
when_to_use: >-
  Triggers: DWS Viewer API; cloud-hosted document viewer; "mint/generate a viewer session"; viewer
  session JWT or session token handed to the browser; `POST /viewer/documents` or
  `POST /viewer/sessions`; embed a PDF viewer backed by Nutrient cloud with no server to run;
  annotation/forms/signing/real-time collaboration via cloud infrastructure; `NutrientViewer.load`
  *with a `session:` token*. Covers the server-side half only: upload to Nutrient storage + session
  mint. Not for the self-hosted WASM viewer, license keys, or React/Vue/Angular embed wiring
  (`@nutrient-sdk/viewer`, `NutrientViewer.load` without a DWS session) — those go to
  `nutrient-web-sdk`; not for self-hosted annotation persistence or data-residency/custom-auth
  backends — those go to `nutrient-document-engine`.
license: MIT
metadata:
  author: nutrient-sdk
  version: "1.0"
  homepage: "https://www.nutrient.io/api/viewer-api/"
  repository: "https://github.com/PSPDFKit-labs/nutrient-skills"
  compatibility: "Requires Python 3.10+, uv, and internet. Works with Claude Code, Codex CLI, Gemini CLI, OpenCode, Cursor, Windsurf, GitHub Copilot, Amp, or any Agent Skills-compatible product."
  short-description: "Upload documents and mint viewer session JWTs via the Nutrient DWS Viewer API"
---

# Nutrient DWS Viewer API

The DWS Viewer API is Nutrient's **cloud-hosted** document viewing service. The flow is three
server-side steps: upload a document to Nutrient-managed storage (or reference an app-provided one),
mint a short-lived session JWT, and hand that JWT to the browser, where the Nutrient Web SDK renders
a full viewer backed by Nutrient infrastructure — storage, streaming, annotation sync, and
collaboration, with no viewing/storage servers to run. (You still need a small trusted backend
or serverless endpoint to mint the session token — the API key must never reach the browser;
this skill is exactly that server-side step.)

This skill covers the **server-side half** — upload and session mint, the part agents get wrong. The
one-line browser embed (`NutrientViewer.load({ container, session })`) is documented in
`references/embed-guide.md`; framework integration belongs to the `nutrient-web-sdk` skill.

## When to use

- "Embed a PDF viewer for document review/approval in our SaaS app — I don't want to run servers."
- "Add annotation, forms, or signing to a document workflow without hosting infrastructure."
- "Mint a viewer session token / session JWT for the browser."
- "Add multi-user real-time annotation to a document, cloud-backed."

Three Nutrient products show documents in a browser. Pick the right one **before** writing code:

| Product | Infra hosting | Storage | Persistence / collab | Route here when |
|---|---|---|---|---|
| **DWS Viewer API** (this skill) | Nutrient cloud | Nutrient cloud or app-provided | Built in | Cloud-first; no server infra; collab fast |
| **Nutrient Web SDK** (`nutrient-web-sdk`) | Developer (browser WASM) | Developer's server | Via Document Engine | Self-hosted/offline; `@nutrient-sdk/viewer` embed |
| **Document Engine** (`nutrient-document-engine`) | Developer's server | Developer's DB | Yes (server-side) | Self-hosted persistence; custom auth; data residency |

- **Route here (DWS Viewer API)** when the user wants a cloud-backed viewer fast, does not want to
  run servers, or needs annotation persistence / real-time collab out of the box.
- **Route to `nutrient-web-sdk`** for the self-hosted WASM viewer, license keys, or
  `NutrientViewer.load()` / `@nutrient-sdk/viewer` embed wiring **without** a DWS session.
- **Route to `nutrient-document-engine`** for self-hosted annotation persistence or
  data-residency / custom-auth backends.

The full comparison and routing rules live in `references/viewer-decision-matrix.md` (the single
source of truth for this disambiguation).

## Setup

The DWS Viewer API is a **separate product** with its own API key — distinct from the Processor key
(`NUTRIENT_API_KEY`) and the Extraction key (`NUTRIENT_EXTRACT_API_KEY`). Do **not** reuse another
product's key here.

- Get a DWS Viewer API key at <https://dashboard.nutrient.io/>.
- Export it as `NUTRIENT_DWS_VIEWER_API_KEY`:
  ```bash
  export NUTRIENT_DWS_VIEWER_API_KEY="pdf_live_..."
  ```
- Run from the directory containing this SKILL.md:
  ```bash
  cd <directory containing this SKILL.md> && uv run scripts/viewer-session.py --help
  ```

This skill does **not** silently fall back to `NUTRIENT_API_KEY`. The Viewer API's wrong-key
behavior is unconfirmed, so a silent fallback could mint a real browser session JWT against the
wrong product/tenant with no signal (a confused-deputy). If your tenant has migrated to a global
DWS key, opt in explicitly with `--allow-global-key`, which warns at the point of fallback.

## Tool preference

- `scripts/viewer-session.py` — the cloud-side operations (upload, session mint, combined).
- `references/embed-guide.md` — the browser embed (`NutrientViewer.load`), CDN snippet, llms.txt
  pointers, and the pointer to `nutrient-web-sdk` for framework recipes.
- `references/viewer-decision-matrix.md` — full product decision matrix and routing rules.

## Document modes

- **DWS-managed** — upload the document to Nutrient storage (`upload`), then mint a session for its
  `document_id`. Nutrient stores, streams, and (optionally) persists annotations. Counts against the
  upload/storage quota; uploaded documents should be torn down when no longer needed (see Rules).
- **App-provided** — the developer streams their own file to the SDK in the browser; the backend
  only mints a session with an empty body (`session --app-provided`). No document is uploaded to
  Nutrient storage, so nothing needs teardown — but each session still consumes session quota.

## Operations

### `viewer-session.py` — upload + session mint

```bash
# Upload a document to Nutrient storage; prints document_id
uv run scripts/viewer-session.py upload --file doc.pdf

# Mint a read-only session JWT for a DWS-managed document (write the token to a 0600 file)
uv run scripts/viewer-session.py session --document-id <id> --jwt-out session.jwt

# Elevate permissions explicitly (least privilege is the default — see Rules)
uv run scripts/viewer-session.py session --document-id <id> --allow-write --allow-download --jwt-out session.jwt

# One-shot: upload then mint (the common case and the live smoke path)
uv run scripts/viewer-session.py upload-and-session --file doc.pdf --jwt-out session.jwt

# Interactive only: echo the JWT to stdout instead of a file (opt-in; stdout is logged)
uv run scripts/viewer-session.py session --document-id <id> --print-jwt

# App-provided mode: mint a session with an empty body (no upload). See Rules — scope is
# UNVERIFIED and TTL is unbounded; do not use it as a default.
uv run scripts/viewer-session.py session --app-provided --jwt-out session.jwt

# Tear down a DWS-managed document when done (teardown)
uv run scripts/viewer-session.py delete --document-id <id>
```

- Upload: `POST https://api.nutrient.io/viewer/documents`, binary body; response `data.document_id`.
- Session: `POST https://api.nutrient.io/viewer/sessions`, body
  `{ allowed_documents: [{ document_id, permissions }], exp }` (DWS-managed) or `{}` (app-provided);
  response `{ jwt }`. The JWT prints **once** to stdout for capture.
- `upload-and-session` on partial failure (upload succeeds, session mint fails) attempts best-effort
  cleanup — it deletes the just-uploaded document (`DELETE /viewer/documents/{id}`, confirmed live)
  so a failed run does not orphan a document in cloud storage.

## Rules

- **The JWT needs an explicit sink.** A session-minting command requires either `--jwt-out <file>`
  (written `0600`) or `--print-jwt`. The default is the file — printing a browser bearer token to
  stdout is opt-in because agent/CI transcripts capture stdout. The script errors before any billed
  call if neither is given.
- **Least privilege by default.** A session grants **`["read"]`** only. `write` and `download`
  require explicit `--allow-write` / `--allow-download` (or an explicit `--permissions` list). A
  minted JWT is a browser-facing bearer credential; defaulting to read-only limits the blast radius
  of a leaked token.
- **Short TTL.** Default session expiry is 1 hour. `--expires-in` can extend it up to a documented
  ceiling (24h); the script warns above a short-TTL threshold. A leaked long-TTL JWT is an open
  exfiltration window for as long as it is valid.
- **`--app-provided` is not least-privilege — don't default to it.** It mints an empty-body session
  whose authorization scope is **unverified** and whose TTL is **not bounded** by `--expires-in`
  (the API applies its own). Use DWS-managed mode (`--document-id`) for any real session. Only reach
  for `--app-provided` when you deliberately stream your own file to the browser SDK and have
  independently confirmed the scope you get — not as a shortcut for smoke runs.
- **Tear down uploaded documents.** Every document created with `upload` / `upload-and-session`
  draws down a metered quota (Free tier: 100 docs / 500 MiB / 100 uploads per month) and carries
  data-retention exposure. Delete it when done with `viewer-session.py delete --document-id <id>`.
  Verify deletion by the document's absence from `GET /viewer/documents` (a GET-by-id always 404s
  and is not a liveness signal).
- **Fail fast** on a missing key or missing required args, with a message naming
  `NUTRIENT_DWS_VIEWER_API_KEY`.
- If a future `nutrient-dws` client adds Viewer methods, the script can swap its `httpx` calls for
  them; today it uses `httpx` directly (the SDK targets Processor/Extraction).

## Security Hardening Addendum

- Never store `NUTRIENT_DWS_VIEWER_API_KEY` in committed files. Use process env injection at runtime
  (shell/export, secrets manager, or host env).
- **Never expose the session JWT in client-side source bundles or commit it.** It is a bearer
  credential granting document access until `exp`. Leaking it is equivalent to leaking the API key.
- The script prints the JWT **once to stdout** for interactive capture and never logs it at
  debug/verbose level. stdout is **not** an inherently safe sink — it is captured into agent
  transcripts and CI build logs. For automation, write the JWT to a `0600` file or an env-export
  rather than raw stdout, and do not retain CI logs from runs that mint real JWTs.
- The script redacts the API key from any error body before printing, and never sets
  `httpx verify=False`.
- **Revocation:** no session-revocation endpoint is confirmed. A leaked JWT can only be contained by
  **rotating the underlying API key** and waiting out the current sessions' `exp`. Keep TTLs short
  for high-sensitivity documents.
- **App-provided scope:** an empty-body (`--app-provided`) session's authorization scope is
  unconfirmed — the least-privilege `permissions` list does not attach to that path. The script
  warns when `--app-provided` is used.

## Documentation

- Viewer API guides (llms.txt): <https://www.nutrient.io/guides/dws-viewer/llms.txt>
- Cross-product index: <https://www.nutrient.io/llms.txt>
- Product overview: <https://www.nutrient.io/api/viewer-api/>

## Reference map

- `references/viewer-decision-matrix.md` — full Viewer API vs Web SDK vs Document Engine matrix and
  routing rules; the single source of truth for the disambiguation. Also records the confirmed
  delete/teardown contract.
- `references/embed-guide.md` — browser embed (`NutrientViewer.load`), CDN snippet, llms.txt
  pointers, and the pointer to `nutrient-web-sdk` for framework recipes.
- Sibling `nutrient-web-sdk/SKILL.md` — the self-hosted WASM viewer and `@nutrient-sdk/viewer` embed.
