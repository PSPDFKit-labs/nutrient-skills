# DWS Viewer API — live smoke-test guide

Manual verification against the real Viewer API. Requires `NUTRIENT_DWS_VIEWER_API_KEY`. The keyless
and mocked tests live in `scripts/test_viewer_session.py` (`uv run scripts/test_viewer_session.py`);
this guide covers the live scenarios that need a real key.

**v1 mode: delete-confirmed (U6).** `DELETE /viewer/documents/{id}` was confirmed live (200, hard +
synchronous), so the upload smoke runs **with required teardown** of every uploaded document.
Use the DWS-managed path for real sessions; `--app-provided` (step 5) is exercised only to verify
its warnings — it is not the recommended default (its scope is unverified and its TTL is unbounded).

Run all commands from the skill directory:

```bash
cd plugins/nutrient-dws/skills/dws-viewer-api
```

## 1. Key presence check (non-disclosing — R-14)

Confirm the key is set **without printing it**. Do **not** `echo $NUTRIENT_DWS_VIEWER_API_KEY` — that
writes a live bearer credential into terminal scrollback, CI logs, and transcripts.

```bash
test -n "$NUTRIENT_DWS_VIEWER_API_KEY" && echo "key: set (…${NUTRIENT_DWS_VIEWER_API_KEY: -4})" || { echo "key: missing"; exit 1; }
```

Prints `key: set (…<last4>)` or `key: missing`. Never the full value.

## 2. Upload test (creates a document — must be torn down in step 7)

Use a small **PDF** (SVG/Office support for upload is not confirmed; use a PDF to be safe):

```bash
uv run scripts/viewer-session.py upload --file tests/fixtures/sample.pdf
```

Expect exit 0 and a line `document_id=<id>`. Record the `document_id` for steps 3 and 7.

## 3. Session test (DWS-managed, read-only default)

```bash
uv run scripts/viewer-session.py session --document-id <id from step 2> --jwt-out /tmp/viewer.jwt
```

Expect exit 0 and `jwt_written=/tmp/viewer.jwt`. Verify the JWT is a three-segment token **without
printing it**:

```bash
python3 -c "t=open('/tmp/viewer.jwt').read(); assert t.count('.')==2, 'not a 3-segment JWT'; print('jwt: valid 3-segment,', len(t), 'chars')"
rm -f /tmp/viewer.jwt
```

(Use `--print-jwt` instead of `--jwt-out` to echo the JWT to stdout for interactive capture — but
remember stdout is captured in CI logs and transcripts. Omitting **both** is an error.)

## 4. Combined test (`upload-and-session` — primary live smoke; creates a document)

```bash
uv run scripts/viewer-session.py upload-and-session --file tests/fixtures/sample.pdf --jwt-out /tmp/viewer.jwt
```

Expect both `document_id=<id>` (stdout) and `jwt_written=/tmp/viewer.jwt`. Record the `document_id`
for teardown. Verify and discard the JWT as in step 3.

## 5. App-provided mode (no document created — preferred for routine smoke)

```bash
uv run scripts/viewer-session.py session --app-provided --jwt-out /tmp/viewer.jwt
```

Expect exit 0, a warning on stderr about the unconfirmed app-provided scope, and a valid JWT in the
file. No document is uploaded, so nothing needs teardown. Verify and discard the JWT as in step 3.

## 6. Missing-key test (fail fast — R-05)

```bash
NUTRIENT_DWS_VIEWER_API_KEY="" uv run scripts/viewer-session.py upload --file /dev/null
```

Expect exit 1 and an error naming `NUTRIENT_DWS_VIEWER_API_KEY`. No network call.

## 7. Teardown (blocking — R-16/R-17)

Delete **every** document created in steps 2 and 4 with the script's `delete` subcommand, then
confirm removal by **list-absence** (a direct `GET /viewer/documents/{id}` always returns 404 and is
**not** a liveness signal; the authoritative check is that the `document_id` no longer appears in
`GET /viewer/documents`):

```bash
# Delete each document created in steps 2 and 4:
uv run scripts/viewer-session.py delete --document-id <id from step 2>
uv run scripts/viewer-session.py delete --document-id <id from step 4>
```

```bash
# Verify no orphans remain (list-absence). GET /viewer/documents is the only authoritative check.
uv run - <<'PY'
import os, httpx
KEY = os.environ["NUTRIENT_DWS_VIEWER_API_KEY"]
H = {"Authorization": f"Bearer {KEY}"}
BASE = "https://api.nutrient.io/viewer/documents"
DOC_IDS = ["<id from step 2>", "<id from step 4>"]  # fill in
listing = httpx.get(BASE, headers=H, timeout=60).json()
present = {d["id"] for d in listing.get("data", [])}
orphans = [d for d in DOC_IDS if d in present]
assert not orphans, f"ORPHANS REMAIN: {orphans}"
print(f"teardown verified — no orphans; document_count={listing.get('document_count')}")
PY
```

This step is **not optional** in delete-confirmed mode: the smoke is incomplete while any uploaded
document remains in Nutrient storage.

## Routing collision check (R-01)

Mechanized (keyless) in `tests/smoke_viewer.py` — run `python3 tests/smoke_viewer.py`. For a manual
read, compare `nutrient-web-sdk/SKILL.md` `when_to_use` and this skill's `when_to_use` side by side
and confirm:

- `@nutrient-sdk/viewer` / `NutrientViewer.load()` **without** a DWS `session:` routes to
  `nutrient-web-sdk`, **not** here.
- "cloud viewer session", "mint a viewer session JWT", "embed with a session JWT",
  `POST /viewer/sessions` route **here**.
- No trigger phrase appears verbatim in both skills' `when_to_use`. The only shared symbol is
  `NutrientViewer.load`, which this skill qualifies as "with a `session:` token" (the server-side
  half) and `nutrient-web-sdk` owns for the framework embed.
