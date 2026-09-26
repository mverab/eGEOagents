# Change: Blind Jev candidates and a pre-registered validation of the path section mode actually runs

## Why

In 2.2.0 section mode ships with Jev labeled experimental, and its validation number is *provisional*, for three measured reasons:

1. **The candidate ids leak ownership.** Jev sees `own_s03` next to `src_1` (product), and `own` next to `src_1` (eval). The model can tell which text is ours. The v2 run showed exactly the bias this invites: Jev put our page in the top k for 10 of 18 queries, while Perplexity cited it in 3.
2. **The eval does not measure the product.** The gate was decided by the Noul scorer on full-page excerpts. Section mode diagnoses with a single Choice question over *sections*. The number in the report (Choice, AUC 0.62, own accuracy 0.17) comes from a configuration the product does not run either: page excerpts instead of sections, and leaky ids.
3. **The Choice scorer is a weak basis for a gate.** One Choice question concentrates probability on one or two candidates, and ties near 0 dominate the AUC (v1 finding, `eval/jev_selection/README.md`). Noul scored better on the same data: AUC 0.637 against 0.619, and own accuracy 0.50 against 0.17.

Until the eval measures the exact code path section mode runs, with ids that do not reveal ownership, no result, pass or fail, says whether `already_best` (off-page) can be trusted.

## What Changes

- **Blind candidates (product and eval):** Jev sees neutral ids `c01`, `c02`, … assigned after a deterministic shuffle seeded by the query. The mapping back to own section or source stays in code. Diagnosis and verification use the same ids and the same order.
- **One scoring primitive, Noul (owner decision required, see design D2):** section mode scores each candidate with an independent Noul question (one request per decision), replacing the single Choice question for diagnosis and verification. `already_best` requires the best own section to score *strictly* above every source. The fidelity judge stays a Choice question.
- **The eval calls the product function.** `eval/jev_selection` imports `egeo.judge.score_candidates` and builds own candidates with `egeo.judge.own_candidates` from the page's Markdown source (`own_source`), so the gate measures what ships. It keeps a `--ids leaky` switch only to quantify the leak on the old dataset.
- **Report schema (experimental feature):** diagnosis and verification report `scores` (Noul, 0–1) and `"scorer": "noul"` in place of `probabilities` / `confidence`. `jev_validation` records the protocol (`"protocol": "v4"`, `"ids": "blind"`, `"unit": "sections"`).
- **Pre-registered v4 validation:** the protocol, the query list (content hash) and the gate are committed *before* any v4 number exists. First, a non-gating leak diagnostic on dataset v2 (leaky vs blind ids). Then one fresh collection and one evaluation. The consequences of pass and fail are fixed in advance (design D5).
- **Mock mode:** the mock Noul answer becomes word-overlap based (today it is a constant 0.9) so offline runs exercise diagnosis.

## Impact

- Capability: `citation-gap-fixing`. 4 requirements modified (Report And Re-Measure List; Diagnosis Against Real Cited Sources; Verification Re-Judges And Rejects Worse Rewrites; Jev Selection Is Validated Against A Live Engine). 1 added (Jev Candidates Are Blind).
- Code: `egeo/judge.py` (blinding and `score_candidates`, Noul diagnose and verify), `egeo/jev.py` (mock Noul), `egeo/gaps.py` (report keys, `JEV_VALIDATION` after the run), `eval/jev_selection/run.py` (product path, `own_source`, `--ids`).
- **Breaking for consumers of the experimental section-mode JSON:** `probabilities` / `confidence` are replaced by `scores` / `scorer`. Page mode (the default) is untouched.
- Cost: unchanged order of magnitude. One Jev request per diagnosis or verification (≈ $0.0002 per query at 2.2.0 prices).
- Plan: `docs/plans/2026-09-26-jev-blind-validation-plan-v4.md`.
