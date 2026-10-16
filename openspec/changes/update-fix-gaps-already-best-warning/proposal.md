# Change: Demote `already_best` from a verdict to a warning in section mode

## Why

In section mode, when Jev scores the best own section strictly above every cited source, the page gets status `already_best`: nothing is rewritten and the report sends the user off-page. That verdict did not survive its pre-registered test. The v4 validation (2026-10-15, `eval/jev_selection/README.md`) scored mean AUC 0.559 (95% CI 0.489–0.637) against a 0.65 gate, and when Jev said our section was best, Perplexity cited the page in only 1 of 6 queries. A signal that weak should not decide whether the page gets fixed. Owner decision 2026-10-16: keep section mode experimental, and turn `already_best` into a warning in a separate change. This is that change.

## What Changes

- **The page is always rewritten when it has candidates and sources.** When the best own section scores strictly above every source, section mode still rewrites the top-scoring own section and runs the same fidelity rules, fidelity judge and re-check. Final statuses are the existing ones (`rewritten`, `no_change_proposed`, `rejected_*`, `jev_error`, `rewriter_error`).
- **Warning instead of verdict:** the diagnosis carries `warning: "own_text_already_competitive"` (null otherwise). The page result keeps `offpage` with the fetched cited sources, and its message no longer says rewriting is unlikely to help.
- **BREAKING (experimental section-mode JSON only):** the page status `already_best` is removed from `SECTION_STATUSES`, and `diagnosis.status` reports `own_leads` in place of `already_best` (design D1, D2). Page mode, the default, is untouched.
- **CLI line:** a warned page prints `<status>: <page_id> (warning: own text already competitive; off-page: <n> cited sources)`. The `already_best: …` line goes away (design D4).
- **Docs and CHANGELOG** stop describing `already_best` as a reason not to rewrite (design D5).

## Impact

- Capability: `citation-gap-fixing`. 2 requirements modified: "Diagnosis Against Real Cited Sources" and "Report And Re-Measure List". Both deltas are written against the text from `update-jev-blind-validation`, which is complete but not yet archived (design D6).
- Code (at implementation, not in this proposal): `egeo/gaps.py` (`_section_page`, `SECTION_STATUSES`, `OFFPAGE_MESSAGE`, `SECTIONS_NOTE`, CLI line), `egeo/judge.py` (`Diagnosis.status` value and target), `tests/test_gaps_sections.py`, `tests/test_judge.py`, `USAGE.md`, `site/src/content/docs/docs/cli.md`, `CHANGELOG.md`. `eval/jev_selection` keeps its `own_wins` metric; only a docstring reference to `already_best` changes.
- Cost: pages that used to stop at `already_best` now cost one rewriter call, one fidelity-judge request and one re-check request. Under the deterministic mock, the offline end-to-end run ends in `no_change_proposed` instead of `already_best`.
- Does not decide whether Jev stays long term. That comes from `remeasure` evidence, not from another AUC run.
