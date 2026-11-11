# landing-url-audit Specification

## Purpose
The free URL audit as egeoagents.com visitors see it: the hero form, the in-place report view, the 24 h shareable `#audit=<id>` link, the calls to action after a report, and the error and API-down messages. The site stays static, and a build flag keeps the form and its docs page out until the API is live.

## Requirements

### Requirement: Audit Form On The Landing Page

The landing page (`site/src/pages/index.astro`) SHALL include, in the hero section, a form with:
- a required URL input;
- an optional target-query input, up to 200 characters;
- a submit button.

The form SHALL state that no account or email is required. On submit it SHALL `POST` to `https://api.egeoagents.com/api/audit`. The site SHALL stay fully static: no server code is added to `site/`.

#### Scenario: Form present in the build

- **WHEN** the site is built
- **THEN** `dist/index.html` contains the audit form with a URL input and an optional query input
- **AND** `site/verify.sh` checks for that form and passes

#### Scenario: Visitor submits a URL

- **WHEN** a visitor enters `example.com` and submits
- **THEN** the page sends `POST /api/audit` with `{"url": "example.com", "query": null}`
- **AND** it shows static progress steps (fetching page, running checks, rewriting one section) until the response arrives

### Requirement: Audit Form Hidden Until The API Is Live

The form SHALL be visible only when the site is built with `PUBLIC_AUDIT_ENABLED=true`. In any other build, the form SHALL stay in the HTML with the `hidden` attribute and the client script SHALL not run, so the landing page never offers an audit that cannot run. The site workflow SHALL set the flag, and `site/verify.sh` SHALL check that the form's visibility matches it.

#### Scenario: Built before the API is live

- **WHEN** the site is built with `PUBLIC_AUDIT_ENABLED` unset or `false`
- **THEN** `dist/index.html` contains the audit form with the `hidden` attribute
- **AND** no request is sent to the audit API on page load

#### Scenario: Built after the API is live

- **WHEN** the site is built with `PUBLIC_AUDIT_ENABLED=true`
- **THEN** the audit form is visible and `site/verify.sh` passes

### Requirement: Audit Docs Page Gated By The Same Flag

The docs page `/docs/url-audit/`, its sidebar entry and its `llms.txt` line SHALL be built only when `PUBLIC_AUDIT_ENABLED=true`. `site/verify.sh` SHALL check that they match the flag.

#### Scenario: Docs page left out before the API is live

- **WHEN** the site is built with `PUBLIC_AUDIT_ENABLED` unset or `false`
- **THEN** `/docs/url-audit/` is not built, and neither the sidebar, the sitemap nor `llms.txt` links to it

#### Scenario: Docs page published with the form

- **WHEN** the site is built with `PUBLIC_AUDIT_ENABLED=true`
- **THEN** `/docs/url-audit/` is built and listed in the sidebar and `llms.txt`

### Requirement: Report Checks And Features View

The landing page SHALL render the returned report in place, without navigating away.
- Each check SHALL show its status (`pass`, `fail` or `unverifiable`) and its evidence. A failed check SHALL also show its fix with a copy button.
- The 10 GEO features SHALL show their 0–10 scores under a visible "heuristic" label, plus recommendations for scores below 5.
- The report's expiry time SHALL be shown.
- No aggregate score, benchmark or ceiling SHALL be shown.

#### Scenario: Checks and features rendered

- **WHEN** the API returns a report with `challenge: null`
- **THEN** the page shows seven check rows with status and evidence, and 10 features labeled as heuristic
- **AND** no single overall score is shown

### Requirement: Challenged Report View

When `challenge` is not null, the landing page SHALL:
- show a banner above the checks saying that the site answered with a bot challenge, naming the vendor (unless it is `unknown`) and the HTTP status, and that AI crawlers may get the same challenge and fail to read the page;
- say, in place of feature scores, that the features were not scored because the page itself could not be read.

#### Scenario: Challenged report rendered

- **WHEN** the API returns a report with `challenge.vendor: "cloudflare"` and `challenge.http_status: 403`
- **THEN** the page shows the challenge banner naming Cloudflare and HTTP 403, the seven check rows, and a "features not scored" message instead of feature scores

### Requirement: Rewrite View

When `rewrite.status` is `shown`, the page SHALL show:
- `before` and `after` side by side;
- the query used and its source ("your query" or "derived from title");
- a copy button for `after`;
- the fidelity note.

For any other status, the page SHALL show a plain-language reason (see "Rewrite Status Reasons").

#### Scenario: Report with a shown rewrite

- **WHEN** the API returns a report with `rewrite.status: "shown"`
- **THEN** the page shows the before/after section with the query used and the fidelity note

### Requirement: Rewrite Status Reasons

For a status other than `shown`, the page's reason SHALL follow these rules:
- for `withheld_fidelity`, it SHALL also list the violations;
- for `no_change`, it SHALL say the model found nothing to improve in that section for the query used, and suggest trying a more specific target query;
- for `skipped_challenge`, it SHALL say that no rewrite was attempted because the page itself could not be read.

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

### Requirement: Shareable Ephemeral Report Link

After a report renders, the page SHALL set the location fragment to `#audit=<id>` and offer a copy-link control. On load with `#audit=<id>`, the page SHALL fetch `GET /api/audit/<id>` and render that report. On a 404, it SHALL say the report expired after 24 hours and show the form. No new site route SHALL be added for reports, so report links never appear in the sitemap.

#### Scenario: Opening a shared link

- **WHEN** someone opens `https://egeoagents.com/#audit=<id>` within 24 h of the audit
- **THEN** the page loads and renders the same report

#### Scenario: Opening an expired link

- **WHEN** someone opens `https://egeoagents.com/#audit=<id>` after the report expired
- **THEN** the page shows an "expired" message and the audit form

### Requirement: Post-Report Calls To Action

Below every rendered report, the page SHALL show:
- `pip install egeo`, with a copy button;
- `/geo <url>` for Claude Code users, with the audited URL filled in;
- the existing "GEO Audit & Implementation" service link, with UTM `utm_campaign=url_audit`.

#### Scenario: CTAs after a report

- **WHEN** a report for `https://example.com/` renders
- **THEN** the page shows a copyable `pip install egeo`, a copyable `/geo https://example.com/`, and the service link carrying `utm_campaign=url_audit`

### Requirement: API Error Messages

The page SHALL show a specific, human-readable message for each API error code:
- `invalid_url` and `invalid_query`: what to fix;
- `blocked_target`: the URL cannot be audited;
- `rate_limited`: the daily limit was reached, with the retry time from `Retry-After`;
- `fetch_failed`: the page could not be fetched, with the upstream reason;
- `audit_timeout`: try again later.

#### Scenario: Rate limited

- **WHEN** the API responds 429 with `Retry-After: 3600`
- **THEN** the page says the daily free audits are used up and to retry in about 1 hour

### Requirement: API Unavailable Fallback

When the API cannot be reached (a network error, or no response within 35 s), the page SHALL say the audit service is unavailable and show `pip install egeo` as the alternative. The rest of the landing page SHALL work without the API.

#### Scenario: API down

- **WHEN** the request to the API fails with a network error
- **THEN** the page shows that the audit service is unavailable and offers `pip install egeo`
- **AND** the rest of the landing page is unaffected
