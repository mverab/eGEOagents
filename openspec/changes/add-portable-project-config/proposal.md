# Change: Add a portable project contract for loop runs

## Why

The loop already separates state into `$EGEO_HOME`, but project identity, canonical targets, tracked queries, and page ownership still live in a machinery-oriented `config.yaml` or in manual domain charters. That makes the loop bespoke: adopting it for another project requires editing collector code or rediscovering the same inputs by hand.

## What Changes

- Add an additive `$EGEO_HOME/project.yaml` contract for one active project/workspace.
- Keep `config.yaml` responsible for loop machinery: cadence, models, budgets, reflection, and scheduler-facing settings.
- Move project facts into `project.yaml`: project identity, canonical domain, tracked pages, query records, source/measurement settings, and anti-spam/canibalization guardrails.
- Add deterministic loading and validation before collectors or run plans consume project inputs.
- Keep CLI compatibility: existing `config.yaml` collector fields remain accepted during migration; project.yaml takes precedence when present.
- Add an example project file and a portability test that runs the same code with a second project fixture without code edits.

## Impact

- Affected capability: `geo-loop-runtime` and collector configuration.
- Affected code: `egeo/workspace.py`, `egeo/loop.py`, collectors, docs, tests.
- No credentials, API keys, or private Search Console data enter the repository or project contract.
- No visible copy, auto-publish, auto-merge, or payment behavior changes.
