# Nutrient Skills

A Claude Code marketplace containing AI agent skills for [Nutrient](https://www.nutrient.io/) APIs and SDKs.

## Available Skills

| Skill | Description |
|-------|-------------|
| [`nutrient-document-processor-api`](plugins/nutrient-document-processor-api) | Convert, extract, transform, and secure documents via the Nutrient Document Web Services API |

## Installation

### Claude Code (recommended)

Add this repository as a marketplace, then install individual skills:

```
/plugin marketplace add pspdfkit-labs/nutrient-skills
/plugin install nutrient-document-processor-api@nutrient-skills
```

After installation, Claude Code will automatically load the skill in all future sessions.

To install additional skills as they are released:

```
/plugin install <skill-name>@nutrient-skills
```

### OpenAI Codex

Codex scans skills from `~/.codex/skills/` (user-wide) and `.agents/skills/` (project-wide, scanned up to the git root). Each skill directory must have a `SKILL.md` at its root. The `agents/openai.yaml` file is picked up automatically for display name and invocation policy configuration.

Because this is a multi-skill repository, point Codex at the individual skill subdirectory rather than the repo root. Repeat for each skill you want to install.

**User-wide (recommended — symlink stays up to date with `git pull`):**
```bash
git clone https://github.com/pspdfkit-labs/nutrient-skills.git ~/nutrient-skills
ln -s ~/nutrient-skills/plugins/<skill-name> \
  ~/.codex/skills/<skill-name>
```

**Project-wide** (run from your project root):
```bash
mkdir -p .agents/skills
git clone https://github.com/pspdfkit-labs/nutrient-skills.git
ln -s $(pwd)/nutrient-skills/plugins/<skill-name> \
  .agents/skills/<skill-name>
```

### Manual / any agent

Clone the repository and point your agent at the skill directory:

```bash
git clone https://github.com/pspdfkit-labs/nutrient-skills.git
# Each skill lives under plugins/<skill-name>/
# SKILL.md:  nutrient-skills/plugins/<skill-name>/SKILL.md
```

Reference `SKILL.md` directly in your agent's context, or symlink the skill directory into wherever your agent resolves skills.

---

## Repository Layout

```
.claude-plugin/
  marketplace.json                  Claude Code marketplace catalog
plugins/
  <skill-name>/                     One directory per skill
    .claude-plugin/
      plugin.json                   Plugin manifest (Claude Code)
    SKILL.md                        Skill definition (Codex + generic agents)
    skills/
      <skill-name>/
        SKILL.md                    Skill definition (Claude Code auto-discovery)
    agents/
      openai.yaml                   OpenAI Codex interface metadata
    scripts/                        Ready-to-run task scripts
    assets/                         Templates and static assets
    references/                     API docs, method mappings, and guides
```

---

## Requirements

- Python 3.10+ (scripts use [inline script metadata](https://packaging.python.org/en/latest/specifications/inline-script-metadata/) — run with `uv run`)
- A [Nutrient API key](https://dashboard.nutrient.io/)

---

## License

MIT
