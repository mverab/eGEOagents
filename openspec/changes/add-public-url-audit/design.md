## Context

- `site/` is a static Astro Starlight build deployed to Cloudflare Pages (`.github/workflows/site.yml`). The site has no server code. A browser cannot fetch arbitrary third-party pages because of CORS, so the audit needs a server.
- The repo already has the parts an audit needs, all in Python:
  - `egeo.agents.Analyzer`: offline, deterministic scoring of the 10 GEO features, no LLM;
  - `collectors/page.py` `parse_page`: title, meta description, JSON-LD `@type`s and word count, stdlib only;
  - `egeo/sections.py`: byte-exact Markdown section split;
  - `egeo/section_rewriter.py`: one LLM call per section, with `GEO_EVAL_MOCK` support;
  - `egeo/fidelity.py`: deterministic rules on links, numbers, headings, tables, code and length;
  - `llm_client.py`: an OpenAI-compatible client plus `MockClient`.
- `egeo/sources.py` `default_fetcher` follows redirects with plain `urllib` and has no SSRF guard. It is safe for the CLI, where the user picks the URLs, but not for a public endpoint.
- Owner decisions taken for this change (2026-11-02):
  - v1 scope is deterministic checks plus one rewrite;
  - the backend is a separate Python service on an owner VPS (`api.egeoagents.com`);
  - there is no gate and the report link is ephemeral;
  - limits are a per-IP limit, a cache and a global daily LLM cap;
  - the report shows a breakdown with no single score;
  - the target query is optional and supplied by the visitor, the rewrite is checked by fidelity rules only, and the response is synchronous with a timeout.

## Goals / Non-Goals

- Goals:
  - A visitor pastes a URL and gets an honest, evidence-backed report in ≤ 30 s.
  - The report includes one real rewritten section that passed the fidelity rules.
  - Spend and abuse have hard upper bounds.
  - Report logic is reused from `egeo`, with no second implementation.
- Non-Goals (v1):
  - market-question generation, niche detection, benchmarks or cohorts, improvement ceilings;
  - accounts, email capture, saved history, a public leaderboard or permanent report URLs;
  - live answer-engine citation checks;
  - multi-page crawls;
  - paid monitoring;
  - JavaScript rendering (headless browser).

## Decisions

### D1. Core library plus a thin HTTP app

`egeo/url_audit.py` holds every rule and is pure and testable:
- `audit_url(url, query=None, *, fetcher, resolver, rewrite_enabled, deadline) -> dict`;
- fetching through an injectable fetcher;
- the checks;
- HTML→Markdown;
- section selection;
- the rewrite and fidelity check;
- report assembly.

`egeo/audit_service.py` holds only the HTTP concerns: the routes, CORS, client-IP extraction, rate limits, the cache, the report store and the LLM budget.

**Why:** the logic can be tested without a server, and the same function can later back a CLI command.

**Alternatives:**
- Cloudflare Pages Functions in TypeScript: rejected because the checks and the Analyzer would have to be reimplemented and the two copies would drift.
- Python Workers: rejected because of limited dependency and outbound-HTTP support.

### D2. FastAPI and uvicorn as an optional extra

The new extra is `egeo[audit-service]`. The core `pip install egeo` keeps its two dependencies. `egeo/audit_service.py` imports FastAPI lazily, so importing `egeo` never requires it.

**Alternative:** stdlib `http.server`. It was rejected because it has no request validation, the CORS and timeout handling would have to be written by hand, and it is not meant for public traffic.

### D3. SQLite on the VPS for reports, cache, rate counters and the LLM budget

There is one file with three small tables:
- `reports(id, created_at, expires_at, cache_key, json)`;
- `ip_counts(day, ip_hash, count)`;
- `llm_budget(day, used)`.

The 1 h cache is a lookup on `reports` by `cache_key` with `created_at` within 1 h. Expired rows are purged on each write.

**Why:** state survives restarts on a single box and there is no new managed service.

**Alternative:** in-memory dicts, like GeoReady. They were rejected because a restart would reset the daily LLM cap.

### D4. SSRF-guarded fetcher

The fetcher is new and lives in `url_audit`. It does not reuse `sources.default_fetcher`.

- Only `http` and `https` are accepted, on ports 80 and 443.
- The host must be a public DNS name, not an IP literal.
- Every resolved address must be globally routable. Private, loopback, link-local, CGNAT, multicast, reserved and unspecified addresses are rejected, for both IPv4 and IPv6.
- The connection goes to the vetted address so DNS cannot be rebound between check and connect.
- Redirects are followed manually: at most 5, and each hop is re-vetted.
- Each fetch has a 10 s timeout and reads at most 2 MB.

`robots.txt` and `/llms.txt` are fetched with the same guard, from the final page's origin.

### D5. Client IP and origin

Behind Cloudflare the client IP is taken from `CF-Connecting-IP`. The origin accepts traffic only from Cloudflare, either through a firewall allowlist of Cloudflare ranges or a Cloudflare Tunnel, so that header can't be spoofed by a direct hit.

Per-IP counters store `sha256(daily_salt + ip)`. The salt rotates daily and is never persisted past its day.

CORS allows `https://egeoagents.com`. The `AUDIT_ALLOWED_ORIGINS` setting can add `http://localhost:4321` for development.

### D6. Limits and their order

Defaults can be overridden through the environment:
- `AUDIT_IP_DAILY_LIMIT=5`;
- `AUDIT_LLM_DAILY_CAP=200`;
- `AUDIT_CACHE_TTL_S=3600`;
- `AUDIT_REPORT_TTL_S=86400`.

The order is: validate the input → cache hit → per-IP limit → run the audit → reserve one unit of LLM budget just before the rewrite.

A cache hit returns the cached report and does not count toward the IP limit or the LLM budget. When the budget is exhausted, the rewrite is skipped with the reason `daily_budget_exhausted`. A rewrite that errors still consumes its reserved unit, because the provider may have billed it.

### D7. HTML→Markdown for sectioning

`sections.split_sections` and `fidelity` work on Markdown. A small stdlib `html.parser` converter therefore emits:
- `#`…`######` for `h1`–`h6`;
- paragraphs separated by blank lines;
- `- ` list items;
- `[text](href)` links with absolute URLs;
- pipe tables as `| … |` rows.

It skips the same containers as `sources._SKIP` (`head`, `script`, `style`, `noscript`, `nav`, `footer`, `header`, `svg`, `form`, `template`).

The before/after view shows Markdown. That is also the format the visitor would paste into a CMS or hand to `egeo`.

### D8. Section choice and query

- **Candidate sections:** non-preamble sections with 40–600 words.
- **Pick:** the candidate with the lowest `Analyzer` total. Ties go to the earliest section.
- **Query:** the visitor's query, trimmed, ≤ 200 characters; otherwise `f"best {title}"`, as `egeo.pipeline.optimize_content` derives it. `title` is the page `<title>`, or the first `h1` when the title is empty.
- **Fidelity:** `fidelity.check_fidelity(before, after)` with its default ratios. On failure the rewrite is withheld and the report lists the violations. Unfaithful text is never shown.
- **Label:** the rewrite is labeled "checked by deterministic fidelity rules; not verified by an LLM judge".

### D9. Report shape: breakdown, no single score

The report contains:
- `checks[]`, each with `id`, `status` (`pass` / `fail` / `unverifiable`), `evidence` and `fix` (fix only when `fail`);
- `features`: `{method: "heuristic", note, items[]}`, where each item has `id`, `score` 0–10 and `recommendation` when `< 5`;
- `rewrite`, with `status` from the closed list `shown` / `withheld_fidelity` / `skipped_no_candidate` / `skipped_budget` / `skipped_timeout` / `error`, plus `query`, `query_source` (`visitor` / `derived`), `section_heading`, `before`, `after` and `violations`;
- `expires_at`.

There is no aggregate number. `unverifiable` is reported as its own status and is never folded into a pass count.

### D10. Report link is a URL fragment on the landing page

The share link is `https://egeoagents.com/#audit=<id>`. The fragment never reaches a server or a crawler, so:
- no new page is built;
- the sitemap-completeness check in `site/verify.sh` stays as it is;
- nothing becomes indexable.

The id is 128 bits of `secrets.token_urlsafe`. Once the report expires, `GET` returns 404 and the page says the report expired and offers to run the audit again.

### D11. Synchronous within 30 s

The service tracks one deadline per request.

- Fetching the page, `robots.txt` and `llms.txt` plus all checks must finish before the deadline. Otherwise the request returns 504 `audit_timeout`.
- The rewrite starts only if at least 12 s remain. Otherwise it is skipped with `skipped_timeout`.
- The LLM call gets the remaining time minus 1 s as its timeout.

## Risks / Trade-offs

- **The Analyzer is a keyword heuristic.** It could be mistaken for a real ranking signal. → The report labels it `heuristic`, and the landing copy says so.
- **Many sites render content with JavaScript, so there is little or no text without JS.** → The `visible_text` check reports it with evidence (the word count). The rewrite is then usually `skipped_no_candidate`. Rendering is a non-goal for v1.
- **A single VPS is a single point of failure.** → The landing form shows an error state with the `pip install egeo` fallback when the API is unreachable. The rest of the static site does not depend on the API.
- **The LLM cap could be exhausted by a burst.** → The degrade path is a full report without the rewrite. The cap is an environment setting.
- **Third-party sites may block the user agent.** → `fetch_failed` is reported with the HTTP status. The user agent identifies eGEO and `egeoagents.com`.
- **Fidelity rules allow tone changes that the owner of the audited page might dislike.** → The rewrite is shown as a suggestion. The source page is never modified.

## Migration Plan

This change is additive: nothing existing changes.

1. Ship the library and the service behind the extra.
2. Deploy to the VPS with DNS for `api.egeoagents.com` proxied through Cloudflare.
3. Ship the landing form last.

Rollback: remove the form from `index.astro` and redeploy the site. The service can stay up or be stopped independently.

## Open Questions

- **Default limit values** (5 audits per IP per day, 200 rewrites per day): confirm before deploy.
- **LLM provider and model for public rewrites:** the default is `REWRITER_MODEL`, as in the CLI.
- **`egeo audit-url <url>`:** whether a later change should add this CLI command over the same core function.
- **Later funnel steps from the research** (email capture, Turnstile, market questions, benchmark, monitoring upsell): each would be a separate change.
