---
name: query
description: Find the most relevant passages in an already-extracted document (the text or Markdown output of `pdf-to-markdown` / `pdf-to-text`) without reading the whole thing into context — ranked (BM-25) search that returns only the top line windows. Use once such a file exists, to answer a question, locate a clause, or pull the right section from a long converted document. Prefer this over reading the entire converted file or grepping it repeatedly.
license: Proprietary
---

# Query a document

Ranked search over an already-extracted text or Markdown file. You give it a natural-language query; it returns the most relevant line windows (with line numbers), not the whole document. This is the "parse once, then query the file" pattern: convert a PDF a single time, then ask as many questions as you like against the cheap, local text.

This is built for **agent economy**. A converted document can be tens of thousands of lines and will blow out your context window if you read it back. Querying returns only the handful of passages that matter, with line numbers you can use for a precise follow-up read.

## When to use this

- **Use `query`** when you have a converted file and a *question* — "what's the termination clause", "where are the FY24 revenue figures", "does this mention indemnification". It ranks every line and hands back the best windows.
- **Use `pdf-to-markdown` / `pdf-to-text` first** to produce the file. `query` does not parse PDFs; it searches their extracted text.
- **Don't** read the whole converted file into context to find one thing, and don't run grep after grep — that's what this replaces. One ranked query beats many exact-match passes when you don't know the document's exact wording.

## Related Nutrient skills

`query` searches a file a converter already produced, so you'll usually want one of these too — add it the way your agent installs skills (they install separately but share the same underlying binary):

- **`pdf-to-markdown`** — PDF → structured Markdown (headings, lists, tables); best for most RAG / LLM-context work.
- **`pdf-to-text`** — PDF → layout-preserving plain text; best when column/tabular alignment must survive.

## Usage

Before running any commands, set `SKILL_DIR` to the absolute path of the directory containing this SKILL.md file. Use `$SKILL_DIR/bin/query` in all commands below.

The `$SKILL_DIR/bin/query` wrapper installs the platform-specific binary into `~/.local/share/nutrient/cli/` from the CDN (cached; it only checks for updates every 6 hours). The same binary backs `pdf-to-markdown`, `pdf-to-text`, `query`, and `self-update`; installing any one of these skills gets you the same `~/.local/share/nutrient/cli/` install — so once a PDF is converted you can search it with this skill.

```bash
$SKILL_DIR/bin/query text INPUT.md "your natural-language query" [-k N] [-e N]
```

- `INPUT.md` — the extracted text or Markdown file (the output of `pdf-to-markdown` / `pdf-to-text`), **or** a prebuilt index (see below). The input type is auto-detected.
- `"query"` — natural-language query, matched case-insensitively. Put several relevant terms in one query; BM-25 rewards rare, on-topic words, so a richer query ranks better.
- `-k N` — maximum number of windows to return (default 8). Keep it small; you usually want the top 1–3.
- `-e N` — context lines around each hit (default 5). Use `-e 0` for just the matching line, or a larger value when you need more surrounding context.

Each result is a `Lines A-B` window (1-based, inclusive) followed by those lines. Line numbers are **global** to the document, so you can `Read INPUT.md` at that exact range for full context.

### Reusing an index for repeated questions

If you'll ask several questions about the same document, build the index once and query that instead of rebuilding it every call:

```bash
# First call: emit a reusable index alongside the answer.
$SKILL_DIR/bin/query text INPUT.md "first question" --emit-index INPUT.idx

# Later calls: query the index — it's self-contained and skips the rebuild.
$SKILL_DIR/bin/query text INPUT.idx "second question"
$SKILL_DIR/bin/query text INPUT.idx "third question"
```

The index is a self-describing file (it carries the document's lines), so `$SKILL_DIR/bin/query text INPUT.idx "..."` needs nothing else. The wrapper auto-detects whether you passed text or an index — same command either way.

## Workflow

1. **Convert once**: run `pdf-to-markdown` or `pdf-to-text` to produce `INPUT.md` / `INPUT.txt`. Do this a single time per document.
2. **Query, don't read**: ask your question with `$SKILL_DIR/bin/query text INPUT.md "..."`. Do *not* read the full converted file into context to answer — that's the cost this skill exists to avoid.
3. **Use the line numbers**: the windows are usually enough to answer directly. If you need more, `Read INPUT.md` at the reported `Lines A-B` range — a targeted read, not the whole file.
4. **Don't waste time**: for repeat questions on the same document, reuse the `--emit-index` index (above) so each query skips the rebuild.
5. **Report concisely**: answer from the returned windows. Don't paste the whole document back to the user.

## Tips for good queries

- **Be specific and lexical.** BM-25 is keyword ranking, not embeddings — it matches the words you give it. Use the terms you expect on the page ("indemnification", "net revenue", "effective date"), including synonyms, rather than a vague paraphrase.
- **One rich query beats many narrow ones.** Stack the relevant terms into a single query instead of issuing several.
- **Adjust context with `-e`, not by reading the file.** The default `-e 5` already gives a generous window; raise it for more surrounding text, or drop to `-e 0` for just the matching line. Only fall back to a full `Read` at the reported range when you truly need the wider section.
- **Raise `-k` only when you expect multiple distinct mentions.** For a single fact, `-k 1` is enough.

## Troubleshooting

- **`No relevant matches found` (printed to stdout, exit 0)**: nothing ranked above the relevance threshold — the query words don't appear, or are too common. Try different/rarer terms, or `--mode lenient`. This is a message, not document content; don't treat it as a result.
- **Truly empty output / no text to search**: the converted file has no text (an image-only PDF converts to an empty file; `query` searches text only and does not OCR). Re-check the `pdf-to-markdown` / `pdf-to-text` conversion before re-querying.
- **Hits look off-topic**: the query was too generic, so common words dominated. Add rarer, more specific terms, or tighten with `--mode strict`.
- **Inflected words missed** (e.g. "terminate" vs "termination"): pass `--language en` (or another ISO code) to enable stemming; the default is no stemming, exact word forms only. Run `$SKILL_DIR/bin/query --help` for the full flag list.
- **Non-zero exit code**: read stderr. Common causes — the input file doesn't exist, or (on the very first run) a network issue while downloading the binary.
- **First run is slow**: the wrapper downloads the platform binary once (~a few seconds); later runs use the cache. Per-query cost after that is dominated by a one-time index build, which `--emit-index` removes for subsequent calls.

## License

Free for processing up to 1,000 documents per calendar month. Each `query` call is one processing event and counts as one document against that quota — the same as a `pdf-to-markdown` / `pdf-to-text` conversion. The "parse once, query many" guidance saves your agent's context tokens and re-parse time, not the document quota (and an `--emit-index` rebuild saved is time/CPU, not quota).

Commercial license required for:
- processing over 1,000 documents/month
- redistributing the binary
- OEM/white-label use

Contact `sales@nutrient.io` for commercial licensing.
