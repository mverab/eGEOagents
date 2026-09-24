## ADDED Requirements

### Requirement: Fix-Gaps Command Rewrites Pages For Uncited Queries

The CLI SHALL expose `egeo fix-gaps <gaps-file> [--dry-run] [--json] [--out-dir DIR] [--format markdown|html] [--project PATH]`. The command SHALL read citation results from a tracker export, select the queries where the project domain is not cited, map them to local pages through `project.yaml`, and optimize each affected page once with the existing `egeo optimize` pipeline.

#### Scenario: Uncited query maps to a page with a source file

- **WHEN** the gaps file reports query "open source aeo tools" as not cited
- **AND** `project.yaml` has an active query with that text whose `target_pages` includes page `compare` with `source: site/compare.md`
- **THEN** `site/compare.md` is optimized against "open source aeo tools"
- **AND** the outputs are written under `<out-dir>/compare/`
- **AND** `site/compare.md` is not modified

#### Scenario: Cited query is not a gap

- **WHEN** the gaps file reports a query as cited
- **THEN** no page is optimized for that query
- **AND** the report does not list it as a gap

### Requirement: Supported Input Formats Are Auto-Detected

The command SHALL accept (a) geo-optimizer-skill `geo citations --format json` output and (b) a generic gaps file as a JSON array or CSV with `query` and `cited` fields and optional `sources`. Any other shape SHALL fail with a message naming both accepted formats.

#### Scenario: geo-optimizer-skill JSON

- **WHEN** the file is a JSON object whose `entries` items contain `query` and `domain_cited`
- **THEN** each entry with `domain_cited: false` and no `error` is treated as a gap

#### Scenario: Generic CSV

- **WHEN** the file is a CSV with columns `query,cited`
- **THEN** rows with `cited` in {false, 0, no} are treated as gaps

#### Scenario: Unknown shape

- **WHEN** the file is JSON without `entries` and is not an array of objects with `query`
- **THEN** the command exits non-zero and names the two accepted formats

### Requirement: Failed Measurements Never Trigger Rewrites

Entries that carry a tracker error SHALL be skipped and reported as `skipped: tracker_error`. They SHALL NOT be treated as gaps.

#### Scenario: Engine call failed for a query

- **WHEN** a geo-optimizer-skill entry has a non-empty `error`
- **THEN** no page is optimized for that query
- **AND** the report lists it under skipped with reason `tracker_error`

### Requirement: Unmatched Gaps Are Reported, Not Guessed

Matching SHALL use exact text after normalization (lowercase, trimmed, collapsed whitespace, trailing punctuation removed). A gap that cannot be mapped to a page with a readable source SHALL be reported with one reason: `query_not_in_project`, `no_target_page`, `page_has_no_source`, or `source_not_found`.

#### Scenario: Query not in the project contract

- **WHEN** a gap query has no matching active query in `project.yaml`
- **THEN** it is listed as unmatched with reason `query_not_in_project`
- **AND** no page is optimized for it

### Requirement: One Rewrite Per Page Per Run

A page targeted by several gap queries SHALL be optimized once, against the first gap in input order. The remaining gap queries for that page SHALL be listed in the report under that page.

#### Scenario: Page loses two queries

- **WHEN** two gap queries map to page `home`
- **THEN** `home` is optimized once, against the first of them
- **AND** the report lists the second query under `home.other_gaps`

### Requirement: Report And Re-Measure List

Every non-dry run SHALL write `<out-dir>/fix-gaps.json` with the input format, matched gaps, unmatched and skipped entries with reasons, per-page results (query used, output paths, proxy rank before/after), and a `remeasure` list of gap queries. For geo-optimizer-skill input the report SHALL include the `geo citations` command to re-check them. The report SHALL state that rank before/after is an LLM-ranker proxy, not a live engine result.

#### Scenario: Report after a mock run

- **WHEN** `GEO_EVAL_MOCK=1 egeo fix-gaps gaps.json --out-dir out` completes
- **THEN** `out/fix-gaps.json` exists with keys `format`, `pages`, `unmatched`, `skipped`, `remeasure`, `note`

### Requirement: Dry Run Writes Nothing

`--dry-run` SHALL print the plan (pages to optimize, query per page, unmatched and skipped entries) and SHALL NOT write files or call any model.

#### Scenario: Dry run

- **WHEN** `egeo fix-gaps gaps.json --dry-run` runs
- **THEN** the plan is printed
- **AND** no output directory is created and no model is called

### Requirement: Optional Page Source Path In Project Config

`project.yaml` pages SHALL accept an optional `source` string: a path to the page's local content file, relative to the project file. Existing project files without `source` SHALL remain valid.

#### Scenario: Existing project file

- **WHEN** a `project.yaml` without any `pages[].source` is validated
- **THEN** validation passes as before
