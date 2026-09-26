---
title: CLI Reference
description: Complete reference for the egeo command line — optimize, fix-gaps, evaluate, optimize-prompts, runtimes, and loop.
head:
  - tag: script
    attrs:
      type: application/ld+json
    content: |
      {
        "@context": "https://schema.org",
        "@type": "TechArticle",
        "headline": "E-GEO CLI Reference",
        "description": "Complete reference for the egeo command line: optimize, evaluate, optimize-prompts, runtimes, loop.",
        "url": "https://egeoagents.com/docs/cli/",
        "author": {"@type": "Person", "name": "Miguel Vera", "sameAs": ["https://github.com/mverab"]}
      }
---

The `egeo` CLI (v2.0.0) is a runtime-agnostic wrapper around the same `geo_eval.py` and `llm_client.py` modules used by the Claude Code agents. Install with `pip install egeo`, or run `python -m egeo` from a clone without installing.

```
usage: egeo [-h] [--version] {optimize,evaluate,optimize-prompts,runtimes,loop} ...
```

Every command honors `GEO_EVAL_MOCK=1`, which swaps in a deterministic mock LLM client — no API key required. That is exactly how the CLI is exercised in CI.

## `egeo optimize`

Run the full GEO pipeline on a local content file (Markdown/text): analyze → rank → rewrite → schema.

```
usage: egeo optimize [-h] [--out-dir OUT_DIR] [--query QUERY]
                     [--schema-type {Organization,Product,Service,Article,FAQPage}]
                     [--runtime RUNTIME] [--ranker-model RANKER_MODEL]
                     [--rewriter-model REWRITER_MODEL]
                     [--temperature TEMPERATURE] [--json]
                     input
```

| Argument / flag | Default | Meaning |
|---|---|---|
| `input` | — | Path to a local content file (Markdown/text). |
| `--out-dir` | `geo-output` | Output directory. |
| `--query` | derived from the title | Search query to rank against. |
| `--schema-type` | `Article` | JSON-LD schema template to emit: `Organization`, `Product`, `Service`, `Article`, or `FAQPage`. |
| `--runtime` | `python` | Runtime adapter to use. |
| `--ranker-model` / `--rewriter-model` | — | Model overrides. |
| `--temperature` | — | Sampling temperature. |
| `--json` | off | Print only the machine-readable JSON summary. |

```bash
GEO_EVAL_MOCK=1 egeo optimize examples/sample-input.md --out-dir /tmp/egeo
```

## `egeo evaluate`

Evaluate prompt quality on a dataset (wraps `geo_eval.evaluate`). See [Evaluation Harness](/docs/evaluation/) for the dataset format and metric definitions.

```
usage: egeo evaluate [-h] --dataset DATASET [--prompts PROMPTS]
                     [--ranker-model RANKER_MODEL]
                     [--rewriter-model REWRITER_MODEL]
                     [--temperature TEMPERATURE] [--seed SEED] [--limit LIMIT]
                     [--verbose]
```

| Flag | Meaning |
|---|---|
| `--dataset` (required) | Path to the JSONL dataset. |
| `--prompts` | Prompt directory override. |
| `--ranker-model` / `--rewriter-model` | Model names (or env `RANKER_MODEL`, `REWRITER_MODEL`). |
| `--temperature` | Sampling temperature. |
| `--seed` | RNG seed for reproducibility. |
| `--limit N` | Evaluate only the first N examples. |
| `--verbose` | Print per-example before/after ranks. |

```bash
GEO_EVAL_MOCK=1 egeo evaluate --dataset eval/datasets/geo_smoke.jsonl --limit 5
```

## `egeo optimize-prompts`

Meta-optimize the rewriter prompt (wraps `geo_eval.optimize`). **Non-destructive by default**: writes the best prompt to `prompts/rewriter_user.candidate.txt` and leaves the working prompt untouched.

```
usage: egeo optimize-prompts [-h] --train TRAIN --val VAL [--prompts PROMPTS]
                             [--ranker-model RANKER_MODEL]
                             [--rewriter-model REWRITER_MODEL]
                             [--meta-model META_MODEL]
                             [--temperature TEMPERATURE] [--seed SEED]
                             [--iters ITERS] [--apply]
```

| Flag | Meaning |
|---|---|
| `--train` / `--val` (required) | Train and validation JSONL splits. |
| `--meta-model` | Meta-optimizer model name. |
| `--iters` | Meta-optimization iterations. |
| `--apply` | Overwrite the working rewriter prompt in place (default: write `*.candidate.txt`). |

When a loop workspace exists, both prompt destinations move to `$EGEO_HOME/prompts/` and the repo `prompts/` directory stays pristine.

## `egeo runtimes`

List available runtime adapters and their status.

```
usage: egeo runtimes [-h] [--json]
```

| Runtime | Aliases | Mode | Description |
|---|---|---|---|
| `python` | `cli`, `local` | in-process | Pure-Python runtime; runs the full pipeline in-process, honors `GEO_EVAL_MOCK`. |
| `claude-code` | `claude` | host-executed | Executes the `.claude/` agents via Claude Code `/geo` slash commands. Auto-detected when a `.claude/` directory is present. |

Additional hosts can be added by implementing the `RuntimeAdapter` interface in `egeo/runtimes.py`.

## `egeo fix-gaps`

Turn an AI-visibility tracker's report into surgical page rewrites. `fix-gaps` reads the queries where your domain is **not** cited, maps each one to the local page that should win it through `project.yaml`, and rewrites it. The default **page mode** optimizes each affected page with the `optimize` pipeline; the opt-in, **experimental section mode** (`--mode sections`) rewrites only the one section that loses the query. Page mode stays the default until `remeasure` evidence shows section mode helps. Your source files are never modified.

```bash
# 1. Measure with any tracker, e.g. geo-optimizer-skill:
geo citations --brand "Acme" --domain acme.com --format json --output gaps.json
# 2. Plan (writes nothing, calls no model, needs no key):
egeo fix-gaps gaps.json --project project.yaml --dry-run
# 3a. Rewrite the affected pages (default page mode):
egeo fix-gaps gaps.json --project project.yaml --out-dir fix-gaps-output
# 3b. Or rewrite only the losing sections (experimental section mode):
egeo fix-gaps gaps.json --project project.yaml --out-dir fix-gaps-output --mode sections
```

**Inputs (auto-detected):**
- geo-optimizer-skill `geo citations --format json` output. Entries with `domain_cited: false` are gaps; entries with an `error` are skipped, never rewritten.
- A generic gaps file any tracker can export: a JSON array or CSV with `query` and `cited` (true/false, 1/0, yes/no), plus optional `sources` (the URLs the engine cited instead of you).

**Mapping:** the gap query must match an active `queries[].text` in `project.yaml` (case, spacing and trailing punctuation ignored). Its `target_pages` point to `pages[]`, and each page needs a `source` path to its local file (relative to `project.yaml`). Unmapped gaps are reported with a reason (`query_not_in_project`, `no_target_page`, `page_has_no_source`, `source_not_found`), never guessed. A page that loses several queries is rewritten once, against the first.

**Section mode (experimental, opt-in with `--mode sections`) flow:** split the page into sections → pick the own section that loses the query against the cited sources → rewrite **only that section** → **fidelity rules** (heading, links, numbers, table rows, code blocks, length ratio must be preserved) → Jev fidelity judge → Jev re-check. Any rejection keeps your original text untouched. Per-page statuses in `fix-gaps.json`:

| Status | Meaning |
|---|---|
| `rewritten` | accepted rewrite written with a `section.diff` |
| `already_best` | your text already competes — see the off-page recommendation below |
| `no_competitor_sources` | none of the cited sources could be fetched |
| `no_own_candidates` | no own section long enough to compete |
| `no_change_proposed` | the rewriter returned the section unchanged |
| `rejected_fidelity_rules` | rewrite broke a deterministic fidelity rule |
| `rejected_fidelity_judge` | Jev fidelity judge did not accept the rewrite |
| `rejected_worse` | the re-check scored the rewrite worse than the original |
| `jev_error` | TypeSafe failed for this page (other pages continue) |
| `rewriter_error` | the rewriter LLM failed for this page (other pages continue) |

:::caution[Experimental: the Jev comparison]
The two Jev steps (which section loses, and the before/after re-check) measure **text competitiveness** — whether a candidate's *text* directly answers the query. They do **not** model authority, links or brand, and they are **not a prediction of citation**. In a pre-registered validation (30 queries, 2026-09-25) the same single-choice comparison separated Perplexity-cited from uncited sources with mean AUC **0.62 (95% CI 0.56–0.67)** — weak, and below the 0.65 bar we set — and matched the engine's cited/not-cited outcome for the own page in only **17%** of queries. That validation used full-page excerpts, not sections. The Jev fidelity judge was not validated directly (the eval measured selection); it can only reject, after the deterministic rules. A re-check outcome of `won` means any own section now wins, not necessarily the rewritten one. Numbers and method: `eval/jev_selection/README.md`. Every `fix-gaps.json` carries the same figures in `jev_validation`, and every diagnosis/verification is marked `"experimental": true`. **Proof of impact never comes from Jev:** re-run your tracker on the `remeasure` queries.
:::

**`already_best` → off-page recommendation:** when your text already wins the comparison, rewriting it is unlikely to help — the gap is probably off-page. The report lists the sources the engine cited so you can get your page mentioned or linked by them.

**Output:** `<out-dir>/<page-id>/` with the rewritten file, `section.diff` and `diagnosis.json`, plus `<out-dir>/fix-gaps.json` listing pages, statuses, unmatched/skipped gaps, `jev_validation`, and a `remeasure` list (with the exact `geo citations` command for geo-optimizer-skill input).

**Requirements:** page mode needs an OpenAI-compatible key for the ranker and rewriter (`OPENAI_API_KEY`, optional `OPENAI_BASE_URL`). Section mode needs `TYPESAFE_API_KEY` and an OpenAI-compatible key for the rewriter (`OPENAI_API_KEY`, optional `OPENAI_BASE_URL`, model via `--rewriter-model`); keys are checked before the run starts and it fails closed with a clear error otherwise. `GEO_EVAL_MOCK=1` runs fully offline, deterministically.

Flags: `--mode page|sections` (default `page`, the whole-page rewrite from v2.1; `sections` is experimental and opt-in), `--max-sources` (default 6), `--jev-model`, `--project`, `--out-dir` (default `fix-gaps-output`), `--format markdown|html` (page mode), `--dry-run`, `--json`, plus the same `--runtime` and model flags as `optimize` (page mode).

## `egeo loop`

Loop mode keeps state in a per-user workspace (`$EGEO_HOME`, default `~/.egeo`). These commands are the scheduler seam and make **zero LLM calls**.

```
usage: egeo loop [-h] {run,collect,doctor,decide} ...
```

### `egeo loop run <domain> [--dry-run] [--json]`

Resolve and print the run plan for one domain: current focus, collector deltas since the last Timeline entry, and candidate signals. With `--dry-run` nothing is written at all. The interpretive run itself is executed by an agent runtime via `/geo:loop <domain>`.

### `egeo loop collect {page,serp} ...`

Run one deterministic collector pass in-process against `$EGEO_HOME`. Arguments after the collector name are forwarded verbatim (`--fixture`, `--json`, `--query`, `--url`).

```bash
egeo loop collect serp --query "best geo tool" --target-domain example.com
egeo loop collect page --url https://example.com/pricing
```

### `egeo loop doctor [--json]`

Bootstrap the workspace if needed, then self-check it: layout, config, substrate, budgets.

### `egeo loop decide [--dry-run] [--json]`

Rank exactly one next action from `project.yaml`, collector JSONL, and `$EGEO_HOME/data/outcomes/ledger.jsonl`. LLM-free. `--dry-run` writes nothing. Without it, the command may append one ledger row and one proposal doc. It never publishes, merges, or sets `status: applied`.

Full loop-mode guide: [GEO Loop](/docs/geo-loop/).

## Environment variables

| Variable | Purpose |
|---|---|
| `GEO_EVAL_MOCK` | Truthy (`1`/`true`/`yes`/`on`) → offline deterministic mock client, no API key. |
| `OPENAI_API_KEY` | Required for real model runs. |
| `OPENAI_BASE_URL` | Optional OpenAI-compatible endpoint override. |
| `RANKER_MODEL` / `REWRITER_MODEL` / `META_MODEL` | Default model names (default `gpt-4o`). |
| `EGEO_HOME` | Loop workspace location (default `~/.egeo`). |
| `BRAVE_API_KEY` | Required by the `serp` collector only. |
