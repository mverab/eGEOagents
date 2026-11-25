## ADDED Requirements

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
