"""HTTP service for the public URL audit (``POST /api/audit``, ``GET /api/audit/{id}``).

Spec: ``openspec/changes/add-public-url-audit/specs/url-audit-api/spec.md``. All audit logic is
in :mod:`egeo.url_audit`; this module only adds the HTTP contract, CORS, the per-IP daily limit,
the 1 h cache, the global daily LLM cap, and the 24 h report store (SQLite).

FastAPI/uvicorn are the optional extra ``egeo[audit-service]`` and are imported lazily, so
importing this module (or ``egeo``) never requires them. Run with::

    egeo-audit-service                      # reads AUDIT_* env vars, binds AUDIT_HOST:AUDIT_PORT
    uvicorn --factory egeo.audit_service:create_app

The service must only be reachable through Cloudflare (a Cloudflare Tunnel, see
``deploy/audit-service/``): the client IP is taken from ``CF-Connecting-IP``.
"""
# No ``from __future__ import annotations`` here: FastAPI must resolve the ``Request``
# annotation of the route handlers, which is imported lazily inside ``create_app``.
import hashlib
import json
import os
import secrets
import sqlite3
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, List, Optional, Tuple

from . import url_audit

Auditor = Callable[..., Dict[str, Any]]


# --------------------------------------------------------------------------- #
# Settings
# --------------------------------------------------------------------------- #
@dataclass
class Settings:
    db_path: str = "audit-service.sqlite3"
    allowed_origins: List[str] = field(default_factory=lambda: ["https://egeoagents.com"])
    ip_daily_limit: int = 5
    llm_daily_cap: int = 200
    cache_ttl_s: int = 3600
    report_ttl_s: int = 86400
    deadline_s: float = url_audit.DEADLINE_S

    @classmethod
    def from_env(cls, env: Optional[Dict[str, str]] = None) -> "Settings":
        e = os.environ if env is None else env
        s = cls()
        s.db_path = e.get("AUDIT_DB_PATH", s.db_path)
        if e.get("AUDIT_ALLOWED_ORIGINS"):
            s.allowed_origins = [o.strip() for o in e["AUDIT_ALLOWED_ORIGINS"].split(",") if o.strip()]
        s.ip_daily_limit = int(e.get("AUDIT_IP_DAILY_LIMIT", s.ip_daily_limit))
        s.llm_daily_cap = int(e.get("AUDIT_LLM_DAILY_CAP", s.llm_daily_cap))
        s.cache_ttl_s = int(e.get("AUDIT_CACHE_TTL_S", s.cache_ttl_s))
        s.report_ttl_s = int(e.get("AUDIT_REPORT_TTL_S", s.report_ttl_s))
        return s


def utc_day(ts: float) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")


def iso(ts: float) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def seconds_to_utc_midnight(ts: float) -> int:
    now = datetime.fromtimestamp(ts, tz=timezone.utc)
    midnight = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    return max(1, int((midnight - now).total_seconds() + 0.999))


# --------------------------------------------------------------------------- #
# Store (SQLite): reports, per-IP counters, daily salts, LLM budget
# --------------------------------------------------------------------------- #
class Store:
    """Thread-safe SQLite store. Holds no raw IPs: only ``sha256(daily_salt + ip)``."""

    def __init__(self, path: str) -> None:
        self._lock = threading.Lock()
        self._db = sqlite3.connect(path, check_same_thread=False, isolation_level=None)
        self._db.executescript(
            """
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS reports (
                id TEXT PRIMARY KEY, created_at REAL NOT NULL, expires_at REAL NOT NULL,
                cache_key TEXT NOT NULL, json TEXT NOT NULL);
            CREATE INDEX IF NOT EXISTS reports_cache ON reports(cache_key, created_at);
            CREATE TABLE IF NOT EXISTS ip_counts (
                day TEXT NOT NULL, ip_hash TEXT NOT NULL, count INTEGER NOT NULL,
                PRIMARY KEY (day, ip_hash));
            CREATE TABLE IF NOT EXISTS salts (day TEXT PRIMARY KEY, salt TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS llm_budget (day TEXT PRIMARY KEY, used INTEGER NOT NULL);
            """
        )

    def _purge(self, now: float) -> None:
        day = utc_day(now)
        self._db.execute("DELETE FROM reports WHERE expires_at <= ?", (now,))
        self._db.execute("DELETE FROM ip_counts WHERE day <> ?", (day,))
        self._db.execute("DELETE FROM salts WHERE day <> ?", (day,))
        self._db.execute("DELETE FROM llm_budget WHERE day <> ?", (day,))

    # reports -------------------------------------------------------------- #
    def save_report(self, report: Dict[str, Any], key: str, created: float, expires: float) -> None:
        with self._lock:
            self._purge(created)
            self._db.execute(
                "INSERT INTO reports (id, created_at, expires_at, cache_key, json) VALUES (?, ?, ?, ?, ?)",
                (report["id"], created, expires, key, json.dumps(report)),
            )

    def get_report(self, report_id: str, now: float) -> Optional[Dict[str, Any]]:
        with self._lock:
            row = self._db.execute("SELECT expires_at, json FROM reports WHERE id = ?", (report_id,)).fetchone()
            if row is None:
                return None
            if row[0] <= now:
                self._db.execute("DELETE FROM reports WHERE id = ?", (report_id,))
                return None
            return json.loads(row[1])

    def cached_report(self, key: str, now: float, ttl_s: int) -> Optional[Dict[str, Any]]:
        with self._lock:
            row = self._db.execute(
                "SELECT json FROM reports WHERE cache_key = ? AND created_at > ? AND expires_at > ? "
                "ORDER BY created_at DESC LIMIT 1",
                (key, now - ttl_s, now),
            ).fetchone()
            return json.loads(row[0]) if row else None

    # per-IP counters -------------------------------------------------------- #
    def ip_hash(self, ip: str, now: float) -> str:
        day = utc_day(now)
        with self._lock:
            self._purge(now)
            row = self._db.execute("SELECT salt FROM salts WHERE day = ?", (day,)).fetchone()
            if row is None:
                salt = secrets.token_hex(32)
                self._db.execute("INSERT INTO salts (day, salt) VALUES (?, ?)", (day, salt))
            else:
                salt = row[0]
        return hashlib.sha256((salt + ip).encode("utf-8")).hexdigest()

    def take_ip_slot(self, ip_hash: str, now: float, limit: int) -> bool:
        """Count one uncached audit for this IP today; False (and no change) when over the limit."""
        day = utc_day(now)
        with self._lock:
            row = self._db.execute(
                "SELECT count FROM ip_counts WHERE day = ? AND ip_hash = ?", (day, ip_hash)
            ).fetchone()
            used = row[0] if row else 0
            if used >= limit:
                return False
            self._db.execute(
                "INSERT INTO ip_counts (day, ip_hash, count) VALUES (?, ?, 1) "
                "ON CONFLICT(day, ip_hash) DO UPDATE SET count = count + 1",
                (day, ip_hash),
            )
            return True

    # LLM budget ------------------------------------------------------------- #
    def reserve_llm(self, now: float, cap: int) -> bool:
        """Reserve one rewrite call for today; a reserved unit stays consumed even if the call fails."""
        day = utc_day(now)
        with self._lock:
            row = self._db.execute("SELECT used FROM llm_budget WHERE day = ?", (day,)).fetchone()
            used = row[0] if row else 0
            if used >= cap:
                return False
            self._db.execute(
                "INSERT INTO llm_budget (day, used) VALUES (?, 1) "
                "ON CONFLICT(day) DO UPDATE SET used = used + 1",
                (day,),
            )
            return True

    def llm_used(self, now: float) -> int:
        with self._lock:
            row = self._db.execute("SELECT used FROM llm_budget WHERE day = ?", (utc_day(now),)).fetchone()
            return row[0] if row else 0

    def dump(self) -> str:
        """Every stored value as text (used by tests to prove no raw IP is persisted)."""
        with self._lock:
            return "\n".join(self._db.iterdump())


# --------------------------------------------------------------------------- #
# Request handling (framework-free, so it is testable on its own)
# --------------------------------------------------------------------------- #
REPORT_FIELDS = ("id", "url", "final_url", "query", "query_source", "checks", "features", "rewrite",
                 "challenge", "created_at", "expires_at")


def _error(status: int, code: str, message: str, headers: Optional[Dict[str, str]] = None):
    return status, {"error": code, "message": message}, headers or {}


class AuditHandler:
    def __init__(self, settings: Settings, store: Store, *, clock: Callable[[], float] = time.time,
                 auditor: Optional[Auditor] = None) -> None:
        self.settings, self.store, self.clock = settings, store, clock
        self.auditor = auditor or url_audit.audit_url

    def post(self, payload: Any, client_ip: str) -> Tuple[int, Dict[str, Any], Dict[str, str]]:
        if not isinstance(payload, dict):
            return _error(400, "invalid_url", 'Send JSON like {"url": "https://example.com/", "query": null}.')
        try:
            url = url_audit.normalize_url(payload.get("url"))
            query = url_audit.normalize_query(payload.get("query"))
        except url_audit.AuditError as exc:
            return _error(exc.status, exc.code, exc.message)

        now = self.clock()
        key = url_audit.cache_key(url, query)
        cached = self.store.cached_report(key, now, self.settings.cache_ttl_s)
        if cached is not None:
            return 200, cached, {}

        ip_hash = self.store.ip_hash(client_ip, now)
        if not self.store.take_ip_slot(ip_hash, now, self.settings.ip_daily_limit):
            wait = seconds_to_utc_midnight(now)
            return _error(
                429,
                "rate_limited",
                f"The free limit of {self.settings.ip_daily_limit} audits per day is used up. "
                "Try again after midnight UTC, or run `pip install egeo` locally.",
                {"Retry-After": str(wait)},
            )

        try:
            body = self.auditor(
                url,
                query,
                deadline_s=self.settings.deadline_s,
                reserve_llm=lambda: self.store.reserve_llm(self.clock(), self.settings.llm_daily_cap),
            )
        except url_audit.AuditError as exc:
            return _error(exc.status, exc.code, exc.message)
        except Exception:
            return _error(500, "internal_error", "The audit failed unexpectedly. Please try again later.")

        created = self.clock()
        expires = created + self.settings.report_ttl_s
        report = {"id": secrets.token_urlsafe(16), **body, "created_at": iso(created), "expires_at": iso(expires)}
        report = {k: report[k] for k in REPORT_FIELDS}
        self.store.save_report(report, key, created, expires)
        return 200, report, {}

    def get(self, report_id: str) -> Tuple[int, Dict[str, Any], Dict[str, str]]:
        report = self.store.get_report(report_id, self.clock())
        if report is None:
            return _error(404, "not_found", "This report does not exist or expired (reports last 24 hours).")
        return 200, report, {}


# --------------------------------------------------------------------------- #
# FastAPI app (optional extra)
# --------------------------------------------------------------------------- #
def create_app(settings: Optional[Settings] = None, *, store: Optional[Store] = None,
               clock: Callable[[], float] = time.time, auditor: Optional[Auditor] = None):
    try:
        from fastapi import FastAPI, Request
        from fastapi.concurrency import run_in_threadpool
        from fastapi.middleware.cors import CORSMiddleware
        from fastapi.responses import JSONResponse
    except ImportError as exc:  # pragma: no cover - exercised only without the extra
        raise RuntimeError("The audit service needs the optional extra: pip install 'egeo[audit-service]'") from exc

    settings = settings or Settings.from_env()
    store = store or Store(settings.db_path)
    handler = AuditHandler(settings, store, clock=clock, auditor=auditor)

    app = FastAPI(title="E-GEO public URL audit", docs_url=None, redoc_url=None, openapi_url=None)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
        expose_headers=["Retry-After"],
        allow_credentials=False,
    )

    def respond(result: Tuple[int, Dict[str, Any], Dict[str, str]]):
        status, body, headers = result
        return JSONResponse(body, status_code=status, headers={"Cache-Control": "no-store", **headers})

    @app.post("/api/audit")
    async def post_audit(request: Request):
        try:
            payload = await request.json()
        except Exception:
            payload = None
        ip = request.headers.get("cf-connecting-ip") or (request.client.host if request.client else "unknown")
        return respond(await run_in_threadpool(handler.post, payload, ip))

    @app.get("/api/audit/{report_id}")
    async def get_audit(report_id: str):
        return respond(await run_in_threadpool(handler.get, report_id))

    @app.get("/healthz")
    async def healthz():
        return {"ok": True}

    return app


def main(argv: Optional[List[str]] = None) -> None:
    import argparse

    argparse.ArgumentParser(
        prog="egeo-audit-service",
        description="Run the public URL audit API (configured by AUDIT_* and OPENAI_* environment variables; "
        "see docs/audit-service.md).",
    ).parse_args(argv)
    from egeo.url_audit import rewriter_request_options

    rewriter_request_options()  # fail at startup, not on every rewrite, if misconfigured
    import uvicorn

    uvicorn.run(
        create_app(Settings.from_env()),
        host=os.environ.get("AUDIT_HOST", "127.0.0.1"),
        port=int(os.environ.get("AUDIT_PORT", "8787")),
        proxy_headers=False,
    )


__all__ = ["AuditHandler", "Settings", "Store", "create_app", "main"]
