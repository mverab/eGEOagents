#!/usr/bin/env python3
"""AI Overview collector: does Google's AI Overview cite you, and from which pages?

The other collectors observe what you *publish* (``page.py``) and where you
*rank* (``serp.py``). Neither answers the question GEO actually asks: when
Google answers the query itself, in the AI Overview block, which sources does
it name? This collector records that block verbatim: the answer text and the
ordered citation list.

Deterministic, zero LLM calls. One record per query per pass, appended to
``$EGEO_HOME/data/ai_overview/<query-slug>.jsonl``::

    {"v": 1, "ts": "...Z", "query": "...", "engine": "google-ai-overview",
     "available": true,
     "answer": "Solar panels convert sunlight ...",
     "citations": [{"position": 1, "url": "...", "domain": "...", "title": "..."}, ...],
     "target_domain": "example.com", "target_cited": true, "target_position": 2,
     "cost_credits": 3, "remaining_credits": 1234}

``available`` is ``false`` when Google returned no AI Overview for the query:
that is a valid observation (the record still carries ``v``/``ts``/``query``),
not a failure, so the absence itself becomes part of the history.

Data comes from the GoAnyAPI ``google-ai-overview`` endpoint over HTTP
directly (``GOANYAPI_API_KEY``), not through its MCP: a cron-launched collector
has no agent, hence no MCP. Each AI Overview call bills ~3 credits, so live
passes are paced at ≤1 query/second and refuse to exceed
``budgets.queries_per_day``.

Usage::

    python collectors/ai_overview.py                        # queries from config.yaml
    python collectors/ai_overview.py --query "best geo tool"
    python collectors/ai_overview.py --fixture collectors/fixtures/ai_overview_goanyapi_response.json
    python -m egeo loop collect ai_overview                 # equivalent, in-process
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
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

if __package__ in (None, ""):  # executed as a script
    sys.path.insert(0, str(Path(__file__).resolve().parent))

import _common as common  # noqa: E402
from egeo import workspace  # noqa: E402

SCHEMA_VERSION = 1
COLLECTOR = "ai_overview"
ENGINE = "google-ai-overview"
API_URL = "https://api.goanyapi.com/api/v1/google-ai-overview"
API_KEY_ENV = "GOANYAPI_API_KEY"
MAX_CITATIONS = 20
MIN_SECONDS_BETWEEN_QUERIES = 1.0

# Query parameters that only carry attribution; they must not split one cited
# page into two citation slots.
TRACKING_QUERY_PARAMS = {
    "fbclid",
    "gclid",
    "msclkid",
    "ref",
    "referrer",
    "source",
    "yclid",
}


def _domain_of(url: str) -> str:
    """Registered-ish host for a URL: lower-case, no leading ``www.``."""
    host = (urlparse(url).hostname or "").lower().rstrip(".")
    return host[4:] if host.startswith("www.") else host


def _normalize_domain(domain: str) -> str:
    value = (domain or "").strip().lower()
    value = value.removeprefix("https://").removeprefix("http://").split("/")[0]
    value = value.split(":")[0].rstrip(".")
    return value[4:] if value.startswith("www.") else value


def _citation_key(url: str) -> str:
    """Identity of a cited page: scheme, host without ``www.``, path, useful query."""
    parts = urlparse(url.strip())
    host = _domain_of(url)
    if not host:
        return url.strip()
    query = urlencode(
        [
            (key, value)
            for key, value in parse_qsl(parts.query, keep_blank_values=True)
            if key.lower() not in TRACKING_QUERY_PARAMS and not key.lower().startswith("utm_")
        ]
    )
    path = parts.path.rstrip("/") or "/"
    return urlunparse(("https", host, path, "", query, ""))


def parse_ai_overview_response(payload: Dict[str, Any], query: str, target_domain: str) -> Dict[str, Any]:
    """Turn a GoAnyAPI ``google-ai-overview`` body into one versioned observation.

    Citations come from both ``results[].links`` and ``serp_features[].links``
    (the two overlap by design); they are merged, deduplicated and numbered in
    first-seen order, which is the order the Overview presents them.
    """
    if payload.get("code") not in (None, "ok"):
        raise common.CollectorError(
            f"GoAnyAPI reported {payload.get('code')!r} for {query!r}: {payload.get('message')!r}"
        )
    data = payload.get("data")
    if not isinstance(data, dict):
        raise common.CollectorError(f"unexpected GoAnyAPI payload for {query!r}: data is not an object")
    content = (data.get("result") or {}).get("content") or {}
    if not isinstance(content, dict):
        raise common.CollectorError(f"unexpected GoAnyAPI payload for {query!r}: content is not an object")

    parameters = content.get("search_parameters") or {}
    available = parameters.get("feature_available")
    if available is None:
        available = bool(content.get("results"))

    paragraphs: List[str] = []
    citations: List[Dict[str, Any]] = []
    seen: set[str] = set()
    for bucket in ("results", "serp_features"):
        items = content.get(bucket) or []
        if not isinstance(items, list):
            raise common.CollectorError(f"unexpected GoAnyAPI payload for {query!r}: {bucket} is not a list")
        for item in items:
            if not isinstance(item, dict):
                continue
            if bucket == "results":
                text = str(item.get("text") or "").strip()
                if text:
                    paragraphs.append(text)
            for link in item.get("links") or []:
                if not isinstance(link, dict):
                    continue
                url = str(link.get("url") or "").strip()
                if not url:
                    continue
                key = _citation_key(url)
                if key in seen:
                    continue
                seen.add(key)
                citations.append(
                    {
                        "position": len(citations) + 1,
                        "url": url,
                        "domain": _domain_of(url),
                        "title": str(link.get("title") or ""),
                    }
                )
                if len(citations) >= MAX_CITATIONS:
                    break

    target = _normalize_domain(target_domain)
    target_position = None
    if target:
        for citation in citations:
            domain = citation["domain"]
            if domain == target or domain.endswith("." + target):
                target_position = citation["position"]
                break

    return {
        "v": SCHEMA_VERSION,
        "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "query": query,
        "engine": ENGINE,
        "available": bool(available),
        "answer": "\n\n".join(paragraphs),
        "citations": citations,
        "target_domain": target or None,
        "target_cited": target_position is not None,
        "target_position": target_position,
        "cost_credits": data.get("costCredits"),
        "remaining_credits": data.get("remainingCredits"),
    }


def fetch_ai_overview(query: str, api_key: str) -> Dict[str, Any]:
    """Call the GoAnyAPI ``google-ai-overview`` endpoint and return the JSON body."""
    status, body = common.http_post(
        API_URL,
        payload={"query": query, "output": "json"},
        headers={"Accept": "application/json", "Authorization": f"Bearer {api_key}"},
    )
    if status in (401, 403):
        raise common.CollectorError(
            f"GoAnyAPI rejected the request (HTTP {status}). Check ${API_KEY_ENV}."
        )
    if status == 402:
        raise common.CollectorError("GoAnyAPI balance exhausted (HTTP 402); top up before the next pass.")
    if status == 429:
        raise common.CollectorError("GoAnyAPI rate limit hit (HTTP 429); retry later or lower the cadence.")
    if status != 200:
        raise common.CollectorError(f"GoAnyAPI returned HTTP {status} for {query!r}")
    try:
        payload = json.loads(body)
    except json.JSONDecodeError as exc:
        raise common.CollectorError(f"GoAnyAPI returned invalid JSON for {query!r}: {exc}") from exc
    if not isinstance(payload, dict):
        raise common.CollectorError(f"GoAnyAPI returned a non-object body for {query!r}")
    return payload


def load_fixture(path: Path) -> Dict[str, Any]:
    """Read a recorded GoAnyAPI response body from disk (fixture mode)."""
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
) -> Dict[str, Any]:
    """Run one pass over ``queries``. Returns a machine-readable summary."""
    if not queries:
        raise common.CollectorError(
            "no queries configured: add collectors.ai_overview.queries to "
            f"{home / workspace.CONFIG_NAME} or pass --query"
        )
    api_key = os.environ.get(API_KEY_ENV, "").strip()
    if fixture is None and not api_key:
        raise common.CollectorError(
            f"${API_KEY_ENV} is not set. Export a GoAnyAPI key, or run with "
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
            payload = fetch_ai_overview(query, api_key)
        record = parse_ai_overview_response(payload, query, target_domain)
        common.append_record(paths[query], record)
        written.append(
            {
                "query": query,
                "stream": str(paths[query]),
                "available": record["available"],
                "target_cited": record["target_cited"],
                "target_position": record["target_position"],
            }
        )

    cited = sum(1 for item in written if item["target_cited"])
    with_overview = sum(1 for item in written if item["available"])
    summary = (
        f"{len(written)} query observation(s), AI Overview present in {with_overview}/{len(written)}, "
        f"target cited in {cited}/{len(written)}"
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
        help="Query to collect (repeatable). Default: collectors.ai_overview.queries from config.yaml.",
    )
    parser.add_argument(
        "--target-domain",
        default=None,
        help="Domain to report a citation position for. Default: collectors.ai_overview.target_domain.",
    )
    parser.add_argument(
        "--fixture",
        default=None,
        help="Replay a recorded response JSON file instead of calling the API (offline). "
        "Use collectors/fixtures/ai_overview_goanyapi_response.json.",
    )
    parser.add_argument("--json", action="store_true", help="Print the machine-readable summary.")
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    home = common.ensure_workspace()
    try:
        config = workspace.load_config(home)
        project = workspace.load_project_config(home)
    except (OSError, ValueError) as exc:
        return common.fail(str(exc))

    inputs = workspace.project_inputs(project, config)
    queries = args.queries or list(workspace.config_get(config, "collectors.ai_overview.queries", []) or [])
    target_domain = args.target_domain or str(
        workspace.config_get(config, "collectors.ai_overview.target_domain", "")
        or inputs["target_domain"]
        or ""
    )
    budget = workspace.config_get(config, "budgets.queries_per_day", None)

    try:
        result = collect(
            queries=[str(query) for query in queries],
            target_domain=target_domain,
            home=home,
            fixture=Path(args.fixture).expanduser() if args.fixture else None,
            budget=int(budget) if budget else None,
        )
    except common.CollectorError as exc:
        return common.fail(str(exc))

    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        for item in result["observations"]:
            position = item["target_position"]
            overview = "AI Overview" if item["available"] else "no AI Overview"
            print(
                f"✓ {item['query']}: {overview}, target citation "
                f"{position if position else '—'} → {item['stream']}"
            )
        print(result["log"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
