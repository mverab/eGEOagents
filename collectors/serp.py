#!/usr/bin/env python3
"""SERP collector: position history for your queries, from the Brave Search API
or the SerpBase Google Search API.

Deterministic, zero LLM calls. One record per query per pass, appended to
``$EGEO_HOME/data/serp/<query-slug>.jsonl``::

    {"v": 1, "ts": "...Z", "query": "...", "engine": "brave",
     "results": [{"position": 1, "url": "...", "domain": "...", "title": "..."}, ...],
     "target_domain": "example.com", "target_position": 3 | null}

The engine is selected with ``--engine brave|serpbase`` (or
``collectors.serp.engine`` in config.yaml; default ``brave``):

- ``brave`` — Brave Search API over HTTP directly (``BRAVE_API_KEY``).
- ``serpbase`` — SerpBase Google Search API (``SERPBASE_API_KEY``): Google
  organic results (plus AI Overviews on the SERP) as JSON, no browser.

Both are called over their HTTP API directly (``BRAVE_API_KEY`` /
``SERPBASE_API_KEY``) rather than through an MCP: a cron-launched collector
has no agent, hence no MCP. Live passes are paced at ≤1 query/second and
refuse to exceed ``budgets.queries_per_day``.

Usage::

    python collectors/serp.py                       # queries from config.yaml
    python collectors/serp.py --query "best geo tool"
    python collectors/serp.py --engine serpbase     # Google SERP via SerpBase
    python collectors/serp.py --fixture collectors/fixtures/serp_brave_response.json
    python collectors/serp.py --engine serpbase --fixture collectors/fixtures/serp_serpbase_response.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode, urlparse

if __package__ in (None, ""):  # executed as a script
    sys.path.insert(0, str(Path(__file__).resolve().parent))

import _common as common  # noqa: E402
from egeo import workspace  # noqa: E402

SCHEMA_VERSION = 1
COLLECTOR = "serp"
ENGINE = "brave"
API_URL = "https://api.search.brave.com/res/v1/web/search"
API_KEY_ENV = "BRAVE_API_KEY"
SERPBASE_ENGINE = "serpbase"
SERPBASE_API_URL = "https://api.serpbase.dev/google/search"
SERPBASE_API_KEY_ENV = "SERPBASE_API_KEY"
MAX_RESULTS = 10
MIN_SECONDS_BETWEEN_QUERIES = 1.0


def _normalize_domain(host: str) -> str:
    host = (host or "").strip().lower().rstrip(".")
    return host[4:] if host.startswith("www.") else host


def _domain_of(url: str) -> str:
    try:
        return _normalize_domain(urlparse(url).hostname or "")
    except ValueError:
        return ""


def parse_brave_response(payload: Dict[str, Any], query: str, target_domain: str) -> Dict[str, Any]:
    """Turn a Brave web-search body into one versioned observation record.

    No interpretation: positions are the order Brave returned, the target
    position is the first result whose domain matches, or ``None``.
    """
    web = payload.get("web") or {}
    raw_results = web.get("results") or []
    if not isinstance(raw_results, list):
        raise common.CollectorError(f"unexpected Brave payload for {query!r}: web.results is not a list")

    results: List[Dict[str, Any]] = []
    for index, item in enumerate(raw_results[:MAX_RESULTS], start=1):
        if not isinstance(item, dict):
            raise common.CollectorError(f"unexpected Brave payload for {query!r}: result is not an object")
        url = str(item.get("url", ""))
        results.append(
            {
                "position": index,
                "url": url,
                "domain": _domain_of(url),
                "title": str(item.get("title", "")),
            }
        )

    target = _normalize_domain(target_domain)
    target_position = None
    if target:
        for result in results:
            if result["domain"] == target or result["domain"].endswith("." + target):
                target_position = result["position"]
                break

    return {
        "v": SCHEMA_VERSION,
        "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "query": query,
        "engine": ENGINE,
        "results": results,
        "target_domain": target or None,
        "target_position": target_position,
    }


def parse_serpbase_response(payload: Dict[str, Any], query: str, target_domain: str) -> Dict[str, Any]:
    """Turn a SerpBase ``/google/search`` body into one versioned observation record.

    Same contract as :func:`parse_brave_response`: positions are the rank
    Google returned (``rank``; ``position`` is the normalized alias), the
    target position is the first result whose domain matches, or ``None``.
    """
    if payload.get("status") != 0:
        raise common.CollectorError(
            f"SerpBase API reported status {payload.get('status')!r} for {query!r} "
            f"(request_id={payload.get('request_id')!r})"
        )
    raw_results = payload.get("organic") or []
    if not isinstance(raw_results, list):
        raise common.CollectorError(f"unexpected SerpBase payload for {query!r}: organic is not a list")

    results: List[Dict[str, Any]] = []
    for index, item in enumerate(raw_results[:MAX_RESULTS], start=1):
        if not isinstance(item, dict):
            raise common.CollectorError(f"unexpected SerpBase payload for {query!r}: result is not an object")
        url = str(item.get("link") or item.get("url") or "")
        results.append(
            {
                "position": int(item.get("rank") or index),
                "url": url,
                "domain": _domain_of(url),
                "title": str(item.get("title", "")),
            }
        )

    target = _normalize_domain(target_domain)
    target_position = None
    if target:
        for result in results:
            if result["domain"] == target or result["domain"].endswith("." + target):
                target_position = result["position"]
                break

    return {
        "v": SCHEMA_VERSION,
        "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "query": query,
        "engine": SERPBASE_ENGINE,
        "results": results,
        "target_domain": target or None,
        "target_position": target_position,
    }


def fetch_brave(query: str, api_key: str, count: int = MAX_RESULTS) -> Dict[str, Any]:
    """Call the Brave Search API and return the parsed JSON body."""
    url = f"{API_URL}?{urlencode({'q': query, 'count': count})}"
    status, body = common.http_get(
        url,
        headers={"Accept": "application/json", "X-Subscription-Token": api_key},
    )
    if status == 401 or status == 403:
        raise common.CollectorError(
            f"Brave API rejected the request (HTTP {status}). Check ${API_KEY_ENV}."
        )
    if status == 429:
        raise common.CollectorError("Brave API rate limit hit (HTTP 429); retry later or lower the cadence.")
    if status != 200:
        raise common.CollectorError(f"Brave API returned HTTP {status} for {query!r}")
    try:
        payload = json.loads(body)
    except json.JSONDecodeError as exc:
        raise common.CollectorError(f"Brave API returned invalid JSON for {query!r}: {exc}") from exc
    if not isinstance(payload, dict):
        raise common.CollectorError(f"Brave API returned a non-object body for {query!r}")
    return payload


def fetch_serpbase(query: str, api_key: str, count: int = MAX_RESULTS) -> Dict[str, Any]:
    """Call the SerpBase Google Search API and return the parsed JSON body.

    SerpBase is a POST JSON API (``X-API-Key`` header); the response envelope
    is ``{"status": 0, "request_id": "...", "organic": [...]}``.
    """
    url = SERPBASE_API_URL
    status, body = common.http_post(
        url,
        headers={"Content-Type": "application/json", "X-API-Key": api_key},
        payload={"q": query, "hl": "en", "gl": "us", "device": "default"},
    )
    if status == 401 or status == 403:
        raise common.CollectorError(
            f"SerpBase API rejected the request (HTTP {status}). Check ${SERPBASE_API_KEY_ENV}."
        )
    if status == 429:
        raise common.CollectorError("SerpBase API rate limit hit (HTTP 429); retry later or lower the cadence.")
    if status != 200:
        raise common.CollectorError(f"SerpBase API returned HTTP {status} for {query!r}")
    try:
        payload = json.loads(body)
    except json.JSONDecodeError as exc:
        raise common.CollectorError(f"SerpBase API returned invalid JSON for {query!r}: {exc}") from exc
    if not isinstance(payload, dict):
        raise common.CollectorError(f"SerpBase API returned a non-object body for {query!r}")
    return payload


def load_fixture(path: Path) -> Dict[str, Any]:
    """Read a recorded Brave response body from disk (fixture mode)."""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise common.CollectorError(f"fixture not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise common.CollectorError(f"fixture is not valid JSON: {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise common.CollectorError(f"fixture must contain a JSON object: {path}")
    return payload


def collect(
    *,
    queries: List[str],
    target_domain: str,
    home: Path,
    fixture: Optional[Path] = None,
    budget: Optional[int] = None,
    engine: str = ENGINE,
) -> Dict[str, Any]:
    """Run one pass over ``queries``. Returns a machine-readable summary."""
    if not queries:
        raise common.CollectorError(
            "no queries configured: add collectors.serp.queries to "
            f"{home / workspace.CONFIG_NAME} or pass --query"
        )
    if engine not in (ENGINE, SERPBASE_ENGINE):
        raise common.CollectorError(f"unknown SERP engine {engine!r}: choose from '{ENGINE}', '{SERPBASE_ENGINE}'")

    key_env = API_KEY_ENV if engine == ENGINE else SERPBASE_API_KEY_ENV
    api_key = os.environ.get(key_env, "").strip()
    if fixture is None and not api_key:
        raise common.CollectorError(
            f"${key_env} is not set. Export a {engine} API key, or run with "
            "--fixture <recorded-response.json> for an offline pass."
        )

    paths = {query: common.stream_path(COLLECTOR, common.slugify(query), home) for query in queries}
    if budget:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        already = common.count_today(sorted(workspace.data_dir(COLLECTOR, home).glob("*.jsonl")), today)
        if already + len(queries) > budget:
            raise common.CollectorError(
                f"budgets.queries_per_day={budget} would be exceeded: "
                f"{already} recorded today + {len(queries)} requested. "
                "Raise the budget in config.yaml or shorten the query list."
            )

    payload_cache = load_fixture(fixture) if fixture is not None else None
    written: List[Dict[str, Any]] = []
    for index, query in enumerate(queries):
        if payload_cache is not None:
            payload = payload_cache
        else:
            if index:
                time.sleep(MIN_SECONDS_BETWEEN_QUERIES)
            if engine == SERPBASE_ENGINE:
                payload = fetch_serpbase(query, api_key)
            else:
                payload = fetch_brave(query, api_key)
        if engine == SERPBASE_ENGINE:
            record = parse_serpbase_response(payload, query, target_domain)
        else:
            record = parse_brave_response(payload, query, target_domain)
        common.append_record(paths[query], record)
        written.append({"query": query, "stream": str(paths[query]), "target_position": record["target_position"]})

    positions = [item["target_position"] for item in written]
    found = sum(1 for value in positions if value is not None)
    summary = (
        f"{len(written)} query observation(s), target ranked in {found}/{len(written)}"
        f"{' (fixture mode)' if fixture is not None else ''}, outcome=success"
    )
    log_line = common.log_pass(COLLECTOR, summary, home=home)
    return {"collector": COLLECTOR, "observations": written, "log": log_line}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--query",
        action="append",
        dest="queries",
        help="Query to collect (repeatable). Default: collectors.serp.queries from config.yaml.",
    )
    parser.add_argument(
        "--target-domain",
        default=None,
        help="Domain to report a position for. Default: collectors.serp.target_domain.",
    )
    parser.add_argument(
        "--engine",
        choices=[ENGINE, SERPBASE_ENGINE],
        default=None,
        help=f"SERP source engine: '{ENGINE}' (Brave Search API) or '{SERPBASE_ENGINE}' "
        f"(SerpBase Google Search API). Default: collectors.serp.engine from config.yaml, else '{ENGINE}'.",
    )
    parser.add_argument(
        "--fixture",
        default=None,
        help="Replay a recorded response JSON file instead of calling the API (offline). "
        "Use --engine serpbase with collectors/fixtures/serp_serpbase_response.json for a Google SERP pass.",
    )
    parser.add_argument("--json", action="store_true", help="Print the machine-readable summary.")
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    home = common.ensure_workspace()
    try:
        config = workspace.load_config(home)
    except (OSError, ValueError) as exc:
        return common.fail(str(exc))

    queries = args.queries or list(workspace.config_get(config, "collectors.serp.queries", []) or [])
    target_domain = args.target_domain or str(
        workspace.config_get(config, "collectors.serp.target_domain", "") or ""
    )
    engine = args.engine or str(workspace.config_get(config, "collectors.serp.engine", ENGINE) or ENGINE)
    budget = workspace.config_get(config, "budgets.queries_per_day", None)

    try:
        result = collect(
            queries=[str(query) for query in queries],
            target_domain=target_domain,
            home=home,
            fixture=Path(args.fixture).expanduser() if args.fixture else None,
            budget=int(budget) if budget else None,
            engine=engine,
        )
    except common.CollectorError as exc:
        return common.fail(str(exc))

    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        for item in result["observations"]:
            position = item["target_position"]
            print(f"✓ {item['query']}: target position {position if position else '—'} → {item['stream']}")
        print(result["log"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
