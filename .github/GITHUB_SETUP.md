# GitHub Repository Configuration

This file contains all the information needed to configure the E-GEO repository for maximum discoverability on GitHub.

## Manual GitHub Setup Required

The following actions must be completed manually on GitHub:

### 1. Repository Description

**Settings → General → Description**

```
Generative Engine Optimization skills for AI agents. Optimize content for ChatGPT, Perplexity, Claude, and Gemini.
```

### 2. Repository Topics

**Settings → General → Topics** (Add 8-10 topics)

```
geo, generative-engine-optimization, ai-search, agent-skills, claude-code, codex, cursor, windsurf, llm, content-optimization, schema-markup
```

### 3. Website URL

**Settings → General → Website**

```
https://skills.sh/mverab/egeoagents
```

### 4. Enable Discussions

**Settings → General → Features**

Check: ☑️ Discussions

### 5. About Section

**Settings → About → Display name**

```
E-GEO: Generative Engine Optimization
```

**Settings → About → Description**

```
🌍 Generative Engine Optimization skills for AI agents. Optimize content for ChatGPT, Perplexity, Claude, and Gemini with practical command workflows.
```

### 6. Social Image

**Settings → General → Social preview**

Upload the image from: `assets/hero-banner.png`

> **Tip:** This image shows "Rank #1" with AI engine logos - perfect for social sharing.

---

## Automated Release

The release v1.0.0 is defined in `.github/release-notes/v1.0.0.md`

Create the release via GitHub CLI:

```bash
gh release create v1.0.0 --title "v1.0.0: Initial Release" --notes-file .github/release-notes/v1.0.0.md
```

Or manually create on GitHub: **Releases → Draft a new release**

## GitHub CLI Shortcuts

Set description and website:

```bash
gh repo edit mverab/eGEOagents \
  --description "Generative Engine Optimization skills for AI agents. Optimize content for ChatGPT, Perplexity, Claude, and Gemini." \
  --homepage "https://skills.sh/mverab/egeoagents"
```

Set topics:

```bash
gh repo edit mverab/eGEOagents --add-topic geo --add-topic generative-engine-optimization --add-topic ai-search --add-topic agent-skills --add-topic claude-code --add-topic codex --add-topic cursor --add-topic windsurf --add-topic llm --add-topic content-optimization --add-topic schema-markup
```

---

## Topics Breakdown

| Topic | Purpose |
|-------|---------|
| `geo` | Primary category |
| `generative-engine-optimization` | Full keyword |
| `ai-search` | AI search optimization |
| `agent-skills` | Agent skills ecosystem signal |
| `claude-code` | Claude Code discoverability |
| `codex` | OpenAI Codex discoverability |
| `cursor` | Cursor discoverability |
| `windsurf` | Windsurf discoverability |
| `llm` | Large Language Models |
| `content-optimization` | Content strategy |
| `schema-markup` | Technical SEO |

---

## Launch Checklist

Before making the repository public:

- [ ] Repository description set (60 chars max)
- [ ] Topics configured (8-10 relevant tags)
- [ ] About URL configured (skills.sh source page)
- [ ] Discussions enabled
- [ ] Release v1.0.0 published
- [ ] README badges link to correct repository
- [ ] LICENSE file is correct (MIT)
- [ ] Contributing guidelines complete
- [ ] Code of conduct present
- [ ] Issue templates configured
- [ ] PR template configured

---

## Post-Launch

After launch, monitor:

- **Stars growth** via GitHub Insights
- **Traffic sources** via GitHub Traffic
- **Issues and PRs** for community engagement
- **Discussions** for questions and feedback
