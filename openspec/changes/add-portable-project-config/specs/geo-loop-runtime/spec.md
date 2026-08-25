## ADDED Requirements

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
