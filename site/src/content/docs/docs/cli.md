---
title: CLI Reference
description: Complete reference for the egeo command line — optimize, evaluate, optimize-prompts, runtimes, and loop.
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

The `egeo` CLI (v2.0.0) is a runtime-agnostic wrapper around the same `geo_eval.py` and `llm_client.py` modules used by the Claude Code agents. Install with `pip install -e .` from the repo root, or run `python -m egeo` without installing.

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
