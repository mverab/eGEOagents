## MODIFIED Requirements

### Requirement: Report Checks And Features View

The landing page SHALL render the returned report in place, without navigating away.
- Each check SHALL show its status (`pass`, `fail` or `unverifiable`) and its evidence. A failed check SHALL also show its fix with a copy button.
- The 10 GEO features SHALL show their 0–10 scores under a visible "heuristic" label, plus recommendations for scores below 5. When `features.items` is empty, the page SHALL say that the features were not scored because the page itself could not be read.
- When `challenge` is not null, a banner above the checks SHALL say that the site answered with a bot challenge (naming the vendor unless it is `unknown`, and the HTTP status), and that AI crawlers may get the same challenge and fail to read the page.
- The report's expiry time SHALL be shown.
- No aggregate score, benchmark or ceiling SHALL be shown.

#### Scenario: Checks and features rendered

- **WHEN** the API returns a report with `challenge: null`
- **THEN** the page shows seven check rows with status and evidence, and 10 features labeled as heuristic
- **AND** no single overall score is shown

#### Scenario: Challenged report rendered

- **WHEN** the API returns a report with `challenge.vendor: "cloudflare"` and `challenge.http_status: 403`
- **THEN** the page shows the challenge banner naming Cloudflare and HTTP 403, the seven check rows, and a "features not scored" message instead of feature scores

### Requirement: Rewrite View

When `rewrite.status` is `shown`, the page SHALL show:
- `before` and `after` side by side;
- the query used and its source ("your query" or "derived from title");
- a copy button for `after`;
- the fidelity note.

For any other status, the page SHALL show a plain-language reason:
- for `withheld_fidelity`, it SHALL also list the violations;
- for `no_change`, it SHALL say the model found nothing to improve in that section for the query used, and suggest trying a more specific target query;
- for `skipped_challenge`, it SHALL say that no rewrite was attempted because the page itself could not be read.

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

#### Scenario: Rewrite skipped for a challenge

- **WHEN** the API returns `rewrite.status: "skipped_challenge"`
- **THEN** the page says no rewrite was attempted because the page could not be read
