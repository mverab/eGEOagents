# Frequently Asked Questions

> Common questions about E-GEO, GEO optimization, and getting started.

---

## General Questions

### What is Generative Engine Optimization (GEO)?

GEO is the practice of optimizing content to rank higher in AI-powered search engines like ChatGPT, Perplexity, Claude, and Gemini. Unlike traditional SEO (which optimizes for Google/Bing crawlers), GEO focuses on how Large Language Models perceive, understand, and recommend content.

### Is GEO the same as SEO?

No. While they share goals (visibility in search), they target different systems:

| Aspect | SEO | GEO |
|--------|-----|-----|
| **Target** | Google, Bing crawlers | ChatGPT, Perplexity, Claude, Gemini |
| **Key signals** | Backlinks, keywords, page speed | Content features, authority, relevance |
| **Optimization** | Technical + content | Content structure + persuasive features |
| **Results timeline** | Months | Minutes to hours |

GEO complements SEO — you should do both.

### Is E-GEO based on real research?

Yes. E-GEO is based on the research paper *"E-GEO: Optimizing Content for Generative Engines"* (arXiv:2511.20867). The paper identified 10 universal features that consistently improve AI-engine rankings.

---

## Getting Started

### Do I need coding skills to use E-GEO?

No. E-GEO runs inside Claude Code. You just type commands like `/geo https://yoursite.com`.

### What do I need to install?

1. Claude Code (free during beta)
2. Copy the `.claude/` folder from this repo to your project

That's it. No Python dependencies, no API keys required for basic usage.

### Can I use E-GEO without Claude Code?

Not directly. E-GEO is designed as a Claude Code extension. However, you can read the prompts in `prompts/` and adapt them for other LLM interfaces.

---

## Usage

### What URLs can I optimize?

Any public webpage. E-GEO fetches content via:
- MCP fetch server (default)
- Web-reader fallback
- Local files (via `/geo:optimize`)

### How long does optimization take?

- **Single page:** 2-5 minutes
- **Batch folder:** 5-15 minutes depending on file count

### What if I don't have MCP servers configured?

E-GEO works without MCP servers, but outputs are marked as **"Low Confidence"**. For best results, configure Brave Search and Chrome DevTools MCP servers. Use the `validation-doctor` skill for setup help.

### Can E-GEO optimize content in languages other than English?

Currently, E-GEO is optimized for English content. Multi-language support is on the roadmap.

---

## Output & Results

### Are the ranking predictions guaranteed?

No. Ranking predictions are estimates based on simulated AI-engine behavior. Actual rankings depend on:
- Content quality and competition
- AI engine algorithm changes
- Time since optimization

We recommend re-running audits every 2-4 weeks.

### Does E-GEO fabricate statistics or testimonials?

**No.** E-GEO never invents statistics, testimonials, or ratings. If your content lacks social proof, the report will flag it as a gap with recommendations on how to add real proof.

### What schema types does E-GEO generate?

Currently:
- `SoftwareApplication`
- `Organization`
- `Article`
- `Product`
- `FAQPage`

More types are planned. See [Issue #1](https://github.com/mverab/eGEOagents/issues) for contributing new schema types.

### Where do I put the generated schema?

Add the JSON-LD to your HTML `<head>` section:

```html
<script type="application/ld+json">
{ ... generated schema ... }
</script>
```

Or upload the `.json` files to your web server. See `geo-output/schema/IMPLEMENTATION.md` for detailed instructions.

---

## Technical

### What LLM does E-GEO use?

E-GEO runs on Claude (via Claude Code). The evaluation script (`geo_eval.py`) can use any OpenAI-compatible API.

### Can I customize the agents?

Yes. Agent configurations are in `.claude/agents/`. Each agent is a markdown file with system instructions. Edit them to customize behavior.

### How do I add a new skill?

1. Create a `SKILL.md` file in `.claude/skills/[skill-name]/`
2. Include frontmatter with `name`, `description`, and optional `allowed-tools`
3. Test with `npx skills add --list`

See [CONTRIBUTING.md](../CONTRIBUTING.md) for detailed guidelines.

---

## Contributing

### How can I contribute?

- Report bugs via [GitHub Issues](https://github.com/mverab/eGEOagents/issues)
- Submit pull requests for features
- Improve documentation
- Share your GEO results

See [CONTRIBUTING.md](../CONTRIBUTING.md) for full guidelines.

### Is this project AI-generated?

Parts of it. E-GEO is developed with AI assistance. See [AI Transparency](../CONTRIBUTING.md#ai-transparency) for details on what's AI-generated vs human-authored.

---

## Troubleshooting

### "MCP servers unavailable" warning

Configure MCP servers:
1. Install Brave Search MCP: `npx -y @anthropics/mcp-brave-search`
2. Install Chrome DevTools MCP: `npx -y @anthropics/mcp-chrome-devtools`
3. Add to your Claude Code MCP config

Use the `validation-doctor` skill for exact setup commands.

### Optimization takes too long

- Check your internet connection
- Large pages may take longer
- Try `/geo:audit` first (analysis only, faster)

### Output quality is low

- Ensure the target URL is accessible
- Check that MCP servers are configured
- Try optimizing a simpler page first

---

## See Also

- [Getting Started](getting-started.md) — Step-by-step tutorial
- [How It Works](how-it-works.md) — Technical deep dive
- [Skills.sh Playbook](skills-sh-playbook.md) — Distribution guide
- [USAGE.md](../USAGE.md) — Complete command reference
- [Contributing](../CONTRIBUTING.md) — Contribution guidelines

---

*Built for the AI-first web. Based on research from [arXiv:2511.20867](https://arxiv.org/abs/2511.20867).*
