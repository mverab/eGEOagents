## 1. Implementation
- [x] 1.1 `egeo/decide.py`: `_overview_stream`, `_cited_instead`, the `escalate_uncited` rule (3 shown observations, latest shown, stream within cadence), its place before `escalate_absent`.
- [x] 1.2 `egeo/decide.py`: grader for `escalate_uncited` with the `unobservable` grade; `details` on the action and the ledger row; "Cited instead" section in the proposal doc.

## 2. Tests
- [x] 2.1 `tests/test_decide.py`: proposal after three shown and uncited observations; `available: false` not counted; one citation stops it; stale stream not judged; doc and ledger carry `cited_instead`; `verified`, `resolved_unattributed`, `unchanged`, `unobservable`; priority over `escalate_absent`.

## 3. Docs and verification
- [x] 3.1 `site/src/content/docs/docs/geo-loop.md`, `site/src/content/docs/docs/cli.md`, `.claude/skills/geo-loop/SKILL.md`, `CHANGELOG.md`.
- [x] 3.2 Full suite, `openspec validate add-decide-ai-overview-citations --strict`.
