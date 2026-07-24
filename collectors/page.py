#!/usr/bin/env python3
"""Page collector: content and schema drift on the pages you optimize.

Deterministic, zero LLM calls. One record per URL per pass, appended to
``$EGEO_HOME/data/page/<page-slug>.jsonl``::

    {"v": 1, "ts": "...Z", "url": "...", "status": 200,
     "content_hash": "<sha256 of the body>", "title": "...",
     "meta_description": "..." | null, "jsonld_types": ["Article"], "word_count": 812}

``content_hash`` is stable for an unchanged page, so the agent detects drift by
comparing consecutive records. HTML is parsed with ``html.parser`` — no
third-party dependency anywhere in loop mode.

Usage::

    python collectors/page.py                      # urls from config.yaml
    python collectors/page.py --url https://example.com/pricing
    python collectors/page.py --fixture collectors/fixtures/pages/
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Dict, List, Optional

if __package__ in (None, ""):  # executed as a script
    sys.path.insert(0, str(Path(__file__).resolve().parent))

import _common as common  # noqa: E402
from egeo import workspace  # noqa: E402

SCHEMA_VERSION = 1
COLLECTOR = "page"
FIXTURE_SUFFIXES = (".html", ".htm", ".txt")


class _PageParser(HTMLParser):
    """Extract title, meta description, JSON-LD @types and visible text."""

    _SKIP_TEXT_IN = {"script", "style", "noscript", "template"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title: Optional[str] = None
        self.meta_description: Optional[str] = None
        self.jsonld_blocks: List[str] = []
        self.text_parts: List[str] = []
        self._stack: List[str] = []
        self._in_title = False
        self._in_jsonld = False

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        self._stack.append(tag)
        attributes = {key.lower(): (value or "") for key, value in attrs}
        if tag == "title" and self.title is None:
            self._in_title = True
        elif tag == "meta":
            name = attributes.get("name", "").lower()
            prop = attributes.get("property", "").lower()
            if self.meta_description is None and name == "description":
                self.meta_description = attributes.get("content", "").strip() or None
            elif self.meta_description is None and prop == "og:description":
                self.meta_description = attributes.get("content", "").strip() or None
        elif tag == "script" and attributes.get("type", "").lower() == "application/ld+json":
            self._in_jsonld = True
            self.jsonld_blocks.append("")

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag == "title":
            self._in_title = False
        if tag == "script":
            self._in_jsonld = False
        for index in range(len(self._stack) - 1, -1, -1):
            if self._stack[index] == tag:
                del self._stack[index:]
                break

    def handle_data(self, data):
        if self._in_title:
            self.title = ((self.title or "") + data).strip() or None
            return
        if self._in_jsonld and self.jsonld_blocks:
            self.jsonld_blocks[-1] += data
            return
        if not any(tag in self._SKIP_TEXT_IN for tag in self._stack):
            self.text_parts.append(data)


def _jsonld_types(blocks: List[str]) -> List[str]:
    """Collect declared ``@type`` values across all JSON-LD blocks, in order.

    Unparseable blocks are recorded as ``"<invalid-json-ld>"``: the collector
    reports what is on the page, it does not judge it.
    """
    types: List[str] = []

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            value = node.get("@type")
            if isinstance(value, str):
                types.append(value)
            elif isinstance(value, list):
                types.extend(str(item) for item in value)
            for child in node.values():
                walk(child)
        elif isinstance(node, list):
            for child in node:
                walk(child)

    for block in blocks:
        text = block.strip()
        if not text:
            continue
        try:
            walk(json.loads(text))
        except json.JSONDecodeError:
            types.append("<invalid-json-ld>")

    seen: List[str] = []
    for value in types:
        if value not in seen:
            seen.append(value)
    return seen


def parse_page(url: str, status: int, body: str) -> Dict[str, Any]:
    """Turn a fetched page body into one versioned observation record."""
    parser = _PageParser()
    parser.feed(body)
    parser.close()
    text = re.sub(r"\s+", " ", " ".join(parser.text_parts)).strip()
    return {
        "v": SCHEMA_VERSION,
        "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "url": url,
        "status": status,
        "content_hash": hashlib.sha256(body.encode("utf-8")).hexdigest(),
        "title": parser.title,
        "meta_description": parser.meta_description,
        "jsonld_types": _jsonld_types(parser.jsonld_blocks),
        "word_count": len(text.split()) if text else 0,
    }


def fixture_body(fixture: Path, url: str) -> str:
    """Read the recorded body for ``url`` from a fixture file or directory.

    A directory is matched by slug: ``<page-slug>.html`` (``.htm``/``.txt`` also
    accepted). A file is used directly, which makes single-URL replays trivial.
    """
    if fixture.is_file():
        return fixture.read_text(encoding="utf-8")
    if not fixture.is_dir():
        raise common.CollectorError(f"fixture not found: {fixture}")
    slug = common.slugify(url)
    for suffix in FIXTURE_SUFFIXES:
        candidate = fixture / f"{slug}{suffix}"
        if candidate.is_file():
            return candidate.read_text(encoding="utf-8")
    raise common.CollectorError(
        f"no fixture for {url} in {fixture} (expected {slug}{FIXTURE_SUFFIXES[0]})"
    )


def collect(
    *,
    urls: List[str],
    home: Path,
    fixture: Optional[Path] = None,
    budget: Optional[int] = None,
) -> Dict[str, Any]:
    """Run one pass over ``urls``. Returns a machine-readable summary."""
    if not urls:
        raise common.CollectorError(
            "no URLs configured: add collectors.page.urls to "
            f"{home / workspace.CONFIG_NAME} or pass --url"
        )
    if budget:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        already = common.count_today(sorted(workspace.data_dir(COLLECTOR, home).glob("*.jsonl")), today)
        if already + len(urls) > budget:
            raise common.CollectorError(
                f"budgets.pages_per_day={budget} would be exceeded: "
                f"{already} recorded today + {len(urls)} requested. "
                "Raise the budget in config.yaml or shorten the URL list."
            )

    written: List[Dict[str, Any]] = []
    changed = 0
    for url in urls:
        if fixture is not None:
            status, body = 200, fixture_body(fixture, url)
        else:
            status, body = common.http_get(url)
            if status >= 400:
                raise common.CollectorError(f"{url} returned HTTP {status}")
        record = parse_page(url, status, body)
        path = common.stream_path(COLLECTOR, common.slugify(url), home)
        previous = common.read_records(path)
        if previous and previous[-1].get("content_hash") != record["content_hash"]:
            changed += 1
        common.append_record(path, record)
        written.append(
            {
                "url": url,
                "stream": str(path),
                "status": record["status"],
                "content_hash": record["content_hash"],
                "word_count": record["word_count"],
                "jsonld_types": record["jsonld_types"],
            }
        )

    summary = (
        f"{len(written)} page observation(s), {changed} changed since last pass"
        f"{' (fixture mode)' if fixture is not None else ''}, outcome=success"
    )
    log_line = common.log_pass(COLLECTOR, summary, home=home)
    return {"collector": COLLECTOR, "observations": written, "changed": changed, "log": log_line}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--url",
        action="append",
        dest="urls",
        help="URL to collect (repeatable). Default: collectors.page.urls from config.yaml.",
    )
    parser.add_argument(
        "--fixture",
        default=None,
        help="Replay recorded HTML from a file or a directory of <page-slug>.html files (offline).",
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

    urls = args.urls or list(workspace.config_get(config, "collectors.page.urls", []) or [])
    budget = workspace.config_get(config, "budgets.pages_per_day", None)

    try:
        result = collect(
            urls=[str(url) for url in urls],
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
            types = ", ".join(item["jsonld_types"]) or "no JSON-LD"
            print(f"✓ {item['url']}: {item['word_count']} words, {types} → {item['stream']}")
        print(result["log"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
