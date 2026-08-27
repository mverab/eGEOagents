## 1. Spec and contract

- [x] 1.1 Add OpenSpec delta for the decision layer.
- [x] 1.2 Define ledger schema v1 and action kinds.

## 2. Implementation

- [x] 2.1 Implement ledger read/append and grading helpers (LLM-free).
- [x] 2.2 Implement `egeo loop decide` with dry-run and JSON output.
- [x] 2.3 Write at most one proposal doc and one LOG line when not dry-run.
- [x] 2.4 Dedupe against open ledger rows; never set status `applied`.

## 3. Tests

- [x] 3.1 Rank `escalate_absent` from ≥3 null SERP observations.
- [x] 3.2 Rank `propose_schema` from empty jsonld_types.
- [x] 3.3 Rank `wait_for_window` when an open action has not matured.
- [x] 3.4 Grade improved vs unchanged from later observations.
- [x] 3.5 Dry-run writes nothing; invalid project.yaml fails closed.

## 4. Verification

- [x] 4.1 `openspec validate add-loop-decision-layer --strict`
- [x] 4.2 Unit tests + compileall + git diff --check
- [x] 4.3 Dry-run against a temp workspace cloned from SlashStack collector data (no writes to ~/.egeo)
