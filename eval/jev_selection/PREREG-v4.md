# Pre-registration — Jev validation v4

**Status: DRAFT — not registered yet.** This file is registered when the owner approves it and it is
committed with this line changed to `Status: REGISTERED`. That commit's SHA is the `--prereg-sha`
of every v4 run. No live v4 run (leak diagnostic included) happens before that commit.
After it, nothing in this file changes.

Change: `openspec/changes/update-jev-blind-validation` (design D3–D5).
Plan: `docs/plans/2026-09-26-jev-blind-validation-plan-v4.md` §3–§4.

## What is measured

Whether `egeo.judge.score_candidates`, the function section mode runs to diagnose and verify, scores
the sources Perplexity cites above the sources it does not cite, when Jev cannot tell which
candidates are ours.

| Setting | Value |
|---|---|
| Scorer | `noul` (one independent Noul question per candidate, `egeo.judge.NOUL_INSTRUCTIONS`) |
| Ids | `blind` (`c01`, `c02`, … ordered by `sha256(query + "\n" + text)`) |
| Unit | `sections` for items with `own_source`, `page_excerpt` otherwise (2 items) |
| Candidate cap | `egeo.judge.MAX_CANDIDATE_CHARS` = 1500 chars; `MIN_SECTION_WORDS` = 30 |
| Sources per class | `MAX_PER_CLASS` = 8 cited, 8 uncited |
| Metric | mean per-query ROC AUC over sources (cited = 1, uncited SERP = 0), Mann-Whitney, ties 0.5 |
| Interval | bootstrap 95% CI, 2000 resamples, seed 0 |
| Jev model | the request asks for `jev-latest`; the exact model string the API returns is recorded per query (`jev_model`) and per run (`jev_models_returned`) |

## Queries

`eval/jev_selection/queries-v3.json`: the same 30 queries as v2
(`~/Sync/mkt/egeo-expansion/jev-selection/queries-v2.json`), in the same order, with the same
`own_url`, plus `own_source` (the page's Markdown under `site/src/content/docs/`) for the 16 queries
whose own page has a local source. The 2 own pages without one (`https://egeoagents.com/` and the
GitHub repository) stay `page_excerpt` and are excluded from own metrics.

sha256 of `queries-v3.json`: `094e056c7ee12b4f75af36b57a8cfb5a7639f303bf526d8d03c0e2f5d4fb1718`

`own_source` is read from a checkout of `main` at the last commit before the v3 collection started
(`git rev-list -1 --before="<collection start, UTC>" main`). That SHA is recorded in the README next
to the result, so the sections scored are the ones that were live when Perplexity answered.

## Gate

`gate_passed = mean_auc >= 0.65 AND n_scored >= 25`, on the blind-id run of dataset v3, with this
file's commit SHA passed as `--prereg-sha`. Unchanged from v2, for comparability.

Own metrics (`own_wins` × `egeo_cited` confusion table, `own_accuracy` with a Wilson 95% interval,
sections items only) are reported and **do not gate**.

## Steps, each run once

1. **Leak diagnostic (non-gating)** on `dataset-v2-2026-09-25.json`: `--ids leaky`, then `--ids blind`,
   same day. Report Δ own-win rate, Δ mean own rank and Δ mean AUC. It changes nothing in this file.
2. **Collect dataset v3 once**, on a date after the registering commit, with
   `~/.hermes/scripts/egeo_jev_selection_collect.py --queries eval/jev_selection/queries-v3.json`
   (the collector must copy `own_source` into each item). Save it as `dataset-v3-<date>.json`.
   No re-collection.
3. **Evaluate once:**
   `python -m eval.jev_selection.run --dataset …/dataset-v3-<date>.json --out …/results-v3-<date>.json --prereg-sha <SHA> --repo-root <checkout>`.
   A run that dies before writing a result (network, quota) may be restarted. A completed run is
   final. No re-runs, prompt edits or threshold changes after seeing numbers.

## Consequences, fixed in advance (design D5, verbatim)

- **PASS:** `JEV_VALIDATION` gets the v4 numbers with `"status": "validated"` and `"gate_passed": true`; the `experimental` flags and the 2.2.0 "Known limitations" entry are removed. The report still states that Jev judges text competitiveness and is not a prediction of citation. The `fix-gaps` default does **not** change (that needs `remeasure` evidence).
- **FAIL:** `JEV_VALIDATION` gets the v4 numbers, `"status": "experimental"`, and the labels stay. The owner then chooses, without another run: keep section mode experimental, or remove the Jev diagnosis and verification and keep only the deterministic fidelity rules.
