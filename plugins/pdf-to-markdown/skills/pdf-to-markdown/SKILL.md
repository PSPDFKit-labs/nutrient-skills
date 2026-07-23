---
name: pdf-to-markdown
description: Extract text from a PDF as structured Markdown for analysis, RAG, or LLM context. Parse each PDF ONCE to a file (do not re-parse to search; do not read the PDF as an image). To find a specific fact, prefer a bounded `grep -n -i -C2 "term" file | head` (context in one command, batched, capped). Reach for the `query` skill (BM-25) only when a plain grep would flood — a common/ambiguous discriminator over a corpus too large to scan — where you need the top-k most-relevant passages, not every hit. For tables/invoices/columnar PDFs prefer the `pdf-to-text` skill. ALWAYS use this skill when the user has a PDF and needs its content as text or Markdown — even if they don't explicitly say "convert to markdown".
license: Proprietary
---

## Rules for agents (read first)

- **Parse once** to a file — never re-parse the same PDF to search again.
- **Default search = bounded grep:** `grep -n -i -C2 "term" file | head`. Get context in one command, batch lookups, cap with `head`.
- **Use the `query` skill only when grep would flood** — the discriminating term is common/ambiguous AND the corpus is too large to scan (many matches to sift). query returns a bounded, ranked top-k (small `-k`), keeping context small. Add `--language <lang>` for non-English.
- **Tables where column alignment must survive -> `pdf-to-text`** (this skill preserves Markdown tables fine; prefer `pdf-to-text` only when whitespace/columnar alignment matters). **Don't read the source PDF as an image to get its text** (vision is the fallback only for scanned/image-only PDFs with no text layer).

# PDF to Markdown

Convert PDFs into structured, semantic Markdown that preserves the document's logical structure — headings, tables, lists, and reading order — rather than producing flat text. This is significantly higher quality than reading a PDF directly with the `read` tool, which only extracts raw text without structure.

## Related Nutrient skills

This is one of a family of Nutrient document skills that install separately but are built to work together (same underlying binary). When your task calls for one, add it the way your agent installs skills:

- **`query`** — to *search* the converted file instead of reading a large output back into context: ranked BM-25 search that returns only the top line windows. The recommended way to pull facts from big conversions ("parse once, query many").
- **`pdf-to-text`** — for plain text instead of Markdown, when column/tabular alignment must survive or the consumer can't parse Markdown.

## Usage

Before running any commands, set `SKILL_DIR` to the absolute path of the directory containing this SKILL.md file. Use `$SKILL_DIR/bin/pdf-to-markdown` in all commands below.

The `$SKILL_DIR/bin/pdf-to-markdown` wrapper automatically installs the platform-specific binary into `~/.local/share/nutrient/cli/` from the CDN. It caches the binary and only checks for updates every 6 hours, so subsequent runs are fast.

### Single file

```bash
$SKILL_DIR/bin/pdf-to-markdown INPUT.pdf OUTPUT.md
```

If `OUTPUT.md` is omitted, the converter writes the Markdown to stdout instead.

### Batch directory (2+ files)

For multiple files, pass directories instead of individual files. The converter processes all PDFs in the input directory in parallel, which is much faster than converting one at a time.

```bash
$SKILL_DIR/bin/pdf-to-markdown INPUT_DIR/ OUTPUT_DIR/
```

### Image export

To extract images from the PDF and reference them in the output Markdown, add the `--enable-image-export` flag:

```bash
$SKILL_DIR/bin/pdf-to-markdown --enable-image-export INPUT.pdf OUTPUT.md
```

Images are saved to `{output}_resources/` alongside the output file and referenced as standard Markdown image links. This is useful when feeding output to LLMs that support vision, or when image context improves downstream accuracy. Off by default because it increases processing time for image-heavy documents.

## Workflow

1. **Choose mode**: Use batch directory mode for 2+ files, single file mode otherwise.
2. **Run the converter**: `$SKILL_DIR/bin/pdf-to-markdown INPUT [OUTPUT]`
3. **Check the exit code**: Exit 0 means success. On failure, read stderr for the error message.
4. **Validate the output**: If the output file is empty or near-empty, see Troubleshooting below.
5. **Report the output path**: Tell the user where the converted file(s) are. Do NOT read the markdown back into context by default — converted documents can be very large and will fill the context window. Only read the output if the user's task specifically requires analyzing or summarizing the content (e.g., "summarize this PDF", "what does this contract say about X").

## Troubleshooting

- **Empty or minimal output**: The PDF may be scanned/image-only and contains no extractable text.
- **Non-zero exit code**: Read stderr for the specific error. Common causes: corrupted PDF, unsupported encryption, or network issues during first-run binary download.
- **First run is slow**: The wrapper downloads the platform binary on first use (~a few seconds). Subsequent runs use the cached binary.

## License

Free for processing up to 1,000 documents per calendar month.

Commercial license required for:
- processing over 1,000 documents/month
- redistributing the binary
- OEM/white-label use

Contact `sales@nutrient.io` for commercial licensing.
