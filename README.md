# Nutrient Skills

AI agent skills for [Nutrient](https://www.nutrient.io/) APIs and SDKs. Works with Claude Code, Codex, Cursor, Gemini CLI, and [other agents](https://github.com/vercel-labs/skills#supported-agents).

## Available Skills

| Skill | Description |
|-------|-------------|
| [`nutrient-document-processor-api`](plugins/nutrient-document-processor-api) | Convert, extract, transform, and secure documents via the Nutrient Document Web Services API |

## Installation

### npx skills (recommended)

Install individual skills using the [Skills CLI](https://github.com/vercel-labs/skills):

```bash
npx skills add pspdfkit-labs/nutrient-skills --skill nutrient-document-processor-api
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
/plugin install nutrient-document-processor-api@nutrient-skills
```

After installation, the skill will automatically load in all future sessions.

To install additional skills as they are released:

```
/plugin install <skill-name>@nutrient-skills
```

### Manual / any agent

Clone the repository and point your agent at the skill directory:

```bash
git clone https://github.com/pspdfkit-labs/nutrient-skills.git
# Each skill lives under plugins/<skill-name>/skills/<skill-name>/SKILL.md
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
  <skill-name>/
    .claude-plugin/
      plugin.json                   Plugin manifest (Claude Code)
    .codex-plugin/
      plugin.json                   Plugin manifest (Codex)
    skills/
      <skill-name>/
        SKILL.md                    Skill definition
        scripts/                    Optional: task scripts
        assets/                     Optional: templates, static files
        references/                 Optional: API docs, guides
```
