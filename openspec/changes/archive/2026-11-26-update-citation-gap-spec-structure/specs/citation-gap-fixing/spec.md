## MODIFIED Requirements

### Requirement: Diagnosis Against Real Cited Sources

In `sections` mode, for each processed page the command SHALL fetch the text of the sources the tracker reports for the page's gap query (excluding the project's own domain, at most `--max-sources`, default 6) and score, in one Jev request, each of the page's own sections of at least 30 words and each successfully fetched source with an independent Noul question.

#### Scenario: A cited source beats every own section

- **WHEN** the best source score is greater than or equal to the best own-section score
- **THEN** the own section with the highest score becomes the rewrite target
- **AND** the diagnosis status is `loses` and its `warning` is null
- **AND** the report records every candidate's score and the scorer

#### Scenario: An own section already wins

- **WHEN** the best own-section score is strictly above every source score
- **THEN** the own section with the highest score becomes the rewrite target and a rewrite is attempted
- **AND** the diagnosis status is `own_leads` and its `warning` is `own_text_already_competitive`
- **AND** the page status is the outcome of the rewrite (`rewritten`, `no_change_proposed`, `rejected_fidelity_rules`, `rejected_fidelity_judge`, `rejected_worse`, `jev_error` or `rewriter_error`), never `already_best`
- **AND** the page result carries an `offpage` recommendation listing the fetched cited sources, stating that if the query stays uncited the gap may be off-page (mentions and links)

#### Scenario: A leading page's rewrite is rejected

- **WHEN** the own text leads and the rewrite fails the fidelity rules, the fidelity judge or verification
- **THEN** the page status is the matching `rejected_*` status and no rewritten file is written
- **AND** the diagnosis still carries the warning and the page result still carries `offpage`

#### Scenario: No source text could be fetched

- **WHEN** none of the query's sources can be fetched
- **THEN** the page status is `no_competitor_sources`
- **AND** no rewrite is attempted

### Requirement: Section Mode Fails Closed Without Jev

`sections` mode SHALL exit non-zero with a message naming `TYPESAFE_API_KEY`, `GEO_EVAL_MOCK=1` and `--mode page` when no TypeSafe key is configured and mock mode is off. It SHALL never substitute heuristic scores for Jev answers. TypeSafe errors SHALL mark the page `jev_error` and never produce a rewrite.

#### Scenario: No key

- **WHEN** `TYPESAFE_API_KEY` is unset and `GEO_EVAL_MOCK` is off
- **THEN** `egeo fix-gaps gaps.json` exits non-zero before fetching or rewriting anything

### Requirement: Jev Selection Is Validated Against A Live Engine

The repository SHALL include `eval/jev_selection/`. It SHALL score candidates with the same function and the same blind ids section mode uses. When a query maps to a local Markdown source, the page SHALL be represented by its sections as section mode builds them.

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

## REMOVED Requirements

### Requirement: Report And Re-Measure List

**Reason**: One requirement of 1,693 characters covered six separate behaviors. Its text and its four scenarios are regrouped, word for word, into the six requirements added below.

**Migration**: None. No behavior changes; see "Fix-Gaps Report File And Re-Measure List", "Section-Mode Results In The Report", "Own-Text Warning And Off-Page Recommendation", "Section-Mode CLI Lines", "Report States What Jev Measures" and "Jev Validation Labeling In The Report".

## ADDED Requirements

### Requirement: Fix-Gaps Report File And Re-Measure List

Every non-dry run SHALL write `<out-dir>/fix-gaps.json` with the input format, mode, matched gaps, unmatched and skipped entries with reasons, per-page results and a `remeasure` list of gap queries. For geo-optimizer-skill input the report SHALL include the `geo citations` command to re-check them.

#### Scenario: Report after a mock run

- **WHEN** `GEO_EVAL_MOCK=1 egeo fix-gaps gaps.json --out-dir out` completes
- **THEN** `out/fix-gaps.json` exists with keys `format`, `mode`, `pages`, `unmatched`, `skipped`, `remeasure`, `note`

### Requirement: Section-Mode Results In The Report

In `sections` mode each page result SHALL include its status, fetched sources with success flags, the diagnosis, fidelity results, verification, output paths and `offpage`, and the report SHALL include Jev usage and the thresholds used. Diagnosis and verification SHALL report per-candidate `scores` and the `scorer` used.

#### Scenario: Sections-mode report

- **WHEN** a `sections` mode run completes
- **THEN** each page result includes its status, fetched sources with success flags, the diagnosis, fidelity results, verification, output paths and `offpage`
- **AND** the report includes Jev usage, the thresholds used, per-candidate `scores` and the `scorer`

### Requirement: Own-Text Warning And Off-Page Recommendation

Every non-null diagnosis SHALL carry a `warning` key, either null or `own_text_already_competitive`. `offpage` SHALL be non-null exactly when that warning is set, whatever the page status, and SHALL hold `reason` (`own_text_already_competitive`), a message and the URLs of the successfully fetched sources in fetch order.

#### Scenario: No warning, no off-page recommendation

- **WHEN** a diagnosis has `warning` null
- **THEN** the page result's `offpage` is null

#### Scenario: Warning set on any page status

- **WHEN** a diagnosis carries `own_text_already_competitive`
- **THEN** `offpage` is non-null whatever the page status
- **AND** it holds the reason, a message and the URLs of the successfully fetched sources in fetch order

### Requirement: Section-Mode CLI Lines

The CLI SHALL print one line per page: `<status>: <page_id>`, followed by ` (warning: own text already competitive; off-page: <n> cited sources)` when the warning is set.

#### Scenario: Warning on a rewritten page

- **WHEN** a page whose own text leads is rewritten and accepted
- **THEN** its result has status `rewritten`, `diagnosis.warning` `own_text_already_competitive` and a non-null `offpage`
- **AND** the CLI prints `rewritten: <page_id> (warning: own text already competitive; off-page: <n> cited sources)`

### Requirement: Report States What Jev Measures

The report SHALL state that Jev scores text competitiveness, does not model authority or links, and is not a prediction of citation.

#### Scenario: Statement in a sections-mode report

- **WHEN** a `sections` mode report is written
- **THEN** it states that Jev scores text competitiveness, does not model authority or links, and is not a prediction of citation

### Requirement: Jev Validation Labeling In The Report

The report SHALL carry a `jev_validation` object with the latest pre-registered result for the configuration section mode actually runs (protocol, scorer, ids, unit, mean AUC, 95% interval, number of queries, gate, pass/fail, date). Until that result passes the gate, the Jev comparison SHALL be labeled experimental: `jev_validation.status` SHALL be `"experimental"` and every Jev diagnosis and verification SHALL carry `"experimental": true`.

#### Scenario: Experimental labeling while the gate has not passed

- **WHEN** the latest validation result is below the gate
- **THEN** `fix-gaps.json` contains `jev_validation` with `"status": "experimental"` and `"gate_passed": false`
- **AND** each non-null diagnosis and verification carries `"experimental": true`

#### Scenario: Validation passed

- **WHEN** the latest pre-registered result for the running configuration passes the gate
- **THEN** `jev_validation` has `"status": "validated"` and `"gate_passed": true`
- **AND** diagnosis and verification carry no `experimental` flag
- **AND** the report still states that Jev is not a prediction of citation

### Requirement: Rewrite Target And Diagnosis Status

The rewrite target SHALL be the own section with the highest score, with ties going to the earliest section in the document. When the best source score is greater than or equal to the best own-section score, the diagnosis status SHALL be `loses` and it SHALL carry no warning. When the best own-section score is strictly above every source score, the diagnosis status SHALL be `own_leads` and the diagnosis SHALL carry the warning `own_text_already_competitive`.

#### Scenario: Tie between the best source and the best own section

- **WHEN** the best source score equals the best own-section score
- **THEN** the diagnosis status is `loses` and it carries no warning

#### Scenario: Two own sections share the highest score

- **WHEN** two own sections have the same highest score
- **THEN** the earlier section in the document is the rewrite target

### Requirement: A Jev Score Never Blocks A Rewrite

The page SHALL still be rewritten, through the same fidelity rules, fidelity judge and verification as a losing page. A Jev score SHALL never by itself stop a page from being rewritten.

#### Scenario: Own text leads

- **WHEN** the diagnosis status is `own_leads`
- **THEN** the page is still rewritten through the same fidelity rules, fidelity judge and verification as a losing page

### Requirement: Section Mode Needs A Rewriter Key

Outside mock mode, `sections` mode SHALL also exit non-zero before any work, naming `OPENAI_API_KEY`, when no rewriter key is configured; a rewriter failure (`LLMError`) SHALL mark that page `rewriter_error`, write no rewrite, and let the run continue.

#### Scenario: No rewriter key

- **WHEN** `sections` mode runs outside mock mode with no rewriter key configured
- **THEN** it exits non-zero before any work and names `OPENAI_API_KEY`

#### Scenario: Rewriter fails on one page

- **WHEN** the rewriter raises `LLMError` for a page
- **THEN** that page is marked `rewriter_error` and no rewrite is written for it
- **AND** the run continues with the remaining pages

### Requirement: Jev Validation Metric

Scores SHALL be compared against Perplexity's cited sources (positives) and uncited SERP results (negatives) per query, and the eval SHALL report the mean ROC AUC over sources with a bootstrap 95% interval, plus own-section outcomes (not gating).

#### Scenario: Positives and negatives

- **WHEN** the eval compares scores for a query
- **THEN** Perplexity's cited sources are the positives and uncited SERP results are the negatives
- **AND** own-section outcomes are reported and do not gate

### Requirement: Jev Validation Is Pre-Registered

Each validation SHALL be pre-registered in a committed file before any result exists: query list hash, scorer, ids, unit, gate (mean AUC >= 0.65 with at least 25 scored queries) and the consequences of passing and failing. It SHALL use one collection and one evaluation, and SHALL NOT be re-tuned after seeing results. Documentation SHALL cite the latest result, its interval, its date and its pre-registration commit.

#### Scenario: Pre-registered run fails the gate

- **WHEN** a pre-registered validation run finishes below the gate
- **THEN** the result is reported as it is, with its interval, date and pre-registration commit
- **AND** no re-run, prompt change or threshold change follows from it
