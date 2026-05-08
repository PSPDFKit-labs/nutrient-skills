# Changelog

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
