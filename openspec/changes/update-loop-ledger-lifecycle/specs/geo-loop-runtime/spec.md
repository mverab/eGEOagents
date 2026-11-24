## ADDED Requirements

### Requirement: Ledger State Is Derived From Appended Events

The effective state of a proposal SHALL be computed by folding later ledger lines that reference it (grades and owner marks) onto the proposal line. No ledger line SHALL be rewritten. A proposal SHALL be closed when it is withdrawn, when any grade is `verified` or `resolved_unattributed`, or when its last window is graded. Closed proposals SHALL NOT block ranking and SHALL NOT count as open for duplicate detection.

#### Scenario: A graded window is not graded again

- **WHEN** `egeo loop decide` has recorded the 7-day grade of a proposal
- **AND** it runs again before the 14-day window
- **THEN** no second grade line is appended for that proposal
- **AND** the command ranks the next action

#### Scenario: Several windows are due

- **WHEN** an open proposal is first graded 30 days after its anchor
- **THEN** exactly one grade line is appended, for the 28-day window
- **AND** the proposal is closed

#### Scenario: Ledger written by 2.4.0

- **WHEN** the ledger holds several grade lines without a `window` field for the same proposal and the same window
- **THEN** they fold into one grade
- **AND** the file is not modified by reading it

### Requirement: Owner Records Application Explicitly

The CLI SHALL expose `egeo loop mark <ledger-id> applied|withdrawn [--at TS] [--note TEXT] [--json]`. It SHALL append one event line and one `LOG.md` line, and SHALL reject unknown ids, event lines, closed proposals and a second `applied` mark. `egeo loop decide` SHALL NOT record `applied`.

#### Scenario: Owner marks a proposal applied

- **WHEN** the owner runs `egeo loop mark <id> applied` for an open proposal
- **THEN** one `mark_applied` line referencing `<id>` is appended
- **AND** later grading windows count from the applied time

#### Scenario: Unknown ledger id

- **WHEN** `egeo loop mark` is given an id that is not an open proposal
- **THEN** it exits non-zero and writes nothing

### Requirement: Verified Grades Require Attribution

`decide` SHALL grade `verified` only when the owner recorded the application, or when the observation is itself the proposed change (JSON-LD types present on the page, an active canonical target page in `project.yaml`). When the tracked metric moves and no application was recorded, the grade SHALL be `resolved_unattributed`. Only observations after the anchor (applied time, else proposal time) SHALL count.

#### Scenario: Target appears and nothing was applied

- **WHEN** an `escalate_absent` proposal was never marked applied
- **AND** a later SERP observation has a non-null `target_position`
- **THEN** the grade is `resolved_unattributed`
- **AND** no line claims `verified`

#### Scenario: Target appears after a recorded application

- **WHEN** an `escalate_absent` proposal was marked applied
- **AND** a SERP observation after the applied time has a non-null `target_position`
- **THEN** the grade is `verified`

#### Scenario: Page owner assigned

- **WHEN** a `propose_page_owner` proposal reaches a window
- **AND** `project.yaml` now lists an active target page for the query
- **THEN** the grade is `verified`
