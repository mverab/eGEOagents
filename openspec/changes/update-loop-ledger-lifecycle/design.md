## Context

The ledger is append-only, so a proposal line can never be edited to say "graded" or "applied". 2.4.0 appended grade lines but read state only from the proposal line, which is why nothing ever closed.

## Decisions

### Fold, do not rewrite

`ledger_state(rows)` returns one state per proposal line (kinds `escalate_absent`, `propose_page_owner`, `propose_schema`). Event lines point at a proposal and are folded in file order:

| line `kind` | pointer | effect |
|---|---|---|
| `grade_outcome` | `graded_id`, `window` | `grades[window] = status` |
| `mark_applied` | `target_id` | `applied_ts = ts`, status `applied` |
| `mark_withdrawn` | `target_id` | status `withdrawn`, closed |

A grade line without `window` (2.4.0) gets the largest window reached between the anchor and the grade's `ts` (minimum 7).

### Anchor and windows

Anchor = `applied_ts` if present, else the proposal `ts`. Only observations after the anchor count. Windows stay 7/14/28 days from the anchor. Due windows are those reached and greater than the largest graded one; `decide` grades the latest due window only, so a proposal found at day 30 gets one grade (28), not three copies of today's observation.

Grades recorded before a `mark_applied` measured the untouched page: the fold sets them aside (`pre_application_grades`) and the windows start again from the applied time.

### Grades

| kind | condition after the anchor | applied by owner | not marked |
|---|---|---|---|
| `escalate_absent` | target has a position in a later SERP record | `verified` | `resolved_unattributed` |
| `escalate_absent` | still absent | `unchanged` | `unchanged` |
| `propose_schema` | latest page record has `jsonld_types` | `verified` | `verified` |
| `propose_page_owner` | query has an active target page in `project.yaml` | `verified` | `verified` |

For the last two, the observation is the change that was proposed, so it needs no separate mark. `worse` stays reserved; no v1 kind produces it.

### Closing

Closed when status is `withdrawn`, any grade is `verified` or `resolved_unattributed`, or the last window (28) is graded. A closed proposal is skipped by wait/grade and leaves the dedupe set, so a query still absent after 28 days can be escalated again.

### `mark`

`egeo loop mark <id> applied|withdrawn`. Rejects unknown ids, event lines, closed proposals, and `applied` twice. `--at` backdates the application; it must lie between the proposal time and now. Appends one event line and one LOG.md line. It does not need `project.yaml`.

## Unchanged on purpose

An open proposal younger than 7 days still returns `wait_for_window` before any new proposal (one owner action at a time). Priority order of action kinds is unchanged.

## Risks

- An owner who never runs `mark` gets `resolved_unattributed` instead of `verified` for `escalate_absent`. That is the intended, honest reading.
- `--at` trusts the owner's date; it is bounded, and the event line keeps its own real `ts` in `recorded_ts`.
