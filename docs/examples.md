# Before/After Examples (real runs)

Three real runs of `egeo optimize`, recorded on **2026-10-04** with `egeo 2.2.0`,
`gpt-4o` as ranker and rewriter, temperature 0. Nothing here is hand-edited or
mocked: the "after" text is the rewriter's output verbatim (excerpted where long).

> **Read the numbers with care.** The GEO score is the deterministic, offline
> analyzer in `egeo/agents.py`: a keyword heuristic that rewards words like
> "best", "unlike", "today". A higher score means more GEO signals were
> *detected*, not that an AI engine will cite the page. The rank is a
> simulation against 3 generic, synthetic competitor stubs. For measured
> AI-search visibility, see the [case study](https://egeoagents.com/case-study/).

## Summary

| Page | Query | GEO score | Simulated rank | Words |
|---|---|---|---|---|
| [`examples/sample-input.md`](../examples/sample-input.md) (thin product page) | best analytics platform for small businesses | 22 → 45 | #1 → #1 | 28 → 90 |
| [`rank-in-perplexity.md`](https://egeoagents.com/guides/rank-in-perplexity/) (long how-to guide) | how to get my website cited by Perplexity | 53 → 68 | #1 → #1 | 609 → 352 |
| [`what-is-geo.md`](https://egeoagents.com/concepts/what-is-geo/) (concept page) | what is generative engine optimization | 60 → 61 | #1 → #1 | 517 → 377 |

**What these runs show:**

- **Thin pages gain the most.** The 28-word product page got a real structure, an intent line, and benefit-led bullets.
- **Long, well-sourced pages can lose substance.** Both site pages shrank by about a third, and the rewriter removed material that matters for citation: the "Last verified" date, primary-source links, and specific data points. A score increase does not mean the page got better. Review every rewrite against the original before publishing, and merge the improvements back by hand rather than replacing the page. (`egeo fix-gaps --mode sections`, still experimental, targets this by rewriting only the losing section.)
- **The rank simulation saturates.** Against generic stubs, all three pages ranked #1 both before and after, so it gives no signal here.

---

## 1. Thin product page — `examples/sample-input.md`

**Before** (28 words, GEO score 22/100):

```markdown
# Acme Analytics Platform

We help businesses understand their data.

## Features

- Dashboard
- Reports
- Integrations

## Pricing

Starting at $99/month.

Contact us for more information.
```

**After** (90 words, GEO score 45/100), verbatim:

```markdown
# Acme Analytics Platform

Best for businesses seeking comprehensive data insights.

The Acme Analytics Platform empowers businesses to make informed decisions by providing a deep understanding of their data.

## Key Features

- **Dashboard**: Intuitive interface for real-time data visualization.
- **Reports**: Generate detailed reports to track performance metrics.
- **Integrations**: Seamlessly connect with existing tools for enhanced data flow.

## Pricing

- **Affordable Plans**: Starting at $99/month, offering great value for robust analytics.

For more information, contact us today to see how Acme Analytics can transform your data strategy.
```

**What changed**

| Feature | Before | After |
|---|---|---|
| Ranking emphasis | 0 | 5 |
| User intent | 0 | 8 |
| Narrative | 0 | 2 |
| Urgency | 0 | 8 |
| Others (USPs 8, scannable 10, factual 4; rest 0) | — | unchanged |

- Added an intent line ("Best for …") and a one-sentence value statement.
- Each bare feature got a benefit description.
- **Check before publishing:** "real-time" is not in the original, so it is an unverified claim the rewriter introduced. "Today" is the only thing that raised the urgency score. Social proof stayed at 0 because the source has none to work with, which is correct.

## 2. Long how-to guide — "How to Get Cited by Perplexity"

Source: `site/src/content/docs/guides/rank-in-perplexity.md` (frontmatter and JSON-LD preserved unchanged).

**Before**, opening (verbatim):

> **Last verified: 2026-08-11.** This playbook comes from running a fixed query set against Perplexity every week and recording which sources it cites — including a month where our own project had perfect on-page metadata and zero mentions.
>
> ## The finding that changes everything
>
> Perplexity does not crawl GitHub and sort by stars. In our measured category (open-source GEO tools), projects with **17–37 stars appeared** in answers while a project with **147 stars did not** — for over a month. […] It was presence in the sources Perplexity synthesizes from:
>
> - **Aggregators** (LibHunt was the top-cited source in our category). […]

**After**, opening (verbatim):

> # How to Get Cited by Perplexity (Measured Playbook)
>
> Best for maximizing visibility in Perplexity's search results.
>
> ## Key Insights
> - Projects with 17–37 stars appeared in Perplexity answers, while a project with 147 stars did not.
> - Presence in sources Perplexity synthesizes from is crucial.
>
> ## Differentiation
> Unlike typical alternatives that focus on star count or README optimization, this playbook emphasizes strategic presence in key sources.

**What changed** (GEO score 53 → 68)

- User intent 5 → 10 and competitive differentiation 0 → 10: the new "Best for …" line and the "Unlike typical alternatives …" section.
- Urgency 0 → 5; narrative 7 → 2.
- Steps 1–5 were kept but compressed into short bullets.
- **Lost in the rewrite:**
  - the "Last verified" date, which the page itself recommends as a trust signal;
  - LibHunt as the top-cited source;
  - "a direct answer in the first 50–170 words" and "links to primary sources" from Step 4;
  - the CDN/WAF explanation;
  - the query-set split (2 branded, 8 generic) and "one run is a sample; the trend over weeks is the signal".
- No facts were invented.

## 3. Concept page — "What is GEO"

Source: `site/src/content/docs/concepts/what-is-geo.md` (frontmatter preserved unchanged).

**Before**, opening (verbatim):

> **Generative Engine Optimization (GEO)** is the practice of optimizing content so AI-powered search engines — ChatGPT, Perplexity, Gemini, Claude, Google AI Overviews — can crawl, understand, rank, and **cite** it in their generated answers.

**After**, opening (verbatim):

> # What is GEO (Generative Engine Optimization)?
>
> Best for optimizing content visibility in generative AI engines.
>
> ## Why GEO Exists
> Generative engines provide a single synthesized answer, citing only a few sources. If your content isn't cited, it remains unseen, even if it ranks #1 on traditional search engines.

**What changed** (GEO score 60 → 61)

- Ranking emphasis 5 → 8 and user intent 0 → 8; social proof 7 → 2, competitive differentiation 8 → 5, authority 10 → 8.
- Section structure kept; each section shortened.
- **Lost in the rewrite:**
  - the one-sentence definition that opened the page, which is the direct answer to the query;
  - both research links (Aggarwal et al., KDD 2024 on arXiv, and arXiv:2511.20867);
  - the GitHub link and the MIT-license mention in the summary.

  That makes the page *less* citable even though the score barely moved.
- No facts were invented.

---

## Reproduce

```bash
pip install egeo   # or: pip install -e . from a checkout
export OPENAI_API_KEY=...

egeo optimize examples/sample-input.md \
  --query "best analytics platform for small businesses" \
  --ranker-model gpt-4o --rewriter-model gpt-4o
egeo optimize site/src/content/docs/guides/rank-in-perplexity.md \
  --query "how to get my website cited by Perplexity" \
  --ranker-model gpt-4o --rewriter-model gpt-4o
egeo optimize site/src/content/docs/concepts/what-is-geo.md \
  --query "what is generative engine optimization" \
  --ranker-model gpt-4o --rewriter-model gpt-4o
```

Each run writes `report.md`, `optimized/`, `schema/` and `analysis.json` to
`geo-output/`. Scores come from the deterministic analyzer, so the "before"
scores reproduce exactly; the rewrites depend on the model and may differ
between runs. The "after" scores above come from running the same analyzer
(`egeo.agents.Analyzer`) on the optimized files.
