# url-audit-api Specification

## Purpose
The public URL audit service behind `https://api.egeoagents.com`. It takes a visitor's URL and optional target query and returns an ephemeral report: seven deterministic technical checks, the 10 GEO features scored by the offline heuristic Analyzer, and at most one LLM-rewritten section that passes the fidelity rules. Per-IP limits, a cache, a daily LLM cap and SSRF guards bound its cost and its abuse surface.

## Requirements

### Requirement: Audit Endpoints

The audit service SHALL expose `POST /api/audit` with a JSON body `{"url": string, "query": string | null}` and `GET /api/audit/{id}`. A successful `POST` SHALL return HTTP 200 with a report containing `id`, `url` (normalized input), `final_url` (after redirects), `query`, `query_source`, `checks`, `features`, `rewrite`, `created_at` and `expires_at`. `GET` SHALL return the stored report unchanged.

#### Scenario: Successful audit

- **WHEN** a client posts `{"url": "https://example.com/pricing"}` and the page returns 200 with HTML
- **THEN** the response is HTTP 200 with a report containing every listed field
- **AND** `GET /api/audit/{id}` with the returned id returns the same report

### Requirement: Audit Error Responses

Errors SHALL be JSON `{"error": <code>, "message": <text>}` with these code/status pairs:
- `invalid_url` 400;
- `invalid_query` 400;
- `blocked_target` 422;
- `rate_limited` 429, with a `Retry-After` header;
- `fetch_failed` 502, with a message carrying the upstream status or error class;
- `audit_timeout` 504;
- `not_found` 404, on `GET` only.

A failed audit SHALL NOT store a report.

#### Scenario: Unreachable page

- **WHEN** the target page responds with HTTP 403
- **THEN** the response is HTTP 502 with `error: "fetch_failed"` and a message naming status 403
- **AND** no report is stored

### Requirement: CORS Allowlist

The service SHALL send CORS headers only for origins in `AUDIT_ALLOWED_ORIGINS`, which defaults to `https://egeoagents.com`.

#### Scenario: Disallowed origin

- **WHEN** a browser request arrives with `Origin: https://evil.example`
- **THEN** the response carries no `Access-Control-Allow-Origin` header for that origin

### Requirement: Target URL Validation

The service SHALL accept only absolute `http` or `https` URLs of at most 2,048 characters. The port SHALL be absent, 80 or 443, and the host SHALL be a DNS name, not an IP literal. Any other input SHALL be rejected with `invalid_url`. A bare domain such as `example.com` SHALL be normalized to `https://example.com/`.

#### Scenario: Unsupported scheme or port

- **WHEN** a client posts `file:///etc/passwd`, `ftp://example.com/` or `https://example.com:8443/`
- **THEN** the response is HTTP 400 with `error: "invalid_url"`

#### Scenario: Bare domain normalized

- **WHEN** a client posts `{"url": "example.com"}`
- **THEN** the audited URL is `https://example.com/`

### Requirement: SSRF-Guarded Fetching

Before connecting, the service SHALL resolve the host and reject the request with `blocked_target` if any address is not globally routable (private, loopback, link-local, CGNAT, multicast, reserved or unspecified, in IPv4 or IPv6). It SHALL then connect to a vetted address. It SHALL follow at most 5 redirects, re-validating every hop. Each fetch SHALL time out after 10 s and read at most 2,000,000 bytes. The `robots.txt` and `/llms.txt` fetches SHALL use the same guard.

#### Scenario: Private address rejected

- **WHEN** a client posts a URL whose host resolves to `10.0.0.5` or `127.0.0.1`
- **THEN** the response is HTTP 422 with `error: "blocked_target"`
- **AND** no connection is made to that address

#### Scenario: Redirect into a private network

- **WHEN** a public page responds 302 to `http://169.254.169.254/latest/meta-data/`
- **THEN** the redirect is not followed
- **AND** the response is HTTP 422 with `error: "blocked_target"`

### Requirement: Technical Check Set

The report's `checks` SHALL list, in this order, `ai_crawler_access`, `llms_txt`, `json_ld`, `title`, `meta_description`, `single_h1` and `visible_text`. Each check SHALL be computed without an LLM and SHALL carry:
- `status`: `pass`, `fail` or `unverifiable`;
- `evidence`: the observed value behind the status;
- `fix`: a one-sentence, copy-paste-ready instruction, included only when `status` is `fail`.

#### Scenario: Check order and shape

- **WHEN** any audit completes
- **THEN** `checks` has the seven ids in the listed order, each with `status` and `evidence`
- **AND** only checks with status `fail` have a `fix`

### Requirement: AI Crawler Access Check

`ai_crawler_access` SHALL evaluate the `robots.txt` at the final page's origin for the audited path and these user agents: `GPTBot`, `OAI-SearchBot`, `ChatGPT-User`, `ClaudeBot`, `PerplexityBot` and `Google-Extended`.
- `pass`: none is disallowed. A `robots.txt` that returns 404 also counts as `pass`.
- `fail`: at least one is disallowed. The evidence names the blocked agents.
- `unverifiable`: the fetch failed or returned any other status.

#### Scenario: Crawlers blocked in robots.txt

- **WHEN** the site's `robots.txt` contains `User-agent: GPTBot` followed by `Disallow: /`
- **THEN** `ai_crawler_access` is `fail` with evidence naming `GPTBot` and a `fix` that says which rule to change

#### Scenario: robots.txt cannot be fetched

- **WHEN** fetching `robots.txt` times out
- **THEN** `ai_crawler_access` is `unverifiable` and has no `fix`

### Requirement: llms.txt Check

`llms_txt` SHALL fetch `<origin>/llms.txt`.
- `pass`: the response is 200 with a non-HTML content type.
- `fail`: the response is 404, or 200 with an HTML content type.
- `unverifiable`: any other result.

#### Scenario: Soft-404 HTML page

- **WHEN** `/llms.txt` returns 200 with `Content-Type: text/html`
- **THEN** `llms_txt` is `fail`

### Requirement: Page Metadata Checks

Each check SHALL pass under this condition and use this evidence:
- `json_ld`: at least one `application/ld+json` block yields an `@type`. Evidence: the types.
- `title`: `<title>` is non-empty. Evidence: the title.
- `meta_description`: `<meta name="description">` has non-empty content. Evidence: the content.
- `single_h1`: the HTML has exactly one `h1`. Evidence: the count.

Otherwise the check SHALL be `fail`.

#### Scenario: Two h1 elements

- **WHEN** the page has two `h1` elements
- **THEN** `single_h1` is `fail` with evidence `2`

### Requirement: Visible Text Check

`visible_text` SHALL count the words visible without JavaScript, outside skipped containers. It SHALL be `pass` at 150 words or more and `fail` below that. The evidence SHALL be the word count.

#### Scenario: JavaScript-rendered page

- **WHEN** the HTML body has 12 visible words outside skipped containers
- **THEN** `visible_text` is `fail` with evidence `12 words`

### Requirement: GEO Feature Breakdown

The report's `features` SHALL be an object `{method: "heuristic", note, items}`. Its `items` SHALL list the 10 GEO features scored by the existing offline `egeo.agents.Analyzer` on the page's extracted Markdown. Each item SHALL have `id`, an integer `score` from 0 to 10, and a `recommendation` when the score is below 5.

#### Scenario: Ten features

- **WHEN** any audit completes
- **THEN** `features.items` has 10 entries, each with an integer score between 0 and 10, and `features.method` is `heuristic`

### Requirement: No Aggregate Score

The report SHALL NOT contain a single aggregate score, a percentile, a benchmark against other sites, or a projected "ceiling" score. A status of `unverifiable` SHALL NOT be counted as a pass or a fail anywhere in the report.

#### Scenario: Breakdown only

- **WHEN** any audit completes
- **THEN** the report has no top-level numeric score, percentile, benchmark or ceiling field

### Requirement: Target Query Selection

The `query` field SHALL be optional.
- When present, it SHALL be trimmed. It SHALL be rejected with `invalid_query` if the trimmed text is empty or longer than 200 characters. `query_source` SHALL be `visitor`.
- When it is absent, the service SHALL derive `best <title>` without an LLM, using the page `<title>`, or the first `h1` if the title is empty. `query_source` SHALL be `derived`.

#### Scenario: Visitor query used

- **WHEN** a client posts `{"url": "https://example.com/", "query": "privacy friendly analytics"}`
- **THEN** the report has `query: "privacy friendly analytics"` and `query_source: "visitor"`

#### Scenario: Derived query

- **WHEN** a client posts no query and the page title is `Acme Analytics`
- **THEN** the report has `query: "best Acme Analytics"` and `query_source: "derived"`

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

### Requirement: Rewrite Fidelity Gate

Every rewrite SHALL be checked with `egeo.fidelity.check_fidelity(before, after)` using the default ratios. The rewritten text SHALL appear in the report only when the check passes. Otherwise `rewrite.status` SHALL be `withheld_fidelity`, `rewrite.violations` SHALL list the violations, and the report SHALL contain no `after` text.

#### Scenario: Rewrite fails fidelity

- **WHEN** the rewrite adds a number that is not in the original section
- **THEN** `rewrite.status` is `withheld_fidelity`
- **AND** `violations` includes `number_added:<n>`
- **AND** the report contains no `after` text

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

### Requirement: Per-IP Daily Limit

The service SHALL limit each client IP to `AUDIT_IP_DAILY_LIMIT` uncached audits per UTC day (default 5); cache hits SHALL NOT count. The IP SHALL be read from `CF-Connecting-IP`, and the service SHALL accept connections only from Cloudflare. Over the limit, it SHALL respond 429 `rate_limited` with `Retry-After` set to the seconds until the next UTC midnight.

#### Scenario: Sixth audit in a day

- **WHEN** one IP has completed 5 uncached audits today and posts a new URL
- **THEN** the response is HTTP 429 with `error: "rate_limited"` and a `Retry-After` header

#### Scenario: Cache hit does not consume the limit

- **WHEN** an IP that has used 5 audits today posts a URL and query audited less than 1 h ago
- **THEN** the cached report is returned with HTTP 200

### Requirement: Report Cache

The service SHALL cache reports for `AUDIT_CACHE_TTL_S` seconds (default 3,600). The cache key is the normalized URL plus the effective query; normalization lowercases the scheme and host, drops the fragment and default ports, and turns an empty path into `/`. A cache hit SHALL return the stored report, keeping its original `id` and `expires_at`, without fetching the page or calling the LLM.

#### Scenario: Repeat audit within an hour

- **WHEN** the same URL and query are posted twice within 1 h
- **THEN** the second response returns the first report's `id`
- **AND** no outbound fetch or LLM call is made for it

### Requirement: Global Daily LLM Rewrite Cap

The service SHALL allow at most `AUDIT_LLM_DAILY_CAP` rewrite LLM calls per UTC day across all clients (default 200). It SHALL reserve one unit just before each call; a reserved unit stays consumed even if the call fails. When the cap is reached, the audit SHALL still complete with HTTP 200 and `rewrite.status: "skipped_budget"`.

#### Scenario: Budget exhausted

- **WHEN** 200 rewrite calls have been made today and a new uncached audit runs
- **THEN** the report is returned with every check and feature
- **AND** `rewrite.status` is `skipped_budget`
- **AND** no LLM request is made

### Requirement: Ephemeral Reports

Each report id SHALL carry at least 128 bits of randomness. A report SHALL be retrievable until `expires_at`, which is `created_at` plus `AUDIT_REPORT_TTL_S` (default 86,400 s). After that, `GET` SHALL return 404 `not_found` and the report SHALL be deleted. The service SHALL NOT expose any endpoint that lists reports.

#### Scenario: Expired report

- **WHEN** a client requests a report id 25 h after it was created
- **THEN** the response is HTTP 404 with `error: "not_found"`

#### Scenario: No listing

- **WHEN** a client requests `GET /api/audit` or `GET /api/audits`
- **THEN** the response is not a list of reports

### Requirement: Response Deadline

Each `POST /api/audit` SHALL complete within 30 s.
- If the page fetch and checks have not finished by then, the service SHALL respond 504 `audit_timeout`.
- The rewrite SHALL start only if at least 12 s remain; otherwise `rewrite.status` SHALL be `skipped_timeout`.
- The LLM call's timeout SHALL be the remaining time minus 1 s.

#### Scenario: Slow page leaves no time to rewrite

- **WHEN** fetching the page and running the checks takes 20 s
- **THEN** the report is returned with `rewrite.status: "skipped_timeout"`
- **AND** no LLM request is made

### Requirement: Stored Data Minimization

The service SHALL store only:
- reports: the URL, query and report JSON, with timestamps;
- per-IP counters keyed by `sha256(daily_salt + ip)`, where the salt rotates every UTC day and is not kept after that day;
- the daily LLM budget counter.

It SHALL NOT store raw IPs, request headers, emails or cookies, and it SHALL NOT set cookies.

#### Scenario: No raw IP persisted

- **WHEN** an audit completes
- **THEN** the service's database contains no column or value equal to the client's IP address

### Requirement: Offline Mock Mode

With `GEO_EVAL_MOCK=1`, the core audit function and the service SHALL run without calling an LLM; the rewrite returns the section unchanged, as `rewrite_section` already does. With an injected fetcher and resolver, tests SHALL run with no network access.

#### Scenario: Offline test run

- **WHEN** the test suite runs with `GEO_EVAL_MOCK=1` and fixture HTML served by an injected fetcher
- **THEN** a full report is produced with no outbound network request

### Requirement: Optional Service Install

The HTTP dependencies SHALL be an optional extra, `egeo[audit-service]`. Without the extra, `import egeo` and `import egeo.url_audit` SHALL keep working.

#### Scenario: Core install unaffected

- **WHEN** `pip install egeo` is run without extras and `python -c "import egeo, egeo.url_audit"` is executed
- **THEN** both imports succeed

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
