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

## Live deployment (since 2026-11-05)

Production runs **without Docker** on the owner VPS (`srv1379360`, user `hermes-2`), because that user has no Docker access. There are two systemd **user** services, kept running by linger:

| Unit | What it runs |
|---|---|
| `egeo-audit.service` | `~/.local/share/egeo-audit/venv/bin/egeo-audit-service` on `127.0.0.1:8787` |
| `egeo-audit-tunnel.service` | `~/.local/bin/cloudflared` (2024.12.2), tunnel `egeo-audit`, config `~/.local/share/egeo-audit/tunnel.yml` |

- **Config:** `~/.local/share/egeo-audit/service.env`, with the limits, origins, DB path and model.
- **Key:** `~/.local/share/egeo-audit/secrets.env` (mode 600). It holds only `OPENAI_API_KEY`.
- **Data:** `~/.local/share/egeo-audit/data/audit.sqlite3`.
- **Binding:** the API binds to loopback only, so the tunnel is still the only way in from outside.

### Deploy without Docker

```bash
D=~/.local/share/egeo-audit
mkdir -p "$D" ~/.local/bin
curl -sSL -o ~/.local/bin/cloudflared https://github.com/cloudflare/cloudflared/releases/download/2024.12.2/cloudflared-linux-amd64
chmod +x ~/.local/bin/cloudflared
python3 -m venv "$D/venv"
SRC="$(mktemp -d)"; git archive main | tar -x -C "$SRC"   # a clean copy of main
"$D/venv/bin/pip" install "$SRC[audit-service]"   # never `-e`: production must not follow the working tree
deploy/audit-service/setup-user-systemd.sh   # asks for the OpenAI key and a Cloudflare login link
```

The script can be re-run: it skips what is already done. It creates the tunnel, writes the DNS record, installs both units and checks `https://api.egeoagents.com/healthz`.

### Operate

```bash
systemctl --user status egeo-audit egeo-audit-tunnel
journalctl --user -u egeo-audit -n 100
systemctl --user restart egeo-audit           # after editing service.env or secrets.env
# update to the current main
git fetch && SRC="$(mktemp -d)" && git archive origin/main | tar -x -C "$SRC" \
  && "$D/venv/bin/pip" install --no-deps --force-reinstall "$SRC" && systemctl --user restart egeo-audit
```

### Alerts

`.github/workflows/audit-health.yml` probes `https://api.egeoagents.com/healthz` every 15 minutes. It also requests an unknown report id, which must return `not_found`; that proves requests reach the app through the tunnel. It retries 3 times, 30 s apart, before it fails. GitHub emails a failed scheduled run to whoever last changed the workflow's schedule. To test it, run it by hand from the Actions tab (*Run workflow*).

GitHub pauses scheduled workflows after 60 days without repository activity. If the repo goes quiet for that long, re-enable the workflow in the Actions tab.

The sections below describe the Docker Compose alternative. It is still supported for a host where Docker is available.

## One-time setup

1. Create a Cloudflare Tunnel in Zero Trust (Networks → Tunnels) for the `egeoagents.com` zone.
2. Add a public hostname to the tunnel: `api.egeoagents.com` → service `http://audit:8787`. Cloudflare creates the proxied DNS record.
3. On the VPS, clone the repository, then:
   ```bash
   cp deploy/audit-service/.env.example deploy/audit-service/.env
   ```
4. Fill in `OPENAI_API_KEY`, `REWRITER_MODEL` and `CLOUDFLARE_TUNNEL_TOKEN` in `.env`. The file is gitignored.

## Enable the landing form

The site builds the form hidden until the API is live: `.github/workflows/site.yml` sets `PUBLIC_AUDIT_ENABLED: 'false'`. Once `https://api.egeoagents.com/healthz` answers and the smoke test passes, change it to `'true'` in a PR. The merge redeploys the site with the form visible. The same flag also publishes the docs page `/docs/url-audit/`, its sidebar entry and its `llms.txt` line. `site/verify.sh` checks that all of them match the flag.

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

- **Site:** set `PUBLIC_AUDIT_ENABLED: 'false'` in `.github/workflows/site.yml` and merge. The form is hidden again, its script does not run, and the docs page drops out of the build. The rest of the landing page never depends on the API.
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
