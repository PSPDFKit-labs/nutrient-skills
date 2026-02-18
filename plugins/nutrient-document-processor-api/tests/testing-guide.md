# Testing guide for nutrient-document-processor-api

This guide gives Claude Code and Codex instances a complete test plan for every script in this
plugin. Follow the sections in order. After you finish, run the validation checklist in section 4.

---

## Test environment

**Requirements**

- Python 3.10 or later
- `uv` installed and on `$PATH`
- `NUTRIENT_DWS_API_KEY` exported (section 1 smoke tests don't need it; all other sections do)
- A local PDF to use as input

**API key**

```bash
export NUTRIENT_DWS_API_KEY="nutr_sk_..."
```

**Sample PDF**

Tests below use `A.pdf`, a 2-page PDF at `~/work/pspdf/PSPDFKit-worktree/assets/A.pdf`.
If that file doesn't exist on your machine, substitute any local 2-page (or longer) PDF.
Set a shell variable so you don't repeat the path everywhere:

```bash
PDF=~/work/pspdf/PSPDFKit-worktree/assets/A.pdf
```

**Working directory**

Run all commands from the plugin root — the directory that contains `scripts/`, `assets/`,
and `references/`. Relative paths in the commands below assume that location.

**Output directory**

Create a scratch directory so test output doesn't land in the source tree:

```bash
mkdir -p /tmp/ndp-test
OUT=/tmp/ndp-test
```

---

## Section 1 — Smoke tests (help flags)

Run `--help` on every script. Each call must exit with code 0 and print usage text.
No API key is required. This confirms that `uv` resolves inline dependencies and that
the script parses correctly.

```bash
uv run scripts/convert.py --help
uv run scripts/merge.py --help
uv run scripts/split.py --help
uv run scripts/ocr.py --help
uv run scripts/extract-text.py --help
uv run scripts/extract-table.py --help
uv run scripts/extract-key-value-pairs.py --help
uv run scripts/watermark-text.py --help
uv run scripts/redact-ai.py --help
uv run scripts/rotate.py --help
uv run scripts/sign.py --help
uv run scripts/optimize.py --help
uv run scripts/password-protect.py --help
uv run scripts/add-pages.py --help
uv run scripts/delete-pages.py --help
uv run scripts/duplicate-pages.py --help
uv run scripts/ocr-watermark.py --help
uv run scripts/ocr-watermark-codex.py --help
```

**Pass criteria:** all 18 commands exit 0. Each prints `usage:` followed by argument descriptions.

---

## Section 2 — Operation scripts

### 2.1 convert.py

Converts a document to another format.

**Happy path — PDF to DOCX**

```bash
uv run scripts/convert.py \
  --input "$PDF" \
  --format docx \
  --out "$OUT/result.docx"
```

Verify: `$OUT/result.docx` exists. The script prints `Wrote ... (application/vnd.openxmlformats-officedocument.wordprocessingml.document)`.

**Format variant — PDF to PNG**

```bash
uv run scripts/convert.py \
  --input "$PDF" \
  --format png \
  --out "$OUT/result.png"
```

Verify: `$OUT/result.png` exists. MIME type in output contains `image/png`.

**Format variant — PDF to Markdown**

```bash
uv run scripts/convert.py \
  --input "$PDF" \
  --format markdown \
  --out "$OUT/result.md"
```

Verify: `$OUT/result.md` exists and contains readable text (not binary content).

**Edge case — missing required arg**

```bash
uv run scripts/convert.py --input "$PDF" --format docx
```

Verify: exits non-zero. Argparse prints `error: the following arguments are required: --out`.

---

### 2.2 merge.py

Merges two or more PDFs into one.

**Happy path — merge the same file twice**

```bash
uv run scripts/merge.py \
  --inputs "$PDF,$PDF" \
  --out "$OUT/merged.pdf"
```

Verify: `$OUT/merged.pdf` exists and is larger than the source PDF. The output PDF should have
twice the page count of the source (4 pages for a 2-page input).

**Edge case — fewer than 2 inputs**

```bash
uv run scripts/merge.py --inputs "$PDF" --out "$OUT/merged-fail.pdf"
```

Verify: exits non-zero. Error message contains `at least 2 files`.

---

### 2.3 split.py

Splits one PDF into multiple PDFs by page ranges.

**Happy path — single range**

```bash
uv run scripts/split.py \
  --input "$PDF" \
  --ranges "0:1" \
  --out-dir "$OUT/split-single" \
  --prefix page
```

Verify: `$OUT/split-single/page-01.pdf` exists.

**Optional args — multiple ranges with custom prefix**

```bash
uv run scripts/split.py \
  --input "$PDF" \
  --ranges "0:1,-1:" \
  --out-dir "$OUT/split-multi" \
  --prefix section
```

Verify: `$OUT/split-multi/section-01.pdf` and `$OUT/split-multi/section-02.pdf` both exist.

**Optional args — negative indices**

```bash
uv run scripts/split.py \
  --input "$PDF" \
  --ranges "-1:" \
  --out-dir "$OUT/split-last" \
  --prefix last
```

Verify: `$OUT/split-last/last-01.pdf` exists and is a valid PDF.

**Edge case — missing ranges**

```bash
uv run scripts/split.py \
  --input "$PDF" \
  --ranges "" \
  --out-dir "$OUT/split-fail"
```

Verify: exits non-zero. Error contains `at least one range`.

---

### 2.4 ocr.py

Runs OCR on a scanned document.

**Happy path — single language**

```bash
uv run scripts/ocr.py \
  --input "$PDF" \
  --languages english \
  --out "$OUT/ocr.pdf"
```

Verify: `$OUT/ocr.pdf` exists and MIME type is `application/pdf`.

**Optional args — two languages**

```bash
uv run scripts/ocr.py \
  --input "$PDF" \
  --languages "english,german" \
  --out "$OUT/ocr-bilingual.pdf"
```

Verify: `$OUT/ocr-bilingual.pdf` exists.

---

### 2.5 extract-text.py

Extracts document text as structured JSON, with an optional plain-text export.

**Happy path — full document**

```bash
uv run scripts/extract-text.py \
  --input "$PDF" \
  --out "$OUT/text.json"
```

Verify: `$OUT/text.json` exists and contains a top-level JSON object with a `pages` array.

**Optional args — page range**

```bash
uv run scripts/extract-text.py \
  --input "$PDF" \
  --pages "0:1" \
  --out "$OUT/text-p1.json"
```

Verify: `$OUT/text-p1.json` exists.

**Optional args — plain text output**

```bash
uv run scripts/extract-text.py \
  --input "$PDF" \
  --out "$OUT/text-plain.json" \
  --plain-out "$OUT/text-plain.txt"
```

Verify: both `$OUT/text-plain.json` and `$OUT/text-plain.txt` exist. The `.txt` file contains
readable text, not JSON.

---

### 2.6 extract-table.py

Extracts table data from a document.

**Happy path — full document**

```bash
uv run scripts/extract-table.py \
  --input "$PDF" \
  --out "$OUT/tables.json"
```

Verify: `$OUT/tables.json` exists and is valid JSON (even if the PDF has no tables, the
response is a JSON object rather than an error message).

**Optional args — specific page**

```bash
uv run scripts/extract-table.py \
  --input "$PDF" \
  --pages "0:1" \
  --out "$OUT/tables-p1.json"
```

Verify: `$OUT/tables-p1.json` exists.

---

### 2.7 extract-key-value-pairs.py

Extracts key-value pairs from forms or structured documents.

**Happy path — full document**

```bash
uv run scripts/extract-key-value-pairs.py \
  --input "$PDF" \
  --out "$OUT/kvp.json"
```

Verify: `$OUT/kvp.json` exists and is a valid JSON object.

**Optional args — page range**

```bash
uv run scripts/extract-key-value-pairs.py \
  --input "$PDF" \
  --pages "0:1" \
  --out "$OUT/kvp-p1.json"
```

Verify: `$OUT/kvp-p1.json` exists.

---

### 2.8 watermark-text.py

Stamps a text watermark on every page.

**Happy path — defaults**

```bash
uv run scripts/watermark-text.py \
  --input "$PDF" \
  --text "CONFIDENTIAL" \
  --out "$OUT/watermarked.pdf"
```

Verify: `$OUT/watermarked.pdf` exists and MIME type is `application/pdf`.

**Optional args — explicit opacity, rotation, font size**

```bash
uv run scripts/watermark-text.py \
  --input "$PDF" \
  --text "DRAFT" \
  --opacity 0.4 \
  --rotation 30 \
  --font-size 48 \
  --out "$OUT/watermarked-custom.pdf"
```

Verify: `$OUT/watermarked-custom.pdf` exists.

---

### 2.9 redact-ai.py

Creates AI-generated redactions and optionally burns them in.

**Happy path — stage mode (mark only, don't burn)**

```bash
uv run scripts/redact-ai.py \
  --input "$PDF" \
  --criteria "Remove all email addresses" \
  --mode stage \
  --out "$OUT/staged.pdf"
```

Verify: `$OUT/staged.pdf` exists. In stage mode, redaction annotations are visible but the
underlying text is not yet removed.

**Optional args — apply mode**

```bash
uv run scripts/redact-ai.py \
  --input "$PDF" \
  --criteria "Remove all email addresses" \
  --mode apply \
  --out "$OUT/redacted.pdf"
```

Verify: `$OUT/redacted.pdf` exists. Text matching the criteria is permanently removed.

**Optional args — restrict to first page**

```bash
uv run scripts/redact-ai.py \
  --input "$PDF" \
  --criteria "Remove phone numbers" \
  --mode apply \
  --pages "0:1" \
  --out "$OUT/redacted-p1.pdf"
```

Verify: `$OUT/redacted-p1.pdf` exists.

---

### 2.10 rotate.py

Rotates pages by 90, 180, or 270 degrees.

**Happy path — rotate all pages 90°**

```bash
uv run scripts/rotate.py \
  --input "$PDF" \
  --angle 90 \
  --out "$OUT/rotated-90.pdf"
```

Verify: `$OUT/rotated-90.pdf` exists.

**Optional args — rotate specific page range 180°**

```bash
uv run scripts/rotate.py \
  --input "$PDF" \
  --angle 180 \
  --pages "0:1" \
  --out "$OUT/rotated-180-p1.pdf"
```

Verify: `$OUT/rotated-180-p1.pdf` exists.

**Optional args — 270°**

```bash
uv run scripts/rotate.py \
  --input "$PDF" \
  --angle 270 \
  --out "$OUT/rotated-270.pdf"
```

Verify: `$OUT/rotated-270.pdf` exists.

**Edge case — invalid angle**

```bash
uv run scripts/rotate.py \
  --input "$PDF" \
  --angle 45 \
  --out "$OUT/rotated-fail.pdf"
```

Verify: exits non-zero. Argparse prints `invalid choice: 45` and lists the accepted values
`90`, `180`, `270`.

---

### 2.11 sign.py

Digitally signs a PDF. Only accepts local file paths — URL inputs are rejected.

**Happy path — sign without extra signature data**

```bash
uv run scripts/sign.py \
  --input "$PDF" \
  --out "$OUT/signed.pdf"
```

Verify: `$OUT/signed.pdf` exists and is a valid PDF.

**Edge case — URL passed as input**

```bash
uv run scripts/sign.py \
  --input "https://example.com/doc.pdf" \
  --out "$OUT/signed-fail.pdf"
```

Verify: exits non-zero. Error message contains `must be a local file path`.

---

### 2.12 optimize.py

Reduces PDF file size.

**Happy path — no options**

```bash
uv run scripts/optimize.py \
  --input "$PDF" \
  --out "$OUT/optimized.pdf"
```

Verify: `$OUT/optimized.pdf` exists and is a valid PDF.

**Optional args — inline options JSON**

```bash
uv run scripts/optimize.py \
  --input "$PDF" \
  --options-json '{"mrcCompression":true}' \
  --out "$OUT/optimized-mrc.pdf"
```

Verify: `$OUT/optimized-mrc.pdf` exists.

---

### 2.13 password-protect.py

Protects a PDF with user and owner passwords.

**Happy path — user and owner passwords**

```bash
uv run scripts/password-protect.py \
  --input "$PDF" \
  --user-password "user123" \
  --owner-password "owner456" \
  --out "$OUT/protected.pdf"
```

Verify: `$OUT/protected.pdf` exists. Opening it in a PDF viewer should require a password.

**Optional args — restrict permissions**

```bash
uv run scripts/password-protect.py \
  --input "$PDF" \
  --user-password "user123" \
  --owner-password "owner456" \
  --permissions "printing,copying" \
  --out "$OUT/protected-restricted.pdf"
```

Verify: `$OUT/protected-restricted.pdf` exists.

---

### 2.14 add-pages.py

Inserts blank pages into a PDF.

**Happy path — append one blank page to end**

```bash
uv run scripts/add-pages.py \
  --input "$PDF" \
  --count 1 \
  --out "$OUT/added-end.pdf"
```

Verify: `$OUT/added-end.pdf` exists and has one more page than the source.

**Optional args — insert at index 0 (prepend)**

```bash
uv run scripts/add-pages.py \
  --input "$PDF" \
  --count 1 \
  --index 0 \
  --out "$OUT/added-front.pdf"
```

Verify: `$OUT/added-front.pdf` exists. The first page is blank; original pages follow.

**Edge case — count of 0**

```bash
uv run scripts/add-pages.py \
  --input "$PDF" \
  --count 0 \
  --out "$OUT/added-fail.pdf"
```

Verify: exits non-zero. Error contains `must be a positive integer`.

---

### 2.15 delete-pages.py

Removes specific pages from a PDF.

**Happy path — delete first page**

```bash
uv run scripts/delete-pages.py \
  --input "$PDF" \
  --pages "0" \
  --out "$OUT/deleted-first.pdf"
```

Verify: `$OUT/deleted-first.pdf` exists and has one fewer page than the source.

**Optional args — delete last page using negative index**

```bash
uv run scripts/delete-pages.py \
  --input "$PDF" \
  --pages "-1" \
  --out "$OUT/deleted-last.pdf"
```

Verify: `$OUT/deleted-last.pdf` exists and has one fewer page than the source.

**Edge case — empty pages list**

```bash
uv run scripts/delete-pages.py \
  --input "$PDF" \
  --pages "" \
  --out "$OUT/deleted-fail.pdf"
```

Verify: exits non-zero. Error contains `at least one index`.

---

### 2.16 duplicate-pages.py

Creates a new PDF from a selected set of page indices, supporting reordering and duplication.

**Happy path — reverse page order**

For a 2-page PDF, swap the pages:

```bash
uv run scripts/duplicate-pages.py \
  --input "$PDF" \
  --pages "1,0" \
  --out "$OUT/reversed.pdf"
```

Verify: `$OUT/reversed.pdf` exists and has the same page count as the source.

**Optional args — duplicate a page**

Include page 0 twice:

```bash
uv run scripts/duplicate-pages.py \
  --input "$PDF" \
  --pages "0,0,1" \
  --out "$OUT/duplicated.pdf"
```

Verify: `$OUT/duplicated.pdf` exists and has one more page than the source (3 pages for a
2-page input).

**Edge case — empty page list**

```bash
uv run scripts/duplicate-pages.py \
  --input "$PDF" \
  --pages "" \
  --out "$OUT/dup-fail.pdf"
```

Verify: exits non-zero. Error contains `at least one index`.

---

### 2.17 ocr-watermark.py

OCRs a document and stamps a text watermark in a single pipeline call. This is a bundled
custom pipeline script rather than a primitive operation.

**Happy path — defaults**

```bash
uv run scripts/ocr-watermark.py \
  --input "$PDF" \
  --out "$OUT/ocr-wm.pdf"
```

Verify: `$OUT/ocr-wm.pdf` exists. Default watermark text is `CONFIDENTIAL`.

**Optional args — custom text, opacity, rotation, font size**

```bash
uv run scripts/ocr-watermark.py \
  --input "$PDF" \
  --text "INTERNAL USE ONLY" \
  --opacity 0.2 \
  --rotation 30 \
  --font-size 60 \
  --languages english \
  --out "$OUT/ocr-wm-custom.pdf"
```

Verify: `$OUT/ocr-wm-custom.pdf` exists.

---

### 2.18 ocr-watermark-codex.py

OCRs a PDF and stamps a `DRAFT` watermark. A variant of `ocr-watermark.py` generated by
Codex with slightly different defaults.

**Happy path — defaults**

```bash
uv run scripts/ocr-watermark-codex.py \
  --input "$PDF" \
  --out "$OUT/ocr-wm-codex.pdf"
```

Verify: `$OUT/ocr-wm-codex.pdf` exists. Default watermark text is `DRAFT`.

**Optional args — custom watermark text and opacity**

```bash
uv run scripts/ocr-watermark-codex.py \
  --input "$PDF" \
  --watermark-text "REVIEW COPY" \
  --opacity 0.5 \
  --rotation 0 \
  --out "$OUT/ocr-wm-codex-custom.pdf"
```

Verify: `$OUT/ocr-wm-codex-custom.pdf` exists.

---

## Section 3 — Custom pipeline generation

This section tests that an agent can read the template, write a new script, and run it end-to-end.
Each pipeline task below specifies what to build, where to put it, what arguments to accept, and
how to verify the result.

**Starting point:** `assets/templates/custom-workflow-template.py`

The template already contains a working example (OCR + watermark). Study it before writing
any pipeline. Key patterns to keep:

- PEP 723 inline script header (`# /// script ... ///`) with `dependencies = ["nutrient-dws"]`
- `asyncio.run(main())` entry point
- `create_client()` from `lib.common`
- `BuildActions` from `nutrient_dws.builder.constant`
- `write_workflow_output()` to write the final PDF

---

### 3.1 redact-then-watermark pipeline

**What to build:** An agent reads `assets/templates/custom-workflow-template.py` and writes
`scripts/redact-then-watermark.py`. The script must:

1. AI-redact content matching a user-supplied criteria string (apply mode, burns in redactions).
2. Stamp the text "REDACTED" as a watermark on every page.

**Arguments the script must accept:**

| Argument | Description |
|----------|-------------|
| `--input` | Path or URL to the input PDF |
| `--criteria` | Natural-language redaction criteria |
| `--out` | Output file path |

**Implementation note:** The two steps — `redact_ai` and `watermark_text` — must run as a
single `client.workflow()` call using `BuildActions`, not as two separate API requests. Use
`BuildActions.create_redactions_ai(criteria, "apply")` and
`BuildActions.watermark_text("REDACTED", {"opacity": 0.3})`.

**Verification:**

```bash
uv run scripts/redact-then-watermark.py \
  --input "$PDF" \
  --criteria "Remove all email addresses" \
  --out "$OUT/redact-wm.pdf"
```

Pass criteria:
- Exits 0
- `$OUT/redact-wm.pdf` exists
- File is a valid PDF (not empty, not an error message)

---

### 3.2 ocr-optimize pipeline

**What to build:** An agent writes `scripts/ocr-optimize.py`. The script must:

1. Run OCR on a scanned document with a user-supplied language.
2. Optimize the resulting PDF for reduced file size.

**Arguments the script must accept:**

| Argument | Default | Description |
|----------|---------|-------------|
| `--input` | _(required)_ | Path or URL to the input document |
| `--out` | _(required)_ | Output file path |
| `--language` | `english` | OCR language |

**Implementation note:** Use `BuildActions.ocr(language)` and `BuildActions.optimize()` in a
single workflow. Both steps run on the same file part.

**Verification:**

```bash
uv run scripts/ocr-optimize.py \
  --input "$PDF" \
  --language english \
  --out "$OUT/ocr-optimized.pdf"
```

Pass criteria:
- Exits 0
- `$OUT/ocr-optimized.pdf` exists and is a valid PDF

---

### 3.3 merge-then-split pipeline

**What to build:** An agent writes `scripts/merge-then-split.py`. The script must:

1. Merge two input PDFs into a single combined PDF.
2. Split the result into two ranges supplied by the caller.

Unlike the workflow-based pipelines above, this one chains two separate API calls because
`client.merge()` and `client.split()` don't map to `BuildActions`. Use them directly.

**Arguments the script must accept:**

| Argument | Description |
|----------|-------------|
| `--inputs` | Comma-separated list of exactly 2 local file paths |
| `--range-a` | First split range in `start:end` format |
| `--range-b` | Second split range in `start:end` format |
| `--out-dir` | Directory where split PDFs are written |

**Output files:** `<out-dir>/part-01.pdf` and `<out-dir>/part-02.pdf`.

**Implementation note:** Call `client.merge(inputs)` first and keep the result in memory
(as bytes). Then call `client.split()` on the merged buffer. Write both split parts to disk.
The intermediate merged file does not need to be saved.

**Verification:**

```bash
uv run scripts/merge-then-split.py \
  --inputs "$PDF,$PDF" \
  --range-a "0:2" \
  --range-b "2:" \
  --out-dir "$OUT/merge-split"
```

Pass criteria:
- Exits 0
- `$OUT/merge-split/part-01.pdf` and `$OUT/merge-split/part-02.pdf` both exist
- Both files are valid PDFs

---

## Section 4 — End-to-end validation checklist

Run through this checklist after completing all tests above.

- [ ] All 18 `--help` calls in section 1 exited 0
- [ ] `$OUT/result.docx` exists (convert — DOCX)
- [ ] `$OUT/result.png` exists (convert — PNG)
- [ ] `$OUT/result.md` exists and contains text (convert — Markdown)
- [ ] `$OUT/merged.pdf` exists (merge)
- [ ] `$OUT/split-multi/section-01.pdf` and `section-02.pdf` exist (split)
- [ ] `$OUT/ocr.pdf` exists (ocr)
- [ ] `$OUT/text.json` is a JSON object with a `pages` key (extract-text)
- [ ] `$OUT/text-plain.txt` contains readable text (extract-text — plain out)
- [ ] `$OUT/tables.json` is a valid JSON object (extract-table)
- [ ] `$OUT/kvp.json` is a valid JSON object (extract-key-value-pairs)
- [ ] `$OUT/watermarked.pdf` exists (watermark-text)
- [ ] `$OUT/redacted.pdf` exists (redact-ai — apply mode)
- [ ] `$OUT/rotated-90.pdf` exists (rotate)
- [ ] `rotate.py --angle 45` exited non-zero with `invalid choice` in the error (rotate — error case)
- [ ] `$OUT/signed.pdf` exists (sign)
- [ ] `sign.py` with a URL input exited non-zero with `local file path` in the error (sign — error case)
- [ ] `$OUT/optimized.pdf` exists (optimize)
- [ ] `$OUT/protected.pdf` exists (password-protect)
- [ ] `$OUT/added-end.pdf` exists and has correct page count (add-pages)
- [ ] `$OUT/deleted-first.pdf` exists and has correct page count (delete-pages)
- [ ] `$OUT/reversed.pdf` exists (duplicate-pages — reorder)
- [ ] `$OUT/duplicated.pdf` has one extra page (duplicate-pages — duplicate)
- [ ] `$OUT/ocr-wm.pdf` exists (ocr-watermark)
- [ ] `$OUT/ocr-wm-codex.pdf` exists (ocr-watermark-codex)
- [ ] `scripts/redact-then-watermark.py` exists and `$OUT/redact-wm.pdf` was produced (pipeline 3.1)
- [ ] `scripts/ocr-optimize.py` exists and `$OUT/ocr-optimized.pdf` was produced (pipeline 3.2)
- [ ] `scripts/merge-then-split.py` exists and both part files were produced (pipeline 3.3)
- [ ] No `__pycache__` directories exist outside of `scripts/lib/`
- [ ] All JSON output files pass `python3 -c "import json,sys; json.load(open(sys.argv[1]))"` without error
