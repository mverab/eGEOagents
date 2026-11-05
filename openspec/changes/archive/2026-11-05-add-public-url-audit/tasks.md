## 1. Core library (`egeo/url_audit.py`, stdlib only)
- [x] 1.1 Write URL validation and normalization (scheme, port, length, IP literal, bare domain) and the cache-key normalization, with tests.
- [x] 1.2 Write the SSRF-guarded fetcher with an injectable resolver: public-address check, connect to the vetted address, manual redirects (max 5, each re-vetted), 10 s timeout, 2 MB cap. Test private, loopback, link-local, CGNAT and IPv6 addresses and the redirect-to-metadata case.
- [x] 1.3 Write the HTML→Markdown converter (headings, paragraphs, lists, absolute links, tables; skip the `sources._SKIP` containers), with fixture tests that round-trip through `sections.split_sections`.
- [x] 1.4 Write the seven technical checks with `pass`/`fail`/`unverifiable`, evidence and fix text. Reuse `collectors/page.py` `parse_page` for title, description and JSON-LD; use `urllib.robotparser` for crawler access.
- [x] 1.5 Write the feature breakdown via `egeo.agents.Analyzer`, with `method: "heuristic"` and no aggregate score.
- [x] 1.6 Write query selection (visitor or `best <title>`) and section choice (40–600 words, lowest Analyzer total, document-order ties).
- [x] 1.7 Write the rewrite step: `rewrite_section`, then `check_fidelity`, with the closed status list. Make it deadline-aware (≥ 12 s remaining; LLM timeout = remaining − 1 s) and gated by a budget callback.
- [x] 1.8 Write `audit_url(...)`, which assembles the report. Add an end-to-end test under `GEO_EVAL_MOCK=1` with an injected fetcher and no network.

## 2. HTTP service (`egeo/audit_service.py`, extra `egeo[audit-service]`)
- [x] 2.1 Add the `audit-service` optional extra (fastapi, uvicorn) to `pyproject.toml`, imported lazily. Test that `import egeo, egeo.url_audit` works without the extra.
- [x] 2.2 Add a SQLite store for reports (24 h TTL, purge on write), the 1 h cache lookup, salted-hash per-IP daily counters and the daily LLM budget counter.
- [x] 2.3 Add the routes `POST /api/audit` and `GET /api/audit/{id}`, the error codes and statuses, the `Retry-After` header and the CORS allowlist (`AUDIT_ALLOWED_ORIGINS`).
- [x] 2.4 Enforce the limit order: validate → cache → IP limit → audit → reserve the budget just before the rewrite. Read the client IP from `CF-Connecting-IP`.
- [x] 2.5 Add the 30 s request deadline and the 504 `audit_timeout` response.
- [x] 2.6 Add service tests with a fake clock: 6th audit → 429; cache hit is free; budget exhausted → `skipped_budget`; expired id → 404; no listing route; no raw IP stored.

## 3. Deployment (owner VPS)
- [x] 3.1 Add a Dockerfile (or compose file) for the service, with env-configured limits, `REWRITER_MODEL`, the API key and the SQLite volume.
- [x] 3.2 Restrict the origin to Cloudflare (Tunnel or a firewall allowlist of Cloudflare ranges). Proxy the `api.egeoagents.com` DNS record through Cloudflare.
- [x] 3.3 Write a deploy and rollback runbook in `docs/` (start, stop, change limits, rotate the key).

## 4. Landing page (`site/`)
- [x] 4.1 Add the hero form (URL, optional query, "no account, no email" copy), keeping the site static.
- [x] 4.2 Add the client script: POST, static progress steps, 35 s client timeout, and messages for every error and for API-unreachable.
- [x] 4.3 Add the report view: checks with copy-fix, features labeled heuristic, before/after rewrite or the skip reason, and the expiry time. No aggregate score.
- [x] 4.4 Add the `#audit=<id>` fragment: set it after render, load from it on page load, handle the expired state, and a copy-link control.
- [x] 4.5 Add the post-report CTAs: `pip install egeo`, `/geo <url>`, and the service link with `utm_campaign=url_audit`.
- [x] 4.6 Extend `site/verify.sh` to assert the form is present. Confirm the sitemap-completeness check still passes, since no new route is added.
- [x] 4.7 Gate the form behind the build flag `PUBLIC_AUDIT_ENABLED` (set to `'false'` in `.github/workflows/site.yml`): hidden form and no client script when off, plus a `verify.sh` check that visibility matches the flag.
- [x] 4.8 Gate the docs page `/docs/url-audit/`, its sidebar entry and its `llms.txt` line behind the same flag, with `verify.sh` checks for both states.

## 5. Verification and docs
- [x] 5.1 Run `python -m pytest` (new and existing tests) and `npm run build && ./verify.sh` in `site/`.
- [x] 5.2 Do a manual smoke test against the deployed API with three public URLs: a static page, a JS-rendered page and a page that blocks GPTBot. Record the results in the PR.
- [x] 5.3 Update `CHANGELOG.md`, `USAGE.md` (service section) and `site/src/content/docs/docs/` with a short page on how the public audit works and what it does not measure.
- [x] 5.4 After 5.2 passes, set `PUBLIC_AUDIT_ENABLED: 'true'` in `.github/workflows/site.yml` and confirm the form is live on egeoagents.com.
