# Change: Add a deterministic loop decision layer

## Why

The loop already collects data and prints a run plan, but it does not decide the next unit of work or remember whether a previous action moved a metric. Without that, every wake-up still needs a human to interpret JSONL.

## What Changes

- Add `$EGEO_HOME/data/outcomes/ledger.jsonl` as an append-only, LLM-free outcome ledger.
- Add `egeo loop decide [--dry-run] [--json]` that ranks one next action from collector data, project.yaml, and the ledger.
- Write one proposal document under `$EGEO_HOME/docs/` when not dry-run. Never publish, merge, or edit site copy.
- Grade open ledger rows at 7/14/28 days from later collector observations.
- Keep `reflect.auto_apply` as the only autonomy gate; `decide` never applies.

## Impact

- Affected capability: `geo-loop-runtime`.
- Affected code: `egeo/loop.py`, `egeo/workspace.py` (paths only if needed), docs, tests.
- No credentials, no auto-publish, no auto-merge.
