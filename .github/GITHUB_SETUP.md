# GitHub Repository Configuration

This file contains all the information needed to configure the E-GEO repository for maximum discoverability on GitHub.

## Manual GitHub Setup Required

The following actions must be completed manually on GitHub:

### 1. Repository Description

**Settings → General → Description**

```
Zero-effort Generative Engine Optimization. Rank higher in ChatGPT, Perplexity, Claude, and Gemini with one command. Based on published research.
```

### 2. Repository Topics

**Settings → General → Topics** (Add 8-10 topics)

```
geo, generative-engine-optimization, ai-search, chatgpt-optimization, perplexity, claude, llm, content-optimization, seo, schema-markup
```

### 3. Website URL

**Settings → General → Website**

```
https://arxiv.org/abs/2511.20867
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
🌍 Zero-effort Generative Engine Optimization for AI-powered search engines. Optimize your content for ChatGPT, Perplexity, Claude, and Gemini with one command. Based on published research (arXiv:2511.20867).
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

---

## Topics Breakdown

| Topic | Purpose |
|-------|---------|
| `geo` | Primary category |
| `generative-engine-optimization` | Full keyword |
| `ai-search` | AI search optimization |
| `chatgpt-optimization` | ChatGPT targeting |
| `perplexity` | Perplexity AI |
| `claude` | Anthropic Claude |
| `llm` | Large Language Models |
| `content-optimization` | Content strategy |
| `seo` | Related to SEO |
| `schema-markup` | Technical SEO |

---

## Launch Checklist

Before making the repository public:

- [ ] Repository description set (60 chars max)
- [ ] Topics configured (8-10 relevant tags)
- [ ] About URL configured (arXiv paper link)
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
