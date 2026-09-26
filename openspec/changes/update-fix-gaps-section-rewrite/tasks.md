Implementation plan with exact signatures, test ownership and waves: `docs/plans/2026-09-25-fix-gaps-sections-plan.md`.

## 1. Wave 1 — independent modules (parallel)
- [ ] 1.1 `egeo/sections.py` (tests: `tests/test_sections.py`)
- [ ] 1.2 `egeo/fidelity.py` (tests: `tests/test_fidelity.py`)
- [ ] 1.3 `egeo/sources.py` (tests: `tests/test_sources.py`)
- [ ] 1.4 `egeo/jev.py` + `egeo/judge.py` (tests: `tests/test_jev.py`, `tests/test_judge.py`)
- [ ] 1.5 `egeo/section_rewriter.py` + prompts + packaged copies (tests: `tests/test_section_rewriter.py`)

## 2. Wave 2 — validation gate
- [ ] 2.1 `eval/jev_selection/run.py` (tests: `tests/test_jev_selection_eval.py`)
- [ ] 2.2 Collect dataset on the VPS (Perplexity citations + Brave SERP) and run the eval live
- [ ] 2.3 Report mean AUC; STOP for review if < 0.65

## 3. Wave 3 — integration
- [ ] 3.1 `egeo/gaps.py` section mode + `egeo/cli.py` flags (tests: `tests/test_gaps_sections.py`)
- [ ] 3.2 Docs: CLI reference, USAGE.md, CHANGELOG `[Unreleased]`
- [ ] 3.3 Real dogfood run on E-GEO's gaps; hand outputs to review
