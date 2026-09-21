## 1. Product specification and backend — proposed PR scope
- [x] 1.1 Finalize imported-answer, evidence, run-result, and proposed-action schemas.
- [x] 1.2 Approve technical proposal before implementing backend changes.
- [x] 1.3 Implement optional Jev adapter and deterministic evidence/provenance checks.
- [x] 1.4 Integrate CLI and existing rewrite/approval flow without automatic application.
- [x] 1.5 Test supported, contradicted, insufficient, irrelevant, extraction-failure, and provider-failure cases; Spanish fragments preserved via test transport (live Jev Spanish quality unverified — no API key).

## 2. Local visual demo — required for demo acceptance, excluded from product PR
- [x] 2.1 Build a thin local viewer outside the repository using the same serialized backend results; no duplicate evaluator.
- [x] 2.2 Show query, target page, imported answer, cited sources, capture time, and evidence fragments side by side.
- [x] 2.3 Show covered, actionable-gap, and insufficient/irrelevant groups; inspect exact evidence and proposed diff.
- [x] 2.4 Support labeled recorded replay; show live evaluation only when backed by actual backend execution.
- [x] 2.5 Show real run timing and usage; unknown costs remain unavailable, not zero.
- [ ] 2.6 Exercise the full local demo with real captured evidence and real evaluator output before recording; do not claim increased AI visibility from a better content assessment.
- [x] 2.7 Verify no UI code/dependencies, datasets, credentials, or recordings enter the product PR/package.
