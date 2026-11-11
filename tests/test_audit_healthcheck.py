"""Integration tests for the POSIX audit healthcheck, using loopback HTTP stubs only."""
from __future__ import annotations

import os
import shutil
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(
    shutil.which("sh") is None or shutil.which("curl") is None,
    reason="healthcheck requires sh and curl",
)

SCRIPT = Path(__file__).resolve().parent.parent / "deploy" / "audit-service" / "healthcheck.sh"


class ApiStub:
    def __init__(self) -> None:
        self.public_health = 200
        self.local_health = 200
        self.public = self._server("public")
        self.local = self._server("local")
        self.threads = [
            threading.Thread(target=self.public.serve_forever, daemon=True),
            threading.Thread(target=self.local.serve_forever, daemon=True),
        ]
        for thread in self.threads:
            thread.start()

    def _server(self, leg: str) -> ThreadingHTTPServer:
        stub = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:
                if self.path == "/healthz":
                    status = stub.public_health if leg == "public" else stub.local_health
                    body = b'{"ok":true}' if status == 200 else b"down"
                elif leg == "public" and self.path.startswith("/api/audit/"):
                    status, body = 404, b'{"error":"not_found"}'
                else:
                    status, body = 404, b"not found"
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, format: str, *args: object) -> None:
                pass

        return ThreadingHTTPServer(("127.0.0.1", 0), Handler)

    def base(self, leg: str) -> str:
        server = self.public if leg == "public" else self.local
        return f"http://127.0.0.1:{server.server_port}"

    def close(self) -> None:
        self.public.shutdown()
        self.local.shutdown()
        self.public.server_close()
        self.local.server_close()
        for thread in self.threads:
            thread.join()


@pytest.fixture
def api() -> ApiStub:
    stub = ApiStub()
    try:
        yield stub
    finally:
        stub.close()


@pytest.fixture
def health_env(tmp_path: Path, api: ApiStub) -> dict[str, str]:
    alerts = tmp_path / "alerts.txt"
    alert_script = tmp_path / "alert.sh"
    alert_script.write_text('#!/bin/sh\ncat >> "$1"\n', encoding="utf-8")
    alert_script.chmod(0o755)
    return {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "HOME": str(tmp_path),
        "AUDIT_PUBLIC_BASE": api.base("public"),
        "AUDIT_LOCAL_BASE": api.base("local"),
        "AUDIT_ALERT_CMD": f'"{alert_script}" "{alerts}"',
        "AUDIT_HEALTH_STATE": str(tmp_path / "nested" / "health.state"),
        "AUDIT_HEALTH_TRIES": "2",
        "AUDIT_HEALTH_SLEEP": "0",
    }


def run_healthcheck(env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["sh", str(SCRIPT)], env=env, capture_output=True, text=True, timeout=30, check=False,
    )


def messages(tmp_path: Path) -> list[str]:
    path = tmp_path / "alerts.txt"
    return path.read_text(encoding="utf-8").splitlines() if path.exists() else []


def test_first_healthy_run_records_state_without_alerting(tmp_path: Path, health_env: dict[str, str]) -> None:
    result = run_healthcheck(health_env)
    assert result.returncode == 0, result.stderr
    assert Path(health_env["AUDIT_HEALTH_STATE"]).read_text(encoding="utf-8").strip() == "up"
    assert messages(tmp_path) == []


def test_tunnel_failure_is_alerted_once_and_recovery_is_alerted(
    tmp_path: Path, api: ApiStub, health_env: dict[str, str]
) -> None:
    assert run_healthcheck(health_env).returncode == 0

    api.public_health = 503
    down = run_healthcheck(health_env)
    assert down.returncode == 1
    assert len(messages(tmp_path)) == 1
    assert "tunnel or Cloudflare" in messages(tmp_path)[0]
    assert Path(health_env["AUDIT_HEALTH_STATE"]).read_text(encoding="utf-8").strip() == "down"

    still_down = run_healthcheck(health_env)
    assert still_down.returncode == 1
    assert len(messages(tmp_path)) == 1

    api.public_health = 200
    recovered = run_healthcheck(health_env)
    assert recovered.returncode == 0
    assert len(messages(tmp_path)) == 2
    assert "recovered" in messages(tmp_path)[1].lower()
    assert Path(health_env["AUDIT_HEALTH_STATE"]).read_text(encoding="utf-8").strip() == "up"


def test_app_failure_names_app(tmp_path: Path, api: ApiStub, health_env: dict[str, str]) -> None:
    assert run_healthcheck(health_env).returncode == 0
    api.public_health = 503
    api.local_health = 503
    result = run_healthcheck(health_env)
    assert result.returncode == 1
    assert len(messages(tmp_path)) == 1
    assert "app" in messages(tmp_path)[0].lower()
    assert "tunnel or Cloudflare" not in messages(tmp_path)[0]


def test_failed_alert_preserves_state_and_retries_on_next_run(
    tmp_path: Path, api: ApiStub, health_env: dict[str, str]
) -> None:
    assert run_healthcheck(health_env).returncode == 0
    working_alert = health_env["AUDIT_ALERT_CMD"]
    health_env["AUDIT_ALERT_CMD"] = "exit 1"
    api.public_health = 503

    failed_alert = run_healthcheck(health_env)
    assert failed_alert.returncode == 1
    assert failed_alert.stderr
    assert Path(health_env["AUDIT_HEALTH_STATE"]).read_text(encoding="utf-8").strip() == "up"
    assert messages(tmp_path) == []

    health_env["AUDIT_ALERT_CMD"] = working_alert
    retried_alert = run_healthcheck(health_env)
    assert retried_alert.returncode == 1
    assert len(messages(tmp_path)) == 1
    assert "DOWN" in messages(tmp_path)[0]
    assert Path(health_env["AUDIT_HEALTH_STATE"]).read_text(encoding="utf-8").strip() == "down"
