# Change: Detect bot challenges, clean derived queries, and alert on audit downtime

## Why

The 2026-11-11 review of the live audit (PRs #80–#89) found three problems:

1. **Bot challenges are audited as the real page, or rejected outright.** A challenge served with HTTP 200 is audited as if it were the page (title "Client Challenge", 36 words, a rewrite of challenge text). A challenge served with 403/429/503 returns `fetch_failed`. That is what most sites behind Cloudflare, PerimeterX or DataDome do: on 2026-11-11 that was medium.com, upwork.com, indeed.com, zillow.com, wayfair.com, g2.com and etsy.com. The visitor learns nothing, even though "your site challenges automated fetchers" is itself a GEO finding: AI crawlers likely get the same challenge.
2. **The derived query carries the site name.** `best <title>` keeps suffixes such as ` - Wikipedia` or ` | BBC`, so the rewrite targets a query that nobody searches. This is a 2.4.0 known limitation.
3. **Downtime is noticed hours late.** `audit-health.yml` is scheduled every 15 minutes, but GitHub delayed it to one run every 4–8 hours (21 runs from 2026-11-06 to 2026-11-11). A failure only emails whoever last edited the workflow.

## What Changes

- **Bot challenge detection** (`url-audit-api`).
  - An HTML response with status 200, 403, 429 or 503 is treated as a bot challenge when it has a known challenge title or a strong vendor marker, and fewer than `MIN_VISIBLE_WORDS` visible words.
  - Such a response produces a normal report, not `fetch_failed`. The report gets a new `challenge` object: `vendor`, `http_status`, `evidence`. Reports without a challenge have `challenge: null`.
  - `ai_crawler_access` and `llms_txt` still run. The five page checks become `unverifiable`, with evidence naming the challenge.
  - `features.items` is empty.
  - The rewrite is `skipped_challenge`. No LLM call is made and the daily budget is not consumed.
- **Site-name stripping for the derived query.** When the title has segments split by ` | `, ` - `, ` – `, ` — `, ` · ` or ` :: `, a first or last segment that names the site is dropped. A segment names the site when, lowercased and stripped to letters and digits, it contains the hostname's main label or that label contains it. At least one segment always remains.
- **Local health alert** (ops).
  - `deploy/audit-service/healthcheck.sh` probes the public API and the loopback API. A systemd user timer runs it every 5 minutes.
  - It sends one Telegram message through `hermes send` (configurable) when the state changes: up→down, naming which leg failed (tunnel or app), and down→up.
  - The GitHub workflow stays as an outside observer for a VPS that is down entirely. It becomes hourly, and its comments and the runbook state the real cadence.
- **Landing page.**
  - A challenged report shows a banner explaining the challenge and its GEO meaning.
  - An empty features list says the features were not scored.
  - `skipped_challenge` gets a plain-language reason.

## Impact

- Modified specs:
  - `url-audit-api`: "Audit Endpoints", "GEO Feature Breakdown", "Target Query Selection", "Rewrite Result Object";
  - `landing-url-audit`: "Report Checks And Features View", "Rewrite View".
- Added requirements:
  - `url-audit-api`: "Bot Challenge Detection", "Challenged Report", "Health Probe", "Health Alert On State Change".
- Code:
  - `egeo/url_audit.py`;
  - `site/src/scripts/url-audit.ts`;
  - `deploy/audit-service/healthcheck.sh` and its systemd units;
  - `.github/workflows/audit-health.yml`;
  - `docs/audit-service.md`, `site/src/content/docs/docs/url-audit.md`, `CHANGELOG.md`;
  - tests.
- API: one new top-level field (`challenge`) and one new rewrite status. Existing clients render unknown statuses as a generic reason.
