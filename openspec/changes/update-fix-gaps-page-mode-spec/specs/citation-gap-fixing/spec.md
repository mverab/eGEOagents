## MODIFIED Requirements

### Requirement: Fix-Gaps Command Rewrites Pages For Uncited Queries

The CLI SHALL expose `egeo fix-gaps <gaps-file> [--mode page|sections] [--dry-run] [--json] [--out-dir DIR] [--format markdown|html] [--project PATH] [--max-sources N] [--jev-model MODEL]`. The command SHALL read citation results from a tracker export, select the queries where the project domain is not cited, and map them to local pages through `project.yaml`.

#### Scenario: Uncited query maps to a page with a source file

- **WHEN** the gaps file reports query "open source aeo tools" as not cited
- **AND** `project.yaml` has an active query with that text whose `target_pages` includes page `compare` with `source: site/compare.md`
- **THEN** page `compare` is processed against "open source aeo tools"
- **AND** the outputs are written under `<out-dir>/compare/`
- **AND** `site/compare.md` is not modified

#### Scenario: Cited query is not a gap

- **WHEN** the gaps file reports a query as cited
- **THEN** no page is processed for that query
- **AND** the report does not list it as a gap

#### Scenario: Page mode is the default

- **WHEN** `egeo fix-gaps gaps.json` runs without `--mode`, or with `--mode page`
- **THEN** each affected page is optimized with the `egeo optimize` pipeline, including its fidelity gate

## ADDED Requirements

### Requirement: Fix-Gaps Modes

In `page` mode (the default) the command SHALL optimize each affected page once with the existing `egeo optimize` pipeline. In `sections` mode (experimental, opt-in) it SHALL rewrite at most one section per page as specified by the section-mode requirements. Outside mock mode, `page` mode SHALL exit non-zero before any work, naming `OPENAI_API_KEY`, when no OpenAI-compatible key is configured.

#### Scenario: Page mode without a key

- **WHEN** `--mode page` runs outside mock mode with no OpenAI-compatible key configured
- **THEN** the command exits non-zero before any work and names `OPENAI_API_KEY`

### Requirement: Page Mode Reports The Fidelity Gate

In `page` mode each page result in `fix-gaps.json` SHALL carry `content_type` and `fidelity` (`status`, `violations`, `attempts`) as reported by the `egeo optimize` pipeline. A page whose rewrite is rejected SHALL have no file under its `optimized/` directory, and the CLI SHALL say that the rewrite was rejected.

#### Scenario: Rewrite passes the gate

- **WHEN** a page-mode rewrite meets every fidelity rule
- **THEN** the page result has `fidelity.status` `passed` and the rewrite is under `<out-dir>/<page_id>/optimized/`

#### Scenario: Rewrite rejected

- **WHEN** a page-mode rewrite still fails the fidelity rules after the repair attempt
- **THEN** the page result has `fidelity.status` `rejected` with its violations
- **AND** the rewrite is under `<out-dir>/<page_id>/rejected/`, not `optimized/`
