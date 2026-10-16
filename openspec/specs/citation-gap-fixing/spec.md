# citation-gap-fixing Specification

## Purpose
Turn an AI-visibility tracker's citation report into page rewrites: `egeo fix-gaps` maps each query where the project domain is not cited to its local page through `project.yaml` and rewrites that page with the `optimize` pipeline, without guessing mappings, touching source files, or acting on failed measurements.

## Requirements

### Requirement: Fix-Gaps Command Rewrites Pages For Uncited Queries

The CLI SHALL expose `egeo fix-gaps <gaps-file> [--mode page|sections] [--dry-run] [--json] [--out-dir DIR] [--format markdown|html] [--project PATH] [--max-sources N] [--jev-model MODEL]`. The command SHALL read citation results from a tracker export, select the queries where the project domain is not cited, and map them to local pages through `project.yaml`. In `page` mode (the default) it SHALL optimize each affected page once with the existing `egeo optimize` pipeline. In `sections` mode (experimental, opt-in) it SHALL rewrite at most one section per page as specified by the section-mode requirements. Outside mock mode, `page` mode SHALL exit non-zero before any work, naming `OPENAI_API_KEY`, when no OpenAI-compatible key is configured.

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
- **THEN** each affected page is optimized with the `egeo optimize` pipeline as in version 2.1.0

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

Every non-dry run SHALL write `<out-dir>/fix-gaps.json` with the input format, mode, matched gaps, unmatched and skipped entries with reasons, per-page results and a `remeasure` list of gap queries. For geo-optimizer-skill input the report SHALL include the `geo citations` command to re-check them. In `sections` mode each page result SHALL include its status, fetched sources with success flags, the diagnosis, fidelity results, verification and output paths, and the report SHALL include Jev usage and the thresholds used. Diagnosis and verification SHALL report per-candidate `scores` and the `scorer` used. The report SHALL state that Jev scores text competitiveness, does not model authority or links, and is not a prediction of citation. The report SHALL carry a `jev_validation` object with the latest pre-registered result for the configuration section mode actually runs (protocol, scorer, ids, unit, mean AUC, 95% interval, number of queries, gate, pass/fail, date). Until that result passes the gate, the Jev comparison SHALL be labeled experimental: `jev_validation.status` SHALL be `"experimental"` and every Jev diagnosis and verification SHALL carry `"experimental": true`.

#### Scenario: Experimental labeling while the gate has not passed

- **WHEN** the latest validation result is below the gate
- **THEN** `fix-gaps.json` contains `jev_validation` with `"status": "experimental"` and `"gate_passed": false`
- **AND** each non-null diagnosis and verification carries `"experimental": true`

#### Scenario: Validation passed

- **WHEN** the latest pre-registered result for the running configuration passes the gate
- **THEN** `jev_validation` has `"status": "validated"` and `"gate_passed": true`
- **AND** diagnosis and verification carry no `experimental` flag
- **AND** the report still states that Jev is not a prediction of citation

#### Scenario: Report after a mock run

- **WHEN** `GEO_EVAL_MOCK=1 egeo fix-gaps gaps.json --out-dir out` completes
- **THEN** `out/fix-gaps.json` exists with keys `format`, `mode`, `pages`, `unmatched`, `skipped`, `remeasure`, `note`

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

### Requirement: Diagnosis Against Real Cited Sources

In `sections` mode, for each processed page the command SHALL fetch the text of the sources the tracker reports for the page's gap query (excluding the project's own domain, at most `--max-sources`, default 6) and score, in one Jev request, each of the page's own sections of at least 30 words and each successfully fetched source with an independent Noul question. If the best own section scores strictly above every source, the page status SHALL be `already_best` and nothing SHALL be rewritten. Otherwise the rewrite target SHALL be the own section with the highest score, with ties going to the earliest section in the document.

#### Scenario: A cited source beats every own section

- **WHEN** the best source score is greater than or equal to the best own-section score
- **THEN** the own section with the highest score becomes the rewrite target
- **AND** the report records every candidate's score and the scorer

#### Scenario: An own section already wins

- **WHEN** the best own-section score is strictly above every source score
- **THEN** the page status is `already_best`
- **AND** no rewrite is attempted
- **AND** the page result carries an `offpage` recommendation listing the fetched cited sources, stating that the gap is likely off-page (mentions and links), not the page text

#### Scenario: No source text could be fetched

- **WHEN** none of the query's sources can be fetched
- **THEN** the page status is `no_competitor_sources`
- **AND** no rewrite is attempted

### Requirement: Only The Target Section Is Rewritten

The rewrite SHALL replace only the target section's text. Every other byte of the source file, including frontmatter and other sections, SHALL be preserved. The rewriter SHALL receive only the query, the page title and the target section, never competitor text.

#### Scenario: Other sections untouched

- **WHEN** a rewrite is accepted
- **THEN** the written file equals the original file with only the target section's text replaced

### Requirement: Rewrites Must Pass Fidelity Rules And Judge

A rewritten section SHALL be rejected, keeping the original, when deterministic rules fail (heading line changed, a link removed or added, a number removed or added, fewer table rows, a code block changed, or a word-count ratio outside 0.8–1.6 for sections of 20 words or more), or when the Jev fidelity judge does not answer `faithful` with confidence of at least 0.6.

#### Scenario: Rewrite drops a link

- **WHEN** the rewritten section no longer contains a link present in the original
- **THEN** the page status is `rejected_fidelity_rules`
- **AND** the violation `link_removed:<url>` is reported

#### Scenario: Judge flags added claims

- **WHEN** the Jev fidelity judge answers `adds_claims`
- **THEN** the page status is `rejected_fidelity_judge`

### Requirement: Verification Re-Judges And Rejects Worse Rewrites

After a rewrite passes fidelity, the command SHALL score the same candidates again, under the same ids, with the rewritten section in place. The outcome SHALL be `won` when the best own-section score is strictly above every source score, `improved` when the target's score rises by at least 0.05, `worse` when it falls by at least 0.05, and `no_change` otherwise. A `worse` rewrite SHALL be rejected with status `rejected_worse`.

#### Scenario: Rewrite makes the page lose more

- **WHEN** the target section's score falls by 0.05 or more after the rewrite
- **THEN** the page status is `rejected_worse`
- **AND** no rewritten file is written

### Requirement: Section Mode Fails Closed Without Jev

`sections` mode SHALL exit non-zero with a message naming `TYPESAFE_API_KEY`, `GEO_EVAL_MOCK=1` and `--mode page` when no TypeSafe key is configured and mock mode is off. It SHALL never substitute heuristic scores for Jev answers. TypeSafe errors SHALL mark the page `jev_error` and never produce a rewrite. Outside mock mode, `sections` mode SHALL also exit non-zero before any work, naming `OPENAI_API_KEY`, when no rewriter key is configured; a rewriter failure (`LLMError`) SHALL mark that page `rewriter_error`, write no rewrite, and let the run continue.

#### Scenario: No key

- **WHEN** `TYPESAFE_API_KEY` is unset and `GEO_EVAL_MOCK` is off
- **THEN** `egeo fix-gaps gaps.json` exits non-zero before fetching or rewriting anything

### Requirement: Offline Mock Mode

With `GEO_EVAL_MOCK=1`, `sections` mode SHALL run without network access: sources are not fetched (placeholder text derived from the source URL), Jev answers come from a deterministic word-overlap mock, and the rewriter returns the section unchanged. The report SHALL record `"jev_model": "mock"`.

#### Scenario: CI run without keys

- **WHEN** `GEO_EVAL_MOCK=1 egeo fix-gaps gaps.json --out-dir out` runs with no API keys
- **THEN** it completes and writes `out/fix-gaps.json` without network calls

### Requirement: Jev Selection Is Validated Against A Live Engine

The repository SHALL include `eval/jev_selection/`. It SHALL score candidates with the same function and the same blind ids section mode uses. When a query maps to a local Markdown source, the page SHALL be represented by its sections as section mode builds them. Scores SHALL be compared against Perplexity's cited sources (positives) and uncited SERP results (negatives) per query, and the eval SHALL report the mean ROC AUC over sources with a bootstrap 95% interval, plus own-section outcomes (not gating). Each validation SHALL be pre-registered in a committed file before any result exists: query list hash, scorer, ids, unit, gate (mean AUC >= 0.65 with at least 25 scored queries) and the consequences of passing and failing. It SHALL use one collection and one evaluation, and SHALL NOT be re-tuned after seeing results. Documentation SHALL cite the latest result, its interval, its date and its pre-registration commit.

#### Scenario: Eval run

- **WHEN** the eval runs on a dataset of queries with cited and uncited URLs
- **THEN** it writes per-query AUC, the mean AUC, its bootstrap interval, the scorer, the ids mode, the unit and the number of scored queries

#### Scenario: Own-page prediction

- **WHEN** a dataset item has `own_source` pointing to a Markdown file
- **THEN** its own candidates are that file's sections of at least 30 words
- **AND** the own page is predicted to win (`own_wins`) only when its best section scores strictly above every source

#### Scenario: Leak diagnostic

- **WHEN** the eval runs with `--ids leaky`
- **THEN** candidates carry the 2.2.0 ids (`own_sXX` / `src_N`)
- **AND** the result is marked non-gating

### Requirement: Jev Candidates Are Blind

Every Jev request that compares candidates (diagnosis, verification and the validation eval) SHALL identify candidates only by neutral ids `c01`, `c02`, … assigned in an order derived from the query and the candidate texts. Jev SHALL NOT receive any id, label, host or kind that reveals which candidates are the site's own sections. Diagnosis and verification of the same page SHALL use the same id assignment, computed once from the original texts.

#### Scenario: Ownership is not revealed

- **WHEN** section mode sends the diagnosis request for a page with own sections and fetched sources
- **THEN** every candidate key in the request state matches `^c\d{2}$`
- **AND** no request contains an original candidate id (`own_…`, `src_…`), host or section heading

#### Scenario: Stable ids across diagnosis and verification

- **WHEN** the target section is rewritten and verification runs
- **THEN** every candidate keeps the id it had in the diagnosis request
