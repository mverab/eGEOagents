## ADDED Requirements

### Requirement: Page Rewrites Pass Deterministic Fidelity Rules

`egeo optimize` and page-mode `egeo fix-gaps` SHALL check the rewritten body against the original with the deterministic fidelity rules before writing it: no link or number removed or added, no fewer table rows, fenced code blocks unchanged, and at least 80% of the original word count. Ordered-list markers SHALL NOT count as numbers.

#### Scenario: Thin page grows

- **WHEN** a 28-word page is rewritten to 90 words with no link or number added or removed
- **THEN** the fidelity status is `passed`

#### Scenario: List markers are layout

- **WHEN** the rewrite turns a paragraph into a numbered list and changes nothing else
- **THEN** no `number_added` violation is reported

### Requirement: Failing Rewrites Are Repaired Once Or Kept Out Of `optimized/`

On a fidelity violation the rewriter SHALL be called exactly once more with the violations. A rewrite that still fails SHALL be written under `rejected/`, not `optimized/`, and reported with its violations. `--allow-lossy` SHALL write it under `optimized/` and still report the violations.

#### Scenario: Rewrite drops a source link

- **WHEN** the rewrite omits a URL present in the original and the repair attempt omits it too
- **THEN** no file is written under `optimized/`
- **AND** the rewrite is written under `rejected/`
- **AND** the report and `analysis.json` list `link_removed:<url>` with status `rejected`

#### Scenario: Repair attempt restores what was lost

- **WHEN** the first rewrite removes a number and the second one keeps it
- **THEN** the second rewrite is written under `optimized/`
- **AND** the fidelity status is `repaired` with `attempts: 2`

#### Scenario: Owner accepts a lossy rewrite

- **WHEN** `--allow-lossy` is set and the rewrite still fails after the repair attempt
- **THEN** the rewrite is written under `optimized/`
- **AND** the fidelity status is `lossy_allowed` with the violations listed

### Requirement: Rewriter Prompt Matches The Content Type

`egeo optimize` SHALL accept `--content-type auto|product|article`. With `auto`, a body of at least 150 words or at least 3 headings SHALL be treated as `article`, otherwise as `product`. `article` SHALL use the `rewriter_article_*` prompts, which do not ask for a "Best for" line or superlatives. The chosen content type SHALL be reported. The `product` prompts and `geo_eval evaluate` SHALL be unchanged.

#### Scenario: Long guide

- **WHEN** a 600-word guide is optimized with the default `--content-type auto`
- **THEN** the article prompts are used
- **AND** the report states `content_type: article`

#### Scenario: Short product description

- **WHEN** a 28-word product page is optimized with the default
- **THEN** the product prompts are used
