"""Contract tests for egeo.sources. No network: every test injects a fetcher."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from egeo.sources import (
    SourceDoc,
    fetch_source,
    fetch_sources,
    host_of,
    html_to_excerpt,
    normalize_source,
    placeholder_sources,
)

HTML = """<html><head><title> Best GEO Tools  2026 </title>
<meta name="Description" content="A dated list of GEO tools.">
<style>.x{color:red}</style><script>var a = 1;</script></head>
<body><nav>Home | About</nav><header>Site header</header>
<h1>GEO tools</h1><p>E-GEO   rewrites pages.</p><p>LibHunt lists tools.</p>
<footer>Copyright</footer></body></html>"""


@pytest.mark.parametrize(
    "value,expected",
    [
        ("https://libhunt.com/r/eGEOagents", "https://libhunt.com/r/eGEOagents"),
        ("http://example.com", "http://example.com"),
        ("  libhunt.com ", "https://libhunt.com/"),
        ("www.libhunt.com/path", "https://www.libhunt.com/path"),
        ("", ""),
        ("not a url", ""),
        ("localhost", ""),
    ],
)
def test_normalize_source(value: str, expected: str) -> None:
    assert normalize_source(value) == expected


def test_host_of() -> None:
    assert host_of("https://www.LibHunt.com/r/x") == "libhunt.com"
    assert host_of("https://docs.egeoagents.com/") == "docs.egeoagents.com"


def test_html_to_excerpt() -> None:
    title, excerpt = html_to_excerpt(HTML)
    assert title == "Best GEO Tools 2026"
    assert excerpt == "Best GEO Tools 2026\nA dated list of GEO tools.\nGEO tools E-GEO rewrites pages. LibHunt lists tools."
    assert "Home" not in excerpt and "Copyright" not in excerpt and "var a" not in excerpt and "Site header" not in excerpt


def test_html_to_excerpt_truncates() -> None:
    _, excerpt = html_to_excerpt(HTML, max_chars=30)
    assert excerpt == "Best GEO Tools 2026\nA dated li"


def test_fetch_source_ok_and_errors() -> None:
    ok = fetch_source("https://a.com/", fetcher=lambda u: (200, "text/html; charset=utf-8", HTML))
    assert ok == SourceDoc(url="https://a.com/", ok=True, title="Best GEO Tools 2026", text=html_to_excerpt(HTML)[1], error="")
    assert fetch_source("https://a.com/", fetcher=lambda u: (404, "text/html", "")).error == "http_404"
    assert fetch_source("https://a.com/", fetcher=lambda u: (200, "application/pdf", "%PDF")).error == "not_html"

    def boom(url: str):
        raise TimeoutError("slow")

    failed = fetch_source("https://a.com/", fetcher=boom)
    assert failed.ok is False and failed.error == "TimeoutError"


def test_fetch_sources_normalizes_dedupes_excludes_and_limits() -> None:
    seen = []

    def fetcher(url: str):
        seen.append(url)
        return 200, "text/html", HTML

    docs = fetch_sources(
        ["libhunt.com", "https://libhunt.com/", "https://egeoagents.com/x", "https://www.egeoagents.com/",
         "https://blog.egeoagents.com/", "a.com", "b.com", "c.com"],
        exclude_domain="egeoagents.com",
        limit=3,
        fetcher=fetcher,
    )
    assert [d.url for d in docs] == ["https://libhunt.com/", "https://a.com/", "https://b.com/"]
    assert seen == ["https://libhunt.com/", "https://a.com/", "https://b.com/"]


def test_fetch_sources_cache(tmp_path: Path) -> None:
    cache = tmp_path / "cache.json"
    calls = []

    def fetcher(url: str):
        calls.append(url)
        return 200, "text/html", HTML

    first = fetch_sources(["a.com"], fetcher=fetcher, cache_path=cache)
    second = fetch_sources(["a.com"], fetcher=fetcher, cache_path=cache)
    assert calls == ["https://a.com/"]
    assert first == second
    assert json.loads(cache.read_text(encoding="utf-8"))["https://a.com/"]["ok"] is True


def test_placeholder_sources_no_network() -> None:
    docs = placeholder_sources(["https://www.toolradar.com/best-geo-tools", "egeoagents.com"], exclude_domain="egeoagents.com")
    assert docs == [SourceDoc(url="https://www.toolradar.com/best-geo-tools", ok=True, title="toolradar.com",
                              text="toolradar.com best geo tools", error="")]
