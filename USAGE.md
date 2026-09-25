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

Turn an AI-visibility tracker's report into page rewrites. `fix-gaps` reads the queries where your domain is **not** cited, maps each one to the local page that should win it through `project.yaml`, and runs the `optimize` pipeline once per page. Your source files are never modified.

```bash
# 1. Measure with any tracker, e.g. geo-optimizer-skill:
geo citations --brand "Acme" --domain acme.com --format json --output gaps.json
# 2. Plan (writes nothing, calls no model):
egeo fix-gaps gaps.json --project project.yaml --dry-run
# 3. Rewrite the losing pages:
egeo fix-gaps gaps.json --project project.yaml --out-dir fix-gaps-output
```

**Inputs (auto-detected):**
- geo-optimizer-skill `geo citations --format json` output. Entries with `domain_cited: false` are gaps; entries with an `error` are skipped, never rewritten.
- A generic gaps file any tracker can export: a JSON array or CSV with `query` and `cited` (true/false, 1/0, yes/no), plus optional `sources`.

**Mapping:** the gap query must match an active `queries[].text` in `project.yaml` (case, spacing and trailing punctuation ignored). Its `target_pages` point to `pages[]`, and each page needs a `source` path to its local file (relative to `project.yaml`). Unmapped gaps are reported with a reason (`query_not_in_project`, `no_target_page`, `page_has_no_source`, `source_not_found`), never guessed. A page that loses several queries is rewritten once, against the first.

**Output:** `<out-dir>/<page-id>/` with the usual `optimized/`, `schema/` and `report.md`, plus `<out-dir>/fix-gaps.json` listing pages, unmatched and skipped gaps, and a `remeasure` list (with the exact `geo citations` command for geo-optimizer-skill input). Rank before/after is the LLM-ranker proxy; re-measure with your tracker to confirm real citations.

Flags: `--project`, `--out-dir` (default `fix-gaps-output`), `--format markdown|html`, `--dry-run`, `--json`, plus the same `--runtime` and model flags as `optimize`. `GEO_EVAL_MOCK=1` runs it offline.

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
