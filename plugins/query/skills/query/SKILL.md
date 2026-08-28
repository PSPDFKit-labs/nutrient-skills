---
name: query
description: >-
  Search extracted Markdown or plain text with ranked keyword search. Use this
  skill after pdf-to-markdown or pdf-to-text when you do not know the document's
  exact wording or a plain grep would return too many matches. For a known term,
  use a bounded grep first.
license: Proprietary
---

## Rules for agents

- For a known term, start with a bounded search such as `grep -n -i -C2 "term" file | head`.
- Use `query` when you do not know the exact wording or a plain search returns too many matches.
- Use `-k 1` or `-k 2` for a single fact. Add `--language <lang>` to match related word forms.
- Build an index with `--emit-index` only when you expect several queries over the same file.

# Query a document

Search an extracted Markdown or text file and return the most relevant line ranges. The command reads the local file; it does not parse PDFs.

## Related skills

- **`pdf-to-markdown`** — converts a PDF to structured Markdown.
- **`pdf-to-text`** — converts a PDF to plain text while preserving columns and spacing.

## Usage

Set `SKILL_DIR` to the absolute path of the directory containing this file. Use `$SKILL_DIR/bin/query` in the commands below.

The wrapper downloads the signed CLI from Nutrient's CDN on first use and stores it in `~/.local/share/nutrient/cli/`. It checks for updates every six hours.

```bash
$SKILL_DIR/bin/query text INPUT.md "your question" [-k N] [-e N]
```

- `INPUT.md` — an extracted Markdown or text file, or a saved query index.
- `"your question"` — the words to rank. Include several specific terms when useful.
- `-k N` — the maximum number of result windows. The default is 8; use 1–3 for most questions.
- `-e N` — the number of surrounding lines. The default is 5; use 0 to return only matching lines.

Each result starts with a 1-based `Lines A-B` range. Use that range for a focused follow-up read when needed.

### Reuse an index

Create an index when you expect several questions about the same file:

```bash
$SKILL_DIR/bin/query text INPUT.md "first question" --emit-index INPUT.idx
$SKILL_DIR/bin/query text INPUT.idx "second question"
```

The index contains the source lines, so later queries need only the index file.

## Workflow

1. Convert the PDF once with `pdf-to-markdown` or `pdf-to-text`.
2. Run one focused query with a small `-k` value.
3. Answer from the returned passages. Read a wider line range only when needed.
4. Reuse an index for later questions about the same file.

## Query tips

- Use specific words likely to appear in the document.
- Put related terms in one query instead of running several narrow queries.
- Add `--language en`, or another ISO language code, to match inflected forms.
- Increase `-e` for more context. Increase `-k` only when you expect several separate answers.

## Troubleshooting

- **`No relevant matches found`:** Try a more specific term, a synonym, or `--mode lenient`. The message is not document content.
- **Empty output:** Check that the converted file contains text. `query` does not perform OCR.
- **Poor matches:** Add rarer terms or use `--mode strict`.
- **Nonzero exit:** Read stderr and report the specific error. Common causes are a missing input file or a first-run download failure.
- **First run is slow:** The wrapper downloads the platform binary once. Later runs use the cached copy.

## Usage and licensing

`query` is free to use. It runs locally, requires no account, reports no usage, and uses no Vision pages.

Use is subject to Nutrient's [Terms](https://www.nutrient.io/legal/terms/) and [Privacy Policy](https://www.nutrient.io/legal/privacy-policy/). Redistribution, OEM, embedded, and white-label use require a separate agreement with Nutrient.
