Implementation plan with exact signatures, test ownership and waves: `docs/plans/2026-09-25-fix-gaps-sections-plan.md`.
v2 (metric fix + reframe): `docs/plans/2026-09-25-fix-gaps-sections-plan-v2.md`.
v3 (ship with Jev labeled experimental, owner decision A): `docs/plans/2026-09-25-fix-gaps-sections-plan-v3.md`.

## 1. Wave 1 — independent modules (parallel)
- [x] 1.1 `egeo/sections.py` (tests: `tests/test_sections.py`)
- [x] 1.2 `egeo/fidelity.py` (tests: `tests/test_fidelity.py`)
- [x] 1.3 `egeo/sources.py` (tests: `tests/test_sources.py`)
- [x] 1.4 `egeo/jev.py` + `egeo/judge.py` (tests: `tests/test_jev.py`, `tests/test_judge.py`)
- [x] 1.5 `egeo/section_rewriter.py` + prompts + packaged copies (tests: `tests/test_section_rewriter.py`)

## 2. Wave 2 — validation gate
- [x] 2.1 `eval/jev_selection/run.py` (tests: `tests/test_jev_selection_eval.py`)
- [x] 2.2 Collect dataset on the VPS (Perplexity citations + Brave SERP) and run the eval live
- [x] 2.3 Report mean AUC; STOP for review if < 0.65 — v1 0.6493 (n=10) FAIL; v2 pre-registered noul 0.637 (CI 0.568–0.706, n=30) FAIL → owner decision: ship labeled experimental (option A)

## 3. Wave 3 — integration
- [x] 3.1 `egeo/gaps.py` section mode + `egeo/cli.py` flags (tests: `tests/test_gaps_sections.py`) — incl. off-page reframe (v2) and experimental labeling with `jev_validation` numbers (v3)
- [x] 3.2 Docs: CLI reference, USAGE.md, CHANGELOG `[Unreleased]`
- [x] 3.3 Real dogfood run on E-GEO's gaps; hand outputs to review
- [x] 3.4 Review fixes: report the choice scorer's numbers (the one section mode runs, on full-page excerpts), `rewriter_error` status + `OPENAI_API_KEY` pre-check

## 4. Follow-ups (not in this change)
- [x] 4.1 Moved to change `update-jev-blind-validation` (neutral candidate ids, product-path eval, fresh pre-registered run). Shipped in 2.2.0 with the leak disclosed under CHANGELOG "Known limitations".
- [x] 4.2 Owner decision 2026-09-26: `--mode page` stays the `fix-gaps` default; `sections` is opt-in and labeled experimental. Flipping the default to `sections` is pending `remeasure` evidence.
