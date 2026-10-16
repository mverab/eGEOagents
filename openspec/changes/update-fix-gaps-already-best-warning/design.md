# Design: `already_best` becomes a warning

## Context

Section mode today (`egeo/gaps.py::_section_page`, after `update-jev-blind-validation`):

1. `judge.diagnose` scores every own section and every fetched source with a Noul question under blind ids.
2. If the best own score is strictly above the best source score, `diagnose` returns status `already_best` with `target_id = None`. The page stops there with status `already_best` and an `offpage` object (reason, message, cited source URLs). The CLI prints `already_best: <page_id> (off-page: <n> cited sources)`.
3. Otherwise the top-scoring own section is rewritten, then checked by the fidelity rules, the fidelity judge and the re-check.

The v4 validation failed (mean AUC 0.559, 95% CI 0.489–0.637, gate 0.65). Among the 6 queries where Jev ranked our section above every source, Perplexity cited us in 1. So step 2 skips a fix on a signal that the evidence does not support. Owner decision 2026-10-16: keep section mode experimental and demote `already_best` to a warning.

## Goals / Non-Goals

- Goals: a page whose text Jev rates as leading still gets its top section rewritten through the unchanged gates. The report still says that Jev rated the text as competitive, and it still lists the cited sources for off-page work. Each page has one status, and that status is its real outcome.
- Non-Goals: deciding whether to keep or remove Jev (that comes from `remeasure` evidence); changing the scorer, the blind ids, the fidelity rules or thresholds, `IMPROVE_DELTA`, the eval, page mode, or the `fix-gaps` default; running another validation.

## Decisions

### D1. The `already_best` page status is removed, not kept as a flag (owner decision point 1)

- `already_best` leaves `SECTION_STATUSES`. A page whose own text leads goes through the same path as a losing page and ends in one of the existing statuses: `rewritten`, `no_change_proposed`, `rejected_fidelity_rules`, `rejected_fidelity_judge`, `rejected_worse`, `jev_error`, `rewriter_error`.
- Why: `status` is the page's outcome, one value per page, and consumers branch on it. If `already_best` stayed as a status while the page was also rewritten, the status would hide whether the rewrite was written or rejected. Moving the signal into its own field keeps "what happened" (status) apart from "what Jev thought" (warning).
- Alternative A, keep `already_best` as the status and also rewrite: rejected, because the status would no longer say whether anything was written.
- Alternative B, combined statuses (`rewritten_own_leads`, `rejected_worse_own_leads`, …): rejected, because it doubles the status set for one bit of information.
- Alternative C, a top-level boolean `page.already_best: true` next to the real status: viable, but it keeps the verdict name the evidence withdrew. D2 uses a neutral name instead.

### D2. Diagnosis shape (owner decision point 2: the value name)

- `judge.Diagnosis.status` is `"loses"` or `"own_leads"` (renamed from `"already_best"`; `no_own_candidates` and `no_competitor_sources` stay). In both cases `target_id` is the own section with the highest score, with ties going to the earliest section, which is today's target rule for `loses`.
- Page `diagnosis` gains a `warning` key that is always present: `"own_text_already_competitive"` when `diagnosis.status == "own_leads"`, otherwise `null`. `target_section` is filled in both cases.
- Why rename: `already_best` states a conclusion that the validation did not support. `own_leads` describes what Jev's scores show, nothing more. If the owner prefers the smaller break, `diagnosis.status` can keep the value `"already_best"` while the page status still goes away. The warning and the rewrite stay the same either way.

### D3. `offpage` follows the warning, whatever the outcome

- `offpage` is non-null exactly when `diagnosis.warning` is set, whatever the final page status. Its shape is unchanged: `{"reason", "message", "sources"}`, where `sources` holds the URL of every successfully fetched doc in fetch order.
- `offpage.reason` becomes `"own_text_already_competitive"`, the same string as the warning, so there is one code instead of two (today: `text_already_competitive`).
- New `OFFPAGE_MESSAGE` (it no longer says rewriting is unlikely to help):
  > Jev (experimental; it failed its validation) scores your best section above the sources the answer engine cited. That signal is weak, so the section was still rewritten. If re-measuring shows the query is still not cited, the gap may be off-page: get your page mentioned or linked by these sources.
- Verification is unchanged. On a page that already led, `won` after the rewrite only says that the own text still leads; the report shows `score_before` and `score_after` so the change is visible. `rejected_worse` still guards against degrading text that was already competitive.

### D4. CLI line

- A page with a warning prints: `<status>: <page_id> (warning: own text already competitive; off-page: <n> cited sources)`, for example `rewritten: compare (warning: own text already competitive; off-page: 1 cited sources)`.
- Every other page prints `<status>: <page_id>` as today. The `already_best: …` line is removed. `--json` output is the report itself, so D1–D3 cover it.

### D5. JSON compatibility and CHANGELOG

Only section-mode output changes (`fix-gaps.json` with `"mode": "sections"`, and the per-page `diagnosis.json`). Page mode and the dry-run JSON do not change.

| Field | Before | After |
|---|---|---|
| `pages[].status` | may be `already_best` | never `already_best`; the real outcome |
| `pages[].diagnosis.status` | `loses` / `already_best` | `loses` / `own_leads` |
| `pages[].diagnosis.warning` | absent | `"own_text_already_competitive"` or `null` |
| `pages[].diagnosis.target_section` | `null` when own text led | always set when a diagnosis exists |
| `pages[].fidelity`, `verification`, `output_file`, `diff_file` | `null` when own text led | filled as for any rewritten page |
| `pages[].offpage` | set only for `already_best` | set whenever the warning is set |
| `pages[].offpage.reason` | `text_already_competitive` | `own_text_already_competitive` |
| `pages[].offpage.message` | "…rewriting it is unlikely to help…" | D3 text |

This is a breaking change for consumers of the experimental section-mode JSON, released in the next minor version like the `update-jev-blind-validation` break. CHANGELOG entry under `[Unreleased]` → `### Changed`:

> - **Breaking (experimental section-mode JSON only):** `already_best` is now a warning, not a verdict (owner decision 2026-10-16, openspec `update-fix-gaps-already-best-warning`). When Jev scores your best section above every cited source, section mode still rewrites that section through the same fidelity rules, fidelity judge and re-check, and the page gets its real outcome status. `diagnosis.warning` is `"own_text_already_competitive"`, `diagnosis.status` is `"own_leads"` (was `"already_best"`), and `offpage` still lists the cited sources (reason `own_text_already_competitive`). The page status `already_best` and its CLI line are gone. Page mode, the default, is unchanged.

The `### Known limitations` line "Treat `already_best` as a weak signal and confirm with `remeasure`" becomes "The `own_text_already_competitive` warning is a weak signal; confirm with `remeasure`."

### D6. Sequencing with `update-jev-blind-validation`

`update-jev-blind-validation` is complete but not archived, so `openspec/specs/citation-gap-fixing/spec.md` still has the 2.2.0 Choice wording. This change's deltas are written against the text from `update-jev-blind-validation`, which describes what the code does. Archive `update-jev-blind-validation` first (task 0.2). Then this change's MODIFIED requirements replace those versions when it is archived.

## Risks / Trade-offs

- A rewrite can degrade text that already competes. Mitigation: the deterministic fidelity rules, the fidelity judge, and `rejected_worse` on a drop of 0.05 or more apply unchanged, and source files are never modified.
- Pages that used to stop now cost about one rewriter call plus two Jev requests (≈ $0.0004 at 2.2.0 Jev prices plus the rewriter call). This is acceptable because section mode is opt-in.
- Users who used `already_best` to skip pages lose that skip. They can filter on `diagnosis.warning` instead. Section mode is labeled experimental, so the shape is not yet stable.
- `remeasure` will now include re-checks of pages that Jev thought were already competitive. That is the evidence the owner asked for to decide on Jev.
