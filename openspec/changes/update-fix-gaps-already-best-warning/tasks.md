## 0. Approval and sequencing
- [x] 0.1 Owner approves this proposal and decides D1 (remove the `already_best` page status, recommended, vs keep it as a non-skipping flag) and D2 (`diagnosis.status` value `own_leads`, recommended, vs keeping `already_best`) — approved 2026-10-16: D1 remove, D2 `own_leads`, D3–D6 as recommended
- [x] 0.2 Archive `update-jev-blind-validation` so `openspec/specs/citation-gap-fixing/spec.md` matches the code before this change is applied (design D6)

## 1. Contracts (RED first; no `egeo/` change in this step)
- [x] 1.1 `tests/test_gaps_sections.py`: replace `test_already_best_does_not_rewrite` with `test_own_leads_still_rewrites_with_warning`. Script `ScriptedJev(WON, FAITHFUL, WON)` with `GOOD_REWRITE`. Expect status `rewritten`, rewrite called once with the `Tools` section, `diagnosis.status == "own_leads"`, `diagnosis.warning == "own_text_already_competitive"`, `diagnosis.target_section.id == "s01"`, `diagnosis.experimental is True`, `offpage == {"reason": "own_text_already_competitive", "message": gaps.OFFPAGE_MESSAGE, "sources": ["https://toolradar.com/x"]}`, the rewritten file and `section.diff` written, and `diagnosis.json` saved with the same `offpage`
- [x] 1.2 `test_own_leads_rejected_keeps_warning`: with `ScriptedJev(WON, FAITHFUL, worse)` the status is `rejected_worse`, no rewritten file is written, and `diagnosis.warning` and `offpage` are still set. Add one case for `rejected_fidelity_rules` (`BAD_REWRITE`) with the same warning assertions
- [x] 1.3 `test_loses_has_no_warning`: on the existing `LOSES` path, `diagnosis.warning is None`, `diagnosis.status == "loses"` and `offpage is None`
- [x] 1.4 `test_section_statuses_drop_already_best`: `"already_best" not in gaps.SECTION_STATUSES`, and no page in any test report has status `already_best`
- [x] 1.5 Update `test_cli_mock_end_to_end_offline`: under the mock, status `no_change_proposed` (the mock rewriter returns the section unchanged), the warning is set, and stdout contains `no_change_proposed: compare (warning: own text already competitive; off-page: 1 cited sources)` and no `already_best:` line
- [x] 1.6 `tests/test_judge.py`: `test_diagnose_already_best_needs_strictly_higher_score` becomes `test_diagnose_own_leads_needs_strictly_higher_score`. Expect status `own_leads` with `target_id == "own_s01"` (the best own section). The tie case stays `loses`
- [x] 1.7 Run `pytest tests/test_gaps_sections.py tests/test_judge.py` and confirm the new contracts fail for the expected reason (status/warning mismatch, not import errors); commit RED

## 2. Implementation
- [x] 2.1 `egeo/judge.py`: `diagnose` returns `Diagnosis(scored, best_own_id, "own_leads")` when the own text leads; update the docstring and the `Diagnosis.status` comment
- [x] 2.2 `egeo/gaps.py`: drop `already_best` from `SECTION_STATUSES`; `_section_page` only stops early when `diag.scored is None`; set `diagnosis.warning` and `offpage` per design D2–D3; new `OFFPAGE_REASON` and `OFFPAGE_MESSAGE`; update the `SECTIONS_NOTE` wording ("Treat the `own_text_already_competitive` warning and the re-check as weak signals"); CLI line per D4
- [x] 2.3 `eval/jev_selection/run.py`: the docstring refers to the product's `own_leads` rule (no metric change)
- [x] 2.4 Full suite green (`pytest`)

## 3. Docs
- [x] 3.1 `USAGE.md` and `site/src/content/docs/docs/cli.md`: remove `already_best` from the status lists and describe the warning and the off-page sources (rewrite still attempted)
- [x] 3.2 `CHANGELOG.md` `[Unreleased]`: the D5 entry under `### Changed` and the reworded Known-limitations line
- [x] 3.3 `openspec validate update-fix-gaps-already-best-warning --strict` passes
