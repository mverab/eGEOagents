## MODIFIED Requirements

### Requirement: Audit Endpoints

The audit service SHALL expose `POST /api/audit` with a JSON body `{"url": string, "query": string | null}` and `GET /api/audit/{id}`. A successful `POST` SHALL return HTTP 200 with a report containing `id`, `url` (normalized input), `final_url` (after redirects), `query`, `query_source`, `checks`, `features`, `rewrite`, `challenge`, `created_at` and `expires_at`. `challenge` SHALL be `null` unless a bot challenge was detected. `GET` SHALL return the stored report unchanged.

#### Scenario: Successful audit

- **WHEN** a client posts `{"url": "https://example.com/pricing"}` and the page returns 200 with HTML
- **THEN** the response is HTTP 200 with a report containing every listed field, with `challenge: null`
- **AND** `GET /api/audit/{id}` with the returned id returns the same report

### Requirement: GEO Feature Breakdown

The report's `features` SHALL be an object `{method: "heuristic", note, items}`. Its `items` SHALL list the 10 GEO features scored by the existing offline `egeo.agents.Analyzer` on the page's extracted Markdown. Each item SHALL have `id`, an integer `score` from 0 to 10, and a `recommendation` when the score is below 5. When a bot challenge was detected, `items` SHALL be empty.

#### Scenario: Ten features

- **WHEN** an audit completes without a bot challenge
- **THEN** `features.items` has 10 entries, each with an integer score between 0 and 10, and `features.method` is `heuristic`

#### Scenario: No features for a challenge

- **WHEN** an audit completes with a bot challenge
- **THEN** `features.items` is empty and `features.method` is `heuristic`

### Requirement: Target Query Selection

The `query` field SHALL be optional.
- When present, it SHALL be trimmed. It SHALL be rejected with `invalid_query` if the trimmed text is empty or longer than 200 characters. `query_source` SHALL be `visitor`.
- When it is absent, the service SHALL derive `best <subject>` without an LLM. The subject is the page `<title>`, or the first `h1` if the title is empty, with the site name stripped. `query_source` SHALL be `derived`.
- For a challenged page with no visitor query, the subject SHALL instead be the hostname without a leading `www.`, ignoring the challenge page's title and `h1`.

To strip the site name, the title is split on ` | `, ` - `, ` – `, ` — `, ` · ` and ` :: `. The first or last segment SHALL be dropped when it names the site. A segment names the site when, lowercased and reduced to letters and digits, it contains the hostname's main label (at least 3 characters) or, when the segment has more than 3 characters, that label contains it. At least one segment SHALL remain, and the remaining segments SHALL be rejoined with their original separators.

#### Scenario: Visitor query used

- **WHEN** a client posts `{"url": "https://example.com/", "query": "privacy friendly analytics"}`
- **THEN** the report has `query: "privacy friendly analytics"` and `query_source: "visitor"`

#### Scenario: Derived query

- **WHEN** a client posts no query and the page title is `Acme Analytics`
- **THEN** the report has `query: "best Acme Analytics"` and `query_source: "derived"`

#### Scenario: Site name stripped from the derived query

- **WHEN** a client posts no query for `https://en.wikipedia.org/wiki/Generative_engine_optimization` and the title is `Generative engine optimization - Wikipedia`
- **THEN** the report has `query: "best Generative engine optimization"`

#### Scenario: Title that is only the site name

- **WHEN** a client posts no query for `https://www.bbc.com/` and the title is `BBC`
- **THEN** the report has `query: "best BBC"`

#### Scenario: Derived query for a challenged page

- **WHEN** a client posts no query for `https://www.example.com/` and the page is a Cloudflare challenge titled `Just a moment...`
- **THEN** the report has `query: "best example.com"` and `query_source: "derived"`

### Requirement: Rewrite Result Object

`rewrite` SHALL have:
- `status`: `shown`, `no_change`, `withheld_fidelity`, `skipped_no_candidate`, `skipped_budget`, `skipped_timeout`, `skipped_challenge` or `error`;
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

### Requirement: Bot Challenge Detection

A fetched HTML page with HTTP status 200, 403, 429 or 503 SHALL be treated as a bot challenge only when BOTH of these hold:
- it has a known challenge title or a strong vendor marker (lists in `design.md` D1);
- it has fewer than `MIN_VISIBLE_WORDS` visible words.

Any other non-200 status SHALL still return `fetch_failed`.

#### Scenario: Vendor script on a real page

- **WHEN** the target page responds with HTTP 200, contains `/cdn-cgi/challenge-platform/` and has 900 visible words
- **THEN** the report has `challenge: null` and the page checks run normally

#### Scenario: Plain 403

- **WHEN** the target page responds with HTTP 403 and no challenge signal
- **THEN** the response is HTTP 502 with `error: "fetch_failed"`

### Requirement: Challenged Report

For a detected challenge, the audit SHALL return a report, not `fetch_failed`, with:
- `challenge: {vendor, http_status, evidence}`, where `vendor` is `cloudflare`, `perimeterx`, `datadome`, `imperva`, `akamai`, `ddos-guard` or `unknown`;
- `ai_crawler_access` and `llms_txt` computed as usual, and the five page checks `unverifiable`, with evidence naming the challenge;
- `features.items` empty;
- `rewrite.status: skipped_challenge`, with no LLM call and no use of the daily cap.

#### Scenario: Cloudflare challenge served with 403

- **WHEN** the target page responds with HTTP 403, title `Just a moment...` and `_cf_chl_opt` in its HTML
- **THEN** the response is HTTP 200 with `challenge.vendor: "cloudflare"` and `challenge.http_status: 403`
- **AND** the five page checks are `unverifiable` and `rewrite.status` is `skipped_challenge`
- **AND** the daily LLM budget is unchanged

#### Scenario: Challenge served with 200

- **WHEN** the target page responds with HTTP 200, title `Client Challenge` and 36 visible words
- **THEN** the report has a non-null `challenge` with `vendor: "unknown"`, and no rewrite is attempted

### Requirement: Health Probe

The repository SHALL ship `deploy/audit-service/healthcheck.sh`, plus systemd user units that run it every 5 minutes. The API SHALL count as up only when:
- the public `/healthz` returns 200; and
- an unknown report id returns a body containing `"not_found"`.

The script SHALL try `AUDIT_HEALTH_TRIES` times before reporting down. It SHALL exit 0 when up and 1 when down.

#### Scenario: Healthy API

- **WHEN** both public probes succeed
- **THEN** the script exits 0

### Requirement: Health Alert On State Change

The script SHALL send exactly one message through `AUDIT_ALERT_CMD` per state change, up→down or down→up. The first run SHALL only record the state. A down alert SHALL say whether the loopback API is up (tunnel or Cloudflare problem) or down (app problem).

#### Scenario: API goes down

- **WHEN** the recorded state is up, the public probe fails all tries, and the loopback `/healthz` returns 200
- **THEN** one alert is sent naming the tunnel/Cloudflare leg, the state becomes down, and the exit code is 1

#### Scenario: Still down

- **WHEN** the recorded state is down and the probe fails again
- **THEN** no alert is sent

#### Scenario: Recovery

- **WHEN** the recorded state is down and the probe succeeds
- **THEN** one recovery alert is sent and the state becomes up
