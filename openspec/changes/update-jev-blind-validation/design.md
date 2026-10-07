# Design: blind Jev candidates and the v4 validation

## Context

The 2.2.0 section-mode flow is unchanged in shape: diagnose → rewrite one section → fidelity rules → fidelity judge → verify. This change touches only how Jev *sees and scores* candidates, and how that is validated. Measured facts it rests on (v2 run, 2026-09-25, 30 queries, `eval/jev_selection/README.md`):

| Scorer (leaky ids, page excerpts) | Mean AUC | 95% CI | own_accuracy |
|---|---|---|---|
| Noul | 0.637 | 0.568–0.706 | 0.50 |
| Choice | 0.619 | 0.561–0.674 | 0.17 |

In the Noul run, Jev ranked our page within the top k in 10 of 18 queries that had an own page. Perplexity cited it in 3.

## Goals / Non-Goals

- Goals: Jev cannot tell own candidates from sources. The eval runs the exact product scoring function on the exact product unit (sections). One pre-registered, fresh, single-shot validation decides the label.
- Non-Goals: making Jev predict citation (it judges text only; authority and links stay out of scope). Changing the rewriter, the fidelity rules, the fidelity judge or page mode. Flipping the `fix-gaps` default: that still needs `remeasure` evidence.

## Decisions

### D1. Blinding

- Order: sort all candidates (own sections and sources) by `sha256(f"{query}\n{candidate.text}")`, so the order depends only on the query and the text. Diagnosis and verification must present the same ids. So the order is computed **once, in diagnose**, from the *original* texts, and passed to verify as an explicit id map. It is not recomputed from the rewritten text.
- Ids: `c01`, `c02`, … in that order (two digits; up to 99 candidates, far above `MIN_SECTION_WORDS` sections plus 6 sources on any real page).
- What Jev receives: `{"query", "candidates": {cXX: text[:MAX_CANDIDATE_CHARS]}}` and questions that name only `candidates.cXX`. No labels, hosts, kinds or headings beyond what is in the text itself.
- Accepted residual leak: own section text can name the brand, for example "E-GEO". That is content, and engines see it too.
- Alternatives considered: random ids per run (not reproducible, and breaks before/after comparability); hashing ids from text (ids would change after the rewrite).

### D2. Noul replaces Choice for diagnosis and verification (owner decision required before contracts)

- `score_candidates(query, candidates, client, *, blind=True) -> Scored` sends ONE request with one Noul question per candidate. The instruction is the eval's `NOUL_INSTRUCTIONS`, moved into `egeo/judge.py`, and it references only `candidates.cXX`. It returns `{original_id: score}` plus the id map used.
- Diagnose: `best_own = max(own scores)`, `best_src = max(source scores)`. The status is `already_best` iff `best_own > best_src`, strictly. A tie is not "already best", which is the conservative choice for an off-page claim. Otherwise the target is the own section with the highest score (ties go to the earliest in document order).
- Verify: re-score with the rewritten text under the same id map. `won` iff the best own score is strictly above the best source score. Otherwise `improved` / `worse` when the target's score moves by at least `IMPROVE_DELTA = 0.05` (unchanged constant, now on the Noul scale), and `no_change` otherwise.
- Why: Noul scored better on the same data (above), each candidate gets an independent score (no forced probability split, no ties at 0), and the gate then measures the scorer that ships.
- Alternative A: keep Choice in the product and gate on Choice with blind ids. Smaller diff, but it gates on the metric the v1 review showed is dominated by ties. If the owner picks A, lanes J1 and G4 still apply, with `scorer="choice"`, and lane F4 shrinks to the `jev_validation` protocol fields.

### D3. The eval measures the product path

- `eval/jev_selection/run.py` imports `judge.score_candidates` and `judge.own_candidates`. It no longer builds its own scoring.
- Dataset v3 items add `own_source`: a repo-relative path to the page's `.md`. When it is present, own candidates are that file's sections (frontmatter removed, `MIN_SECTION_WORDS` filter), and the unit is `sections`. When it is absent, the fetched `own_url` excerpt is one own candidate and the unit is `page_excerpt`. Only `sections` items count toward own metrics in the gate report.
- AUC stays over sources only: cited = positive, uncited SERP = negative, with the same Mann-Whitney implementation and the same bootstrap CI (2000 resamples, seed 0).
- Own metrics (reported, **not gating**): `own_wins` (the product's `already_best` rule), a confusion table of `own_wins` × `egeo_cited`, and own_accuracy with a Wilson 95% interval. They are not gating because with about 3 cited positives in about 18 own queries, any gate on them is noise.
- `--ids {blind,leaky}` (default `blind`). `leaky` reproduces the 2.2.0 ids (`own_sXX` / `src_N`) and exists only for the leak diagnostic.

### D4. Pre-registration protocol (committed before any v4 number)

1. **Pre-registration commit** on the implementation branch, *before* any live run. It contains `eval/jev_selection/PREREG-v4.md` with: the query list file and its sha256; scorer `noul`; ids `blind`; unit `sections`; gate `mean_auc >= 0.65 AND n_scored >= 25` (unchanged from v2, for comparability); the Jev model string to pin (the exact `model` the API returns, recorded per request); and D5 verbatim. Its SHA is quoted in every later result.
2. **Leak diagnostic (non-gating)** on dataset v2 (`dataset-v2-2026-09-25.json`, already collected): run `--ids leaky` and `--ids blind`, same scorer, same day. Report the Δ in own-win rate, own mean rank and mean AUC. It cannot change the gate or the protocol.
3. **Fresh collection, once:** dataset v3, collected on a date after the pre-registration commit, with the same collector and the same ≥ 30 queries plus `own_source` mapping. No re-collection.
4. **One evaluation** of v3 with the pre-registered configuration. No re-runs, prompt edits or threshold changes after seeing numbers. If the run dies before producing a result (network, quota), it may be restarted; a completed run is final.

### D5. Consequences, fixed in advance

- **PASS:** `JEV_VALIDATION` gets the v4 numbers with `"status": "validated"` and `"gate_passed": true`; the `experimental` flags and the 2.2.0 "Known limitations" entry are removed. The report still states that Jev judges text competitiveness and is not a prediction of citation. The `fix-gaps` default does **not** change (that needs `remeasure` evidence).
- **FAIL:** `JEV_VALIDATION` gets the v4 numbers, `"status": "experimental"`, and the labels stay. The owner then chooses, without another run: keep section mode experimental, or remove the Jev diagnosis and verification and keep only the deterministic fidelity rules.

## Risks / Trade-offs

- Noul scores for sections of different lengths may favor long sections → `MAX_CANDIDATE_CHARS` already caps every candidate at 1500 chars; the per-section scores are reported, so a length effect is visible in the diagnostic.
- Blinding removes a bias that may have been *helping* AUC → that is the point: v4 reports what the blind product does, whatever the direction.
- 30 queries, one engine, one day (same caveats as v2) → stated in the README. The gate is about the text-competitiveness proxy, not citation.
- Report schema change on an experimental JSON → called out in the CHANGELOG under Changed, with the old and new keys.

## Migration Plan

Section mode is opt-in and experimental. There is no data migration. Consumers of `fix-gaps.json` in `sections` mode read `scores` instead of `probabilities`. Rollback = revert the change. The 2.2.0 behavior and its labels come back with it.

## Open Questions

- D2 (Noul vs Choice) needs the owner's decision before the contract tests are written.
