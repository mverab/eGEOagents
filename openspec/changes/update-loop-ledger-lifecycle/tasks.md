## 1. Tests
- [x] 1.1 Tests (14 fail on the 2.4.0 `decide.py`) in `tests/test_decide.py`: a graded window is not graded again; the next action is ranked after grading; unapplied reappearance is `resolved_unattributed`; applied reappearance is `verified`; windows count from the applied time; closed proposals can be re-proposed; latest due window only; `propose_page_owner` is graded; 2.4.0 duplicate grade lines collapse.
- [x] 1.2 Tests for `mark`: applied, withdrawn, unknown id, closed proposal, applied twice, `--at` bounds; CLI test in `tests/test_cli.py`.
- [x] 1.3 Tests: a waiting proposal does not block a different proposal; a due grade still goes first; `wait_for_window` when nothing else is left.

## 2. Implementation
- [x] 2.1 `egeo/decide.py`: `ledger_state`, anchor/due-window logic, attribution-aware grading, `propose_page_owner` grader, grade lines with `window`.
- [x] 2.2 `egeo/decide.py`: `mark_row`; proposal document names the ledger id and the `mark` command.
- [x] 2.3 `egeo/loop.py`: `egeo loop mark` subcommand; `decide` output shows the ledger id.

## 3. Docs and verification
- [x] 3.1 `README.md`, `USAGE.md`, `site/src/content/docs/docs/cli.md`, `site/src/content/docs/docs/geo-loop.md`, `.claude/skills/geo-loop/SKILL.md`, `CHANGELOG.md`.
- [x] 3.2 Full test suite, the multi-week simulation from the proposal, `openspec validate update-loop-ledger-lifecycle --strict`.
