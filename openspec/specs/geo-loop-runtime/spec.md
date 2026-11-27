# geo-loop-runtime Specification

## Purpose

Loop mode: the per-user workspace (`$EGEO_HOME`), the `egeo loop` subcommands (`run`, `collect`, `doctor`, `decide`, `mark`), the portable `project.yaml` contract, and the append-only outcome ledger that proposes one action at a time and grades it from later collector observations. Nothing in this capability publishes, merges or edits a site.

## Requirements

### Requirement: Loop State Lives Outside the Repository
All loop state — `LOG.md`, signals, docs, collector data, domain charters,
optimized prompts, and configuration — SHALL live in the workspace resolved from
`$EGEO_HOME` (default `~/.egeo/`). No loop run, collector pass, or prompt
optimization SHALL write into the eGEOagents repository tree.

#### Scenario: Updating the repo after months of loop runs
- **WHEN** a user runs `git pull` in eGEOagents after accumulating loop state
- **THEN** the update applies without touching the workspace
- **AND** no workspace file is modified, overwritten, or lost

#### Scenario: Prompt optimization keeps the repo pristine
- **WHEN** `optimize` produces a prompt and a bootstrapped workspace exists
- **THEN** the prompt is written under `$EGEO_HOME/prompts/`
- **AND** the repo's `prompts/` directory is unchanged

#### Scenario: Workspace prompts override repo defaults
- **WHEN** `$EGEO_HOME/prompts/rewriter_user.txt` exists and `evaluate` runs
- **THEN** the workspace file is the prompt actually used
- **AND** deleting that file restores the repo default on the next run

### Requirement: Workspace Bootstrap Is Idempotent
The first invocation against a missing workspace SHALL create the `SUBSTRATE.md`
layout (`LOG.md`, `signals/`, `docs/`, `data/`, `domains/`, `prompts/`), a
`config.yaml` template carrying `cadence`, `models`, `budgets`,
`reflect.auto_apply: never` and `scaling.weights`, a copy of `SUBSTRATE.md`, and
exactly one bootstrap `LOG.md` line. Re-running bootstrap SHALL NOT overwrite any
existing workspace file.

#### Scenario: First run on a new machine
- **WHEN** `egeo loop doctor` runs with no workspace present
- **THEN** the workspace is created with the `SUBSTRATE.md` layout and a config template
- **AND** the command reports the workspace healthy

#### Scenario: Bootstrap re-run over existing state
- **WHEN** bootstrap executes against a populated workspace
- **THEN** every existing file is preserved byte-for-byte
- **AND** no additional bootstrap `LOG.md` line is appended

### Requirement: Loop Commands Are Subcommands of the `egeo` CLI
Loop operations SHALL be exposed as `egeo loop run <domain> [--dry-run]`,
`egeo loop collect <collector>`, and `egeo loop doctor`, runnable as `egeo` or
`python -m egeo`. No separate loop binary SHALL be introduced.

#### Scenario: Discovering the loop surface
- **WHEN** a user runs `egeo loop --help`
- **THEN** the `run`, `collect`, and `doctor` subcommands are listed with help text
- **AND** the help states that the interpretive loop run itself is executed by the agent skill

#### Scenario: Doctor reports workspace health
- **WHEN** `egeo loop doctor` runs against a bootstrapped workspace
- **THEN** it verifies the layout, parses `config.yaml`, lints workspace artifacts against the substrate contract, and checks budget sanity
- **AND** a missing `BRAVE_API_KEY` is reported as a warning rather than a failure
- **AND** secret values are never printed

### Requirement: A Loop Run Is One Bounded Unit Of Work
Each loop run SHALL perform at most one unit of work drawn from the domain's
current focus or backlog, SHALL append exactly one domain `## Timeline` entry
ending in an `Outcome:` line valued `success`, `partial`, `failure`, or `no-op`,
SHALL append exactly one `LOG.md` line, and SHALL re-read both writes before
exiting.

#### Scenario: Normal loop run
- **WHEN** `/geo:loop <domain>` completes
- **THEN** exactly one new Timeline entry with an `Outcome:` class and one new `LOG.md` line exist
- **AND** every written artifact passes the substrate checks

#### Scenario: Dry run writes nothing
- **WHEN** `egeo loop run <domain> --dry-run` is invoked
- **THEN** the run plan — current focus, collector deltas since the last run, candidate signals — is printed
- **AND** no file in the workspace or the repository is created or modified

#### Scenario: Nothing worth doing
- **WHEN** a loop run finds no fresh data and no actionable backlog item
- **THEN** it records a Timeline entry with `Outcome: no-op` and one `LOG.md` line
- **AND** it creates no signals or docs

### Requirement: Triggers Are Scheduler-Agnostic And Delivery-Hygienic
Loop runs and collector passes SHALL be triggerable by plain CLI invocation, so
any scheduler (Hermes cron, system cron, manual, another agent) drives them
identically. Documented scheduler examples SHALL pin provider and model per
agent job, and jobs more frequent than weekly SHALL use local delivery plus a
digest job summarizing `LOG.md`.

#### Scenario: High-frequency collector job
- **WHEN** a collector runs hourly under a scheduler
- **THEN** its output is delivered locally as JSONL plus one `LOG.md` line
- **AND** the owner is notified only through the periodic digest

#### Scenario: Documented agent loop job
- **WHEN** the documented cron example for an agent loop run is read
- **THEN** it pins the provider and model for that job

### Requirement: One-Shot Mode Is Preserved
Existing one-shot behavior — `/geo` and the other `geo*` commands, the four
agents, the existing skills, `egeo optimize`, `egeo evaluate`, and the
`geo-output/` convention — SHALL remain unchanged and SHALL NOT require a
workspace to exist.

#### Scenario: User without a workspace optimizes a file
- **WHEN** a user who never enabled loop mode runs `/geo <url>` or `egeo optimize <file>`
- **THEN** the pipeline behaves exactly as it did before this change
- **AND** no workspace directory is created

#### Scenario: Offline gates stay green
- **WHEN** the existing quality gates run with `GEO_EVAL_MOCK=1` and no workspace
- **THEN** evaluation, skill validation, and JSON-LD validation all pass

### Requirement: Active Project Has a Declarative Contract

A bootstrapped loop workspace MAY contain `$EGEO_HOME/project.yaml`. When present, it SHALL define one active project's identity, canonical URL/domain, tracked query records, tracked page records, measurement settings, and anti-spam/canibalization guardrails. The contract SHALL be versioned and contain no credentials or private tokens.

#### Scenario: Portable project fixture

- **WHEN** the same loop code is pointed at a second workspace containing a valid `project.yaml`
- **THEN** the run plan and fixture collectors use that project's identity, domain, queries, and pages
- **AND** no Python source edit is required

#### Scenario: Contract contains a secret

- **WHEN** `project.yaml` contains a credential-like key or secret value
- **THEN** validation fails with a remediation message
- **AND** no collector record or LOG line is written

### Requirement: Project Contract Is Validated Before Use

The system SHALL validate `project.yaml` deterministically before any collector or run plan consumes project-specific inputs. Validation SHALL reject unsupported schema versions, duplicate IDs, URL/domain mismatches, orphan page references, empty active queries, and conflicting canonical ownership.

#### Scenario: Invalid contract

- **WHEN** an active workspace has invalid `project.yaml`
- **THEN** `egeo loop doctor` reports the exact field and violation
- **AND** `egeo loop collect` exits non-zero without appending JSONL or LOG data

#### Scenario: Anti-cannibalization ownership

- **WHEN** two active query records claim the same canonical page for the same intent without an explicit experiment relationship
- **THEN** validation rejects the contract
- **AND** names the conflicting query and page IDs

### Requirement: Project Configuration Is Separate From Loop Machinery

`project.yaml` SHALL hold project identity and measurement targets; `config.yaml` SHALL hold cadence, models, budgets, reflection, and scheduler-facing machinery. When a valid `project.yaml` exists, its project-specific values SHALL take precedence over legacy collector values in `config.yaml`. Explicit CLI flags SHALL take precedence over both.

#### Scenario: Valid project file takes precedence

- **WHEN** `project.yaml` and `config.yaml` specify different target domains or query lists
- **THEN** the collector uses `project.yaml` values
- **AND** `egeo loop doctor` reports `project.yaml` as the active source

#### Scenario: Legacy workspace remains runnable

- **WHEN** no `project.yaml` exists but legacy `config.yaml` contains collector inputs
- **THEN** current commands continue to work unchanged
- **AND** doctor reports that compatibility fallback is active

### Requirement: Project Source Is Observable

`egeo loop doctor` and `egeo loop run --json` SHALL report the active project ID, canonical domain, project configuration source, validation status, and counts of active queries and pages. They SHALL never print secret values.

#### Scenario: Operator checks portability

- **WHEN** an operator runs doctor on a valid portable workspace
- **THEN** the output identifies the project contract and active target counts
- **AND** the output is sufficient to reproduce the setup in another workspace without reading Python code

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
- **THEN** no second proposed row is appended for that kind and those IDs
- **AND** the ranked action is a due `grade_outcome`, a different proposal, or `wait_for_window` when neither exists

### Requirement: Outcomes Are Graded From Later Observations

When an open proposal has reached a 7, 14, or 28 day window counted from its anchor (the applied time, else the proposal time) and observations newer than the anchor exist, `decide` SHALL grade it once for that window as `verified`, `resolved_unattributed`, `unchanged` or, for `escalate_uncited` only, `unobservable`, using only collector fields and `project.yaml`. `worse` is reserved. `withdrawn` is recorded only by the owner with `egeo loop mark`. `decide` SHALL NOT invent metric movement.

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

### Requirement: Waiting Proposals Do Not Block New Proposals

An open proposal that has no window due SHALL NOT prevent `egeo loop decide` from ranking a different proposal. It SHALL only prevent a second proposal with the same kind and query/page ids. A due grade SHALL be ranked before any new proposal. `wait_for_window` SHALL be ranked only when no grade is due and no new proposal exists while at least one proposal is open.

#### Scenario: Second gap found while the first proposal waits

- **WHEN** a proposal for one query is less than 7 days old
- **AND** a different query is absent in its last three observations
- **THEN** the ranked action is `escalate_absent` for the second query

#### Scenario: Nothing new to propose

- **WHEN** an open proposal has no window due and no other action applies
- **THEN** the ranked action is `wait_for_window` naming that proposal
- **AND** no ledger line is appended

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
