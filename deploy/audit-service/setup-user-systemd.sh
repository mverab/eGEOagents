#!/usr/bin/env bash
# Sets up the eGEO public URL audit API on this VPS, without Docker or sudo:
#   1. asks for the OpenAI key (hidden) and checks it against OpenAI;
#   2. logs in to Cloudflare (open the link it prints, pick egeoagents.com, Authorize);
#   3. creates the tunnel "egeo-audit" and the DNS record api.egeoagents.com;
#   4. installs and starts two systemd user services (API + tunnel);
#   5. checks https://api.egeoagents.com/healthz.
# Safe to run again: every step skips what is already done.
# Prerequisite: the service installed in ~/.local/share/egeo-audit/venv and cloudflared in
# ~/.local/bin (see docs/audit-service.md, "Deploy without Docker").
set -euo pipefail

D="$HOME/.local/share/egeo-audit"
CF="$HOME/.local/bin/cloudflared"
HOSTNAME_API="api.egeoagents.com"
TUNNEL="egeo-audit"
UNITS="$HOME/.config/systemd/user"
SECRETS="$D/secrets.env"

say() { printf '\n==> %s\n' "$*"; }
die() { printf '\nERROR: %s\n' "$*" >&2; exit 1; }

[ -x "$D/venv/bin/egeo-audit-service" ] || die "service not installed in $D/venv"
[ -x "$CF" ] || die "cloudflared not found at $CF"

# 1. OpenAI key -------------------------------------------------------------
key_ok() {
  local k
  k="$(sed -n 's/^OPENAI_API_KEY=//p' "$SECRETS" 2>/dev/null || true)"
  [ -n "$k" ] || return 1
  [ "$(curl -s -o /dev/null -w '%{http_code}' --max-time 20 \
        -H "Authorization: Bearer $k" https://api.openai.com/v1/models)" = 200 ]
}
say "1/5 OpenAI key"
until key_ok; do
  echo "Paste the FULL key from platform.openai.com/api-keys (Create new secret key -> Copy)."
  echo "Nothing is shown while you paste. Press Enter after pasting."
  read -rsp 'Key: ' K; echo
  K="$(printf '%s' "$K" | tr -d '[:space:]')"
  umask 077; printf 'OPENAI_API_KEY=%s\n' "$K" > "$SECRETS"; unset K
  key_ok && break
  echo "OpenAI rejected that key (or it was a masked copy with dots). Try again."
done
chmod 600 "$SECRETS"
echo "OK: OpenAI accepted the key."

# 2. Cloudflare login -------------------------------------------------------
say "2/5 Cloudflare login"
if [ -f "$HOME/.cloudflared/cert.pem" ]; then
  echo "OK: already logged in."
else
  echo "Open the link below NOW (it expires in a few minutes), pick egeoagents.com, click Authorize."
  "$CF" tunnel login
  [ -f "$HOME/.cloudflared/cert.pem" ] || die "login did not finish; run this script again"
fi

# 3. Tunnel + DNS -----------------------------------------------------------
say "3/5 Tunnel and DNS"
if ! "$CF" tunnel info "$TUNNEL" >/dev/null 2>&1; then
  "$CF" tunnel create "$TUNNEL"
fi
TID="$("$CF" tunnel list --output json | python3 -c "import json,sys; print(next(t['id'] for t in json.load(sys.stdin) if t['name']=='$TUNNEL'))")"
[ -f "$HOME/.cloudflared/$TID.json" ] || die "tunnel credentials $HOME/.cloudflared/$TID.json missing; delete the tunnel in the dashboard and rerun"
cat > "$D/tunnel.yml" <<EOF
tunnel: $TID
credentials-file: $HOME/.cloudflared/$TID.json
ingress:
  - hostname: $HOSTNAME_API
    service: http://127.0.0.1:8787
  - service: http_status:404
EOF
"$CF" tunnel route dns --overwrite-dns "$TUNNEL" "$HOSTNAME_API"
echo "OK: tunnel $TID, DNS $HOSTNAME_API."

# 4. systemd user services --------------------------------------------------
say "4/5 Services"
mkdir -p "$UNITS" "$D/data"
cat > "$D/service.env" <<EOF
AUDIT_HOST=127.0.0.1
AUDIT_PORT=8787
AUDIT_DB_PATH=$D/data/audit.sqlite3
AUDIT_ALLOWED_ORIGINS=https://egeoagents.com
AUDIT_IP_DAILY_LIMIT=5
AUDIT_LLM_DAILY_CAP=200
AUDIT_CACHE_TTL_S=3600
AUDIT_REPORT_TTL_S=86400
REWRITER_MODEL=gpt-4o
EOF
cat > "$UNITS/egeo-audit.service" <<EOF
[Unit]
Description=eGEO public URL audit API (127.0.0.1:8787)
After=network-online.target

[Service]
EnvironmentFile=$D/service.env
EnvironmentFile=$SECRETS
ExecStart=$D/venv/bin/egeo-audit-service
Restart=always
RestartSec=3

[Install]
WantedBy=default.target
EOF
cat > "$UNITS/egeo-audit-tunnel.service" <<EOF
[Unit]
Description=Cloudflare Tunnel for $HOSTNAME_API
After=network-online.target egeo-audit.service

[Service]
ExecStart=$CF --no-autoupdate tunnel --config $D/tunnel.yml run
Restart=always
RestartSec=5

[Install]
WantedBy=default.target
EOF
systemctl --user daemon-reload
systemctl --user enable --now egeo-audit.service egeo-audit-tunnel.service
systemctl --user restart egeo-audit.service egeo-audit-tunnel.service

# 5. Health -----------------------------------------------------------------
say "5/5 Health check"
for i in $(seq 1 30); do
  curl -sf --max-time 5 http://127.0.0.1:8787/healthz >/dev/null && break
  sleep 1
done
curl -sf --max-time 5 http://127.0.0.1:8787/healthz >/dev/null || die "API not answering locally: journalctl --user -u egeo-audit -n 50"
echo "OK: API answers on 127.0.0.1:8787."
for i in $(seq 1 60); do
  code="$(curl -s -o /dev/null -w '%{http_code}' --max-time 10 "https://$HOSTNAME_API/healthz" || true)"
  [ "$code" = 200 ] && break
  sleep 5
done
[ "${code:-}" = 200 ] || die "https://$HOSTNAME_API/healthz gives ${code:-nothing} (DNS may still be propagating; rerun in a few minutes)"
echo
echo "DONE: https://$HOSTNAME_API/healthz answers 200. Tell Claude: listo."
