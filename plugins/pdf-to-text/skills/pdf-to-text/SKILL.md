---
name: pdf-to-text
description: Extract layout-preserving plain text from a PDF — best for TABLES, INVOICES, columnar/financial PDFs where cell values and alignment must survive. Parse each PDF ONCE to a file. To find a specific fact, prefer a bounded `grep -n -i -C2 "term" file | head`. Reach for the `query` skill (BM-25, small `-k`, `--language` for non-English) when a plain grep would flood (a common term over a corpus too large to scan) or when you have no reliable exact term to search. Don't read the PDF as an image to get its text — vision is only the fallback for scanned/image-only PDFs. Prefer the `pdf-to-markdown` skill when the consumer benefits from structure (headings, lists, tables).
license: Proprietary
---

## Rules for agents (read first)

- Best for **tables, invoices, columnar/financial PDFs** — layout and cell values survive.
- **Parse once**, then **default to bounded grep:** `grep -n -i -C2 "term" file | head`.
- **Use the `query` skill only when grep would flood** — a common term over a corpus too large to scan; then small `-k`, and `--language <lang>` for non-English.
- **Don't read the source PDF as an image to get its *text*** — this extractor is faster and more accurate for extractable text. (For a scanned/image-only PDF with no text layer, a vision tool is the right fallback — see Troubleshooting.)

# PDF to Text

Convert PDFs into layout-preserving plain text. Each word is placed on a character grid that mirrors its on-page position, so columns, indentation, and tabular alignment survive the conversion. This is significantly higher quality than reading a PDF directly with the `read` tool, which only extracts loose text without spatial fidelity.

## When to use this vs. pdf-to-markdown

- **Use `pdf-to-text`** when the downstream consumer is plain-text only (a non-Markdown LLM, a grep/awk pipeline, a CSV-style table extractor that cares about column alignment).
- **Use `pdf-to-markdown`** when the consumer benefits from semantic structure (headings, lists, tables, reading order). Most RAG and LLM-context pipelines fall here.

## Related Nutrient skills

- **`query`** — once a file is extracted, *search* it instead of reading a large output back into context: ranked BM-25 search that returns only the top line windows ("parse once, query many"). Add it the way your agent installs skills.

## Usage

Before running any commands, set `SKILL_DIR` to the absolute path of the directory containing this SKILL.md file. Use `$SKILL_DIR/bin/pdf-to-text` in all commands below.

The `$SKILL_DIR/bin/pdf-to-text` wrapper automatically installs the platform-specific binary into `~/.local/share/nutrient/cli/` from the CDN. It caches the binary and only checks for updates every 6 hours, so subsequent runs are fast. The same binary backs conversion, search, authentication, and updates, so installing either skill gets you the same `~/.local/share/nutrient/cli/` install.

### Single file

```bash
$SKILL_DIR/bin/pdf-to-text INPUT.pdf OUTPUT.txt
```

If `OUTPUT.txt` is omitted, the converter writes the text to stdout instead.

### Batch directory (2+ files)

For multiple files, pass directories instead of individual files. The converter processes all PDFs in the input directory in parallel, which is much faster than converting one at a time.

```bash
$SKILL_DIR/bin/pdf-to-text INPUT_DIR/ OUTPUT_DIR/
```

### Vision for scanned or visually complex PDFs

Vision can produce a structured local result for scanned documents, handwriting, formulas, and visually complex tables:

```bash
$SKILL_DIR/bin/pdf-to-text --vision INPUT.pdf OUTPUT.json
```

Vision requires a paid Nutrient PDF to Markdown plan. If the command says login is required, surface that message to the user and ask them to run:

```bash
$SKILL_DIR/bin/nutrient auth login
```

Do not retry `--vision` without authentication. In non-interactive environments, the user can provide `NUTRIENT_API_KEY`; never ask them to paste the secret into chat or place it directly in a command argument.

Containers and CI do not receive automatic included credits. In those environments, ask the user to run the bundled `nutrient auth login` command or configure `NUTRIENT_API_KEY`.

## Workflow

1. **Choose mode**: Use batch directory mode for 2+ files, single file mode otherwise.
2. **Run the converter**: `$SKILL_DIR/bin/pdf-to-text INPUT [OUTPUT]`
3. **Check the exit code**: Exit 0 means success. On failure, read stderr for the error message.
4. **Validate the output**: If the output file is empty or near-empty, the PDF is likely image-only — see Troubleshooting below.
5. **Report the output path**: Tell the user where the converted file(s) are. Do NOT read the text back into context by default — converted documents can be very large and will fill the context window. Only read the output if the user's task specifically requires analyzing or summarizing the content.

## Troubleshooting

- **Empty or minimal output**: The PDF is most likely scanned/image-only. Offer `--vision`; if login is required, surface the CLI's instructions rather than retrying.
- **Non-zero exit code**: Read stderr for the specific error. Common causes: corrupted PDF, unsupported encryption, or network issues during first-run binary download.
- **Included credits used**: Stop retrying and ask the user to run `$SKILL_DIR/bin/nutrient auth login`. Never suggest signing out, deleting CLI state, or reinstalling to obtain more credits.
- **First run is slow**: The wrapper downloads the platform binary on first use (~a few seconds). Subsequent runs use the cached binary.
- **Columns look wrong**: The extractor mirrors spatial layout exactly, so unusual PDF page geometry (e.g. rotated pages, two-column reflows) can produce surprising alignment. Try `pdf-to-markdown` if the document has a regular structure the markdown exporter can recognize.

## License

On a supported host, the first standard conversion starts 1,000 one-time credits without signup. They do not expire or renew. Creating an account preserves that workspace and its remaining credits. Signing in to an existing account leaves the earlier balance and history separate. Account plans provide monthly credits. Successful standard conversions use 1 credit, successful Vision conversions use 2, and failed conversions use no credits. Vision is included on paid plans. Existing `--license-key` use remains supported.

Redistribution, OEM, embedded, and white-label use require a separate agreement with Nutrient. See [current pricing](https://www.nutrient.io/api/pricing/#api-pricing-pdf-to-markdown).
