## ADDED Requirements

### Requirement: Offline Deterministic Evaluation
The evaluation harness SHALL run end-to-end without network access or API keys when a mock mode is enabled, so it can execute in CI.

#### Scenario: Mock client is selected by environment flag
- **WHEN** `GEO_EVAL_MOCK` is set to a truthy value (`1`, `true`, `yes`, `on`)
- **THEN** `get_client()` returns a deterministic mock client
- **AND** no outbound network request is made during `evaluate` or `optimize`

#### Scenario: Evaluate completes in CI without secrets
- **WHEN** CI runs `python geo_eval.py evaluate --dataset eval/datasets/geo_smoke.jsonl --limit 5` with `GEO_EVAL_MOCK=1`
- **THEN** the command exits successfully
- **AND** prints a summary containing `avg_rank_improvement`, `win_rate`, and `stderr_rank_improvement`

#### Scenario: Mock output matches each prompt schema
- **WHEN** the mock is asked to act as ranker, rewriter, or meta-optimizer
- **THEN** it returns JSON with `ordered_ids`, `rewritten_description`, or `new_prompt` respectively
- **AND** the ranker returns a permutation of the provided candidate ids

### Requirement: Non-Destructive Prompt Optimization
The `optimize` command SHALL NOT overwrite the working rewriter prompt unless the operator explicitly opts in.

#### Scenario: Default run preserves the working prompt
- **WHEN** `optimize` runs without `--apply`
- **THEN** the optimized prompt is written to `prompts/rewriter_user.candidate.txt`
- **AND** `prompts/rewriter_user.txt` is left unchanged

#### Scenario: Apply flag overwrites in place
- **WHEN** `optimize` runs with `--apply`
- **THEN** `prompts/rewriter_user.txt` is overwritten with the optimized prompt
- **AND** the result payload reports `applied: true`

### Requirement: Skill Frontmatter Validation
The project SHALL validate that every `SKILL.md` has well-formed, unique frontmatter so skills remain discoverable on skills.sh.

#### Scenario: Valid frontmatter passes
- **WHEN** `scripts/validate_skills.py` runs against the repository
- **THEN** every `SKILL.md` with a `name` and `description` and a kebab-case name passes
- **AND** the script exits zero

#### Scenario: Missing field or duplicate name fails
- **WHEN** a `SKILL.md` lacks a required field or reuses an existing `name`
- **THEN** the script reports the offending file and reason
- **AND** exits non-zero

### Requirement: JSON-LD Template Validation
The project SHALL validate the structure of JSON-LD schema templates.

#### Scenario: Valid templates pass
- **WHEN** `scripts/validate_jsonld.py --dir geo-output/schema` runs
- **THEN** every template that is valid JSON with `@context` referencing schema.org and a `@type` (or `@graph`) passes
- **AND** the script exits zero

#### Scenario: Malformed JSON-LD fails
- **WHEN** a file is not valid JSON or is missing `@type`/`@context`
- **THEN** the script reports the error location
- **AND** exits non-zero

### Requirement: Link Integrity Enforcement in CI
Continuous integration SHALL fail when deprecated repository slugs reappear in documentation.

#### Scenario: Deprecated slug blocks the build
- **WHEN** any markdown file contains `egeo-claude-agents`
- **THEN** the CI link-check step fails the build

#### Scenario: Canonical links pass
- **WHEN** markdown references use `eGEOagents`
- **THEN** the link-check step passes

### Requirement: Continuous Quality Gates
The repository SHALL run automated quality gates on every push and pull request to protected branches.

#### Scenario: CI runs all gates
- **WHEN** a pull request targets `main` or a `release/**` branch
- **THEN** CI runs skill frontmatter validation, JSON-LD validation, the link check, a non-blocking skills.sh parser smoke test, and a mock evaluation
- **AND** a failure in any blocking gate fails the build

### Requirement: Monthly QA Gate
The repository SHALL run a scheduled monthly QA gate covering parser validation, dead-link scanning, metadata completeness, and release freshness.

#### Scenario: Monthly workflow executes the gate
- **WHEN** the monthly schedule triggers (or it is dispatched manually)
- **THEN** the workflow runs parser/frontmatter validation, a dead-link scan, JSON-LD metadata validation, and a release/tag freshness report

### Requirement: Documented and Reproducible Evaluation
The project SHALL document the evaluation dataset format, commands, metrics, and the honest limitation that results are an LLM-ranker proxy.

#### Scenario: Evaluation documentation exists and is linked
- **WHEN** a user opens `docs/evaluation.md`
- **THEN** the dataset JSONL format, `evaluate`/`optimize` commands, and metric definitions are documented
- **AND** the document clearly states results are a proxy, not real AI-engine ranking
- **AND** the README links to it with a CI badge and a "Reproducible results" section
