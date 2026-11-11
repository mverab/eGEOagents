#!/bin/sh
set -u

AUDIT_PUBLIC_BASE=${AUDIT_PUBLIC_BASE:-https://api.egeoagents.com}
AUDIT_LOCAL_BASE=${AUDIT_LOCAL_BASE:-http://127.0.0.1:8787}
AUDIT_ALERT_CMD=${AUDIT_ALERT_CMD:-hermes send -t telegram}
AUDIT_HEALTH_STATE=${AUDIT_HEALTH_STATE:-${XDG_STATE_HOME:-$HOME/.local/state}/egeo-audit/health.state}
AUDIT_HEALTH_TRIES=${AUDIT_HEALTH_TRIES:-3}
AUDIT_HEALTH_SLEEP=${AUDIT_HEALTH_SLEEP:-10}

public_base=${AUDIT_PUBLIC_BASE%/}
local_base=${AUDIT_LOCAL_BASE%/}
state_dir=${AUDIT_HEALTH_STATE%/*}
if [ "$state_dir" = "$AUDIT_HEALTH_STATE" ]; then
	state_dir=.
fi
mkdir -p "$state_dir"

previous=
if [ -r "$AUDIT_HEALTH_STATE" ]; then
	IFS= read -r previous < "$AUDIT_HEALTH_STATE" || true
fi

current=down
attempt=1
while [ "$attempt" -le "$AUDIT_HEALTH_TRIES" ]; do
	health=$(curl -s -o /dev/null -w '%{http_code}' --max-time 15 "$public_base/healthz" || true)
	missing=$(curl -s --max-time 15 "$public_base/api/audit/healthcheck-probe-000" || true)
	if [ "$health" = 200 ]; then
		case "$missing" in
			*'"not_found"'*)
				current=up
				break
				;;
		esac
	fi
	if [ "$attempt" -lt "$AUDIT_HEALTH_TRIES" ]; then
		sleep "$AUDIT_HEALTH_SLEEP"
	fi
	attempt=$((attempt + 1))
done

message=
if [ "$current" = up ]; then
	if [ "$previous" = down ]; then
		message="E-GEO audit API recovered: the public health probe is up."
	fi
else
	local_health=$(curl -s -o /dev/null -w '%{http_code}' --max-time 15 "$local_base/healthz" || true)
	if [ "$local_health" = 200 ]; then
		leg="tunnel or Cloudflare"
	else
		leg="app"
	fi
	if [ "$previous" = up ]; then
		message="E-GEO audit API is DOWN: the failing leg is $leg."
	fi
fi

if [ -n "$message" ]; then
	if printf '%s\n' "$message" | sh -c "$AUDIT_ALERT_CMD"; then
		printf '%s\n' "$current" > "$AUDIT_HEALTH_STATE"
	else
		printf 'E-GEO audit health alert failed; keeping previous state "%s".\n' "$previous" >&2
	fi
else
	printf '%s\n' "$current" > "$AUDIT_HEALTH_STATE"
fi

if [ "$current" = up ]; then
	exit 0
fi
exit 1
