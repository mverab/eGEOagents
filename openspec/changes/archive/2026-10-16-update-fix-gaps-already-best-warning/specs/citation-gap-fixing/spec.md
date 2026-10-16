## MODIFIED Requirements

### Requirement: Diagnosis Against Real Cited Sources

In `sections` mode, for each processed page the command SHALL fetch the text of the sources the tracker reports for the page's gap query (excluding the project's own domain, at most `--max-sources`, default 6) and score, in one Jev request, each of the page's own sections of at least 30 words and each successfully fetched source with an independent Noul question. The rewrite target SHALL be the own section with the highest score, with ties going to the earliest section in the document. When the best source score is greater than or equal to the best own-section score, the diagnosis status SHALL be `loses` and it SHALL carry no warning. When the best own-section score is strictly above every source score, the diagnosis status SHALL be `own_leads` and the diagnosis SHALL carry the warning `own_text_already_competitive`. The page SHALL still be rewritten, through the same fidelity rules, fidelity judge and verification as a losing page. A Jev score SHALL never by itself stop a page from being rewritten.

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

### Requirement: Report And Re-Measure List

Every non-dry run SHALL write `<out-dir>/fix-gaps.json` with the input format, mode, matched gaps, unmatched and skipped entries with reasons, per-page results and a `remeasure` list of gap queries. For geo-optimizer-skill input the report SHALL include the `geo citations` command to re-check them. In `sections` mode each page result SHALL include its status, fetched sources with success flags, the diagnosis, fidelity results, verification, output paths and `offpage`, and the report SHALL include Jev usage and the thresholds used. Diagnosis and verification SHALL report per-candidate `scores` and the `scorer` used. Every non-null diagnosis SHALL carry a `warning` key, either null or `own_text_already_competitive`. `offpage` SHALL be non-null exactly when that warning is set, whatever the page status, and SHALL hold `reason` (`own_text_already_competitive`), a message and the URLs of the successfully fetched sources in fetch order. The CLI SHALL print one line per page: `<status>: <page_id>`, followed by ` (warning: own text already competitive; off-page: <n> cited sources)` when the warning is set. The report SHALL state that Jev scores text competitiveness, does not model authority or links, and is not a prediction of citation. The report SHALL carry a `jev_validation` object with the latest pre-registered result for the configuration section mode actually runs (protocol, scorer, ids, unit, mean AUC, 95% interval, number of queries, gate, pass/fail, date). Until that result passes the gate, the Jev comparison SHALL be labeled experimental: `jev_validation.status` SHALL be `"experimental"` and every Jev diagnosis and verification SHALL carry `"experimental": true`.

#### Scenario: Experimental labeling while the gate has not passed

- **WHEN** the latest validation result is below the gate
- **THEN** `fix-gaps.json` contains `jev_validation` with `"status": "experimental"` and `"gate_passed": false`
- **AND** each non-null diagnosis and verification carries `"experimental": true`

#### Scenario: Validation passed

- **WHEN** the latest pre-registered result for the running configuration passes the gate
- **THEN** `jev_validation` has `"status": "validated"` and `"gate_passed": true`
- **AND** diagnosis and verification carry no `experimental` flag
- **AND** the report still states that Jev is not a prediction of citation

#### Scenario: Warning on a rewritten page

- **WHEN** a page whose own text leads is rewritten and accepted
- **THEN** its result has status `rewritten`, `diagnosis.warning` `own_text_already_competitive` and a non-null `offpage`
- **AND** the CLI prints `rewritten: <page_id> (warning: own text already competitive; off-page: <n> cited sources)`

#### Scenario: Report after a mock run

- **WHEN** `GEO_EVAL_MOCK=1 egeo fix-gaps gaps.json --out-dir out` completes
- **THEN** `out/fix-gaps.json` exists with keys `format`, `mode`, `pages`, `unmatched`, `skipped`, `remeasure`, `note`
