## MODIFIED Requirements

### Requirement: Rewrite View

When `rewrite.status` is `shown`, the page SHALL show:
- `before` and `after` side by side;
- the query used and its source ("your query" or "derived from title");
- a copy button for `after`;
- the fidelity note.

For any other status, the page SHALL show a plain-language reason. For `withheld_fidelity` it SHALL also list the violations. For `no_change` it SHALL say the model found nothing to improve in that section for the query used, and suggest trying a more specific target query.

#### Scenario: Report with a shown rewrite

- **WHEN** the API returns a report with `rewrite.status: "shown"`
- **THEN** the page shows the before/after section with the query used and the fidelity note

#### Scenario: Rewrite skipped for budget

- **WHEN** the API returns `rewrite.status: "skipped_budget"`
- **THEN** the page says the free daily rewrites are used up and points to `pip install egeo` to run it locally
- **AND** the checks and features are still shown

#### Scenario: Rewrite with no change

- **WHEN** the API returns `rewrite.status: "no_change"`
- **THEN** the page says the model found nothing to improve in that section for the query used, and suggests a more specific target query
- **AND** no before/after comparison is shown
