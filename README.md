# Nutrient Skills

AI agent skills for [Nutrient](https://www.nutrient.io/) APIs and SDKs. Works with Claude Code, Codex, Pi, Cursor, Gemini CLI, and [other agents](https://github.com/vercel-labs/skills#supported-agents).

## Available Skills

| Plugin | Skill | Description |
|--------|-------|-------------|
| [`nutrient-dws`](plugins/nutrient-dws) | `document-processor-api` | Convert, extract, transform, and secure documents via the Nutrient Document Web Services API |
| [`pdf-to-markdown`](plugins/pdf-to-markdown) | `pdf-to-markdown` | Extract text from PDFs as structured, semantic Markdown |
| [`nutrient-sdk-dev`](plugins/nutrient-sdk-dev) | 13 SDK skills | Build with Nutrient SDKs — Web Viewer, Document Authoring, mobile (iOS/Android/React Native/Flutter/MAUI), server (Python/Java/Node.js/.NET), self-hosted Document Engine, and AI Assistant |

## Installation

### npx skills (recommended)

Install using the [Skills CLI](https://github.com/vercel-labs/skills):

```bash
npx skills add pspdfkit-labs/nutrient-skills --skill document-processor-api
npx skills add pspdfkit-labs/nutrient-skills --skill pdf-to-markdown
```

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
/plugin install nutrient-sdk-dev@nutrient-skills
```

After installation, the plugin's skills will automatically load in all future sessions.

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
    skills/
      <skill-name>/                 One or more skills per plugin
        SKILL.md                    Skill definition
        scripts/                    Optional: task scripts
        assets/                     Optional: templates, static files
        references/                 Optional: API docs, guides
```
