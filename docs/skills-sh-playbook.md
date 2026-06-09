# Skills.sh Playbook

> How to maximize E-GEO's visibility, ranking, and install growth on skills.sh.

---

## What is skills.sh?

[skills.sh](https://skills.sh) is a registry for Claude Code skills. Skills are auto-discovered capabilities that activate based on context. E-GEO publishes its capabilities as skills for easy installation.

---

## Installing E-GEO Skills

### Install the full collection

```bash
npx skills add https://github.com/mverab/eGEOagents
```

### Install a single skill

```bash
npx skills add https://github.com/mverab/eGEOagents --skill competitive-analysis
```

### List available skills

```bash
npx skills add https://github.com/mverab/eGEOagents --list
```

---

## Available Skills

| Skill | Description | Triggers On |
|-------|-------------|-------------|
| **competitive-analysis** | Analyze AI-search competitors for a query | Competitor questions |
| **content-scoring** | Score content against 10 GEO criteria | Score/rate requests |
| **schema-generator** | Generate JSON-LD schema markup | Schema/markup requests |
| **validation-doctor** | Check MCP setup and provide config snippets | Missing dependencies |

---

## Verification Checklist

Before every release, verify:

- [ ] All `SKILL.md` files have valid frontmatter (`name`, `description`)
- [ ] No duplicate skill names across directories
- [ ] `npx skills add --list` parses without errors
- [ ] Skills appear at [skills.sh/mverab/egeoagents](https://skills.sh/mverab/egeoagents)

### Run verification

```bash
npx skills add https://github.com/mverab/eGEOagents --list
```

Expected output: all 4 skills listed with names and descriptions.

---

## Growth Strategy

skills.sh ranking is driven by **install counts**. Each `npx skills add` command contributes to the ranking signal.

### Distribution tactics

1. **Include install commands** in all promotion materials
2. **Show expected output** so users install with clear intent
3. **Promote in communities** where Claude Code users gather
4. **Track weekly deltas** and document which channels convert

### Index pages

- Collection: [skills.sh/mverab/egeoagents](https://skills.sh/mverab/egeoagents)
- Owner page: [skills.sh/mverab](https://skills.sh/mverab)

---

## Skill Structure

Each skill lives in `.claude/skills/[name]/SKILL.md`:

```markdown
---
name: skill-name
description: What this skill does
triggers:
  - trigger phrase 1
  - trigger phrase 2
---

# Skill content...
```

### Required frontmatter

| Field | Description |
|-------|-------------|
| `name` | Unique skill identifier (kebab-case) |
| `description` | 1-2 sentence description |

### Optional frontmatter

| Field | Description |
|-------|-------------|
| `allowed-tools` | List of tool names this skill can use |
| `triggers` | Phrases that auto-activate this skill |

---

## Adding New Skills

1. Create directory: `.claude/skills/[skill-name]/`
2. Write `SKILL.md` with frontmatter + content
3. Ensure unique `name` across all skills
4. Test: `npx skills add . --list`
5. Commit and push

---

## See Also

- [Getting Started](getting-started.md) — Step-by-step tutorial
- [How It Works](how-it-works.md) — Technical architecture
- [FAQ](faq.md) — Common questions
- [USAGE.md](../USAGE.md) — Command reference

---

*Built for the AI-first web.*
