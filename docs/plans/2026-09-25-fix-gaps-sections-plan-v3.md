# Mini-plan v3 — ship section mode with Jev labeled experimental (owner decision: option A)

Follows the v2 hand-back (head `1bf8a53`). v2 code approved (implemented from contracts, 156/156, no test
edited). The pre-registered v2 run did **not** pass the gate:

| Scorer | Mean AUC | 95% CI | own_accuracy | Gate (≥ 0.65, n ≥ 25) |
|---|---|---|---|---|
| noul (decides) | 0.637 | 0.568–0.706 | 0.50 | fail |
| choice (comparison) | 0.619 | 0.561–0.674 | 0.17 | fail |

Reading: a real but weak signal (the whole CI is above 0.5), below the pre-registered bar; Jev overrates our text
(predicted our page citable in 10/18 queries; Perplexity cited it in 3). **Owner decision (A):** keep Jev, label
it experimental, and use it where it judges text: choosing which own section to rewrite, the fidelity judge,
the off-page hint. Proof of impact comes from re-measuring with the tracker (`remeasure`), never from Jev.

Golden rules from the main plan §0 still apply: **do not edit tests**. Contract verified against a private
reference (156/156); on this branch 2 tests are RED.

## Lanes

| Lane | Files | Tests | Order |
|---|---|---|---|
| F3 — experimental labeling | `egeo/gaps.py` | `tests/test_gaps_sections.py` | first |
| H — docs | `site/src/content/docs/docs/cli.md`, `USAGE.md`, `CHANGELOG.md`, `openspec/changes/update-fix-gaps-section-rewrite/tasks.md` | `npm run build && ./verify.sh` | after F3 |
| D — dogfood (VPS) | outputs outside the repo | — | after F3 |

### Lane F3 — `egeo/gaps.py`

The constants `SECTIONS_NOTE`, `JEV_VALIDATION`, `OFFPAGE_MESSAGE` are already written (contract comment
above `JEV_VALIDATION`) — do not change their text. Wire them:
- Add `"jev_validation": dict(JEV_VALIDATION)` to the section-mode report.
- Add `"experimental": True` to every non-null `diagnosis` dict (both the `already_best` branch and the
  `loses` branch) and to the non-null `verification` dict.
- Nothing else changes.

### Lane H — docs (framing is mandatory)

In the `egeo fix-gaps` section of the CLI reference and in `USAGE.md`:
- Section mode is the default; `--mode page` is the legacy whole-page rewrite.
- Flow: pick the own section that loses → rewrite only it → **fidelity rules** (heading, links, numbers,
  tables, code, length) → Jev fidelity judge → Jev re-check. Statuses list (from `SECTION_STATUSES`).
- A clearly marked **"Experimental: the Jev comparison"** box: what it measures (text competitiveness),
  what it does not (authority, links, citation), the v2 numbers (AUC 0.64, 95% CI 0.57–0.71, 30 queries,
  2026-09-25, below the 0.65 bar), link to `eval/jev_selection/README.md`.
- `already_best` → the off-page recommendation. How to prove impact: re-run your tracker on `remeasure`.
- Requirements: `TYPESAFE_API_KEY` for section mode (fails closed), an OpenAI-compatible key for the rewriter
  (`OPENAI_API_KEY`, optional `OPENAI_BASE_URL`), `GEO_EVAL_MOCK=1` for offline runs.
- `CHANGELOG.md` `[Unreleased]`: **Changed** — `fix-gaps` defaults to section mode (page mode via
  `--mode page`); **Added** — section rewrite with fidelity gates, Jev diagnosis/verification (experimental),
  off-page recommendation, `eval/jev_selection`.
- Tick the completed items in `openspec/changes/update-fix-gaps-section-rewrite/tasks.md`.
- Never describe Jev or the verification outcome as a prediction of citation. No version bump.

### Lane D — dogfood run (VPS, after F3)

As in the main plan §4, with these specifics:
- Gaps: the 5 generic queries E-GEO lost in the newest valid weekly measurement; `sources` = that query's
  `cited_urls` from `~/Sync/mkt/egeo-expansion/jev-selection/dataset-v2-2026-09-25.json`.
- Project: map them to `site/src/content/docs/` pages using the `own_url` table in `queries-v2.json`
  (`source:` = absolute path of the page's `.md`). Out dir: `~/Sync/mkt/egeo-expansion/dogfood-sections-YYYY-MM-DD/`.
- Keys: `TYPESAFE_API_KEY`, `OPENAI_API_KEY`, `OPENAI_BASE_URL` from `~/.hermes/.env`;
  `REWRITER_MODEL=openai/gpt-4o`. Budget ≤ $1 LLM. **One run.** Never write into `site/`.

## Hand-back

1. Head SHA; `pytest tests/ -q` (expect 156 passed); site build + verify output.
2. Dogfood: `fix-gaps.json`, every `section.diff`, every `diagnosis.json`, and one line per page: status and
   whether you would publish that diff (yes/no + why).
3. Anything you could not do, and anything you think is wrong in a test or this plan.

The reviewer then reads every diff before anything is proposed for publication or merge.
