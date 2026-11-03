# Change: Public URL audit on the egeoagents.com landing page

## Why

Every GEO tool in the 2026-10-27 competitor research (`docs/research/2026-10-27-url-audit-competitors.md`) lets a visitor paste a URL and see a report. egeoagents.com can't do that today: the landing page sends visitors to `pip install egeo` or to the $199 service. The research also found a gap: none of the five tools rewrites the visitor's content, and eGEO already has a section rewriter with deterministic fidelity rules (`egeo/section_rewriter.py`, `egeo/fidelity.py`). A free audit that ends with one rewritten section, before and after, shows what eGEO does that the others don't.

## What Changes

- **New audit service (Python, separate from the static site).** It exposes `POST /api/audit` and `GET /api/audit/{id}`. The service imports the `egeo` package, so it reuses the existing logic and does not reimplement it in another language. It runs as a container on an owner-run VPS, reachable as `api.egeoagents.com` behind Cloudflare. It ships as an optional extra (`egeo[audit-service]`), so the core package keeps its two dependencies.
- **Audit content (v1):**
  - Deterministic technical checks: reachability/HTML, AI-crawler access in `robots.txt`, `/llms.txt`, JSON-LD, `<title>`, meta description, one `<h1>`, and visible text without JavaScript. Each check reports `pass`, `fail` or `unverifiable`, together with the observed evidence.
  - The existing offline `Analyzer` scores the 10 GEO features (0–10 each), labeled as a heuristic.
  - One LLM rewrite of the weakest qualifying section against the visitor's optional target query. If no query is given, it is derived from the page title (no LLM). The rewrite is checked by the deterministic fidelity rules and is shown only if it passes. It is labeled as not verified by the judge.
- **No single 0–100 score, no benchmark and no "ceiling".** The report shows the breakdown and its evidence. `unverifiable` results never count as a pass or a fail.
- **No gate, ephemeral report.** No account and no email. Each report gets an unguessable id and expires after 24 h. The site renders it from `https://egeoagents.com/#audit=<id>`. There is no public leaderboard and no indexable report page.
- **Abuse and cost limits:**
  - a per-IP daily audit limit;
  - a 1 h cache per normalized URL and query;
  - a global daily LLM-rewrite cap. When the cap is reached, the audit still runs and the rewrite is skipped with a stated reason;
  - SSRF protection: no private, loopback, link-local or reserved targets, re-checked on every redirect.
- **Synchronous response.** One request returns the full report within a 30 s budget. If the rewrite would exceed that budget, it is skipped and the report says so.
- **Landing form and report view.** The hero gets a URL form with an optional query field. The page shows static progress steps and then renders the report in place. The CTAs that follow the report are `pip install egeo`, `/geo` in Claude Code, and the existing $199 service.

## Impact

- New capabilities: `url-audit-api`, `landing-url-audit`.
- No existing spec is modified. The active spec `citation-gap-fixing` is untouched. No pending change in `openspec/changes/` overlaps with this one.
- Code (at implementation, not in this proposal):
  - new `egeo/url_audit.py`: core fetch, checks, HTML→Markdown, section pick, rewrite and report;
  - new `egeo/audit_service.py`: the HTTP app, limits, cache and report store;
  - reuse of `egeo/agents.py` (`Analyzer`), `egeo/sections.py`, `egeo/section_rewriter.py`, `egeo/fidelity.py`, `collectors/page.py` (`parse_page`) and `llm_client.py`;
  - `pyproject.toml` (optional extra), `site/src/pages/index.astro` (form and report view), `site/verify.sh` (form present), deploy files for the VPS, and tests.
- Operations: a new always-on service with an LLM API key, a SQLite file for reports and limits, and a DNS record for `api.egeoagents.com`. LLM spend is bounded by the daily rewrite cap.
- Privacy: the service stores the audited URL, the query and the report for 24 h, and per-IP counters keyed by a salted hash that rotates daily. It stores no raw IPs and no personal data.
