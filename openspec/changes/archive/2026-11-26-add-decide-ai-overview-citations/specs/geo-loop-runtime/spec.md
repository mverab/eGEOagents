## ADDED Requirements

### Requirement: Decision Proposes From AI Overview Citations

`egeo loop decide` SHALL rank `escalate_uncited` with `next_gate: owner` for an active query when its latest AI Overview observation has `available: true`, is not older than the measurement cadence, and the last three observations with `available: true` all have `target_cited: false`. Observations with `available: false` SHALL NOT count as uncited. `escalate_uncited` SHALL be ranked before `escalate_absent`.

#### Scenario: Overview shown three times without the target

- **WHEN** the last three AI Overview observations that showed an overview for a query did not cite the target
- **THEN** the ranked action kind is `escalate_uncited`
- **AND** it cites the AI Overview stream path
- **AND** the proposal lists the domains cited instead with the number of observations each appeared in

#### Scenario: No AI Overview shown

- **WHEN** an observation has `available: false`
- **THEN** it is not counted toward the three uncited observations
- **AND** no `escalate_uncited` is ranked while the latest observation has `available: false`

#### Scenario: Workspace without AI Overview data

- **WHEN** no `data/ai_overview/` stream exists
- **THEN** `decide` ranks the same action it ranked before this requirement existed

### Requirement: Citation Outcomes Are Graded From AI Overview Observations

An `escalate_uncited` proposal SHALL be graded only from AI Overview observations after its anchor: `verified` when the target is cited after an owner-recorded application, `resolved_unattributed` when it is cited with no recorded application, `unchanged` when an overview was shown and the target is still not cited, and `unobservable` when no later observation showed an overview. `unobservable` SHALL NOT close the proposal before its last window.

#### Scenario: Cited after the owner applied a change

- **WHEN** the proposal was marked applied and a later observation has `target_cited: true`
- **THEN** the grade is `verified`

#### Scenario: Overview disappears

- **WHEN** every observation after the anchor has `available: false`
- **THEN** the grade is `unobservable`
- **AND** the proposal stays open for its next window
