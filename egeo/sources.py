"""Fetch and excerpt the pages a tracker says were cited instead of the site.

SCAFFOLD — implement until ``tests/test_sources.py`` passes. Tests never touch the network:
they inject ``fetcher``.

- ``normalize_source``: strip whitespace; ``http(s)://...`` URLs are kept as-is; a bare domain
  (``libhunt.com`` or ``www.libhunt.com/path``) becomes ``https://`` + value, and a bare domain
  without a path gets a trailing ``/``; anything else (empty, contains spaces, no dot in the
  host) returns ``""``.
- ``host_of``: lowercase hostname without a leading ``www.``.
- ``html_to_excerpt``: stdlib ``html.parser``. Body text ignores everything inside head, script,
  style, noscript, nav, footer, header, svg, form, template. Title = text of ``<title>``
  (whitespace collapsed, stripped). Description = ``content`` of ``<meta name="description">``
  (attribute name compared case-insensitively). Body text = the remaining text chunks joined
  with single spaces, then all whitespace runs collapsed to one space and stripped.
  Excerpt = ``"\\n".join(part for part in (title, description, body) if part)``, truncated to
  ``max_chars`` characters and right-stripped. Returns ``(title, excerpt)``.
- ``default_fetcher(url) -> (status, content_type, text)``: urllib GET with User-Agent
  ``USER_AGENT``, timeout 15 s, read at most 2,000,000 bytes, decode with the response charset
  or utf-8 (errors="replace").
- ``fetch_source``: status != 200 -> ok=False, error ``"http_<status>"``; content type not
  containing ``html`` -> ok=False, error ``"not_html"``; any exception -> ok=False, error = the
  exception class name. Otherwise ok=True with title/text from ``html_to_excerpt``.
- ``fetch_sources``: normalize, drop ``""``, de-duplicate keeping first occurrence, drop URLs
  whose host equals ``exclude_domain`` or ends with ``"." + exclude_domain`` (compare with
  ``host_of``), keep the first ``limit``, fetch sequentially in that order. With ``cache_path``:
  read an existing JSON object ``{url: SourceDoc-as-dict}``, reuse cached entries whose
  ``ok`` is true, and write the updated cache back (indent=2) after fetching.
- ``placeholder_sources``: mock-mode stand-in (no network): same normalization/dedupe/exclude/
  limit, returns ``SourceDoc(url, ok=True, title=host, text=" ".join([host, *path_words]))`` where
  ``path_words`` are the non-empty pieces of the URL path split on ``/``, ``-``, ``_`` and ``.``.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, List, Optional, Tuple

USER_AGENT = "Mozilla/5.0 (compatible; egeo-fix-gaps; +https://egeoagents.com)"
DEFAULT_MAX_CHARS = 1500
DEFAULT_MAX_SOURCES = 6

Fetcher = Callable[[str], Tuple[int, str, str]]


@dataclass(frozen=True)
class SourceDoc:
    url: str
    ok: bool
    title: str = ""
    text: str = ""
    error: str = ""


import json as _json
import re as _re
from html.parser import HTMLParser
from urllib.parse import urlparse


def normalize_source(value: str) -> str:
    v = (value or "").strip()
    if not v or _re.search(r"\s", v):
        return ""
    if v.startswith(("http://", "https://")):
        return v
    host, _, path = v.partition("/")
    if "." not in host:
        return ""
    return "https://" + host + ("/" + path if path else "/")


def host_of(url: str) -> str:
    h = (urlparse(url).hostname or "").lower()
    return h[4:] if h.startswith("www.") else h


_SKIP = {"head", "script", "style", "noscript", "nav", "footer", "header", "svg", "form", "template"}


class _P(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.depth = 0; self.in_title = False; self.title = []; self.desc = ""; self.body = []

    def handle_starttag(self, tag, attrs):
        if tag == "title":
            self.in_title = True
        if tag == "meta":
            d = {k.lower(): (v or "") for k, v in attrs}
            if d.get("name", "").lower() == "description":
                self.desc = d.get("content", "")
        if tag in _SKIP:
            self.depth += 1

    def handle_endtag(self, tag):
        if tag == "title":
            self.in_title = False
        if tag in _SKIP and self.depth:
            self.depth -= 1

    def handle_data(self, data):
        if self.in_title:
            self.title.append(data)
        elif not self.depth:
            self.body.append(data)


def _ws(s):
    return _re.sub(r"\s+", " ", s).strip()


def html_to_excerpt(html: str, *, max_chars: int = DEFAULT_MAX_CHARS):
    p = _P(); p.feed(html); p.close()
    title = _ws("".join(p.title)); desc = _ws(p.desc); body = _ws(" ".join(p.body))
    excerpt = "\n".join(x for x in (title, desc, body) if x)[:max_chars].rstrip()
    return title, excerpt


def default_fetcher(url: str):
    import urllib.request
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=15) as r:
        raw = r.read(2_000_000)
        cs = r.headers.get_content_charset() or "utf-8"
        return r.status, r.headers.get("Content-Type", ""), raw.decode(cs, errors="replace")


def fetch_source(url: str, *, fetcher=None, max_chars: int = DEFAULT_MAX_CHARS) -> SourceDoc:
    f = fetcher or default_fetcher
    try:
        status, ctype, text = f(url)
    except Exception as exc:
        return SourceDoc(url=url, ok=False, error=type(exc).__name__)
    if status != 200:
        return SourceDoc(url=url, ok=False, error=f"http_{status}")
    if "html" not in (ctype or ""):
        return SourceDoc(url=url, ok=False, error="not_html")
    title, excerpt = html_to_excerpt(text, max_chars=max_chars)
    return SourceDoc(url=url, ok=True, title=title, text=excerpt)


def _select(values, exclude_domain, limit):
    out, seen = [], set()
    ex = (exclude_domain or "").lower()
    for v in values:
        u = normalize_source(v)
        if not u or u in seen:
            continue
        seen.add(u)
        h = host_of(u)
        if ex and (h == ex or h.endswith("." + ex)):
            continue
        out.append(u)
    return out[:limit]


def fetch_sources(values, *, exclude_domain: str = "", limit: int = DEFAULT_MAX_SOURCES, fetcher=None,
                  cache_path=None, max_chars: int = DEFAULT_MAX_CHARS):
    cache = {}
    if cache_path and Path(cache_path).exists():
        cache = _json.loads(Path(cache_path).read_text(encoding="utf-8"))
    docs = []
    for u in _select(values, exclude_domain, limit):
        c = cache.get(u)
        if c and c.get("ok"):
            docs.append(SourceDoc(**c)); continue
        d = fetch_source(u, fetcher=fetcher, max_chars=max_chars)
        cache[u] = d.__dict__.copy(); docs.append(d)
    if cache_path:
        Path(cache_path).parent.mkdir(parents=True, exist_ok=True)
        Path(cache_path).write_text(_json.dumps(cache, indent=2), encoding="utf-8")
    return docs


def placeholder_sources(values, *, exclude_domain: str = "", limit: int = DEFAULT_MAX_SOURCES):
    docs = []
    for u in _select(values, exclude_domain, limit):
        h = host_of(u)
        words = [w for w in _re.split(r"[/\-_.]", urlparse(u).path) if w]
        docs.append(SourceDoc(url=u, ok=True, title=h, text=" ".join([h, *words])))
    return docs
