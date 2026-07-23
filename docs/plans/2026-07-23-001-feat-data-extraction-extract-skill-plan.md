---
artifact_contract: ce-unified-plan/v1
artifact_readiness: implementation-ready
execution: code
product_contract_source: ce-plan-bootstrap
title: "feat: Add schema Extract capability to the Data Extraction skill, reposition grounded-rag, guard processors"
created: 2026-07-23
depth: standard
target_repo: PSPDFKit-labs/nutrient-skills
---

# feat: Data Extraction `extract` skill + grounded-rag repositioning + guarded processors

**Target repo:** `PSPDFKit-labs/nutrient-skills` (paths below are relative to that repo root). Skills live under `plugins/nutrient-dws/skills/`.

## Summary

The Nutrient Data Extraction API is two GA primitives — `POST /extraction/parse` (whole-document spatial/markdown) and `POST /extraction/extract` (schema-driven field extraction with per-field citations). The `document-extraction-api` skill implements only `parse`. This plan adds an `extract` capability to that skill (the primary, independently shippable work), repositions `grounded-rag-ingestion` so field-level requests route to `extract` instead of parse→chunk (a small doc-only change), and adds optional, feature-guarded support for stored `processor` configs (a lower-priority add-on). All three are source-verified against the live DWS service (`PSPDFKit/PSPDFKit` `hosted/lib/hosted_web/router.ex` + `controllers/data_extraction/*`, master @ 2026-07-23).

The work is phased so each item ships on its own: **Phase 1** = the `extract` script + skill routing (PR A), **Phase 2** = grounded-rag repositioning (PR B, doc-only), **Phase 3** = processors (PR C, guarded).

---

## Problem Frame

An agent asked to "pull the invoice number and total from this PDF, with citations" today has no cited-field-extraction tool. It gets routed to `parse` (dump every element, sort and search it yourself) or to `grounded-rag-ingestion` (chunk the whole doc, embed, retrieve) — both wrong for known-field extraction. The GA `/extraction/extract` endpoint answers exactly this: supply a JSON Schema, get back your fields with per-field citations grounding each value to page coordinates. It is unimplemented in any skill, and the Python SDK (`nutrient-dws` 3.1.0) has `parse()` but no schema `extract()` — so it must be called via raw multipart `httpx`, the same transport the `dws-viewer-api` skill already uses.

Two secondary problems: (a) `grounded-rag-ingestion` doesn't tell an agent when NOT to use it (field extraction should go to `extract`), and (b) the API's stored/versioned "processor" configs and run history are entirely unsurfaced.

---

## Requirements

- **R1** — Add a script that calls `POST /extraction/extract` with a caller-supplied JSON Schema and returns the extracted fields plus per-field citations. GA, API-key auth, raw `httpx` multipart.
- **R2** — Validate the schema client-side only against the **unambiguous** limits (root type `object`; UTF-8-serialized JSON ≤ 32 KB; free-text `instructions` ≤ 10,000 chars) so gross oversize/malformed input fails fast **before** the billed call. Do **not** replicate the server's node-count/depth walk client-side (the exact algorithm — what counts as a node, how `$defs`/`$ref`/arrays/keys are counted — is not knowable from public sources and a mismatch would reject valid schemas or pass invalid ones); delegate those to the server and surface its `validation_error` paths verbatim. (Revised per adversarial review, finding P1-5.)
- **R3** — Accept a **local file OR a URL** (unlike `parse`, which is local-only — `/extraction/extract` supports a `url` field).
- **R4** — Support `instructions` (free text), `parseConfig.mode` (default `understand`, matching the server default), `options.includeCitations` (default **true**), and `storeRun` (default false).
- **R5** — Reuse the skill's key handling (`NUTRIENT_EXTRACT_API_KEY`) and never print the key; redact it from error output. No key in committed files.
- **R6** — Preflight a credit-cost **estimate** using the correct combined rate — parse-mode cost **plus the flat +6 cr/page extract surcharge** (text 7, structure 7.5, understand 15, agentic 24 cr/page) — and gate high-cost runs behind confirmation. When page count is unknown (a URL input, or a non-PDF whose pages can't be counted locally), the estimate is unavailable: warn that cost can't be pre-estimated and **proceed** (do not hard-block the default path), with `--yes` to silence. The server-returned `usage` is authoritative and is printed after the call. (Revised per adversarial review, findings P1-1, P1-2.)
- **R7** — Update the `document-extraction-api` SKILL.md (and discovery metadata) so field-level intents ("extract these fields", "map to my schema", "with citations", "invoice number and total") route to `extract`, while whole-document/RAG/markdown intents stay on `parse`.
- **R8** — Add the first unit-test file to the extraction skill, keyless/mocked (`httpx.MockTransport` for the network path; pure-function tests for schema validation and response surfacing; subprocess tests for CLI error paths), matching the `dws-viewer-api` / `grounded-rag-ingestion` test style.
- **R9** — Reposition `grounded-rag-ingestion` (doc-only): its `when_to_use` and "related skills" route known-field requests to `extract`; no change to `chunk.py`.
- **R10** — Add optional stored-`processor` support (run a processor by reference from `extract`, plus minimal processor management) guarded on the `data_extraction_processors` feature so it degrades with a clear "feature not enabled for this tenant" message rather than an opaque error.
- **R11** — Harden the output write like the sibling skills: preflight the `--out` target (parent exists/writable, not a symlink, not a directory) **before** the billed call, and write the response with `O_NOFOLLOW` + `0600`, mirroring `grounded-rag-ingestion`'s `chunk.py`. The extracted response contains the document's sensitive content and must not land at a wider mode, follow a planted symlink, or be lost after a paid call. (Added per adversarial review, finding P1-7.)

Out of scope (see Scope Boundaries): `generate_schema` / `classify` / `form` (internal preview), OAuth-token auth, and any SDK change.

---

## Key Technical Decisions

**KTD-1 — Extend the existing `document-extraction-api` skill; do not create a new skill.** `parse` and `extract` are sibling primitives of one product; the skill is named for the product. Adding `scripts/extract.py` alongside `scripts/parse.py` (mirroring the `pdf-to-markdown` / `pdf-to-text` / `query` one-family pattern) keeps routing in one place. Agent routing between the two is handled by the SKILL.md `description`/`when_to_use` (U4), not by skill boundaries.

**KTD-2 — Raw `httpx` multipart, not the SDK.** `nutrient-dws` 3.1.0 exposes `parse()` but no schema `extract()`. `extract.py` posts multipart to `https://api.nutrient.io/extraction/extract` directly, exactly as `dws-viewer-api/scripts/viewer-session.py` does for the viewer endpoints. The script declares `httpx>=0.27` in its PEP-723 inline deps. This keeps `parse.py` (SDK) untouched.

**KTD-3 — Key resolution helper in `lib/common.py`, returning the bearer string.** `create_client()` returns a `NutrientClient` (useless for a raw request). Add `resolve_extract_key()` to `scripts/lib/common.py` that returns the raw key string using the **same** precedence `create_client()` already uses, and refactor `create_client()` to call it so the two never drift. Add a `redact(text, key)` helper mirroring `viewer-session.py`'s.

**KTD-4 — Match `parse.py`'s key-fallback behavior, not the viewer's stricter opt-in.** Within the extraction skill, `parse.py` already falls back `NUTRIENT_EXTRACT_API_KEY` → `NUTRIENT_API_KEY` silently. `extract.py` matches that for intra-skill consistency (two scripts, identical auth behavior), rather than importing the viewer skill's `--allow-global-key` gate. Rationale: surprise-minimization within a skill outweighs cross-skill uniformity; the viewer's stricter gate exists because a viewer JWT is browser-facing, which does not apply here. *(This is the one place the plan diverges from the loose "no silent fallback" phrasing in the request; flagged for reviewer confirmation.)*

**KTD-5 — Validate only the *unambiguous* limits client-side; delegate node-count/depth to the server.** Client-side, reject only what is unambiguous and cheap to check exactly: root type not `object`, UTF-8-serialized JSON > 32 KB, `instructions` > 10,000 chars. Do **not** re-implement the server's schema *walk* (`@max_schema_nodes 500`, `@max_schema_depth 5` in `extract/request.ex`): the walk's counting rules (keys vs values, arrays, `$defs`/`$ref` expansion, root inclusion) aren't derivable from public sources, and a client validator that disagrees with the server would reject valid schemas or pass invalid ones — worse than delegating. The server returns precise `validation_error` paths for those; `extract.py` surfaces them verbatim. (Narrowed per adversarial review, finding P1-5.)

**KTD-6 — Citations on by default; summarize *honestly*, don't over-claim.** `options.includeCitations` defaults true. `extract.py` writes the full JSON response to `--out` and prints a compact summary. `output.metadata` **mirrors the structure of `output.data`** (a parallel tree, not a flat map), so the summary reports (a) the top-level field names of `output.data`, and (b) whether citations are present overall (`output.metadata` non-empty). It does **not** claim per-field "cited/uncited" status for nested objects/arrays unless it walks the two trees in parallel — a naive flat check would falsely label valid nested citations as absent. A `--no-citations` flag sets `includeCitations:false`. (Revised per adversarial review, finding P1-6.)

**KTD-7 — Processors are feature-guarded and isolated to Phase 3.** `extract.py` gains an optional `--processor <public_id[:version]>` that sends a `processor` reference instead of an inline `schema`; a separate `scripts/processors.py` does create/list/show/versions/publish. No processor code ships in Phase 1. **Feature-off detection must key on the server's specific feature-flag signal**, not a bare 403/404 — a missing processor, bad identifier, auth failure, or wrong path also produce those statuses. When the signal is present, print "the `data_extraction_processors` feature is not enabled for this tenant"; when a 403/404 lacks the flag signal, report it as the specific error (not-found / unauthorized), or, if the shape is uncertain, say "possibly not enabled" rather than asserting. (Tightened per adversarial review, finding P2-3.)

**KTD-8 — Extract cost = parse-mode cost + a flat +6 cr/page surcharge; the reused `MODE_COST` is parse-only.** `grounded-rag-ingestion`'s `MODE_COST` (`text 1 / structure 1.5 / understand 9 / agentic 18`) is the **parse** rate; extract bills a "price composition" of parse **plus** a flat +6 cr/page (per the public pricing page and `Hosted.Usage.FeatureCost.extract_price_composition`). `extract.py` uses its own `EXTRACT_MODE_COST` (`text 7 / structure 7.5 / understand 15 / agentic 24`) for the preflight estimate — reusing `MODE_COST` verbatim would undercharge every estimate and silently bypass the gate. The estimate is approximate; the server `usage` printed after the call is authoritative. (Added per adversarial review, finding P1-1.)

**KTD-9 — `httpx` client needs an explicit timeout, and 2xx bodies are not trusted.** Set an explicit extraction timeout on the `httpx` call (the viewer skill uses 180 s; extract may run longer under `agentic` — use a generous default, e.g. 300 s, overridable). A 2xx response whose body is not JSON, or is missing `output`, is treated as a failure (redact + report), never as an empty success — mirroring the viewer skill's non-JSON / missing-result handling. (Added per adversarial review, finding P2-1.)

---

## High-Level Technical Design

Routing is the crux of U4 — the decision an agent makes before calling either script:

| Intent in the request | Route to | Why |
|---|---|---|
| "extract the invoice number and total", "pull these fields", "map to my schema", "with citations", form/invoice **fields** | `extract.py` | Known target fields → schema extract, one cited call |
| "parse this doc", "give me the whole document", "markdown for RAG", "chunk for embeddings", search indexing, migration | `parse.py` (then `grounded-rag-ingestion` for chunking) | Whole-document model, open-ended retrieval |
| "extract every table / all key-value regions" (no target schema) | `parse.py` (spatial) | Enumerate all elements; `extract` needs a schema |

`extract.py` request/response flow (directional, not implementation spec):

```
load schema file ── validate (KTD-5) ──┐
                                        ├─► build instructions JSON {schema, instructions?, parseConfig.mode, options.includeCitations, storeRun?}
resolve key (KTD-3) ────────────────────┘        │
                                                 ▼
       preflight --out (R11) + cost gate (R6) ──► POST multipart /extraction/extract (file part OR url in body)
                                                 │
                                    ┌────────────┴─────────────┐
                              2xx JSON w/ output ▼     non-2xx / non-JSON / no output ▼
                    safe-write full JSON to --out (0600)   redact key, print server
                    print output.data + citation           validation paths, exit 1
                    summary + usage (parse vs
                    extract credits)
```

---

## Implementation Units

### Phase 1 — `extract` capability (PR A, independently shippable)

### U1. `lib/common.py` — key-string resolver + redaction helper

- **Goal:** Provide a raw bearer-key resolver and a key-redaction helper that `extract.py` (and future raw-HTTP scripts) can share, and fix a latent empty-key bug in `create_client()` along the way.
- **Requirements:** R5, KTD-3, KTD-4.
- **Dependencies:** none.
- **Files:** `plugins/nutrient-dws/skills/document-extraction-api/scripts/lib/common.py` (modify); `plugins/nutrient-dws/skills/document-extraction-api/scripts/lib/test_common.py` (new).
- **Approach:** Add `resolve_extract_key() -> str` with the `EXTRACT → NUTRIENT_API` precedence, but **corrected**: an explicitly empty `NUTRIENT_EXTRACT_API_KEY` raises, rather than being passed through. This is a deliberate fix — the current `create_client()` docstring *claims* an empty key is "a misconfiguration to surface," but the code actually passes `""` to `NutrientClient` (the `is None` guard lets an empty string through). Refactor `create_client()` to call `resolve_extract_key()`; this **intentionally changes** `create_client`'s empty-key behavior to match its own documented contract. Add `redact(text, key) -> str` mirroring `dws-viewer-api/scripts/viewer-session.py`.
- **Execution note:** This is an intentional behavior change, not a characterization-locked refactor — the test asserts the *corrected* behavior, and the change is called out in the PR description so a reviewer sees it. (Resolves the plan contradiction flagged in adversarial review, finding P1-4.)
- **Patterns to follow:** existing `create_client()` precedence in the same file; `redact()` in `plugins/nutrient-dws/skills/dws-viewer-api/scripts/viewer-session.py`.
- **Test scenarios:**
  - `resolve_extract_key` returns the extract key when set; returns the fallback when only `NUTRIENT_API_KEY` is set; raises when both unset; **raises when the extract key is explicitly empty string** (the corrected behavior).
  - `create_client` after refactor: resolves identically when a real key is set (unchanged for the normal path); now **raises** on an explicitly-empty extract key where it previously passed `""` — assert the new, correct behavior and note the change.
  - `redact` replaces the key everywhere it appears; is a no-op when key is `None` or absent from the text.
- **Verification:** `test_common.py` passes; `parse.py` still resolves keys identically for real keys; the empty-key path now errors clearly.

### U2. `scripts/extract.py` — the extract script

- **Goal:** Call `/extraction/extract` with a validated schema (or URL/file), surface cited fields, gate cost, harden output.
- **Requirements:** R1–R6, R11, KTD-2, KTD-5, KTD-6, KTD-8, KTD-9.
- **Dependencies:** U1.
- **Files:** `plugins/nutrient-dws/skills/document-extraction-api/scripts/extract.py` (new).
- **Approach:** PEP-723 deps `["httpx>=0.27", "pypdf>=4.0"]` (`pypdf` for the local page-count estimate, matching `chunk.py`). Args: `--input <path>` XOR `--url <url>` (exactly one required); `--schema <path>` (required in Phase 1; becomes optional-with-`--processor` in Phase 3); `--out <path>`; `--instructions <text>`; `--mode {text,structure,understand,agentic}` default `understand`; `--no-citations`; `--store-run`; `--yes` (bypass cost gate). Pure helpers (unit-tested): `load_schema(path)`, `validate_schema(schema)` (KTD-5 — root object, ≤32 KB UTF-8, instructions ≤10k only), `build_instructions(...)`, `estimate_cost(pages, mode)` using `EXTRACT_MODE_COST` (KTD-8), `preflight(pages, mode, yes)` (unknown pages → warn + proceed per R6, not block), `summarize_response(response)` (honest top-level + citations-present per KTD-6). Network: for a local file, multipart with a **`file`** part and an **`instructions`** JSON-string part; for a URL, a JSON body carrying `url` plus the instruction fields. `Authorization: Bearer <resolve_extract_key()>`; explicit `httpx` timeout (KTD-9); POST to `https://api.nutrient.io/extraction/extract`. Non-2xx OR a 2xx that isn't JSON / lacks `output`: `redact` the key from the body and print the server's validation paths, exit 1. **Output hardening (R11):** preflight the `--out` target before the billed call (parent exists/writable, not a symlink, not a dir), and write with `O_NOFOLLOW` + `0600` — copy the pattern from `chunk.py` steps 3b and 5.
- **Technical design (directional):** see the request/response flow diagram above. The multipart `instructions` part is the JSON-serialized `{schema, instructions?, parseConfig:{mode}, options:{includeCitations}, storeRun?}` — key order in `schema` is preserved by the server, so serialize the loaded schema without re-sorting keys. **Multipart shape source:** the `file` + `instructions` part names and the JSON-URL body are taken from `PSPDFKit/PSPDFKit` `hosted/lib/hosted_web/controllers/data_extraction/extract_controller.ex` (docstring) — not visible in this repo, so U3's tests pin the shape and a live smoke test confirms it before merge (see Risks).
- **Patterns to follow:** `dws-viewer-api/scripts/viewer-session.py` (raw httpx, `redact`, explicit timeout, `O_NOFOLLOW`+`0600` write, non-JSON-2xx handling, error-path shape); `grounded-rag-ingestion/scripts/chunk.py` (`preflight_decision`, `_local_page_count` via pypdf, `--out` preflight at step 3b, safe write at step 5); `parse.py` usage-summary printing. **Do not** reuse `MODE_COST` — it is parse-only (KTD-8).
- **Test scenarios:** (in U3)
- **Verification:** `--help` exits 0; a mocked 2xx run writes the response (0600) and prints an honest cited-field summary; an oversized (>32 KB) schema exits non-zero before any network call; a URL run with unknown page count proceeds (does not hard-block).

### U3. `scripts/test_extract.py` — first test file for the skill

- **Goal:** Keyless/mocked coverage of extract's pure logic, network path, and CLI error paths.
- **Requirements:** R8.
- **Dependencies:** U2.
- **Files:** `plugins/nutrient-dws/skills/document-extraction-api/scripts/test_extract.py` (new).
- **Approach:** PEP-723 deps `["httpx>=0.27", "pytest>=8.0", "pypdf>=4.0"]`. `extract.py` has no hyphen, so it's importable directly (unlike the viewer script, which `test_viewer_session.py` loads via `importlib`). Pure-function tests + `httpx.MockTransport` for the POST + `subprocess` for CLI error paths, mirroring `dws-viewer-api/scripts/test_viewer_session.py`.
- **Test scenarios:**
  - **Schema validation (pure) — narrowed per KTD-5:** valid minimal object schema passes; non-object root rejected; a schema whose UTF-8 serialization exceeds 32 KB rejected (fixture at the exact boundary — 32 KB passes, 32 KB + 1 rejected); `instructions` > 10,000 chars rejected. **No client-side node-count/depth tests** — those are the server's to enforce; assert instead that a deeply-nested but small schema is *accepted* client-side (so the client doesn't over-reject) and that the server's `validation_error` for such a case is surfaced verbatim (mocked).
  - **build_instructions (pure):** `options.includeCitations:true` by default, `false` under `--no-citations`; `parseConfig.mode` defaults to `understand`; `storeRun` present only when set; schema key order preserved (serialized order matches input, not sorted).
  - **estimate_cost / preflight (pure):** `understand` estimates **15** cr/page (not 9) — asserts the surcharge is applied; over-threshold without `--yes` blocks (exit 2), `--yes` proceeds; **unknown page count (URL or non-PDF) warns and proceeds** (does not block the default `understand` path) — this is the R6 fix and directly guards the P1-2 regression.
  - **summarize_response (pure) — honest per KTD-6:** lists top-level `output.data` field names and reports citations-present when `output.metadata` is non-empty; a **nested** `output.data`/`output.metadata` fixture does **not** get its nested citations mislabeled as absent; empty `output.metadata` (citations disabled) reports "no citations" without error or false per-field claims.
  - **Network (MockTransport) — pin the wire shape:** a 2xx JSON response is written to `--out` and the summary printed; the request carries `Authorization: Bearer <key>`; for a local file the body is multipart with a part **named `file`** AND a part **named `instructions`** whose content is valid JSON containing `schema`/`parseConfig`/`options` and which does **not** carry an accidental filename; a `--url` run sends a JSON body containing `url` and the instruction fields and **no** file part.
  - **Error paths:** non-2xx surfaces the server validation body with the key **redacted** and exits 1; a **2xx with a non-JSON body** and a **2xx missing `output`** are each treated as failures (redacted, exit 1), never as empty success; missing key exits 1 naming `NUTRIENT_EXTRACT_API_KEY`; empty `NUTRIENT_EXTRACT_API_KEY` exits 1 (U1 corrected behavior); both `--input` and `--url` (or neither) exits 1; `--input` that doesn't exist exits 1.
  - **Output hardening (R11):** the written file is mode `0600`; a symlinked `--out` is refused before the billed call; a non-writable/`--out`-is-a-dir target fails before the call. Model these on `test_viewer_session.py`'s `--jwt-out` symlink/dir tests.
- **Verification:** `python3 -m pytest test_extract.py -q` and the plain runner both green, no network, no key; the wire-shape and unknown-page-count tests specifically guard the adversarial-review findings.

### U4. `document-extraction-api` SKILL.md — extract routing + docs

- **Goal:** Route field-level intents to `extract`, whole-doc to `parse`; document `extract` invocation, citations, URL input, and the cost note.
- **Requirements:** R7.
- **Dependencies:** U2 (so documented flags match the script).
- **Files:** `plugins/nutrient-dws/skills/document-extraction-api/SKILL.md` (modify); `plugins/nutrient-dws/skills/document-extraction-api/references/extract-output-and-citations.md` (new, brief — mirrors `references/parse-output-filtering.md`, links the public `guides/dws-data-extraction/extract/` docs).
- **Approach:** Rewrite `description`/`when_to_use` to add the extract triggers and the parse-vs-extract routing table (from the HTD section). Add an "## `/extraction/extract` — schema field extraction with citations" section: invocation examples (file and URL), the `includeCitations` default, the credit note (parse stage + extract stage billed separately, +6 cr/page), and a pointer to the new references file. Keep the existing parse content intact. Preserve the block-scalar `description` style used across the family (avoid the bare-`:` YAML pitfall fixed in the query skill).
- **Patterns to follow:** the existing SKILL.md structure; `references/parse-output-filtering.md` for the references-file shape.
- **Test scenarios:** `Test expectation: none — documentation unit.` Verification is a YAML-frontmatter parse check (block scalar valid) + a human read that the routing table is unambiguous.
- **Verification:** frontmatter parses under a strict YAML parser; routing table present; extract flags documented match `extract.py --help`.

### U7. Discovery metadata — README + plugin manifests mention `extract`

- **Goal:** Make Phase 1 actually discoverable as "parse **and** extract", not Parse-only, so it's independently shippable.
- **Requirements:** R7 (discoverability half).
- **Dependencies:** U2, U4.
- **Files:** `README.md` (modify — the `nutrient-dws` / `document-extraction-api` skills-table row); `plugins/nutrient-dws/.claude-plugin/plugin.json` and `plugins/nutrient-dws/.codex-plugin/plugin.json` (modify — description strings that currently describe extraction as parse-only).
- **Approach:** Update the one-line descriptions so they name schema field extraction with citations alongside parse. Keep them short; don't restructure the table. (Addresses adversarial-review finding P2-2 — without this, a discovery reader still sees a Parse-only skill.)
- **Test scenarios:** `Test expectation: none — metadata/doc unit.` Verification: both `plugin.json` files remain valid JSON; the README table row still renders.
- **Verification:** `plugin.json` files parse; README row mentions extract.

---

### Phase 2 — grounded-rag repositioning (PR B, doc-only)

### U5. `grounded-rag-ingestion` positioning + cross-references

- **Goal:** Make an agent choose `extract` for known fields and `grounded-rag-ingestion` only for whole-document RAG.
- **Requirements:** R9.
- **Dependencies:** U4 (so the referenced extract capability exists and links resolve).
- **Files:** `plugins/nutrient-dws/skills/grounded-rag-ingestion/SKILL.md` (modify); `plugins/nutrient-dws/skills/document-extraction-api/SKILL.md` (modify — add a back-reference to grounded-rag under related skills).
- **Approach:** In grounded-rag's `when_to_use`/"When to use"/"Related skills": add a one-line "for known target fields with citations, use the `document-extraction-api` skill's `extract` instead of chunking the whole document." No change to `chunk.py`, its schema doc, or tests. Add the reciprocal one-liner to the extraction SKILL.md.
- **Patterns to follow:** the existing "Related Nutrient skills" blocks in the family.
- **Test scenarios:** `Test expectation: none — documentation-only unit.`
- **Verification:** both SKILL.md frontmatters still parse; cross-references name the correct skills and are reciprocal.

---

### Phase 3 — processors (PR C, feature-guarded add-on)

### U6. Stored-`processor` support in `extract.py` + `processors.py` management

- **Goal:** Run a stored/versioned processor from `extract`, and manage processors, degrading clearly when the feature is off.
- **Requirements:** R10, KTD-7.
- **Dependencies:** U2, U3.
- **Files:** `plugins/nutrient-dws/skills/document-extraction-api/scripts/extract.py` (modify — add `--processor`); `plugins/nutrient-dws/skills/document-extraction-api/scripts/processors.py` (new); `plugins/nutrient-dws/skills/document-extraction-api/scripts/test_processors.py` (new); `plugins/nutrient-dws/skills/document-extraction-api/SKILL.md` (modify — document processors as feature-gated).
- **Approach:** `extract.py` gains `--processor <public_id[:version]>`; when set, `--schema` becomes optional and the request sends a `processor` reference instead of an inline schema (and `storeRun` may still accompany it, per the server contract); `--processor` + `--schema` together is rejected. `processors.py` implements `create`/`list`/`show`/`create-version`/`publish-version` against `/extraction/processors...` via the same raw-httpx + key handling. Feature-off detection keys on the **specific feature-flag signal** (KTD-7), not any 403/404 — a missing processor, bad id, auth failure, or wrong path is reported as that specific error; only a flag-signalled response prints "the `data_extraction_processors` feature is not enabled for this tenant — contact Nutrient to enable it"; an ambiguous 403/404 says "possibly not enabled" rather than asserting.
- **Patterns to follow:** U2's httpx + redact + error-path shape; the router's `/extraction/processors` verbs (`index`/`create`/`show`/`rename`/`delete`/`create_version`/`show_version`/`publish_version`).
- **Test scenarios:**
  - `extract.py --processor` sends a `processor` reference (no inline schema) and omits schema validation; `--processor` + `--schema` together is rejected with a clear message.
  - `processors.py` create/list/show/versions/publish each hit the right method+path (MockTransport asserts).
  - a mocked feature-flag-signalled response prints the "feature not enabled" message and exits non-zero; a generic 404 (missing processor) reports not-found, NOT "feature disabled"; a generic 403 (auth) reports unauthorized — for both `extract --processor` and each `processors.py` verb.
  - key redaction holds on processor error paths.
- **Verification:** `test_processors.py` green keyless/mocked; feature-off path is graceful and specific across all processor entry points.

---

## Scope Boundaries

**In scope:** `extract` script + routing + tests + discovery metadata (Phase 1); grounded-rag doc repositioning (Phase 2); guarded processors + run-a-processor (Phase 3).

### Deferred to Follow-Up Work
- **Runs API surface** (`/extraction/runs` list/show/delete/download-asset/shares). `extract.py` can already set `storeRun`; a dedicated runs-management script is a separate follow-up once processors land.
- **OAuth access-token auth** for extraction (the endpoint accepts it; the skill stays API-key-only for now).
- **An SDK-based extract path** — revisit if `nutrient-dws` adds a schema `extract()` method; today raw httpx is the only option.

### Outside this work's identity
- **`generate_schema`, `classify`, `form`** — these `/extraction/*` endpoints are **internal preview** (`data_extraction_preview` flag; 404 for public tenants). A public skill targeting them would fail for real users. Note them only as a one-line roadmap comment in the extraction SKILL.md; do not implement.

---

## Risks & Dependencies

- **Multipart request shape unverifiable from this repo (Medium — the load-bearing risk).** The `file` + `instructions` part names and the JSON-URL body come from `PSPDFKit/PSPDFKit` `hosted/.../extract_controller.ex`, which is **not** in this repo, so tests can only pin the shape the plan asserts, not prove it against the server. Mitigation: U3 asserts the full shape (both part names, instructions-is-JSON, no accidental filename, URL-body form) AND a **live smoke test against a real key is a merge gate for Phase 1** (manual, out of CI — same posture as the viewer skill's live-smoke guide). If the live call disagrees, fix `build_instructions`/request assembly before merge.
- **Cost estimate is approximate (Low).** `EXTRACT_MODE_COST` encodes the published parse+6 rates, but the server computes the authoritative "price composition"; the preflight can drift if pricing changes. Mitigation: the estimate is labeled approximate and the server `usage` is printed after the call as the source of truth.
- **Server-side finer schema limits (Low).** Node-count/depth are enforced server-side (KTD-5); the client intentionally doesn't replicate them, so there's nothing to drift — the trade is a billed call for an over-limit schema the client can't catch, which the cost gate and the server's fast 400 both bound.
- **`create_client()` empty-key behavior change (Low, intentional).** U1 deliberately makes an explicitly-empty extract key raise (aligning code with its docstring). Called out in the PR; the only affected path is a misconfiguration that previously failed later and more opaquely.
- **Processor feature detection fragility (Low, Phase 3 only).** Keyed on the specific feature-flag signal, not bare 403/404 (KTD-7); ambiguous statuses report "possibly not enabled" rather than asserting.
- **Dependencies:** `httpx>=0.27` and `pypdf>=4.0` (both already used elsewhere in the family; declared per-script in PEP-723 blocks, no repo-level dependency change).

---

## Definition of Done

- `extract.py` exists, calls `/extraction/extract` via raw httpx with an explicit timeout, validates only the unambiguous schema limits client-side (root object, ≤32 KB, instructions ≤10k), accepts file or URL, surfaces cited fields honestly, gates cost using the correct parse+6 rate, hardens the output write (`--out` preflight + `O_NOFOLLOW`/`0600`), treats non-JSON/`output`-less 2xx as failure, and redacts the key from errors.
- `test_extract.py` and `test_common.py` pass keyless/mocked, including the wire-shape (both multipart part names), unknown-page-count-proceeds, nested-citation-honesty, and output-hardening scenarios; `parse.py` behavior unchanged for real keys (empty-key path now errors intentionally, per U1).
- The `document-extraction-api` SKILL.md routes field intents to `extract` and whole-doc intents to `parse`, with valid block-scalar frontmatter; README + both `plugin.json` files describe extract (U7), so Phase 1 is discoverable.
- `grounded-rag-ingestion` SKILL.md points known-field requests at `extract`; `chunk.py` untouched.
- Phase 3 (if landed): `--processor` and `processors.py` work mocked and degrade with a *specific* message (flag-signalled vs generic 403/404) when the feature is off.
- Three PRs staged (Phase 1 / Phase 2 / Phase 3), each independently reviewable; human merges. **Live smoke of one real extract call is a merge gate for Phase 1** (confirms the multipart wire shape).

---

## Sources & Research

- Live API surface (authoritative): `PSPDFKit/PSPDFKit` `hosted/lib/hosted_web/router.ex` (`/extraction` scopes), `hosted/lib/hosted_web/controllers/data_extraction/extract_controller.ex`, `hosted/lib/hosted/data_extraction/extract/request.ex` (schema limits, `includeCitations` default, `parseConfig.mode` default), `hosted/lib/hosted/data_extraction/extract.ex` (`extract_price_composition` billing) — master, pushed 2026-07-23.
- Public docs: `nutrient.io/api/data-extraction-api/`, `nutrient.io/guides/dws-data-extraction/extract/`, `nutrient.io/api/pricing/data-extraction-api/` (parse+6 cr/page extract surcharge).
- SDK gap: `PSPDFKit/nutrient-dws-client-python` `src/nutrient_dws/client.py` (has `parse`, no schema `extract`), PyPI `nutrient-dws` 3.1.0.
- In-repo patterns: `plugins/nutrient-dws/skills/document-extraction-api/scripts/{parse.py,lib/common.py}`, `plugins/nutrient-dws/skills/dws-viewer-api/scripts/{viewer-session.py,test_viewer_session.py}`, `plugins/nutrient-dws/skills/grounded-rag-ingestion/scripts/chunk.py` (preflight cost gate, safe write, page count).
- Adversarial review (2026-07-23, codex high-reasoning): 7 P1 + 3 P2 findings, all addressed in this revision (P1-1 cost, P1-2 page-count dep, P1-3 wire shape, P1-4 U1 contradiction, P1-5 schema limits, P1-6 citation honesty, P1-7 output hardening, P2-1 timeout/malformed-2xx, P2-2 discovery metadata, P2-3 processor signal).
---
