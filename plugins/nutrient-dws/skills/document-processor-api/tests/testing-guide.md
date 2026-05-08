# Testing Guide

## Requirements

- Python 3.10+
- `uv` on `PATH`
- `NUTRIENT_API_KEY` set
- **Multi-page PDF input** (3+ pages recommended for comprehensive testing)

```bash
export NUTRIENT_API_KEY="nutr_sk_..."
# NOTE: Use a multi-page PDF (3+ pages required for split.py and delete-pages.py)
PDF=/path/to/your/input.pdf
OUT=/tmp/ndp-test
mkdir -p "$OUT"
```

Run commands from repository root.

## 1. Smoke tests

All scripts should print help and exit 0:

```bash
uv run nutrient-document-processing/scripts/convert.py --help
uv run nutrient-document-processing/scripts/merge.py --help
uv run nutrient-document-processing/scripts/split.py --help
uv run nutrient-document-processing/scripts/ocr.py --help
uv run nutrient-document-processing/scripts/extract-text.py --help
uv run nutrient-document-processing/scripts/extract-table.py --help
uv run nutrient-document-processing/scripts/extract-key-value-pairs.py --help
uv run nutrient-document-processing/scripts/watermark-text.py --help
uv run nutrient-document-processing/scripts/redact-ai.py --help
uv run nutrient-document-processing/scripts/rotate.py --help
uv run nutrient-document-processing/scripts/sign.py --help
uv run nutrient-document-processing/scripts/optimize.py --help
uv run nutrient-document-processing/scripts/password-protect.py --help
uv run nutrient-document-processing/scripts/add-pages.py --help
uv run nutrient-document-processing/scripts/delete-pages.py --help
uv run nutrient-document-processing/scripts/duplicate-pages.py --help
```

## 2. Single-operation happy-path checks

```bash
uv run nutrient-document-processing/scripts/convert.py --input "$PDF" --format docx --out "$OUT/convert.docx"
uv run nutrient-document-processing/scripts/merge.py --inputs "$PDF,$PDF" --out "$OUT/merge.pdf"
uv run nutrient-document-processing/scripts/split.py --input "$PDF" --ranges "0:1" --out-dir "$OUT/split" --prefix part
uv run nutrient-document-processing/scripts/ocr.py --input "$PDF" --languages english --out "$OUT/ocr.pdf"
uv run nutrient-document-processing/scripts/extract-text.py --input "$PDF" --out "$OUT/text.json"
uv run nutrient-document-processing/scripts/extract-table.py --input "$PDF" --out "$OUT/tables.json"
uv run nutrient-document-processing/scripts/extract-key-value-pairs.py --input "$PDF" --out "$OUT/kvp.json"
uv run nutrient-document-processing/scripts/watermark-text.py --input "$PDF" --text CONFIDENTIAL --out "$OUT/watermark.pdf"
uv run nutrient-document-processing/scripts/redact-ai.py --input "$PDF" --criteria "Remove all SSNs" --mode stage --out "$OUT/redact-stage.pdf"
uv run nutrient-document-processing/scripts/rotate.py --input "$PDF" --angle 90 --out "$OUT/rotate.pdf"
uv run nutrient-document-processing/scripts/sign.py --input "$PDF" --out "$OUT/sign.pdf"
uv run nutrient-document-processing/scripts/optimize.py --input "$PDF" --out "$OUT/optimize.pdf"
uv run nutrient-document-processing/scripts/password-protect.py --input "$PDF" --user-password upass --owner-password opass --out "$OUT/protected.pdf"
uv run nutrient-document-processing/scripts/add-pages.py --input "$PDF" --count 1 --out "$OUT/add-pages.pdf"
uv run nutrient-document-processing/scripts/delete-pages.py --input "$PDF" --pages 0 --out "$OUT/delete-pages.pdf"
uv run nutrient-document-processing/scripts/duplicate-pages.py --input "$PDF" --pages 1,0,1 --out "$OUT/duplicate-pages.pdf"
```

## 3. Multi-step workflow behavior

No multi-step script should exist in `scripts/`.

Build runtime pipelines in a temporary file using the template:

```bash
TMP_SCRIPT=/tmp/ndp-runtime-pipeline.py
cp nutrient-document-processing/assets/templates/custom-workflow-template.py "$TMP_SCRIPT"
# edit $TMP_SCRIPT for the requested pipeline
uv run "$TMP_SCRIPT" --input "$PDF" --out "$OUT/pipeline.pdf"
rm -f "$TMP_SCRIPT"
```

## 4. Pass criteria

- All `--help` commands succeed.
- Single-operation scripts produce output files (using a multi-page PDF).
- Multi-step workflows are run from temporary scripts only.
- No committed pipeline scripts exist in `nutrient-document-processing/scripts/`.

**Note:** Single-page PDFs will cause failures in `split.py` and `delete-pages.py`. Use a multi-page PDF (3+ pages) for complete test coverage.
