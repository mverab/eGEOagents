## ADDED Requirements

### Requirement: Runtime-Agnostic Agent Contract
The system SHALL define the four GEO agents (Analyzer, Ranker, Rewriter, Indexer) as a runtime-agnostic contract that is independent of any specific host runtime.

#### Scenario: Agents are defined once and shared across runtimes
- **WHEN** a runtime adapter is asked to construct the Analyzer, Ranker, Rewriter, or Indexer
- **THEN** every adapter returns an object implementing the same agent contract
- **AND** the Ranker and Rewriter agents delegate to the existing `geo_eval` ranking and rewriting functions rather than re-implementing them

#### Scenario: Ranker and Rewriter reuse the shared prompts and harness
- **WHEN** the Ranker ranks candidates or the Rewriter rewrites a description
- **THEN** it uses the templates in `prompts/` and the client returned by `llm_client.get_client()`
- **AND** no ranking or rewriting logic is duplicated outside `geo_eval.py`

### Requirement: Pluggable Runtime Adapters
The system SHALL provide a runtime adapter layer with a registry so that multiple runtimes can supply implementations of the four-agent contract.

#### Scenario: Python runtime executes the agents in-process
- **WHEN** the `python` (alias `cli`) runtime is selected
- **THEN** the agents execute in-process using `llm_client` and the `prompts/` templates
- **AND** the runtime reports itself as available

#### Scenario: Claude Code runtime is a host-executed descriptor
- **WHEN** the `claude-code` runtime is selected
- **THEN** it maps each agent to its `.claude/agents/*.md` definition and slash command
- **AND** it reports itself available only when a `.claude/` directory is present
- **AND** attempting to execute one of its agents in-process raises a clear error directing the user to run it via Claude Code

#### Scenario: Runtimes are discoverable through a registry
- **WHEN** `list_runtimes()` is called or `egeo runtimes` is run
- **THEN** the known runtimes are returned with their names and availability status

### Requirement: Standalone `egeo` CLI
The project SHALL provide a standalone `egeo` command, runnable as `egeo` or `python -m egeo`, exposing the GEO pipeline outside Claude Code.

#### Scenario: Optimize a local file end-to-end
- **WHEN** a user runs `egeo optimize <file>`
- **THEN** the analyze → rank → rewrite → index pipeline runs against the file
- **AND** `report.md`, `analysis.json`, an optimized content file, and a JSON-LD schema file are written to the output directory

#### Scenario: Evaluate mirrors the harness
- **WHEN** a user runs `egeo evaluate --dataset <path> [--limit N]`
- **THEN** the command delegates to `geo_eval.evaluate`
- **AND** prints a summary containing `avg_rank_improvement`, `win_rate`, and `stderr_rank_improvement`

#### Scenario: Optimize-prompts mirrors the meta-optimizer
- **WHEN** a user runs `egeo optimize-prompts --train <path> --val <path>`
- **THEN** the command delegates to `geo_eval.optimize`
- **AND** it is non-destructive by default, writing to `prompts/rewriter_user.candidate.txt` unless `--apply` is passed

#### Scenario: List runtimes
- **WHEN** a user runs `egeo runtimes`
- **THEN** the CLI lists `python` and `claude-code` with their availability

### Requirement: Offline Deterministic CLI Execution
The `egeo` CLI SHALL run end-to-end without network access or API keys when the mock client is enabled, so it can execute in CI.

#### Scenario: Optimize runs offline under the mock client
- **WHEN** `GEO_EVAL_MOCK=1 egeo optimize <file>` is run
- **THEN** no outbound network request is made
- **AND** the pipeline completes and writes its artifacts

#### Scenario: Evaluate runs offline under the mock client
- **WHEN** `GEO_EVAL_MOCK=1 egeo evaluate --dataset eval/datasets/geo_smoke.jsonl --limit 3` is run
- **THEN** the command exits successfully and prints the metric summary

#### Scenario: Emitted schema passes JSON-LD validation
- **WHEN** the Indexer writes a JSON-LD schema file during `egeo optimize`
- **THEN** the file passes `scripts/validate_jsonld.py`

### Requirement: CI Smoke Test for the CLI
Continuous integration SHALL exercise the `egeo` CLI on every push and pull request to protected branches using the mock client.

#### Scenario: CLI smoke test runs in CI
- **WHEN** CI runs on a pull request targeting `main` or a `release/**` branch
- **THEN** it runs `python -m egeo optimize`, `python -m egeo evaluate`, and `python -m egeo runtimes` with `GEO_EVAL_MOCK=1`
- **AND** a non-zero exit from any of those commands fails the build
- **AND** the pre-existing quality gates remain unchanged

### Requirement: Automated GitHub Release Publishing
The repository SHALL publish a GitHub Release automatically when a version tag is pushed, sourcing the release notes from `CHANGELOG.md`.

#### Scenario: Tag push publishes a release
- **WHEN** a tag matching `v*` is pushed
- **THEN** the release workflow resolves the tag, extracts the matching `## [VERSION]` section from `CHANGELOG.md`, and publishes a GitHub Release with those notes

#### Scenario: Manual dispatch publishes a release
- **WHEN** the workflow is triggered via `workflow_dispatch` with a `tag` input
- **THEN** it publishes (or updates) the release for that tag

#### Scenario: Missing changelog section falls back gracefully
- **WHEN** `CHANGELOG.md` has no section for the released version
- **THEN** the workflow uses an auto-generated notes placeholder instead of failing

### Requirement: Documented Supported Runtimes and CLI Usage
The project SHALL document which runtimes are supported and how to use the `egeo` CLI.

#### Scenario: README documents runtimes and the CLI
- **WHEN** a user reads `README.md`
- **THEN** a "Supported Runtimes" section lists the supported runtimes and their status
- **AND** CLI usage for `optimize`, `evaluate`, `optimize-prompts`, and `runtimes` (including the `GEO_EVAL_MOCK=1` offline path) is documented
