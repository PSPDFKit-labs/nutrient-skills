# Changelog

## nutrient-dws grounded-rag-ingestion 1.0.0

Initial release of the grounded RAG ingestion skill in the `nutrient-dws` plugin.

**New:**
- `chunk.py` doer script: transforms `/extraction/parse` spatial output into provenance-carrying JSONL — one chunk per logical element, each with element type, page index, bounding box, confidence, and reading order
- Reuses `document-extraction-api`'s `create_client()` + `client.parse()` rather than re-implementing the API call; runs its own preflight credit-cost gate
- Collision-safe `chunk_id` scheme: content-anchored `doc_id` (never the basename) plus `_e` inter-element and `_tr`/`_kv`/`_w` intra-element discriminators
- Three chunking strategies (element, reading-order-window, table-row), table span-expansion, key-value region mapping, and `--min-confidence` filtering
- `references/provenance-chunk-schema.md`, an illustrative embedding example, and a generated test fixture

## make-pdf 1.0.1 / remediate-pdf 1.0.1

Repackaged both skills as standalone plugins so the install id matches the skill.

**Changed:**
- Install ids are now `make-pdf@nutrient-skills` and `remediate-pdf@nutrient-skills` (previously both shipped inside `nutrient-dws`, whose id said nothing about either skill)
- `remediate-pdf` now bundles its own copy of `verify-pdf.py`, so checking tagged output no longer reaches into the make-pdf plugin (a smoke-test assertion keeps the two copies byte-identical in-repo)
- `make-pdf`'s chaining docs now reference `document-processor-api` (sign/redact/merge) and `remediate-pdf` as separately installable plugins
- `nutrient-dws` returns to its API-scripts scope (`document-processor-api`, `document-extraction-api`)

## nutrient-dws remediate-pdf 1.0.0

Initial release of the remediate-pdf skill in the `nutrient-dws` plugin (auto-tag only).

**New:**
- `autotag.py` doer script: uploads a PDF to `POST /accessibility/autotag` and writes back the PDF/UA-tagged document, via the dedicated DWS Accessibility API (separate `NUTRIENT_ACCESSIBILITY_API_KEY`)
- Direct `httpx` transport (the `nutrient-dws` SDK exposes no Accessibility method); no silent fallback to the Processor key; `--url` SSRF validation; client-side 150 MiB check; quota-confirmation gate; API-key redaction from error output
- `references/accessibility-api-reference.md` and `references/pdf-ua-wcag-compliance-notes.md`
- Conformance **validation is intentionally not part of this skill**: the DWS Accessibility API exposes no validation endpoint yet. Check tagged output with the sibling `make-pdf` skill's `verify-pdf.py` (structural PDF/UA signals, optional veraPDF audit)

## nutrient-dws make-pdf 1.0.0

Initial release of the make-pdf skill in the `nutrient-dws` plugin — Markdown/HTML to compliance-grade PDF via the DWS Build API.

**New:**
- `make-pdf.py`: single files or whole directories (non-recursive, 4 concurrent builds, per-file frontmatter/first-heading/filename titles, no overwriting); outputs standard PDF, accessible PDF/UA (`--accessible`), or archival PDF/A (`--pdfa`, all seven conformance levels), with diagonal text watermarks (`--watermark`)
- Built-in conformance verification after every compliance build: exit `3` = generated but failed verification (PDF kept for inspection); `--no-verify` is the explicit opt-out; verification that cannot run also exits `3` rather than silently passing
- `verify-pdf.py`: standalone structural PDF/UA-1 / PDF/A checker for any PDF or directory (pikepdf), escalating to a full veraPDF audit when `verapdf` is on PATH
- `document`/`memo` templates with light/dark print CSS; real CommonMark+GFM parsing (`markdown-it-py`); documented Chromium limits (no CSS running headers or `target-counter` TOC page numbers)
- Fully offline smoke suite (14 checks, no key or network)

## query 1.0.0

Initial release of the query skill — ranked (BM-25) search over an already-extracted document, returning only the most relevant line windows instead of the whole file.

**New:**
- `query` skill: `query text INPUT "QUERY"` ranks every line of a converted `.md`/`.txt` (or a prebuilt index) and returns the top line windows with global line numbers — "parse once, query many"
- `--emit-index` writes a reusable, self-contained index so repeat questions skip the rebuild
- Shares the `~/.local/share/nutrient/cli/` install and 6-hour update check with `pdf-to-markdown` / `pdf-to-text` (one binary backs all of them)
- Claude Code and Codex plugin manifests

## pdf-to-markdown 1.2.0

**Changed:**
- SKILL.md now points to the `query` skill for searching large conversions instead of reading them back into context ("parse once, query many")

## pdf-to-text 1.1.0

**Changed:**
- SKILL.md now points to the `query` skill for searching large conversions instead of reading them back into context ("parse once, query many")

## pdf-to-text 1.0.0

Initial release of the pdf-to-text skill — layout-preserving plain-text extraction from PDFs, backed by the same `nutrient` CLI as pdf-to-markdown.

**New:**
- `pdf-to-text` skill: each word is placed on a character grid mirroring its on-page position, so columns, indentation, and tabular alignment survive the conversion
- Shares the `~/.local/share/nutrient/cli/` install and 6-hour update check with `pdf-to-markdown` (one binary backs `pdf-to-markdown`, `pdf-to-text`, and `self-update`)
- Claude Code plugin manifest

## pdf-to-markdown 1.1.0

Adapts the wrapper for nutrient 1.1.0's verb-aware CLI.

**Changed:**
- `bin/pdf-to-markdown` now execs through a `pdf-to-markdown`-named symlink so the multi-call binary dispatches on `argv[0]`; forward- and backward-compatible with pre-1.1.0 binaries

## nutrient-sdk-dev 1.0.0

Initial release of the Nutrient SDK development plugin — an umbrella set of skills for building with the Nutrient SDK families.

**New:**
- 13 skills, one per SDK family: `nutrient-web-sdk`, `nutrient-document-authoring`, `nutrient-ios-sdk`, `nutrient-android-sdk`, `nutrient-react-native-sdk`, `nutrient-flutter-sdk`, `nutrient-maui-sdk`, `nutrient-python-sdk`, `nutrient-java-server-sdk`, `nutrient-nodejs-server-sdk`, `nutrient-dotnet-server-sdk`, `nutrient-document-engine`, `nutrient-ai-assistant`
- Each skill points to the relevant nutrient.io API reference and guide URLs (`llms.txt` dumps where available) and example repositories for that SDK
- Corrects stale training data on package names and APIs (e.g. `@nutrient-sdk/viewer` / `NutrientViewer.load`, the PSPDFKit → Nutrient rebrand)
- Claude Code and Codex plugin manifests

## nutrient-dws 2.0.0

Full content rewrite and relicense (Apache-2.0 → MIT) of the DWS document processing skill.

**Changed:**
- Skill content replaced with the canonical implementation from `PSPDFKit-labs/nutrient-agent-skill/nutrient-document-processing/`
- Relicensed from Apache-2.0 to MIT (all authors are Nutrient employees)
- `SKILL.md` rewritten with richer decision rules, anti-patterns, multi-step workflow guidance, and security hardening addendum
- `scripts/` refreshed: 17 single-operation Python scripts (added `add-pages.py`, `delete-pages.py`, `duplicate-pages.py`; removed demo `ocr-watermark*.py` scripts)
- `references/` expanded from 2 to 8 documents: added `compliance-and-optimization.md`, `extraction-and-ocr.md`, `generation-and-conversion.md`, `pdf-manipulation.md`, `request-basics.md`, `security-signing-and-forms.md`, `workflow-recipes.md`
- `assets/templates/custom-workflow-template.py` updated to reflect new multi-step workflow pattern
- `agents/openai.yaml` added for OpenAI Codex agent interface
- `tests/testing-guide.md` added

## nutrient-document-processor-api 1.0.0

Initial release of the Nutrient DWS Processor API plugin.

**New:**
- 18 ready-to-run Python scripts for document conversion, extraction, transformation, and security operations
- Custom workflow template for multi-step document pipelines
- Support for Claude Code (via marketplace), OpenAI Codex, and manual agent installation
