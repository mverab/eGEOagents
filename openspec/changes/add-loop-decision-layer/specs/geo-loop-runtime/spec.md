## ADDED Requirements

### Requirement: Decision Command Ranks One Next Action

The CLI SHALL expose `egeo loop decide [--dry-run] [--json]`. The command SHALL be LLM-free, SHALL require a valid `project.yaml`, and SHALL emit exactly one ranked action from collector JSONL, the project contract, and the outcome ledger.

#### Scenario: Target absent from SERP

- **WHEN** an active query has `target_position: null` in at least three observations
- **THEN** the ranked action kind is `escalate_absent`
- **AND** the action cites the SERP stream path
- **AND** `next_gate` is `owner`

#### Scenario: Dry run writes nothing

- **WHEN** `egeo loop decide --dry-run` runs against a valid workspace
- **THEN** the ranked action is printed
- **AND** no ledger row, proposal doc, or extra LOG line is written

### Requirement: Outcome Ledger Is Append-Only

Decision outcomes SHALL be appended to `$EGEO_HOME/data/outcomes/ledger.jsonl`. Existing lines SHALL never be rewritten. Each record SHALL include schema version `v`, `id`, `ts`, `project_id`, `kind`, `status`, evidence paths, and `auto_apply: false`.

#### Scenario: Proposed action is recorded

- **WHEN** `egeo loop decide` runs without `--dry-run` and ranks a new action
- **THEN** exactly one new ledger line is appended with `status: proposed`
- **AND** `auto_apply` is `false`
- **AND** the command never sets `status: applied`

#### Scenario: Duplicate open action is not re-proposed

- **WHEN** an open ledger row already exists for the same kind and query/page IDs
- **THEN** the ranked action is `wait_for_window` or `grade_outcome`
- **AND** no second proposed row is appended

### Requirement: Outcomes Are Graded From Later Observations

When an open ledger row has reached a 7, 14, or 28 day window and newer collector observations exist, `decide` SHALL grade that row as `verified`, `unchanged`, `worse`, or `withdrawn` using only collector fields. It SHALL NOT invent metric movement.

#### Scenario: Window reached with no position change

- **WHEN** a proposed `escalate_absent` row is older than 7 days and later SERP observations still have null `target_position`
- **THEN** the command records a grade of `unchanged` for that window
- **AND** it does not claim improvement

### Requirement: Decision Never Publishes

`egeo loop decide` SHALL NOT edit the site, open a pull request, merge, deploy, or change `reflect.auto_apply`. Proposal documents SHALL name the owner gate.

#### Scenario: Schema gap proposal

- **WHEN** a tracked page has empty `jsonld_types`
- **THEN** the ranked action kind is `propose_schema`
- **AND** the proposal document states that visible copy must not be changed automatically
