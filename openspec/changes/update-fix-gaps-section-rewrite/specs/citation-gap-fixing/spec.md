## MODIFIED Requirements

### Requirement: Fix-Gaps Command Rewrites Pages For Uncited Queries

The CLI SHALL expose `egeo fix-gaps <gaps-file> [--mode sections|page] [--dry-run] [--json] [--out-dir DIR] [--format markdown|html] [--project PATH] [--max-sources N] [--jev-model MODEL]`. The command SHALL read citation results from a tracker export, select the queries where the project domain is not cited, and map them to local pages through `project.yaml`. In `sections` mode (the default) it SHALL rewrite at most one section per page as specified by the section-mode requirements. In `page` mode it SHALL optimize each affected page once with the existing `egeo optimize` pipeline.

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

#### Scenario: Legacy page mode

- **WHEN** `egeo fix-gaps gaps.json --mode page` runs
- **THEN** each affected page is optimized with the `egeo optimize` pipeline as in version 2.1.0

### Requirement: Report And Re-Measure List

Every non-dry run SHALL write `<out-dir>/fix-gaps.json` with the input format, mode, matched gaps, unmatched and skipped entries with reasons, per-page results and a `remeasure` list of gap queries. For geo-optimizer-skill input the report SHALL include the `geo citations` command to re-check them. In `sections` mode each page result SHALL include its status, fetched sources with success flags, the diagnosis, fidelity results, verification and output paths, and the report SHALL include Jev usage and the thresholds used. The report SHALL state that Jev's choice and the ranking harness are proxies, not live engine results.

#### Scenario: Report after a mock run

- **WHEN** `GEO_EVAL_MOCK=1 egeo fix-gaps gaps.json --out-dir out` completes
- **THEN** `out/fix-gaps.json` exists with keys `format`, `mode`, `pages`, `unmatched`, `skipped`, `remeasure`, `note`

## ADDED Requirements

### Requirement: Diagnosis Against Real Cited Sources

In `sections` mode, for each processed page the command SHALL fetch the text of the sources the tracker reports for the page's gap query (excluding the project's own domain, at most `--max-sources`, default 6) and ask Jev one Choice question over the page's own sections of at least 30 words and the successfully fetched sources. If an own section wins, the page status SHALL be `already_best` and nothing SHALL be rewritten. If a source wins, the rewrite target SHALL be the own section with the highest probability.

#### Scenario: A cited source beats every own section

- **WHEN** Jev selects a fetched source for the query
- **THEN** the own section with the highest probability becomes the rewrite target
- **AND** the report records the winner, its kind, the probabilities and the confidence

#### Scenario: An own section already wins

- **WHEN** Jev selects one of the page's own sections
- **THEN** the page status is `already_best`
- **AND** no rewrite is attempted

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

After a rewrite passes fidelity, the command SHALL ask the same Jev Choice question with the rewritten section in place and the same candidates. The outcome SHALL be `won` when an own section wins, `improved` when the target's probability rises by at least 0.05, `worse` when it falls by at least 0.05, and `no_change` otherwise. A `worse` rewrite SHALL be rejected with status `rejected_worse`.

#### Scenario: Rewrite makes the page lose more

- **WHEN** the target section's probability falls by 0.05 or more after the rewrite
- **THEN** the page status is `rejected_worse`
- **AND** no rewritten file is written

### Requirement: Section Mode Fails Closed Without Jev

`sections` mode SHALL exit non-zero with a message naming `TYPESAFE_API_KEY`, `GEO_EVAL_MOCK=1` and `--mode page` when no TypeSafe key is configured and mock mode is off. It SHALL never substitute heuristic scores for Jev answers. TypeSafe errors SHALL mark the page `jev_error` and never produce a rewrite.

#### Scenario: No key

- **WHEN** `TYPESAFE_API_KEY` is unset and `GEO_EVAL_MOCK` is off
- **THEN** `egeo fix-gaps gaps.json` exits non-zero before fetching or rewriting anything

### Requirement: Offline Mock Mode

With `GEO_EVAL_MOCK=1`, `sections` mode SHALL run without network access: sources are not fetched (placeholder text derived from the source URL), Jev answers come from a deterministic word-overlap mock, and the rewriter returns the section unchanged. The report SHALL record `"jev_model": "mock"`.

#### Scenario: CI run without keys

- **WHEN** `GEO_EVAL_MOCK=1 egeo fix-gaps gaps.json --out-dir out` runs with no API keys
- **THEN** it completes and writes `out/fix-gaps.json` without network calls

### Requirement: Jev Selection Is Validated Against A Live Engine

The repository SHALL include `eval/jev_selection/`, which scores Jev's Choice probabilities against Perplexity's cited sources (positives) and uncited SERP results (negatives) per query and reports the mean ROC AUC. Documentation of section-mode verification SHALL cite the latest result and its date.

#### Scenario: Eval run

- **WHEN** the eval runs on a dataset of queries with cited and uncited URLs
- **THEN** it writes per-query AUC, the mean AUC and the number of scored queries
