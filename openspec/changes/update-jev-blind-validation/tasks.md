Implementation plan with lanes, contracts and the run protocol: `docs/plans/2026-09-26-jev-blind-validation-plan-v4.md`.

## 0. Approval
- [ ] 0.1 Owner approves this proposal and decides D2 (Noul, recommended, vs Choice)

## 1. Contracts (RED)
- [ ] 1.1 Contract tests for blinding, `score_candidates`, Noul diagnose and verify, mock Noul, the eval product path and the report keys; stubs with signatures in docstrings

## 2. Implementation
- [ ] 2.1 `egeo/judge.py` + `egeo/jev.py` (lane J1)
- [ ] 2.2 `eval/jev_selection/run.py` (lane G4)
- [ ] 2.3 `egeo/gaps.py` report keys (lane F4)
- [ ] 2.4 Full suite green; reviewer reads the diff

## 3. Validation (pre-registered; design D4)
- [ ] 3.1 Commit `eval/jev_selection/PREREG-v4.md` (queries sha256, scorer, ids, unit, gate, consequences) before any live run
- [ ] 3.2 Leak diagnostic on dataset v2: `--ids leaky` vs `--ids blind` (non-gating)
- [ ] 3.3 Collect dataset v3 once (≥ 30 queries, `own_source` mapped)
- [ ] 3.4 Evaluate v3 once; record the result in the README

## 4. Outcome (design D5)
- [ ] 4.1 Update `JEV_VALIDATION`, docs and CHANGELOG per the pre-registered consequence; owner decision if FAIL
