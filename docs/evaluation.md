# Evaluation Harness

E-GEO ships a small, self-contained evaluation harness (`geo_eval.py` +
`llm_client.py`) that measures whether the GEO **rewriter** prompt actually
moves a target item *up* in an LLM-simulated ranking.

> **⚠️ Honest limitation — read this first.**
> These numbers are a **proxy**, not a measurement of real AI-search rankings.
> The "ranking" is produced by an LLM acting as a re-ranking judge over a fixed
> candidate list. It does **not** query ChatGPT, Perplexity, Claude, or Gemini,
> and it does not reflect live retrieval, indexing, or user behavior. Treat the
> metrics as a relative signal for prompt iteration, **not** as evidence of
> real-world rank gains.

---

## How it works

For each example the harness:

1. Asks the **ranker** model to order all candidates for a query → records the
   target's `rank_before`.
2. Asks the **rewriter** model to rewrite the target's description (no new
   facts).
3. Asks the **ranker** to re-order the candidates with the rewritten target →
   records `rank_after`.
4. Computes `rank_improvement = rank_before - rank_after` (positive = moved up).

`optimize` wraps this in a meta-optimization loop that asks a **meta-optimizer**
model to propose an improved rewriter prompt, keeping the best one on a
validation split.

---

## Dataset format (JSONL)

One JSON object per line. See [`eval/datasets/geo_smoke.jsonl`](../eval/datasets/geo_smoke.jsonl).

```json
{
  "query_id": "q1",
  "query": "best lightweight laptop for travel under 1kg",
  "target_id": "p1",
  "candidates": [
    { "id": "p1", "title": "Aero One 13", "description": "13-inch ultrabook, 980g, 16GB RAM, 512GB SSD." },
    { "id": "p2", "title": "WorkPro 15", "description": "15-inch aluminum laptop weighing 1.8kg ..." },
    { "id": "p3", "title": "BudgetBook 14", "description": "14-inch plastic chassis laptop ..." }
  ]
}
```

| Field | Required | Description |
|-------|----------|-------------|
| `query` | ✅ | The user query the candidates are ranked against. |
| `candidates` | ✅ | List of items, each with `id`, `title`, `description`. |
| `target_id` | ⛳ optional | The candidate to optimize. If omitted, one is chosen at random (seeded). |
| `query_id` / `id` | optional | Identifier used in verbose output. |

---

## Commands

### Evaluate

```bash
# Real models (requires OPENAI_API_KEY)
python geo_eval.py evaluate --dataset eval/datasets/geo_smoke.jsonl --limit 5 --verbose

# Offline, deterministic mock (no API key, used in CI)
GEO_EVAL_MOCK=1 python geo_eval.py evaluate --dataset eval/datasets/geo_smoke.jsonl --limit 5 --verbose
```

### Optimize

`optimize` is **non-destructive by default**: it writes the best prompt to
`prompts/rewriter_user.candidate.txt` and leaves `prompts/rewriter_user.txt`
untouched. Use `--apply` to overwrite the working prompt in place.

```bash
# Writes prompts/rewriter_user.candidate.txt (safe)
GEO_EVAL_MOCK=1 python geo_eval.py optimize \
  --train eval/datasets/geo_smoke.jsonl \
  --val   eval/datasets/geo_smoke.jsonl \
  --iters 2

# Promote the candidate to the working prompt
GEO_EVAL_MOCK=1 python geo_eval.py optimize \
  --train eval/datasets/geo_smoke.jsonl \
  --val   eval/datasets/geo_smoke.jsonl \
  --iters 2 --apply
```

### Useful flags

| Flag | Default | Applies to | Meaning |
|------|---------|-----------|---------|
| `--dataset` | — | evaluate | Path to the JSONL dataset. |
| `--train` / `--val` | — | optimize | Train / validation JSONL splits. |
| `--limit N` | all | evaluate | Evaluate only the first N examples. |
| `--iters N` | 5 | optimize | Meta-optimization iterations. |
| `--apply` | off | optimize | Overwrite the working prompt in place. |
| `--ranker-model` / `--rewriter-model` / `--meta-model` | `gpt-4o` | both | Model names (or env `RANKER_MODEL`, etc.). |
| `--temperature` | 0.0 | both | Sampling temperature. |
| `--seed` | 7 | both | RNG seed for reproducibility. |
| `--verbose` | off | evaluate | Print per-example before/after ranks. |

### Environment variables

| Variable | Purpose |
|----------|---------|
| `GEO_EVAL_MOCK` | When truthy (`1`/`true`/`yes`/`on`), use the offline deterministic mock client. |
| `OPENAI_API_KEY` | Required for real runs. |
| `OPENAI_BASE_URL` | Optional OpenAI-compatible endpoint override. |
| `RANKER_MODEL` / `REWRITER_MODEL` / `META_MODEL` | Default model names. |

---

## Metrics

The summary object reports:

| Metric | Definition |
|--------|------------|
| `n` | Number of evaluated examples. |
| `avg_rank_improvement` | Mean of `rank_before - rank_after` across examples. Positive means the rewriter, on average, moved targets up. |
| `win_rate` | Fraction of examples with a strictly positive `rank_improvement` (target moved up at least one position). |
| `stderr_rank_improvement` | Standard error of the mean rank improvement (sample stddev / √n). Use it to judge whether `avg_rank_improvement` is meaningfully above zero. |

Example output:

```json
{
  "avg_rank_improvement": 2.0,
  "n": 5,
  "stderr_rank_improvement": 0.0,
  "win_rate": 1.0
}
```

> With the mock client these values are **deterministic by construction** (the
> mock rewriter always adds a ranking signal), so they verify the *pipeline*,
> not model quality. Real model runs will vary and should be reported with
> `stderr_rank_improvement` for context.

---

## Reproducible results

To reproduce the CI smoke result locally with no API key:

```bash
pip install pyyaml jsonschema
GEO_EVAL_MOCK=1 python geo_eval.py evaluate \
  --dataset eval/datasets/geo_smoke.jsonl --limit 5 --verbose
```

This is exactly what the [CI workflow](../.github/workflows/ci.yml) runs on
every pull request, alongside the skill, JSON-LD, and link validators.
