# Change: Make the outcome ledger lifecycle close, and grade only what was applied

## Why

`egeo loop decide` (openspec `add-loop-decision-layer`) cannot complete one propose → apply → grade cycle. Reproduced on 2026-11-24 in a temporary workspace with `examples/project.yaml`:

- **The loop sticks on the first graded row.** A grade is appended as a new ledger line, but the proposal keeps `status: proposed` and empty `grades`. Every later run grades the same window again (6 ledger lines, 5 of them duplicate grades) and never ranks another action.
- **`verified` is recorded with nothing applied.** No code path can record `applied`, and windows count from the proposal time. A page that shows up in a SERP by itself is graded as a verified outcome of an intervention that never happened.
- **One open proposal blocks all others for 7 days**, and again for 7 days after it is marked applied, so five gaps take over a month just to be listed.
- **`propose_page_owner` has no grader.** From day 7 it returns `wait_for_window` forever and blocks every other action.

## What Changes

- The effective state of a proposal is **derived by folding** later ledger lines (grades, owner marks) onto it. The file stays append-only; no line is rewritten.
- New owner command `egeo loop mark <ledger-id> applied|withdrawn [--at TS] [--note TEXT]`. `decide` still never sets `applied`.
- Windows count from the applied time when there is one, otherwise from the proposal time.
- Grades: `verified` needs an owner-recorded application, or an observation that is itself the applied change (JSON-LD present on the page, a canonical target page in `project.yaml`). A metric that moves with no recorded application is `resolved_unattributed`.
- A proposal **closes** on `verified`, `resolved_unattributed`, `withdrawn`, or once its last window is graded. Closed proposals no longer block ranking or dedupe.
- One grade per window. Each grade line carries `graded_id` and `window`. When several windows are due, only the latest one is graded.
- `propose_page_owner` is graded from `project.yaml`.
- An open proposal that is waiting for its window no longer stops `decide` from proposing other, different actions (owner decision 2026-11-24). `wait_for_window` is returned only when nothing is due and nothing new can be proposed.
- Ledgers written by 2.4.0 load unchanged: grade lines without `window` are assigned one from their timestamps, so their duplicates collapse.
- The proposal document names the ledger id and the `mark` command.

## Impact

- Affected capability: `geo-loop-runtime`. This delta adds requirements; it refines the requirement "Outcomes Are Graded From Later Observations" of the unarchived `add-loop-decision-layer` (new grade `resolved_unattributed`, attribution rule). Reconcile both when that change is archived.
- Affected code: `egeo/decide.py`, `egeo/loop.py`, `tests/test_decide.py`, `tests/test_cli.py`, docs.
- No new dependency, no network, no LLM, no auto-publish. Ledger schema stays `v: 1` (additive fields only).
- Out of scope: reading AI Overview or answer-engine citations in `decide`, and detecting application from `content_hash`.
