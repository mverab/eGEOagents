# Jev source-selection validation

**Question:** does Jev score candidate sources the way Perplexity actually cites them? This is the
validation gate for section-mode `fix-gaps` (`openspec/changes/update-fix-gaps-section-rewrite`).
Section mode uses Jev to judge **text competitiveness** — whose text best answers the query — *not*
to predict citations (Jev sees text only; engines also weigh authority and links).

## v1 → v2 (2026-09-25 review)

v1 (one Choice question over all candidates, n=10) reported mean AUC 0.6493 against a 0.65 gate and
was replaced for three measured reasons:

1. **The metric was flawed by design.** One Choice spreads probability over 1–2 candidates: 44% of
   candidates got p < 0.01, so AUC was dominated by ties at ~0, and `own_predicted_cited` (compared
   against the *minimum* cited probability, 0.0 in 9/10 queries) was always True.
2. **0.65 was inside the noise.** Re-running Jev on the same data moved mean AUC 0.6493 → 0.6272.
3. **Real signal, reframed.** Jev picked our page in 5–6/10 queries where Perplexity cited us in
   3/10 — Jev judges *text*, Perplexity also weighs *authority*. So Jev is a text-competitiveness
   judge, not a citation predictor, and the product speaks of it that way.

## v2 method

Per query (30 pre-registered queries, `~/Sync/mkt/egeo-expansion/jev-selection/queries-v2.json`):

- **Positives:** URLs Perplexity Sonar cited; **negatives:** Brave SERP top-10 minus cited.
- Each URL fetched once, reduced to a ≤1500-char excerpt (`egeo.sources`).
- **Noul scorer (default, gate-deciding):** ONE Jev request per query with one Noul question per
  candidate (`NOUL_INSTRUCTIONS`, "would an engine cite candidates.X…"). AUC over the per-candidate
  scores; `own_predicted_cited = own_rank <= n_cited`.
- **Choice scorer (comparison only):** v1's single Choice question, kept for reference.
- `mean_auc_ci`: bootstrap 95% CI (2000 resamples, seed 0).

**Pre-registration:** scorer `noul`, gate `mean_auc >= 0.65` with `n_scored >= 25`, dataset collected
once, evaluated once. No re-runs, prompt or threshold changes after seeing numbers.

## Reproduce

```bash
# 1. Collect the dataset (owner infra; the collector lives outside the repo on purpose:
#    ~/.hermes/scripts/egeo_jev_selection_collect.py — Perplexity via AIsa + Brave SERP)
python3 ~/.hermes/scripts/egeo_jev_selection_collect.py \
  --queries ~/Sync/mkt/egeo-expansion/jev-selection/queries-v2.json

# 2. Run the eval (live TypeSafe; ~30 requests, ≈ $0.007)
set -a; . <(grep -E '^TYPESAFE_API_KEY=' ~/.hermes/.env); set +a
python -m eval.jev_selection.run \
  --dataset ~/Sync/mkt/egeo-expansion/jev-selection/dataset-v2-2026-09-25.json \
  --out ~/Sync/mkt/egeo-expansion/jev-selection/results-v2-2026-09-25.json
# comparison only (does not decide the gate):
python -m eval.jev_selection.run --dataset … --out … --scorer choice
```

## Result — 2026-09-25 — GATE FAIL

| Metric | Noul (gate) | Choice (comparison) |
|---|---|---|
| mean AUC | **0.6369** | 0.6194 |
| 95% CI | [0.568, 0.706] | [0.561, 0.674] |
| n_scored | 30/30 | 30/30 |
| own_accuracy | 0.50 (own in 18 queries) | 0.167 |
| Jev usage | 30 req, 171,920 in-tokens, $0.0072 | 30 req, 169,383 in-tokens, $0.0071 |

Files: `~/Sync/mkt/egeo-expansion/jev-selection/dataset-v2-2026-09-25.json`,
`results-v2-2026-09-25.json` (noul), `results-v2-choice-2026-09-25.json` (choice).

Worst noul AUCs: `best answer engine optimization tools for developers` 0.12, `AI agent memory
frameworks open source` 0.25, `does llms.txt help SEO` 0.26. Best: the head GEO-tools query 1.00,
`open source AEO tools` 0.88, `what is answer engine optimization` 0.83.

## Caveats

- 30 queries, one answer engine (Perplexity Sonar via AIsa), one day, one run.
- Candidates are 1500-char excerpts; the engine sees full pages plus authority signals Jev never sees.
- SERP negatives come from Brave's index, not Perplexity's own retrieval.
- Noul fixes the v1 pathologies (no forced probability split, rank-based own metric) and beats Choice,
  but still does not clear the gate.

**Decision:** the gate failed on the pre-registered run. Per the v2 plan, section mode keeps its
deterministic fidelity gates (they need no validation); whether the Jev diagnosis/verification steps
ship labeled *experimental* or are removed is the owner's call.
