# Jev source-selection validation

**Question:** does Jev's Choice among candidate source excerpts rank the sources that Perplexity
actually cited above the ones it did not? This is the validation gate for section-mode
`fix-gaps` (`openspec/changes/update-fix-gaps-section-rewrite`): section mode uses Jev's choice
as a *proxy* for an answer engine's citation decision, so we measure how good that proxy is
before shipping it.

## Method

Per query (10 fixed queries from the E-GEO visibility loop):

- **Positives (label 1):** the URLs Perplexity Sonar cited in its answer.
- **Negatives (label 0):** Brave SERP top-10 for the same query, minus cited URLs.
- Each URL's page is fetched and reduced to a ≤1500-char excerpt (`egeo.sources`).
- `egeo.judge.select_best` asks Jev one Choice question over all candidates (neutral ids,
  truncated texts). We score the returned probabilities with a Mann-Whitney AUC per query and
  average. `own_rank` / `own_predicted_cited` track where E-GEO's own page lands.

## Reproduce

```bash
# 1. Collect the dataset (owner infra; the collector lives outside the repo on purpose:
#    ~/.hermes/scripts/egeo_jev_selection_collect.py — Perplexity via AIsa + Brave SERP)
python3 ~/.hermes/scripts/egeo_jev_selection_collect.py

# 2. Run the eval (live TypeSafe; ~10 requests, ≈ $0.003)
set -a; . <(grep -E '^TYPESAFE_API_KEY=' ~/.hermes/.env); set +a
python -m eval.jev_selection.run \
  --dataset ~/Sync/mkt/egeo-expansion/jev-selection/dataset-2026-09-25.json \
  --out ~/Sync/mkt/egeo-expansion/jev-selection/results-2026-09-25.json
```

Gate: `mean_auc >= 0.65` and `n_scored >= 6`.

## Result — 2026-09-25 — GATE FAIL

| Metric | Value |
|---|---|
| mean AUC | **0.6493** (gate: ≥ 0.65) |
| n_scored | 10 / 10 |
| own_accuracy | 0.30 (own predicted cited in 10/10; actually cited in 3/10) |
| Jev model | `jev-latest` (10 requests, 61,587 input tokens, $0.0026) |

Per-query AUC ranged from 0.286 (`best answer engine optimization tools for developers`,
below random) to 0.881 (`best GEO tools 2026`). Results file:
`~/Sync/mkt/egeo-expansion/jev-selection/results-2026-09-25.json`.

## Caveats

- 10 queries, one answer engine (Perplexity Sonar via AIsa), one day, one run.
- Candidates are 1500-char excerpts, not full pages; the engine sees more than Jev did.
- SERP negatives come from Brave's index, not Perplexity's own retrieval.
- `own_predicted_cited` fired on every query, so it carried no signal in this sample.

**Decision:** the proxy did not clear the gate. Section mode stays in review until the reviewer
decides whether to tune the proxy, rerun on a different day/engine, or drop the Jev gate.
