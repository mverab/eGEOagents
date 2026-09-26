# GEO harness (rank-delta)

## Files
- `geo_eval.py`: evaluation + lightweight prompt meta-optimization
- `llm_client.py`: OpenAI-compatible HTTP client (stdlib only)
- `prompts/`: prompt templates
- `egeo/loop.py`: loop-mode CLI (`egeo loop run|collect|doctor|decide`)
- `egeo/decide.py`: deterministic next-action ranking + outcome ledger
- `egeo/workspace.py`: `$EGEO_HOME` resolution + substrate bootstrap
- `collectors/`: deterministic collectors (`serp`, `page`) and their fixtures

## Environment
- `OPENAI_API_KEY`: required
- `OPENAI_BASE_URL`: optional (defaults to `https://api.openai.com/v1`)
- `RANKER_MODEL`: optional (default `gpt-4o`)
- `REWRITER_MODEL`: optional (default `gpt-4o`)
- `META_MODEL`: optional (default `gpt-4o`)

## Dataset format (JSONL)
One JSON object per line:

- `query_id` (string)
- `query` (string)
- `candidates` (array of 10 objects)
  - `id` (string)
  - `title` (string)
  - `description` (string)
- `target_id` (optional string). If missing, the script picks a random candidate.

## Evaluate

```bash
python3 geo_eval.py evaluate --dataset /absolute/path/to/dataset.jsonl
```

## Optimize (prompt meta-optimization)

```bash
python3 geo_eval.py optimize --train /absolute/path/to/train.jsonl --val /absolute/path/to/val.jsonl --iters 5
```

The best-on-validation prompt is written to
`prompts/rewriter_user.candidate.txt`; pass `--apply` to promote it over the
working `prompts/rewriter_user.txt`. When a loop workspace exists (see below)
both destinations move to `$EGEO_HOME/prompts/` and the repo `prompts/`
directory is left untouched.

## Fix gaps (`egeo fix-gaps`)

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

Inputs: geo-optimizer-skill `geo citations --format json`, or a generic JSON/CSV with `query`, `cited` and optional `sources` (URLs the engine cited instead of you). Mapping and unmatched reasons work exactly as documented in the CLI reference.

Section mode (experimental, `--mode sections`) flow: pick the own section that loses → rewrite only it → deterministic **fidelity rules** (heading, links, numbers, tables, code, length) → Jev fidelity judge → Jev re-check. Statuses: `rewritten`, `already_best`, `no_competitor_sources`, `no_own_candidates`, `no_change_proposed`, `rejected_fidelity_rules`, `rejected_fidelity_judge`, `rejected_worse`, `jev_error`, `rewriter_error`.

> **Experimental: the Jev comparison.** The Jev steps measure *text competitiveness* only — not authority, links or citation. Pre-registered validation of the same single-choice comparison (30 queries, 2026-09-25): mean AUC 0.62, 95% CI 0.56–0.67, below the 0.65 bar; it matched the engine's cited/not-cited outcome for the own page in only 17% of queries. It was run on full-page excerpts, not sections (`eval/jev_selection/README.md`). The Jev fidelity judge was not validated directly (the eval measured selection); it can only reject, after the deterministic rules. A re-check outcome of `won` means any own section now wins, not necessarily the rewritten one. Every report carries the figures in `jev_validation` and marks Jev judgments `"experimental": true`. Prove impact by re-running your tracker on `remeasure`, never from Jev.

`already_best` means your text already competes — the gap is probably off-page; the report lists the cited sources to get mentioned or linked by. Output: `<out-dir>/<page-id>/` (rewritten file, `section.diff`, `diagnosis.json`) plus `<out-dir>/fix-gaps.json`.

Requirements: page mode needs `OPENAI_API_KEY` (+ optional `OPENAI_BASE_URL`) for the ranker and rewriter; section mode needs `TYPESAFE_API_KEY` and `OPENAI_API_KEY` (+ optional `OPENAI_BASE_URL`, for the rewriter). Keys are checked before the run starts (fails closed); a rewriter failure on one page marks it `rewriter_error` and the run continues; `GEO_EVAL_MOCK=1` for offline runs.

Flags: `--mode page|sections` (default `page`, the whole-page rewrite; `sections` is experimental and opt-in), `--max-sources`, `--jev-model`, `--project`, `--out-dir`, `--format markdown|html` (page mode), `--dry-run`, `--json`, plus the `optimize` runtime/model flags (page mode).

## Loop mode

Loop mode is opt-in and keeps all state in the workspace resolved from
`$EGEO_HOME` (default `~/.egeo/`). The repo tree is never written to by a loop
run, a collector pass, or a prompt optimization. Everything above keeps working
without a workspace.

### Environment
- `EGEO_HOME`: optional (defaults to `~/.egeo`)
- `BRAVE_API_KEY`: required by the `serp` collector only

### Commands

```bash
# Bootstrap (idempotent) + health check: layout, config, budgets, substrate lint
egeo loop doctor

# Collector passes — deterministic, budget-aware, append-only JSONL
egeo loop collect serp --query "best geo tool" --target-domain example.com
egeo loop collect page --url https://example.com/pricing

# Offline/deterministic collector runs (no network)
egeo loop collect serp --query "best geo tool" --target-domain example.com \
  --fixture collectors/fixtures/serp_brave_response.json
egeo loop collect page --url https://example.com/pricing \
  --fixture collectors/fixtures/pages

# Print the run plan for a domain — writes nothing
egeo loop run example-com --dry-run

# Rank one next action from collector JSONL + the outcome ledger — writes nothing
egeo loop decide --dry-run

# Execute one bounded iteration (the agent does the interpretive work)
claude -p "/geo:loop example-com"

# Verify the workspace against SUBSTRATE.md
python3 -m egeo.substrate_lint
```

### The run contract

One wake-up performs at most **one** unit of work from the domain's
`## Current focus` or `## Backlog`, appends exactly **one**
`### YYYY-MM-DD run` Timeline entry ending in
`Outcome: success|partial|failure|no-op`, appends exactly **one** `LOG.md` line,
and verifies both writes before exiting. See
[`.claude/skills/geo-loop/SKILL.md`](.claude/skills/geo-loop/SKILL.md) and
[`SUBSTRATE.md`](SUBSTRATE.md).

### Scheduling

Any scheduler works; pin provider and model per job. Jobs more frequent than
weekly deliver locally (JSONL + LOG line) and a weekly digest job summarizes
`$EGEO_HOME/LOG.md` — that digest is the only job that notifies.

```
0 * * * *   provider=anthropic model=claude-sonnet-4-5 deliver=local \
            egeo loop collect page --url https://example.com/pricing
30 6 * * *  provider=anthropic model=claude-sonnet-4-5 deliver=local \
            claude -p "/geo:loop example-com"
0 9 * * 1   provider=anthropic model=claude-opus-4-1 deliver=notify \
            claude -p "Summarize $EGEO_HOME/LOG.md for the past 7 days"
```
