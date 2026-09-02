---
name: pdf-to-markdown
description: >-
  Convert PDF content to structured Markdown for analysis or AI workflows.
  Use this skill whenever a user needs text or Markdown from a PDF. Use Standard
  for PDFs with selectable text and Vision for scans or visually complex pages.
  Use pdf-to-text instead when whitespace and column alignment must be preserved.
license: Proprietary
---

## Rules for agents

- Convert each PDF once and save the result. Search the saved file instead of converting it again.
- For a known term, start with a bounded search such as `grep -n -i -C2 "term" file | head`.
- Use the `query` skill when you do not know the exact wording or a plain search returns too many matches.
- Use `pdf-to-text` when whitespace and column alignment matter more than Markdown structure.
- Do not render PDF pages as images to extract selectable text. Use Vision for scans and image-only PDFs.

# PDF to Markdown

Convert PDFs to Markdown while preserving headings, tables, lists, and reading order.

## Related skills

- **`pdf-to-text`** — preserves whitespace and column alignment in plain text.
- **`query`** — searches a large converted file and returns only the most relevant passages.

## Usage

Set `SKILL_DIR` to the absolute path of the directory containing this file. Use `$SKILL_DIR/bin/pdf-to-markdown` in the commands below.

The wrapper downloads the signed CLI from Nutrient's CDN on first use and stores it in `~/.local/share/nutrient/cli/`. It checks for updates every six hours.

### Convert one PDF

```bash
$SKILL_DIR/bin/pdf-to-markdown INPUT.pdf OUTPUT.md
```

Omit `OUTPUT.md` to write Markdown to stdout.

### Convert several PDFs

For two or more PDFs, pass an input directory and an output directory. The CLI converts the files in parallel.

```bash
$SKILL_DIR/bin/pdf-to-markdown INPUT_DIR/ OUTPUT_DIR/
```

### Export images

Add `--enable-image-export` to save images next to the Markdown output and link to them from the file.

```bash
$SKILL_DIR/bin/pdf-to-markdown --enable-image-export INPUT.pdf OUTPUT.md
```

Images are stored in `{output}_resources/`. Image export is off by default because it adds work for image-heavy PDFs.

### Use Vision

Vision handles scans, photographs, handwriting, formulas, and complex layouts.

```bash
$SKILL_DIR/bin/pdf-to-markdown --vision INPUT.pdf OUTPUT.md
```

Standard conversion is free and does not require an account. Vision requires a Nutrient account, API key, or existing SDK license. With an account or API key, each input page uses one Vision page from the account's monthly allowance. Existing SDK licenses keep their existing terms. Failed conversions do not use Vision pages.

If Vision asks for an account, show that message to the user and ask them to run:

```bash
$SKILL_DIR/bin/nutrient auth login
```

Do not start sign-in automatically. Do not retry Vision without authentication.

For unattended use, the user can set `NUTRIENT_API_KEY`. Never ask the user to paste a key into chat or put it directly in a command.

### Account commands

```bash
$SKILL_DIR/bin/nutrient auth login
$SKILL_DIR/bin/nutrient auth status
$SKILL_DIR/bin/nutrient auth logout
```

`status` shows the current plan, Vision access, and usage waiting to be reported. Never sign out or switch accounts unless the user asks.

## Workflow

1. Choose Standard or Vision. Start with Standard unless the PDF is scanned or image-only.
2. Convert the PDF once and check the exit code. Exit 0 means success.
3. Check that the output exists and is not empty.
4. Tell the user where the output was saved.
5. Do not read a large output file back into context unless the user wants it analyzed. Search it with bounded `grep` or the `query` skill instead.

## Offline behavior

Standard can continue when Nutrient is unavailable. After Vision connects, it can work offline for one hour and process up to 100 pages before it must reconnect. A document that crosses the 100-page threshold can finish.

## Troubleshooting

- **Empty or minimal output:** The PDF may be scanned or image-only. Offer Vision.
- **Vision asks for sign-in:** Show the CLI message and ask the user to run `$SKILL_DIR/bin/nutrient auth login`. Do not retry first.
- **No Vision pages remain:** Show the CLI message and the [pricing page](https://www.nutrient.io/api/pricing/pdf-to-markdown/). Do not retry or change account state.
- **Credential error during Standard conversion:** An explicitly configured key or saved sign-in is invalid. Show the error. Do not remove or replace credentials unless the user asks.
- **First run is slow:** The wrapper downloads the platform binary once. Later runs use the cached copy.
- **Other nonzero exit:** Read stderr and report the specific error. Common causes include a damaged PDF, unsupported encryption, or a first-run download failure.

## Plans and licensing

Standard conversion is free. With an account or API key, Vision uses the account's monthly allowance. Existing SDK licenses keep their existing terms. See [current plans](https://www.nutrient.io/api/pricing/pdf-to-markdown/).

Use is subject to Nutrient's [Terms](https://www.nutrient.io/legal/terms/) and [Privacy Policy](https://www.nutrient.io/legal/privacy-policy/). Redistribution, OEM, embedded, and white-label use require a separate agreement with Nutrient.
