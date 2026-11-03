# Public URL audit service: runbook

This runbook covers the service behind the audit form on egeoagents.com (`POST /api/audit` and `GET /api/audit/{id}` at `https://api.egeoagents.com`).

- Spec and design: `openspec/changes/add-public-url-audit/`.
- Code: `egeo/url_audit.py` (audit logic, stdlib only) and `egeo/audit_service.py` (HTTP layer, limits, store).
- Deploy files: `deploy/audit-service/`.

## Topology

```
browser (egeoagents.com) ──HTTPS──▶ Cloudflare ──Tunnel──▶ cloudflared ──▶ audit:8787 (container)
                                                                            └─ /data/audit.sqlite3
```

- **No published ports.** The API container publishes no ports, so the only way in is the Cloudflare Tunnel. That is why the service can trust `CF-Connecting-IP` for the per-IP limit. Never add a `ports:` mapping to `compose.yml`.
- **State.** All state is in one SQLite file on the `audit-data` volume: reports for 24 h, per-IP counters keyed by a daily-salted hash, today's salt, and today's LLM budget. Rows from earlier days are purged on write.

## One-time setup

1. Create a Cloudflare Tunnel in Zero Trust (Networks → Tunnels) for the `egeoagents.com` zone.
2. Add a public hostname to the tunnel: `api.egeoagents.com` → service `http://audit:8787`. Cloudflare creates the proxied DNS record.
3. On the VPS, clone the repository, then:
   ```bash
   cp deploy/audit-service/.env.example deploy/audit-service/.env
   ```
4. Fill in `OPENAI_API_KEY`, `REWRITER_MODEL` and `CLOUDFLARE_TUNNEL_TOKEN` in `.env`. The file is gitignored.

## Enable the landing form

The site builds the form hidden until the API is live: `.github/workflows/site.yml` sets `PUBLIC_AUDIT_ENABLED: 'false'`. Once `https://api.egeoagents.com/healthz` answers and the smoke test passes, change it to `'true'` in a PR. The merge redeploys the site with the form visible, and `site/verify.sh` checks that the form's visibility matches the flag.

## Deploy, update, stop

```bash
# start or update (rebuilds the image from the checked-out commit)
git pull
docker compose -f deploy/audit-service/compose.yml up -d --build

# check
docker compose -f deploy/audit-service/compose.yml ps        # audit should be "healthy"
curl -s https://api.egeoagents.com/healthz                   # {"ok":true}
curl -s -X POST https://api.egeoagents.com/api/audit \
  -H 'Content-Type: application/json' -d '{"url":"https://example.com/"}' | head -c 400

# logs
docker compose -f deploy/audit-service/compose.yml logs -f audit

# stop (the landing form then shows "service unavailable" and offers pip install)
docker compose -f deploy/audit-service/compose.yml down
```

## Change limits

Edit `deploy/audit-service/.env`, then run `docker compose ... up -d` (no rebuild needed).

| Variable | Default | Meaning |
|---|---|---|
| `AUDIT_IP_DAILY_LIMIT` | 5 | Uncached audits per client IP per UTC day; cache hits are free |
| `AUDIT_LLM_DAILY_CAP` | 200 | Rewrite LLM calls per UTC day for all visitors; past it, audits still run without the rewrite (`skipped_budget`) |
| `AUDIT_CACHE_TTL_S` | 3600 | Same URL and query within this window → same report, no fetch, no LLM |
| `AUDIT_REPORT_TTL_S` | 86400 | Report lifetime; after it, the link returns 404 |
| `AUDIT_ALLOWED_ORIGINS` | `https://egeoagents.com` | CORS allowlist, comma-separated (add `http://localhost:4321` only for development) |

The worst-case LLM spend per day is `AUDIT_LLM_DAILY_CAP` × the cost of one section rewrite with `REWRITER_MODEL`. Each audit makes at most one call, with no retries.

## Rotate the LLM key

1. Create the new key at the provider.
2. Update `OPENAI_API_KEY` in `.env` and run `docker compose ... up -d`.
3. Revoke the old key.

## Rollback

- **Site:** set `PUBLIC_AUDIT_ENABLED: 'false'` in `.github/workflows/site.yml` and merge. The form is hidden again and its script does not run. The rest of the landing page never depends on the API.
- **Service:** check out the previous commit and run `up -d --build`, or stop the service with `down`.
- **Data:** the SQLite file holds only short-lived data. Deleting the volume (`docker volume rm <project>_audit-data`) resets reports and counters.

## Data held

The service stores:
- the audited URL and query, plus the report JSON, for 24 h;
- per-IP counters as `sha256(daily_salt + ip)`, with the salt deleted after its UTC day;
- the daily LLM counter.

It does not store raw IPs, request headers, emails or cookies, and sets no cookies.

## Local development

```bash
pip install -e ".[audit-service]"
GEO_EVAL_MOCK=1 AUDIT_ALLOWED_ORIGINS=http://localhost:4321 AUDIT_DB_PATH=/tmp/audit.sqlite3 egeo-audit-service
# API on http://127.0.0.1:8787. For the site, run `npm run dev` in site/ with
# PUBLIC_AUDIT_ENABLED=true PUBLIC_AUDIT_API=http://127.0.0.1:8787 so the form shows
# and posts to the local API.
```

`GEO_EVAL_MOCK=1` makes the rewrite return the section unchanged, with no LLM call.
