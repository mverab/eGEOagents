## MODIFIED Requirements

### Requirement: Rewrite Section Selection

The service SHALL convert the page's main HTML to Markdown and split it with `egeo.sections.split_sections`. Candidate sections are the non-preamble sections with 40–600 words that are not excluded as non-content (see the requirement "Non-Content Section Exclusion"). It SHALL rewrite only the candidate with the lowest `Analyzer` total, breaking ties by document order, using `egeo.section_rewriter.rewrite_section` and the report's query. It SHALL make at most one LLM call per audit.

#### Scenario: No qualifying section

- **WHEN** every non-preamble section has fewer than 40 words
- **THEN** `rewrite.status` is `skipped_no_candidate`
- **AND** no LLM request is made

#### Scenario: One call only

- **WHEN** a page has several qualifying sections
- **THEN** exactly one section is rewritten
- **AND** exactly one LLM request is made

### Requirement: Rewrite Result Object

`rewrite` SHALL have:
- `status`: `shown`, `no_change`, `withheld_fidelity`, `skipped_no_candidate`, `skipped_budget`, `skipped_timeout` or `error`;
- `query`;
- `section_heading`;
- `before`;
- `after`, only when `shown`;
- `violations`, only when `withheld_fidelity`;
- `note`: "Checked by deterministic fidelity rules; not verified by an LLM judge."

A rewriter error SHALL NOT fail the audit.

#### Scenario: Rewrite shown

- **WHEN** the page has a qualifying section and the rewrite passes the fidelity rules and differs from the original
- **THEN** `rewrite.status` is `shown` with both `before` and `after`, and the fidelity `note`

#### Scenario: Rewriter error

- **WHEN** the LLM provider returns an error
- **THEN** `rewrite.status` is `error`
- **AND** the rest of the report is returned with HTTP 200

## ADDED Requirements

### Requirement: Unchanged Rewrite Reported As No Change

When a rewrite passes the fidelity rules but equals the original section after whitespace normalization (runs of whitespace collapsed, ends trimmed), `rewrite.status` SHALL be `no_change` and the report SHALL contain no `after` text. The LLM call SHALL still count against the daily rewrite cap.

#### Scenario: Model returns the section unchanged

- **WHEN** the LLM returns the selected section with only whitespace differences
- **THEN** `rewrite.status` is `no_change`
- **AND** the report contains `before` but no `after`

#### Scenario: Offline mock mode

- **WHEN** the audit runs with `GEO_EVAL_MOCK=1`, where the rewriter returns the section unchanged
- **THEN** `rewrite.status` is `no_change`

### Requirement: Non-Content Section Exclusion

A section SHALL NOT be a rewrite candidate when its heading is a single Markdown link, or when at least half of its non-empty body lines (excluding the heading line) are a lone Markdown link, optionally as a list item or followed by one separator character. These rules are deterministic.

#### Scenario: Site header is skipped

- **WHEN** the lowest-scoring 40–600-word section has the heading `[Example Weblog](https://example.com/)`
- **THEN** that section is not rewritten
- **AND** the next lowest-scoring content section is chosen instead

#### Scenario: Footer link list is skipped

- **WHEN** a section's body is a list of lone links (for example "Pricing", "Blog", "Careers")
- **THEN** that section is not a candidate
