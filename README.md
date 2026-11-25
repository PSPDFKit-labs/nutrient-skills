# Nutrient Skills

AI agent skills for [Nutrient](https://www.nutrient.io/) APIs and SDKs. Works with Claude Code, Codex, Pi, Cursor, Gemini CLI, and [other agents](https://github.com/vercel-labs/skills#supported-agents).

For an agent to process a document in chat, use the [Nutrient plugin for hosted MCP](https://github.com/PSPDFKit/nutrient-mcp-plugins). It bundles the connector with document workflows and uses browser sign-in. To build document processing into your own app, use the API and SDK skills below.

## Why these skills

The PDF-to-Markdown, PDF-to-Text, and Query skills run the Nutrient CLI on your computer. The conversion results come from the public 200-document [opendataloader-bench](https://github.com/opendataloader-project/opendataloader-bench) corpus.

- **Fast.** Standard conversion processes PDFs with selectable text at about **0.004 seconds per page**. On this benchmark, it has roughly **134× Docling's throughput** and the same rounded overall accuracy (0.89). Nutrient processes the batch in parallel, while Docling processes it sequentially; see the [benchmark method](https://github.com/PSPDFKit/pdf-to-markdown/blob/main/docs/benchmarks.md#speed).
- **Efficient for agents.** Convert each PDF once. Search the saved output with a bounded `grep`, or use `query` when you do not know the exact wording or expect too many matches.
- **Better on difficult pages.** Vision handles scans, photographs, handwriting, formulas, and complex layouts. In the benchmark, it leads every accuracy measure shown while remaining faster than Docling.
- **Local files.** The CLI does not upload your PDF or converted output to Nutrient. Usage reports include a random event ID, the command, Standard or Vision mode, input page count, time, and CLI version. They do not include file names, paths, document contents, or output. Text sent to an AI agent follows that provider's policies.

Standard conversion is free and does not require an account, including in containers and CI. Vision requires a Nutrient account, API key, or Nutrient CLI license key. With an account or API key, each input page uses one Vision page from the account's monthly allowance. Nutrient CLI license keys keep their existing terms. See [current plans](https://www.nutrient.io/api/pricing/pdf-to-markdown/).

The CLI runs on macOS 13 or newer with Apple Silicon, Linux with glibc 2.38 or newer, and Windows. Linux also needs libcurl 4, ICU, and OpenSSL 3. The wrappers download the CLI from Nutrient's CDN on first use. The CLI creates a one-way identifier for the installation. It never sends the system details used to create the identifier. The identifier cannot reveal those details or restore a lost sign-in.

Method and full tables: [PDF to Markdown benchmarks](https://github.com/PSPDFKit/pdf-to-markdown#benchmarks).

## Available Skills

| Plugin | Skill | Description |
|--------|-------|-------------|
| [`nutrient-dws`](plugins/nutrient-dws) | `document-processor-api` | Generate, convert, assemble, OCR, redact, sign, archive, and optimize documents via the Nutrient Document Web Services API |
| [`nutrient-dws`](plugins/nutrient-dws) | `document-extraction-api` | Parse documents into Markdown or spatial elements, extract schema-defined fields with citations, classify documents, and detect document boundaries in a packet via the Nutrient Data Extraction API |
| [`nutrient-dws`](plugins/nutrient-dws) | `grounded-rag-ingestion` | Chunk documents into provenance-carrying JSONL (element type, page, bbox, confidence, reading order) for grounded, auditable RAG pipelines |
| [`nutrient-dws`](plugins/nutrient-dws) | `dws-viewer-api` | Upload documents and mint viewer session JWTs for the Nutrient cloud Viewer API. Embeds interactive viewing, annotation, forms, and signing via cloud infrastructure — no viewing/storage servers to run (you still mint session tokens from your backend) |
| [`nutrient-dws`](plugins/nutrient-dws) | `ai-gateway` | Call OpenAI-compatible chat models or the TypeSafe-compatible decision API (calibrated noul/choice/score judgments) via the Nutrient AI Gateway |
| [`make-pdf`](plugins/make-pdf) | `make-pdf` | Generate PDFs from Markdown or HTML — single files or whole directories — with accessible PDF/UA, archival PDF/A, and watermark outputs, plus built-in conformance verification |
| [`remediate-pdf`](plugins/remediate-pdf) | `remediate-pdf` | Make existing documents accessible with the Nutrient Accessibility API: auto-tag PDFs with PDF/UA semantic structure (headings, lists, tables, reading order), validate against PDF/UA-1 with a JSON report, and route Word, image, and scanned files through conversion and OCR first (offline check: verify with the bundled verify-pdf.py) |
| [`pdf-to-markdown`](plugins/pdf-to-markdown) | `pdf-to-markdown` | Convert PDF content to structured Markdown |
| [`pdf-to-text`](plugins/pdf-to-text) | `pdf-to-text` | Extract layout-preserving plain text from PDFs |
| [`query`](plugins/query) | `query` | Find relevant passages in an extracted document with ranked keyword search |
| [`nutrient-sdk-dev`](plugins/nutrient-sdk-dev) | 14 SDK skills | Build with Nutrient SDKs — Web Viewer, Document Authoring, mobile (iOS/Android/React Native/Flutter/MAUI), server (Python/Java/Node.js/.NET), self-hosted Document Engine, and AI Assistant |

## Installation

### npx skills (recommended)

Install using the [Skills CLI](https://github.com/vercel-labs/skills):

```bash
npx skills add pspdfkit-labs/nutrient-skills --skill document-processor-api
npx skills add pspdfkit-labs/nutrient-skills --skill document-extraction-api
npx skills add pspdfkit-labs/nutrient-skills --skill grounded-rag-ingestion
npx skills add pspdfkit-labs/nutrient-skills --skill dws-viewer-api
npx skills add pspdfkit-labs/nutrient-skills --skill make-pdf
npx skills add pspdfkit-labs/nutrient-skills --skill remediate-pdf
npx skills add pspdfkit-labs/nutrient-skills --skill pdf-to-markdown
npx skills add pspdfkit-labs/nutrient-skills --skill pdf-to-text
npx skills add pspdfkit-labs/nutrient-skills --skill query
npx skills add pspdfkit-labs/nutrient-skills --skill ai-gateway
```

The `nutrient-sdk-dev` plugin's skills install the same way: `--skill nutrient-sdk` for the routing skill, or one of the 13 per-SDK skills (e.g. `--skill nutrient-web-sdk`).

This works with Claude Code, Codex, Cursor, Gemini CLI, and [many other agents](https://github.com/vercel-labs/skills#supported-agents).

To list all available skills in this repo:

```bash
npx skills add pspdfkit-labs/nutrient-skills --list
```

### Claude Code / Codex plugin marketplace

Both Claude Code and Codex support the `/plugin` command:

```
/plugin marketplace add pspdfkit-labs/nutrient-skills
/plugin install nutrient-dws@nutrient-skills
/plugin install make-pdf@nutrient-skills
/plugin install remediate-pdf@nutrient-skills
/plugin install pdf-to-markdown@nutrient-skills
/plugin install pdf-to-text@nutrient-skills
/plugin install query@nutrient-skills
/plugin install nutrient-sdk-dev@nutrient-skills
```

After installation, the plugin's skills will automatically load in all future sessions.

### Hosted Nutrient MCP

Follow the [Nutrient plugin install instructions](https://github.com/PSPDFKit/nutrient-mcp-plugins#install) to connect your agent and load the document workflow skill. For an MCP client that connects directly, use the [hosted MCP setup guide](https://www.nutrient.io/api/mcp-server-pdf-automation-llm/).

If you previously installed `nutrient-dws-mcp@nutrient-skills` in Codex, switch to the hosted plugin. The [local DWS MCP server](https://github.com/PSPDFKit/nutrient-dws-mcp-server) it bundles is retired.

### Pi

You can install the Nutrient skills with:

```bash
pi install git:github.com/PSPDFKit-labs/nutrient-skills
```

Pi will load all skills from the packaged `plugins/*/skills` directories. If you only want to try the package without installing it, use:

```bash
pi -e git:github.com/PSPDFKit-labs/nutrient-skills
```

You can still point Pi at a specific plugin's `skills/` directory or at the repo-wide `plugins/` directory in `~/.pi/agent/settings.json` or a project-local `.pi/settings.json` if you prefer manual control.

### Manual / any agent

Clone the repository and point your agent at the skill directory:

```bash
git clone https://github.com/pspdfkit-labs/nutrient-skills.git
# Skills live under plugins/<plugin>/skills/<skill>/SKILL.md
```

Reference `SKILL.md` directly in your agent's context, or symlink the skill directory into wherever your agent resolves skills.

## Updating

An existing install does not pick up a new version on its own. Update it with the tool you installed with.

### Claude Code

Refresh the marketplace first, then update the plugin:

```bash
claude plugin marketplace update nutrient-skills
claude plugin update nutrient-sdk-dev@nutrient-skills
```

Repeat the second command for each plugin you installed, then restart Claude Code. The plugin update compares against your local copy of the marketplace, so if you skip the first command it reports that you are already on the latest version.

Claude Code turns auto-update off by default for marketplaces other than Anthropic's own. To turn it on, run `/plugin`, open the Marketplaces tab, and enable auto-update for `nutrient-skills`.

### Codex

```bash
codex plugin marketplace upgrade
```

### Skills CLI

```bash
npx skills update
```

---

## Repository Layout

```
.claude-plugin/
  marketplace.json                  Marketplace catalog
AGENTS.md                           Agent instructions (Codex, generic)
CLAUDE.md                           Agent instructions (Claude Code)
plugins/
  <plugin-name>/                    One directory per plugin
    .claude-plugin/
      plugin.json                   Plugin manifest (Claude Code)
    .codex-plugin/
      plugin.json                   Plugin manifest (Codex)
    .mcp.json                       Optional bundled MCP server configuration
    skills/
      <skill-name>/                 One or more skills per plugin
        SKILL.md                    Skill definition
        scripts/                    Optional: task scripts
        assets/                     Optional: templates, static files
        references/                 Optional: API docs, guides
```
