## 1. Contract and loader

- [x] 1.1 Add the v1 `project.yaml` schema contract and example fixture.
- [x] 1.2 Implement workspace project loading with strict validation and clear errors.
- [x] 1.3 Keep `config.yaml` machinery separate from project inputs.

## 2. Runtime integration

- [x] 2.1 Make SERP collector resolve active queries and canonical domain from project.yaml when present.
- [x] 2.2 Make page collector resolve active tracked pages from project.yaml when present.
- [x] 2.3 Include project identity and configuration source in `egeo loop run --json` and `egeo loop doctor`.
- [x] 2.4 Preserve explicit CLI overrides and legacy config fallback.

## 3. Enforcement and portability tests

- [x] 3.1 Reject duplicate query IDs, duplicate canonical owners, orphan page references, and mixed branded/generic ownership.
- [x] 3.2 Add offline fixture tests for E-GEO-shaped and second-project-shaped configurations.
- [x] 3.3 Verify invalid project.yaml fails closed without writing JSONL or LOG entries.
- [x] 3.4 Verify one-shot commands remain unaffected when no workspace exists.

## 4. Documentation and verification

- [x] 4.1 Document the project.yaml/config.yaml boundary and migration path.
- [x] 4.2 Run `openspec validate add-portable-project-config --strict`.
- [x] 4.3 Run the full Python test/quality suite and fixture collector passes.
- [x] 4.4 Run two dry-run plans with the same code and different project fixtures.
