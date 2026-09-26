# Mini-plan v2 — fix the validation eval and reframe section mode

Follows the review of the v1 hand-back (PR #59, head `5117feb`). The v1 code is approved (identical to the
reference, 148/148). This round changes **one measurement** and **one product behavior**. Golden rules from
`2026-09-25-fix-gaps-sections-plan.md` §0 still apply — above all: **do not edit tests**. The new tests were
verified against a private reference implementation (156/156 pass); on this branch 15 are RED.

## Why (reviewer findings, measured)

1. **The v1 metric was flawed by design (reviewer's mistake, not Jev's).** One Choice question spreads
   probability over 1–2 candidates: 44% of candidates got p < 0.01, so AUC was dominated by ties at ~0, and
   `own_predicted_cited` compared against the *minimum* cited probability (0.0 in 9/10) — always True.
2. **0.65 was inside the noise.** Re-running Jev on the same data: mean AUC 0.6493 → 0.6272.
3. **Real signal:** Jev picked our page in 5–6/10 queries; Perplexity cited us in 3/10. Jev judges *text*;
   Perplexity also weighs *authority*. So Jev is a **text-competitiveness** judge, not a citation predictor —
   the product must say so, and use it that way.

## Lanes

| Lane | Files | Tests | Parallel |
|---|---|---|---|
| G2 — eval v2 (code) | `eval/jev_selection/run.py` | `tests/test_jev_selection_eval.py` | yes |
| F2 — off-page reframe | `egeo/gaps.py` | `tests/test_gaps_sections.py` | yes |
| G3 — eval v2 live run | collector outside repo + README | — | after G2 |
| H — docs | as in the main plan, plus the framing below | `site` build + `verify.sh` | after G3 |

### Lane G2 — `eval/jev_selection/run.py`

The module docstring is the contract (v2 section). Implement `score_candidates_noul`, `bootstrap_ci`, and the
new `scorer` parameter of `score_query` / `run`; add `--scorer` to `main()` and print the CI.

Pitfalls:
- **One** Jev request per query for the Noul scorer, with **one Noul question per candidate**, question id =
  candidate id. Do not send one request per candidate.
- `own_rank` counts candidates with a **strictly** higher score; `own_predicted_cited = own_rank <= n_pos`.
- Rename `own_prob` → `own_score` everywhere (results keys and README).
- `mean_auc_ci` is a **list** `[low, high]` (JSON), or None.
- The skipped dict now carries `"scorer"`.
- `GATE_MIN_QUERIES` is 25 and `NOUL_INSTRUCTIONS` is fixed text — do not edit constants.

### Lane F2 — `egeo/gaps.py`

The contract comment above `OFFPAGE_REASON` is the spec:
- Every page dict gets `"offpage"`. For `already_best` it is
  `{"reason": OFFPAGE_REASON, "message": OFFPAGE_MESSAGE, "sources": [urls of ok fetched docs, fetch order]}`;
  for every other status `None`.
- CLI line for `already_best`: `already_best: <page_id> (off-page: <n> cited sources)`.
- `SECTIONS_NOTE` was already rewritten in the scaffold ("text competitiveness … not a prediction of citation").
  Do not change it.

### Lane G3 — eval v2 live run (VPS). Pre-registered: run ONCE.

1. Extend the collector `~/.hermes/scripts/egeo_jev_selection_collect.py` with `--queries <file>` reading
   `~/Sync/mkt/egeo-expansion/jev-selection/queries-v2.json` (30 items `{query, own_url|null}`, already written;
   do **not** edit it). Keep everything else identical to v1 (Perplexity sonar via AIsa, Brave top 10,
   2 s spacing, abort if > half of the answers are empty). `own_url: null` → `""` in the dataset.
   Output: `dataset-v2-YYYY-MM-DD.json`.
2. Run the eval **once** with the default scorer:
   `python -m eval.jev_selection.run --dataset …/dataset-v2-YYYY-MM-DD.json --out …/results-v2-YYYY-MM-DD.json`
3. Also run `--scorer choice` on the same dataset → `results-v2-choice-YYYY-MM-DD.json` (comparison only;
   the gate is decided by the Noul run).
4. Update `eval/jev_selection/README.md`: v1 result and why it was replaced (the three findings above), the
   v2 method, the pre-registration, v2 results (mean AUC + 95% CI, n_scored, own_accuracy, both scorers),
   date, model, and the caveat that Jev measures text competitiveness, not citation.
5. **STOP and hand back** whatever the result is. **No re-runs, no prompt or threshold changes** after seeing
   numbers. Budget: 30 Perplexity + 30 Brave calls + ~60 Jev requests (< $0.05).

### Lane H — docs (after G3; same list as the main plan) with this framing

- Describe the Jev step as **"does your text compete?"** and `already_best` as **"your text already wins; the
  gap is off-page — here are the sources the engine cited"**.
- Never describe Jev or the verification outcome as a prediction of citation. Cite the v2 AUC and its CI.

## Hand-back (to the reviewer)

1. Branch head SHA and `pytest tests/ -q` summary line (expect 156 passed).
2. `results-v2-*.json` (both scorers), the updated README, the dataset file name.
3. Anything you could not do, and anything you believe is wrong in a test or this plan.

## Decision rule after G3 (for the reviewer and owner, not the implementer)

- **Noul mean AUC ≥ 0.65 with n ≥ 25:** Jev is a validated text-competitiveness triage; proceed to Lane H,
  dogfood, and review for merge.
- **Below:** section mode still ships its fidelity gates (they need no validation), but the Jev diagnosis and
  verification are labeled experimental in docs and report notes, or removed — owner decides.
