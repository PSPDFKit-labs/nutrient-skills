# Changelog

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
