---
title: FAQ
description: Common questions about E-GEO — how it differs from geo-optimizer-skill, whether it needs Claude Code or API keys, and how GEO relates to SEO.
head:
  - tag: script
    attrs:
      type: application/ld+json
    content: |
      {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
          {
            "@type": "Question",
            "name": "How is E-GEO different from geo-optimizer-skill?",
            "acceptedAnswer": {"@type": "Answer", "text": "geo-optimizer-skill (Auriti-Labs, ~644 stars as of 2026-08) is audit-focused and scores sites 0-100 across 47 methods, with CLI, Python library, MCP, and Astro integration. E-GEO rewrites content (full analyze-rank-rewrite-schema pipeline), ships a reproducible evaluation harness, adds a continuous geo-loop mode, and is built on published GEO research (arXiv:2511.20867, building on Princeton's KDD 2024 GEO study). Both are MIT-licensed."}
          },
          {
            "@type": "Question",
            "name": "Does E-GEO work without Claude Code?",
            "acceptedAnswer": {"@type": "Answer", "text": "Yes. The standalone egeo Python CLI runs the full pipeline anywhere Python runs: egeo optimize, evaluate, optimize-prompts, runtimes, and loop. Claude Code adds the agent workflow (/geo commands) and MCP-based validation, but is not required."}
          },
          {
            "@type": "Question",
            "name": "Do I need API keys to use E-GEO?",
            "acceptedAnswer": {"@type": "Answer", "text": "Not to try it. Every egeo command honors GEO_EVAL_MOCK=1, which uses a deterministic offline mock client with no API key. Real model runs need OPENAI_API_KEY (any OpenAI-compatible endpoint via OPENAI_BASE_URL), and the serp collector needs BRAVE_API_KEY."}
          },
          {
            "@type": "Question",
            "name": "Is GEO the same as SEO?",
            "acceptedAnswer": {"@type": "Answer", "text": "No. SEO optimizes for search-engine crawlers and ranked blue links (Google, Bing); GEO optimizes for being cited in AI-generated answers (ChatGPT, Perplexity, Gemini, Claude). They complement each other — do both."}
          },
          {
            "@type": "Question",
            "name": "Is E-GEO based on real research?",
            "acceptedAnswer": {"@type": "Answer", "text": "Yes. E-GEO is based on the E-GEO research paper (arXiv:2511.20867, Bagga et al., 2025), which builds on the original Princeton GEO study (Aggarwal et al., KDD 2024)."}
          },
          {
            "@type": "Question",
            "name": "Does E-GEO fabricate statistics or testimonials?",
            "acceptedAnswer": {"@type": "Answer", "text": "No. E-GEO never invents statistics, testimonials, or ratings. If content lacks social proof, the report flags it as a gap with recommendations on how to add real proof."}
          }
        ]
      }
---

## The big questions

### How is E-GEO different from geo-optimizer-skill?

[geo-optimizer-skill](https://github.com/Auriti-Labs/geo-optimizer-skill) (Auriti-Labs) is a strong, popular tool — ~644 stars as of 2026-08 vs E-GEO's 147 — offering a CLI, Python library, MCP, and an Astro integration, and scoring sites 0–100 across 47 methods. If you want the broadest audit coverage, it is a fair choice.

E-GEO differentiates on four things:

1. **Rewriting, not just auditing** — the full analyze → rank → rewrite → schema pipeline outputs copy-paste-ready optimized content.
2. **Reproducible evaluation harness** — measure prompt quality yourself, offline, deterministically; the same check runs in CI.
3. **Continuous geo-loop mode** — watch domains over time with a persistent workspace (`$EGEO_HOME`) and deterministic collectors.
4. **Research-backed** — built on the E-GEO paper ([arXiv:2511.20867](https://arxiv.org/abs/2511.20867)) and the Princeton GEO study (KDD 2024).

Full comparison: [E-GEO vs geo-optimizer-skill](/compare/e-geo-vs-geo-optimizer-skill/).

### Does E-GEO work without Claude Code?

**Yes.** The standalone `egeo` Python CLI runs the full pipeline anywhere Python runs — local shells, notebooks, Docker, CI:

```bash
pip install egeo
egeo optimize path/to/page.md
```

Claude Code adds the agent workflow (`/geo` slash commands), auto-triggered skills, and MCP-based validation, but it is not required. Both runtimes share the same `geo_eval.py` / `llm_client.py` modules — no duplicated logic. The one exception: the interpretive part of a [loop-mode](/docs/geo-loop/) run (`/geo:loop <domain>`) is executed by an agent runtime; the LLM-free parts (`egeo loop run|collect|doctor`) work from any shell.

### Do I need API keys?

**Not to try it.** Every command honors `GEO_EVAL_MOCK=1`, which swaps in a deterministic mock LLM client — no API key at all. For real runs:

| Key | Needed for |
|---|---|
| `OPENAI_API_KEY` | Real model runs (any OpenAI-compatible endpoint via `OPENAI_BASE_URL`) |
| `BRAVE_API_KEY` | The `serp` collector in loop mode only |

### Is GEO the same as SEO?

No. They share the goal of visibility but target different systems:

| Aspect | SEO | GEO |
|--------|-----|-----|
| **Target** | Google, Bing crawlers | ChatGPT, Perplexity, Claude, Gemini |
| **Key signals** | Backlinks, keywords, page speed | Content features, authority, relevance |
| **Outcome** | Ranked blue links | Citations in AI-generated answers |

GEO complements SEO — you should do both. Deep dive: [GEO vs SEO](/concepts/geo-vs-seo/).

## General

### What is Generative Engine Optimization (GEO)?

GEO is the practice of optimizing content to rank higher in AI-powered search engines like ChatGPT, Perplexity, Claude, and Gemini. Unlike traditional SEO (which optimizes for crawlers), GEO focuses on how Large Language Models perceive, understand, and recommend content. See [What is GEO?](/concepts/what-is-geo/).

### Is E-GEO based on real research?

Yes. E-GEO is based on the paper *"E-GEO: Optimizing Content for Generative Engines"* ([arXiv:2511.20867](https://arxiv.org/abs/2511.20867)), which identified 10 universal features that consistently improve AI-engine rankings.

### Do I need coding skills to use E-GEO?

No for the Claude Code workflow — you type commands like `/geo https://yoursite.com`. Basic terminal familiarity helps for the standalone CLI.

## Usage

### What can I optimize?

Local Markdown/text files via `egeo optimize <file>` or `/geo:optimize <file>`; any public webpage via `/geo <url>` in Claude Code (fetched through MCP fetch or a web-reader fallback); entire folders via `/geo:batch`.

### What if I don't have MCP servers configured?

E-GEO works without them, but outputs are marked **"Low Confidence"**. For best results configure Brave Search and Chrome DevTools MCP servers — the `validation-doctor` skill prints exact setup commands. See [MCP Server](/docs/mcp-server/).

### Can E-GEO optimize content in languages other than English?

Currently E-GEO is optimized for English content. Multi-language support is on the roadmap.

## Output & results

### Are the ranking predictions guaranteed?

No. Ranking predictions are estimates based on simulated AI-engine behavior. Actual rankings depend on content quality, competition, AI engine algorithm changes, and time since optimization. The [evaluation harness](/docs/evaluation/) documents this limitation explicitly: its metrics are a proxy, not real ChatGPT/Perplexity rankings.

### Does E-GEO fabricate statistics or testimonials?

**No.** E-GEO never invents statistics, testimonials, or ratings. If your content lacks social proof, the report flags it as a gap with recommendations on how to add real proof.

### What schema types does E-GEO generate?

`SoftwareApplication`, `Organization`, `Article`, `Product`, `Service`, and `FAQPage`. The CLI's `--schema-type` flag currently accepts `Organization`, `Product`, `Service`, `Article`, and `FAQPage`.

### Where do I put the generated schema?

Add the JSON-LD to your HTML `<head>`:

```html
<script type="application/ld+json">
{ ... generated schema ... }
</script>
```

## Technical

### What LLM does E-GEO use?

The Claude Code workflow runs on Claude. The evaluation harness and CLI can use any OpenAI-compatible API (`OPENAI_BASE_URL`), defaulting to `gpt-4o` for ranker, rewriter, and meta-optimizer models.

### Can I customize the agents?

Yes. Agent configurations live in `.claude/agents/` as markdown files with system instructions. Edit them to customize behavior.

## Troubleshooting

### "MCP servers unavailable" warning

Add Brave Search and Chrome DevTools MCP servers to your Claude Code MCP config, or run the `validation-doctor` skill for exact setup commands. E-GEO still works without them — outputs are just marked Low Confidence.

### Optimization takes too long

Single pages typically take 2–5 minutes; batch folders 5–15 minutes. Try `/geo:audit` first (analysis only, faster), and check that the target URL is accessible.
