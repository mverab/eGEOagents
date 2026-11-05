"""Contract tests for egeo.audit_service (spec: openspec/changes/add-public-url-audit, url-audit-api).

Fake clock, fake auditor or fake network: never the real network.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List

import pytest

from egeo import audit_service as svc
from egeo import url_audit as ua

pytest.importorskip("fastapi")
pytest.importorskip("httpx")
from fastapi.testclient import TestClient  # noqa: E402

T0 = 1_793_000_000.0  # 2026-10-26T07:33:20Z
CLIENT_IP = "203.0.113.77"


class Clock:
    def __init__(self, t: float = T0) -> None:
        self.t = t

    def __call__(self) -> float:
        return self.t


class FakeAuditor:
    """Stands in for url_audit.audit_url; optionally consumes the LLM budget like the real one."""

    def __init__(self, *, use_llm: bool = True, error: Exception = None) -> None:
        self.calls: List[Dict[str, Any]] = []
        self.use_llm, self.error = use_llm, error

    def __call__(self, url, query, *, deadline_s, reserve_llm):
        self.calls.append({"url": url, "query": query, "deadline_s": deadline_s})
        if self.error:
            raise self.error
        status = "shown" if (not self.use_llm or reserve_llm()) else "skipped_budget"
        return {
            "url": url,
            "final_url": url,
            "query": query or "best Acme",
            "query_source": "visitor" if query else "derived",
            "checks": [{"id": i, "status": "pass", "evidence": "ok"} for i in ua.CHECK_IDS],
            "features": {"method": "heuristic", "note": "", "items": []},
            "rewrite": {"status": status, "query": query or "best Acme", "note": ua.REWRITE_NOTE},
        }


@pytest.fixture
def env(tmp_path: Path):
    clock = Clock()
    settings = svc.Settings(db_path=str(tmp_path / "audit.sqlite3"))
    store = svc.Store(settings.db_path)
    auditor = FakeAuditor()
    app = svc.create_app(settings, store=store, clock=clock, auditor=auditor)
    client = TestClient(app)
    return clock, settings, store, auditor, client


def post(client, url="https://acme.example/", query=None, ip=CLIENT_IP, origin=None):
    headers = {"CF-Connecting-IP": ip}
    if origin:
        headers["Origin"] = origin
    return client.post("/api/audit", json={"url": url, "query": query}, headers=headers)


def test_successful_audit_and_get(env) -> None:
    clock, settings, store, auditor, client = env
    r = post(client)
    assert r.status_code == 200
    body = r.json()
    assert list(body) == list(svc.REPORT_FIELDS)
    assert len(body["id"]) >= 22  # token_urlsafe(16): 128 bits
    assert body["expires_at"] == svc.iso(T0 + 86400)
    g = client.get(f"/api/audit/{body['id']}")
    assert g.status_code == 200 and g.json() == body


@pytest.mark.parametrize(
    "payload,code",
    [({"url": "file:///etc/passwd"}, "invalid_url"), ({"url": "https://example.com:8443/"}, "invalid_url"),
     ({"url": "https://acme.example/", "query": " "}, "invalid_query"),
     ({"url": "https://acme.example/", "query": "x" * 201}, "invalid_query"), ([], "invalid_url")],
)
def test_validation_errors(env, payload, code) -> None:
    *_, auditor, client = env
    r = client.post("/api/audit", json=payload, headers={"CF-Connecting-IP": CLIENT_IP})
    assert r.status_code == 400 and r.json()["error"] == code and r.json()["message"]
    assert auditor.calls == []


def test_non_json_body(env) -> None:
    *_, client = env
    r = client.post("/api/audit", content=b"url=x", headers={"Content-Type": "text/plain"})
    assert r.status_code == 400 and r.json()["error"] == "invalid_url"


@pytest.mark.parametrize(
    "exc,status,code",
    [(ua.FetchFailed("The page returned HTTP 403."), 502, "fetch_failed"),
     (ua.BlockedTarget("private"), 422, "blocked_target"),
     (ua.AuditTimeout("late"), 504, "audit_timeout")],
)
def test_audit_errors_store_nothing(tmp_path, exc, status, code) -> None:
    settings = svc.Settings(db_path=str(tmp_path / "a.sqlite3"))
    store = svc.Store(settings.db_path)
    client = TestClient(svc.create_app(settings, store=store, clock=Clock(), auditor=FakeAuditor(error=exc)))
    r = post(client)
    assert r.status_code == status and r.json()["error"] == code
    if code == "fetch_failed":
        assert "403" in r.json()["message"]
    assert "INSERT INTO \"reports\"" not in store.dump()


def test_cors_allowlist(env) -> None:
    *_, client = env
    ok = post(client, origin="https://egeoagents.com")
    assert ok.headers.get("access-control-allow-origin") == "https://egeoagents.com"
    bad = post(client, url="https://acme.example/x", origin="https://evil.example")
    assert "access-control-allow-origin" not in bad.headers


def test_sixth_audit_is_rate_limited(env) -> None:
    clock, settings, store, auditor, client = env
    for i in range(5):
        assert post(client, url=f"https://acme.example/p{i}").status_code == 200
    r = post(client, url="https://acme.example/p6")
    assert r.status_code == 429 and r.json()["error"] == "rate_limited"
    midnight_wait = svc.seconds_to_utc_midnight(T0)
    assert r.headers["retry-after"] == str(midnight_wait)
    assert len(auditor.calls) == 5
    # another IP is unaffected; a new UTC day resets the limit
    assert post(client, url="https://acme.example/p6", ip="198.51.100.9").status_code == 200
    clock.t += midnight_wait + 1
    assert post(client, url="https://acme.example/p7").status_code == 200


def test_cache_hit_is_free_and_keeps_id(env) -> None:
    clock, settings, store, auditor, client = env
    first = post(client, url="https://acme.example/", query="q").json()
    for i in range(4):
        post(client, url=f"https://acme.example/o{i}")
    clock.t += 1800
    again = post(client, url="https://ACME.example/#top", query="q")  # same normalized key
    assert again.status_code == 200
    assert again.json()["id"] == first["id"] and again.json()["expires_at"] == first["expires_at"]
    assert len(auditor.calls) == 5  # no new audit for the cache hit
    clock.t += 1801  # cache window (1 h) over -> runs again, but this IP is now at its limit
    assert post(client, url="https://acme.example/", query="q").status_code == 429


def test_different_query_is_a_different_cache_entry(env) -> None:
    *_, auditor, client = env
    a = post(client, query="one").json()
    b = post(client, query="two").json()
    assert a["id"] != b["id"] and len(auditor.calls) == 2


def test_budget_exhausted_still_returns_report(tmp_path) -> None:
    settings = svc.Settings(db_path=str(tmp_path / "b.sqlite3"), llm_daily_cap=2, ip_daily_limit=100)
    store = svc.Store(settings.db_path)
    clock = Clock()
    client = TestClient(svc.create_app(settings, store=store, clock=clock, auditor=FakeAuditor()))
    statuses = [post(client, url=f"https://acme.example/{i}").json()["rewrite"]["status"] for i in range(3)]
    assert statuses == ["shown", "shown", "skipped_budget"]
    assert store.llm_used(clock()) == 2


def test_failed_llm_call_keeps_budget_consumed(tmp_path) -> None:
    store = svc.Store(str(tmp_path / "c.sqlite3"))
    assert store.reserve_llm(T0, 1) is True  # reserved, then the call fails: nothing is refunded
    assert store.reserve_llm(T0, 1) is False


def test_expired_report_is_404_and_deleted(env) -> None:
    clock, settings, store, auditor, client = env
    rid = post(client).json()["id"]
    clock.t += 25 * 3600
    r = client.get(f"/api/audit/{rid}")
    assert r.status_code == 404 and r.json()["error"] == "not_found"
    assert rid not in store.dump()


def test_unknown_id_is_404(env) -> None:
    *_, client = env
    assert client.get("/api/audit/nope").status_code == 404


def test_no_listing_endpoint(env) -> None:
    *_, client = env
    post(client)
    for path in ("/api/audit", "/api/audits", "/api/audit/"):
        r = client.get(path)
        assert r.status_code in (404, 405)
        assert not isinstance(r.json(), list)


def test_no_raw_ip_persisted_and_no_cookies(env) -> None:
    clock, settings, store, auditor, client = env
    r = post(client)
    assert "set-cookie" not in r.headers
    assert CLIENT_IP not in store.dump()


def test_daily_salt_rotates(tmp_path) -> None:
    store = svc.Store(str(tmp_path / "d.sqlite3"))
    h1 = store.ip_hash(CLIENT_IP, T0)
    assert store.ip_hash(CLIENT_IP, T0 + 60) == h1
    h2 = store.ip_hash(CLIENT_IP, T0 + 86400)
    assert h2 != h1
    assert svc.utc_day(T0) not in store.dump()  # yesterday's salt is gone


def test_real_auditor_offline_end_to_end(tmp_path, monkeypatch) -> None:
    """Service + real url_audit with an injected network, in GEO_EVAL_MOCK mode."""
    monkeypatch.setenv("GEO_EVAL_MOCK", "1")
    html = (
        "<html><head><title>Acme</title></head><body><h1>Acme</h1><h2>Why</h2><p>"
        + " ".join(["fast private analytics"] * 20)
        + "</p></body></html>"
    )

    def transport(ip, url, timeout, deadline):
        if url == "https://acme.example/":
            return ua.RawResponse(200, {"content-type": "text/html"}, html.encode())
        return ua.RawResponse(404, {"content-type": "text/html"}, b"")

    def auditor(url, query, **kw):
        return ua.audit_url(url, query, resolver=lambda h, p: ["93.184.216.34"], transport=transport, **kw)

    settings = svc.Settings(db_path=str(tmp_path / "e.sqlite3"))
    store = svc.Store(settings.db_path)
    client = TestClient(svc.create_app(settings, store=store, clock=Clock(), auditor=auditor))
    body = post(client).json()
    assert [c["id"] for c in body["checks"]] == list(ua.CHECK_IDS)
    assert body["rewrite"]["status"] == "shown"
    assert store.llm_used(T0) == 1


def test_core_import_without_extra() -> None:
    """`import egeo, egeo.url_audit, egeo.audit_service` must not need fastapi."""
    code = (
        "import sys, builtins\n"
        "real = builtins.__import__\n"
        "def guard(name, *a, **k):\n"
        "    if name.split('.')[0] in ('fastapi', 'uvicorn', 'starlette'):\n"
        "        raise ImportError(name)\n"
        "    return real(name, *a, **k)\n"
        "builtins.__import__ = guard\n"
        "import egeo, egeo.url_audit, egeo.audit_service\n"
        "print('ok')\n"
    )
    root = Path(__file__).resolve().parent.parent
    out = subprocess.run([sys.executable, "-c", code], cwd=root, capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    assert out.stdout.strip() == "ok"


def test_settings_from_env() -> None:
    s = svc.Settings.from_env({
        "AUDIT_IP_DAILY_LIMIT": "7", "AUDIT_LLM_DAILY_CAP": "9", "AUDIT_CACHE_TTL_S": "60",
        "AUDIT_REPORT_TTL_S": "120", "AUDIT_ALLOWED_ORIGINS": "https://egeoagents.com, http://localhost:4321",
        "AUDIT_DB_PATH": "/data/a.sqlite3",
    })
    assert (s.ip_daily_limit, s.llm_daily_cap, s.cache_ttl_s, s.report_ttl_s) == (7, 9, 60, 120)
    assert s.allowed_origins == ["https://egeoagents.com", "http://localhost:4321"]
    assert s.db_path == "/data/a.sqlite3"
    d = svc.Settings.from_env({})
    assert (d.ip_daily_limit, d.llm_daily_cap, d.cache_ttl_s, d.report_ttl_s) == (5, 200, 3600, 86400)


def test_main_help_exits_without_starting_the_server(capsys) -> None:
    # `egeo-audit-service --help` once started a server with no config on the VPS.
    with pytest.raises(SystemExit) as exc:
        svc.main(["--help"])
    assert exc.value.code == 0
    assert "AUDIT_" in capsys.readouterr().out
