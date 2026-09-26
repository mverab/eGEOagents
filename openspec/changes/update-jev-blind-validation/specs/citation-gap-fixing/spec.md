## ADDED Requirements

### Requirement: Jev Candidates Are Blind

Every Jev request that compares candidates (diagnosis, verification and the validation eval) SHALL identify candidates only by neutral ids `c01`, `c02`, … assigned in an order derived from the query and the candidate texts. Jev SHALL NOT receive any id, label, host or kind that reveals which candidates are the site's own sections. Diagnosis and verification of the same page SHALL use the same id assignment, computed once from the original texts.

#### Scenario: Ownership is not revealed

- **WHEN** section mode sends the diagnosis request for a page with own sections and fetched sources
- **THEN** every candidate key in the request state matches `^c\d{2}$`
- **AND** no question text contains `own` or `src`

#### Scenario: Stable ids across diagnosis and verification

- **WHEN** the target section is rewritten and verification runs
- **THEN** every candidate keeps the id it had in the diagnosis request

## MODIFIED Requirements

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

### Requirement: Verification Re-Judges And Rejects Worse Rewrites

After a rewrite passes fidelity, the command SHALL score the same candidates again, under the same ids, with the rewritten section in place. The outcome SHALL be `won` when the best own-section score is strictly above every source score, `improved` when the target's score rises by at least 0.05, `worse` when it falls by at least 0.05, and `no_change` otherwise. A `worse` rewrite SHALL be rejected with status `rejected_worse`.

#### Scenario: Rewrite makes the page lose more

- **WHEN** the target section's score falls by 0.05 or more after the rewrite
- **THEN** the page status is `rejected_worse`
- **AND** no rewritten file is written

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
