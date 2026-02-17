# Nutrient Skills

A Claude Code marketplace containing AI agent skills for [Nutrient](https://www.nutrient.io/) APIs and SDKs.

## Available Plugins

| Plugin | Description |
|--------|-------------|
| [`nutrient-document-processor-api`](plugins/nutrient-document-processor-api) | Convert, extract, transform, and secure documents via the Nutrient DWS API |

## Installation

### Claude Code (recommended)

Add this repository as a marketplace, then install individual plugins:

```
/plugin marketplace add pspdfkit-labs/nutrient-skills
/plugin install nutrient-document-processor-api@nutrient-skills
```

After installation, Claude Code will automatically load the skill in all future sessions.

To install additional plugins as they are released:

```
/plugin install <plugin-name>@nutrient-skills
```

### OpenAI Codex

Codex scans skills from `~/.codex/skills/` (user-wide) and `.agents/skills/` (project-wide, scanned up to the git root). Each skill directory must have `SKILL.md` at its root. The `agents/openai.yaml` file is picked up automatically for display name and invocation policy configuration.

Because this is a multi-plugin repository, point Codex at the plugin subdirectory rather than the repo root.

**User-wide (recommended — symlink stays up to date with `git pull`):**
```bash
git clone https://github.com/pspdfkit-labs/nutrient-skills.git ~/nutrient-skills
ln -s ~/nutrient-skills/plugins/nutrient-document-processor-api \
  ~/.codex/skills/nutrient-document-processor-api
```

**Project-wide** (run from your project root):
```bash
mkdir -p .agents/skills
git clone https://github.com/pspdfkit-labs/nutrient-skills.git
ln -s $(pwd)/nutrient-skills/plugins/nutrient-document-processor-api \
  .agents/skills/nutrient-document-processor-api
```

### Manual / any agent

Clone the repository and point your agent at the plugin directory:

```bash
git clone https://github.com/pspdfkit-labs/nutrient-skills.git
# Plugin root: nutrient-skills/plugins/nutrient-document-processor-api/
# SKILL.md:    nutrient-skills/plugins/nutrient-document-processor-api/SKILL.md
```

Reference `SKILL.md` directly in your agent's context, or symlink the plugin directory into wherever your agent resolves skills.

---

## Repository layout

```
.claude-plugin/
  marketplace.json                  Claude Code marketplace catalog
plugins/
  nutrient-document-processor-api/  Nutrient DWS API plugin
    .claude-plugin/
      plugin.json                   Plugin manifest
    SKILL.md                        Skill definition (Codex + generic agents)
    skills/
      nutrient-document-processor-api/
        SKILL.md                    Skill definition (Claude Code auto-discovery)
    agents/
      openai.yaml                   OpenAI Codex interface metadata
    scripts/                        Ready-to-run Node.js task scripts
    assets/templates/               Custom workflow template
    references/                     API method mapping and pipeline guides
```

---

## Requirements

- Node.js 18+
- A [Nutrient API key](https://dashboard.nutrient.io/)

---

## License

MIT
