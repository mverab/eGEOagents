"""Public URL audit core: one page -> checks, GEO feature breakdown, one rewritten section.

Spec: ``openspec/changes/add-public-url-audit/specs/url-audit-api/spec.md``; design: same
change, ``design.md``. Stdlib only: the HTTP layer lives in :mod:`egeo.audit_service` and
is an optional extra, so ``import egeo.url_audit`` works on a plain ``pip install egeo``.

Pipeline (:func:`audit_url`):

1. ``normalize_url`` / ``normalize_query`` validate the input (``invalid_url`` / ``invalid_query``).
2. ``guarded_fetch`` fetches the page through the SSRF guard: every hop (max 5 redirects) is
   re-validated, every resolved address must be globally routable, and the connection goes to
   the vetted address (no DNS rebinding between check and connect).
3. ``html_to_markdown`` turns the page into Markdown (headings, paragraphs, lists, links,
   tables) for ``egeo.sections`` and ``egeo.fidelity``, which both work on Markdown.
4. Seven deterministic checks, the offline ``Analyzer`` breakdown (no aggregate score), and at
   most ONE LLM rewrite of the weakest qualifying section, shown only if it passes
   ``egeo.fidelity.check_fidelity``.

Every network and clock dependency is injectable (``resolver``, ``transport``, ``now``) so the
tests never touch the network.
"""
from __future__ import annotations

import http.client
import ipaddress
import os
import re
import socket
import ssl
import time
from dataclasses import dataclass
from html.parser import HTMLParser
from typing import Any, Callable, Dict, List, Optional, Tuple
from urllib import robotparser
from urllib.parse import urljoin, urlsplit, urlunsplit

from . import fidelity as _fidelity
from . import section_rewriter as _section_rewriter
from . import sections as _sections
from .agents import GEO_FEATURES, _RECOMMENDATIONS, Analyzer
from .sources import _SKIP

USER_AGENT = "Mozilla/5.0 (compatible; egeo-audit/1.0; +https://egeoagents.com)"

MAX_URL_LENGTH = 2048
MAX_QUERY_LENGTH = 200
MAX_REDIRECTS = 5
FETCH_TIMEOUT_S = 10.0
MAX_BYTES = 2_000_000
DEADLINE_S = 30.0
MIN_REWRITE_REMAINING_S = 12.0
MIN_SECTION_WORDS = 40
MAX_SECTION_WORDS = 600
MIN_VISIBLE_WORDS = 150

AI_CRAWLERS: Tuple[str, ...] = (
    "GPTBot",
    "OAI-SearchBot",
    "ChatGPT-User",
    "ClaudeBot",
    "PerplexityBot",
    "Google-Extended",
)
CHECK_IDS: Tuple[str, ...] = (
    "ai_crawler_access",
    "llms_txt",
    "json_ld",
    "title",
    "meta_description",
    "single_h1",
    "visible_text",
)
REWRITE_STATUSES: Tuple[str, ...] = (
    "shown",
    "withheld_fidelity",
    "skipped_no_candidate",
    "skipped_budget",
    "skipped_timeout",
    "error",
)
REWRITE_NOTE = "Checked by deterministic fidelity rules; not verified by an LLM judge."
FEATURES_NOTE = (
    "Keyword heuristic from E-GEO's offline Analyzer: a quick signal of which GEO features the "
    "text expresses, not a prediction of how any answer engine ranks the page."
)
_REDIRECTS = {301, 302, 303, 307, 308}
_INVALID_JSONLD = "<invalid-json-ld>"


# --------------------------------------------------------------------------- #
# Errors
# --------------------------------------------------------------------------- #
class AuditError(Exception):
    """An audit failure that maps to one API error code and HTTP status."""

    code = "audit_error"
    status = 500

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class InvalidUrl(AuditError):
    code, status = "invalid_url", 400


class InvalidQuery(AuditError):
    code, status = "invalid_query", 400


class BlockedTarget(AuditError):
    code, status = "blocked_target", 422


class FetchFailed(AuditError):
    code, status = "fetch_failed", 502


class AuditTimeout(AuditError):
    code, status = "audit_timeout", 504


# --------------------------------------------------------------------------- #
# Input validation
# --------------------------------------------------------------------------- #
_HOST_RE = re.compile(r"^[a-z0-9-]+(\.[a-z0-9-]+)+$")


def normalize_url(value: Any) -> str:
    """Validate and normalize an audit target URL, or raise :class:`InvalidUrl`.

    Accepts absolute ``http``/``https`` URLs (or a bare domain, which becomes ``https://``) of at
    most 2,048 characters, with no port or port 80/443, a DNS host name (no IP literal, no
    credentials). Normalization lowercases scheme and host, drops the fragment and default
    ports, and turns an empty path into ``/``. The result doubles as the cache-key URL.
    """
    if not isinstance(value, str):
        raise InvalidUrl("Enter the URL of a public web page, e.g. https://example.com/pricing.")
    v = value.strip()
    if not v or len(v) > MAX_URL_LENGTH or re.search(r"\s", v):
        raise InvalidUrl("Enter one URL of at most 2,048 characters, with no spaces.")
    if "://" not in v:
        if v.startswith("/") or "." not in v.split("/", 1)[0]:
            raise InvalidUrl("Enter a full URL such as https://example.com/.")
        v = "https://" + v
    parts = urlsplit(v)
    scheme = parts.scheme.lower()
    if scheme not in ("http", "https"):
        raise InvalidUrl("Only http:// and https:// URLs can be audited.")
    try:
        port = parts.port
    except ValueError:
        raise InvalidUrl("The URL has an invalid port.") from None
    if port not in (None, 80, 443):
        raise InvalidUrl("Only the standard ports (80 and 443) can be audited.")
    if parts.username is not None or parts.password is not None:
        raise InvalidUrl("URLs with credentials cannot be audited.")
    host = (parts.hostname or "").rstrip(".")
    if not host:
        raise InvalidUrl("The URL has no host name.")
    try:
        ipaddress.ip_address(host)
    except ValueError:
        pass
    else:
        raise InvalidUrl("Use the site's domain name, not an IP address.")
    try:
        host = host.encode("idna").decode("ascii").lower()
    except UnicodeError:
        raise InvalidUrl("The host name is not valid.") from None
    if not _HOST_RE.match(host):
        raise InvalidUrl("The host name is not valid.")
    default_port = 80 if scheme == "http" else 443
    netloc = host if port in (None, default_port) else f"{host}:{port}"
    out = urlunsplit((scheme, netloc, parts.path or "/", parts.query, ""))
    if len(out) > MAX_URL_LENGTH:
        raise InvalidUrl("Enter one URL of at most 2,048 characters, with no spaces.")
    return out


def normalize_query(value: Any) -> Optional[str]:
    """Return the trimmed visitor query, ``None`` when absent, or raise :class:`InvalidQuery`."""
    if value is None:
        return None
    if not isinstance(value, str):
        raise InvalidQuery("The target query must be text.")
    q = value.strip()
    if not q or len(q) > MAX_QUERY_LENGTH:
        raise InvalidQuery("The target query must be 1 to 200 characters, or left empty.")
    return q


def cache_key(url: str, query: Optional[str]) -> str:
    """Cache key: normalized URL + the requested query ('' means "derive from the page").

    The derived query is a pure function of the page, so URL + "derive" identifies it.
    """
    return f"{url}\n{query or ''}"


# --------------------------------------------------------------------------- #
# SSRF-guarded fetching
# --------------------------------------------------------------------------- #
Resolver = Callable[[str, int], List[str]]


@dataclass(frozen=True)
class RawResponse:
    status: int
    headers: Dict[str, str]  # lowercased names
    body: bytes


Transport = Callable[[str, str, float, float], RawResponse]  # (ip, url, timeout, deadline)


@dataclass(frozen=True)
class FetchResult:
    url: str  # final URL after redirects
    status: int
    content_type: str
    text: str


def is_public_address(value: str) -> bool:
    """True only for globally routable unicast addresses (IPv4-mapped IPv6 is unwrapped)."""
    try:
        ip = ipaddress.ip_address(value.split("%", 1)[0])
    except ValueError:
        return False
    mapped = getattr(ip, "ipv4_mapped", None)
    if mapped is not None:
        ip = mapped
    return bool(
        ip.is_global
        and not ip.is_private
        and not ip.is_loopback
        and not ip.is_link_local
        and not ip.is_multicast
        and not ip.is_reserved
        and not ip.is_unspecified
    )


def default_resolver(host: str, port: int) -> List[str]:
    infos = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    out: List[str] = []
    for info in infos:
        addr = info[4][0]
        if addr not in out:
            out.append(addr)
    return out


class _PinnedHTTPConnection(http.client.HTTPConnection):
    def __init__(self, host: str, port: int, ip: str, timeout: float) -> None:
        super().__init__(host, port, timeout=timeout)
        self._ip = ip

    def connect(self) -> None:
        self.sock = socket.create_connection((self._ip, self.port), self.timeout)


class _PinnedHTTPSConnection(http.client.HTTPSConnection):
    def __init__(self, host: str, port: int, ip: str, timeout: float) -> None:
        super().__init__(host, port, timeout=timeout, context=ssl.create_default_context())
        self._ip = ip

    def connect(self) -> None:
        sock = socket.create_connection((self._ip, self.port), self.timeout)
        self.sock = self._context.wrap_socket(sock, server_hostname=self.host)


def default_transport(ip: str, url: str, timeout: float, deadline: float) -> RawResponse:
    """One GET to an already-vetted address; never follows redirects; reads <= 2 MB."""
    parts = urlsplit(url)
    https = parts.scheme == "https"
    port = parts.port or (443 if https else 80)
    cls = _PinnedHTTPSConnection if https else _PinnedHTTPConnection
    conn = cls(parts.hostname or "", port, ip, timeout)
    path = (parts.path or "/") + (f"?{parts.query}" if parts.query else "")
    try:
        conn.request(
            "GET",
            path,
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "text/html,application/xhtml+xml,text/plain;q=0.9,*/*;q=0.5",
                "Accept-Encoding": "identity",
            },
        )
        resp = conn.getresponse()
        chunks: List[bytes] = []
        size = 0
        while size < MAX_BYTES:
            if time.monotonic() >= deadline:
                raise TimeoutError("deadline reached while reading")
            chunk = resp.read(min(65536, MAX_BYTES - size))
            if not chunk:
                break
            chunks.append(chunk)
            size += len(chunk)
        headers = {k.lower(): v for k, v in resp.getheaders()}
        return RawResponse(status=resp.status, headers=headers, body=b"".join(chunks))
    finally:
        conn.close()


def _decode(body: bytes, content_type: str) -> str:
    m = re.search(r"charset=([\w.-]+)", content_type or "", re.I)
    charset = m.group(1) if m else "utf-8"
    try:
        return body.decode(charset, errors="replace")
    except LookupError:
        return body.decode("utf-8", errors="replace")


def guarded_fetch(
    url: str,
    *,
    resolver: Optional[Resolver] = None,
    transport: Optional[Transport] = None,
    now: Callable[[], float] = time.monotonic,
    deadline: float,
    max_redirects: int = MAX_REDIRECTS,
) -> FetchResult:
    """GET ``url`` through the SSRF guard, following at most ``max_redirects`` vetted redirects.

    Raises :class:`BlockedTarget` when any hop resolves to a non-public address (or a redirect
    points at an IP literal, a non-http(s) scheme or a non-standard port), :class:`FetchFailed`
    on network errors / too many redirects, :class:`AuditTimeout` once ``deadline`` has passed.
    """
    resolve = resolver or default_resolver
    send = transport or default_transport
    current = url
    for hop in range(max_redirects + 1):
        if hop:
            try:
                current = normalize_url(current)
            except InvalidUrl as exc:
                raise BlockedTarget(f"The page redirects to a URL that cannot be audited ({exc.message})") from None
        parts = urlsplit(current)
        host = parts.hostname or ""
        port = parts.port or (443 if parts.scheme == "https" else 80)
        remaining = deadline - now()
        if remaining <= 0:
            raise AuditTimeout("The audit ran out of time.")
        try:
            addresses = resolve(host, port)
        except (OSError, UnicodeError):
            raise FetchFailed(f"DNS lookup failed for {host}.") from None
        if not addresses:
            raise FetchFailed(f"DNS lookup returned no address for {host}.")
        if not all(is_public_address(a) for a in addresses):
            raise BlockedTarget(f"{host} resolves to a private or reserved address and cannot be audited.")
        try:
            resp = send(addresses[0], current, min(FETCH_TIMEOUT_S, remaining), deadline)
        except AuditError:
            raise
        except Exception as exc:  # network, TLS, protocol, timeout
            if now() >= deadline:
                raise AuditTimeout("The audit ran out of time.") from None
            raise FetchFailed(f"Could not fetch {host}: {type(exc).__name__}.") from None
        location = resp.headers.get("location")
        if resp.status in _REDIRECTS and location:
            current = urljoin(current, location.strip())
            continue
        ctype = resp.headers.get("content-type", "")
        return FetchResult(url=current, status=resp.status, content_type=ctype, text=_decode(resp.body, ctype))
    raise FetchFailed(f"Too many redirects (more than {max_redirects}).")


# --------------------------------------------------------------------------- #
# HTML -> Markdown (+ the page facts the checks need)
# --------------------------------------------------------------------------- #
_BLOCK_TAGS = {
    "p", "div", "section", "article", "main", "aside", "blockquote", "pre", "ul", "ol", "dl",
    "dd", "dt", "figure", "figcaption", "table", "thead", "tbody", "tfoot", "body", "html",
}
_HEADINGS = {f"h{i}": i for i in range(1, 7)}
_VOID = {"br", "img", "hr", "meta", "link", "input", "source", "wbr", "area", "base", "col", "embed", "param", "track"}


def _ws(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


@dataclass
class PageFacts:
    markdown: str
    meta_description: str
    h1_count: int
    first_h1: str
    visible_words: int


class _MarkdownParser(HTMLParser):
    def __init__(self, base_url: str) -> None:
        super().__init__(convert_charrefs=True)
        self.base = base_url
        self.skip = 0
        self.blocks: List[str] = []
        self.buf: List[str] = []
        self.kind: Tuple[str, int] = ("p", 0)
        self.links: List[Tuple[int, str]] = []
        self.row: Optional[List[str]] = None
        self.cell: Optional[List[str]] = None
        self.meta_description = ""
        self.h1_count = 0
        self.first_h1 = ""
        self.visible: List[str] = []

    # -- block handling -------------------------------------------------- #
    def _flush(self) -> None:
        text = _ws("".join(self.buf))
        self.buf = []
        kind, level = self.kind
        self.kind = ("p", 0)
        if not text:
            return
        if kind == "h":
            self.blocks.append("#" * level + " " + text)
        elif kind == "li":
            self.blocks.append("- " + text)
        else:
            if text.startswith("#"):
                text = "\\" + text  # never let a paragraph become a heading
            self.blocks.append(text)

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]) -> None:
        tag = tag.lower()
        a = {k.lower(): (v or "") for k, v in attrs}
        if tag == "meta" and a.get("name", "").lower() == "description" and not self.meta_description:
            self.meta_description = _ws(a.get("content", ""))
        if tag == "h1":
            self.h1_count += 1
        if tag in _SKIP:
            self.skip += 1
            return
        if self.skip:
            return
        if tag in _HEADINGS:
            self._flush()
            self.kind = ("h", _HEADINGS[tag])
        elif tag == "li":
            self._flush()
            self.kind = ("li", 0)
        elif tag == "tr":
            self._flush()
            self.row = []
        elif tag in ("td", "th") and self.row is not None:
            self.cell = []
        elif tag in _BLOCK_TAGS:
            self._flush()
        elif tag == "br":
            self._target().append(" ")
        elif tag == "a":
            href = a.get("href", "").strip()
            absolute = urljoin(self.base, href) if href else ""
            if not absolute.startswith(("http://", "https://")):
                absolute = ""
            self.links.append((len(self._target()), absolute))

    def handle_startendtag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]) -> None:
        self.handle_starttag(tag, attrs)
        if tag.lower() not in _VOID:
            self.handle_endtag(tag)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in _SKIP:
            if self.skip:
                self.skip -= 1
            return
        if self.skip:
            return
        if tag in _HEADINGS:
            if tag == "h1" and not self.first_h1:
                self.first_h1 = _ws("".join(self.buf))
            self._flush()
        elif tag == "li":
            self._flush()
        elif tag in ("td", "th") and self.row is not None and self.cell is not None:
            self.row.append(_ws("".join(self.cell)).replace("|", "\\|"))
            self.cell = None
        elif tag == "tr" and self.row is not None:
            if any(self.row):
                self.blocks.append("| " + " | ".join(self.row) + " |")
            self.row = None
        elif tag in _BLOCK_TAGS:
            self._flush()
        elif tag == "a" and self.links:
            start, href = self.links.pop()
            target = self._target()
            text = _ws("".join(target[start:]))
            del target[start:]
            target.append(f"[{text}]({href})" if (text and href) else text)

    def _target(self) -> List[str]:
        return self.cell if self.cell is not None else self.buf

    def handle_data(self, data: str) -> None:
        if self.skip:
            return
        self.visible.append(data)
        self._target().append(data)

    def close(self) -> None:
        super().close()
        self._flush()


def html_to_markdown(html: str, base_url: str) -> PageFacts:
    """Convert the page's main content to Markdown and collect the facts the checks need.

    Skips the same containers as ``egeo.sources`` (head, script, style, noscript, nav, footer,
    header, svg, form, template). ``h1_count`` counts every ``h1`` in the document.
    """
    p = _MarkdownParser(base_url)
    p.feed(html)
    p.close()
    md = "\n\n".join(p.blocks)
    return PageFacts(
        markdown=md + ("\n" if md else ""),
        meta_description=p.meta_description,
        h1_count=p.h1_count,
        first_h1=p.first_h1,
        visible_words=_sections.count_words(" ".join(p.visible)),
    )


_page_collector = None


def _parse_page(url: str, status: int, html: str) -> Dict[str, Any]:
    """Title and JSON-LD ``@type``s via the loop-mode page collector (``collectors/page.py``)."""
    global _page_collector
    if _page_collector is None:
        from .loop import load_collector

        _page_collector = load_collector("page")
    return _page_collector.parse_page(url, status, html)


# --------------------------------------------------------------------------- #
# Checks
# --------------------------------------------------------------------------- #
def _check(check_id: str, status: str, evidence: str, fix: Optional[str] = None) -> Dict[str, Any]:
    out: Dict[str, Any] = {"id": check_id, "status": status, "evidence": evidence}
    if status == "fail":
        out["fix"] = fix or ""
    return out


def _origin(url: str) -> str:
    p = urlsplit(url)
    return f"{p.scheme}://{p.netloc}"


def check_ai_crawler_access(robots: Optional[FetchResult], error: str, page_url: str) -> Dict[str, Any]:
    cid = "ai_crawler_access"
    if robots is None:
        return _check(cid, "unverifiable", f"robots.txt could not be fetched ({error}).")
    if robots.status == 404:
        return _check(cid, "pass", "No robots.txt (HTTP 404): no crawler is restricted.")
    if robots.status != 200:
        return _check(cid, "unverifiable", f"robots.txt returned HTTP {robots.status}.")
    rp = robotparser.RobotFileParser()
    rp.parse(robots.text.splitlines())
    blocked = [agent for agent in AI_CRAWLERS if not rp.can_fetch(agent, page_url)]
    if not blocked:
        return _check(cid, "pass", "robots.txt allows " + ", ".join(AI_CRAWLERS) + " on this path.")
    names = ", ".join(blocked)
    return _check(
        cid,
        "fail",
        f"robots.txt blocks {names} on this path.",
        f"In /robots.txt, remove the Disallow rules that match this path for {names} "
        f"(or add `Allow: /` under `User-agent: {blocked[0]}`) so AI search crawlers can read the page.",
    )


def check_llms_txt(llms: Optional[FetchResult], error: str) -> Dict[str, Any]:
    cid = "llms_txt"
    fix = "Publish /llms.txt (llmstxt.org format): a short Markdown summary of the site with links to its key pages."
    if llms is None:
        return _check(cid, "unverifiable", f"/llms.txt could not be fetched ({error}).")
    is_html = "html" in (llms.content_type or "").lower()
    if llms.status == 200 and not is_html:
        return _check(cid, "pass", f"/llms.txt found ({llms.content_type or 'no content type'}).")
    if llms.status == 404:
        return _check(cid, "fail", "/llms.txt not found (HTTP 404).", fix)
    if llms.status == 200 and is_html:
        return _check(cid, "fail", "/llms.txt returns an HTML page (likely a soft 404).", fix)
    return _check(cid, "unverifiable", f"/llms.txt returned HTTP {llms.status}.")


def check_page_metadata(record: Dict[str, Any], facts: PageFacts) -> List[Dict[str, Any]]:
    types = [t for t in record.get("jsonld_types") or [] if t != _INVALID_JSONLD]
    invalid = _INVALID_JSONLD in (record.get("jsonld_types") or [])
    if types:
        json_ld = _check("json_ld", "pass", "JSON-LD types: " + ", ".join(types) + ".")
    else:
        json_ld = _check(
            "json_ld",
            "fail",
            "No JSON-LD @type found" + (" (an invalid JSON-LD block is present)." if invalid else "."),
            "Add a JSON-LD block (e.g. Organization, Product or Article) that describes this page; "
            "`egeo optimize` or `/geo` can generate one.",
        )
    title = (record.get("title") or "").strip()
    title_check = (
        _check("title", "pass", title)
        if title
        else _check("title", "fail", "No <title>.", "Add a <title> that names what the page offers.")
    )
    meta = facts.meta_description
    meta_check = (
        _check("meta_description", "pass", meta)
        if meta
        else _check(
            "meta_description",
            "fail",
            'No <meta name="description">.',
            'Add <meta name="description" content="..."> with one sentence on what the page offers and for whom.',
        )
    )
    n = facts.h1_count
    if n == 1:
        h1 = _check("single_h1", "pass", "1")
    else:
        h1 = _check(
            "single_h1",
            "fail",
            str(n),
            "Add one <h1> that states the page's main topic." if n == 0 else "Keep one <h1> and turn the others into <h2>.",
        )
    return [json_ld, title_check, meta_check, h1]


def check_visible_text(facts: PageFacts) -> Dict[str, Any]:
    n = facts.visible_words
    if n >= MIN_VISIBLE_WORDS:
        return _check("visible_text", "pass", f"{n} words")
    return _check(
        "visible_text",
        "fail",
        f"{n} words",
        "Serve the main content as HTML (server-side or static rendering) so crawlers that do not run JavaScript can read it.",
    )


# --------------------------------------------------------------------------- #
# Features, query, rewrite
# --------------------------------------------------------------------------- #
def feature_breakdown(markdown: str, title: str) -> Dict[str, Any]:
    analysis = Analyzer().analyze(markdown, title=title or None)
    items = []
    for feat in GEO_FEATURES:
        score = int(analysis.scores[feat])
        item: Dict[str, Any] = {"id": feat, "score": score}
        if score < 5:
            item["recommendation"] = _RECOMMENDATIONS[feat]
        items.append(item)
    return {"method": "heuristic", "note": FEATURES_NOTE, "items": items}


def effective_query(visitor_query: Optional[str], title: str, first_h1: str, url: str) -> Tuple[str, str]:
    if visitor_query:
        return visitor_query, "visitor"
    subject = title or first_h1 or (urlsplit(url).hostname or "")
    return f"best {subject}".strip(), "derived"


class _OneShotClient:
    """OpenAI-compatible client bound to the remaining time; exactly one attempt, no retries."""

    def __init__(self, timeout_s: float) -> None:
        import llm_client

        base = llm_client.OpenAICompatibleClient.from_env()
        cfg = base._config
        self._inner = llm_client.OpenAICompatibleClient(
            llm_client.OpenAICompatibleConfig(
                api_key=cfg.api_key, base_url=cfg.base_url, timeout_seconds=max(1, int(timeout_s))
            )
        )

    def chat_text(self, **kwargs: Any) -> str:
        kwargs["max_retries"] = 1
        return self._inner.chat_text(**kwargs)


def _mock_enabled() -> bool:
    return (os.environ.get("GEO_EVAL_MOCK") or "").strip().lower() in {"1", "true", "yes"}


def default_llm_factory(timeout_s: float) -> Any:
    return None if _mock_enabled() else _OneShotClient(timeout_s)


def pick_section(markdown: str) -> Optional[_sections.Section]:
    """Lowest Analyzer total among non-preamble sections with 40-600 words; ties -> earliest."""
    candidates = [
        s
        for s in _sections.split_sections(markdown)
        if s.level > 0 and MIN_SECTION_WORDS <= s.word_count <= MAX_SECTION_WORDS
    ]
    if not candidates:
        return None
    analyzer = Analyzer()
    scored = [(analyzer.analyze(s.text, title=s.heading or None).total_score, i, s) for i, s in enumerate(candidates)]
    return min(scored, key=lambda t: (t[0], t[1]))[2]


def rewrite_one_section(
    markdown: str,
    *,
    title: str,
    query: str,
    now: Callable[[], float],
    deadline: float,
    reserve_llm: Callable[[], bool],
    llm_factory: Callable[[float], Any],
    model: str,
) -> Dict[str, Any]:
    out: Dict[str, Any] = {"status": "", "query": query, "section_heading": None, "before": None, "note": REWRITE_NOTE}
    section = pick_section(markdown)
    if section is None:
        out["status"] = "skipped_no_candidate"
        return out
    out["section_heading"] = section.heading
    out["before"] = section.text
    remaining = deadline - now()
    if remaining < MIN_REWRITE_REMAINING_S:
        out["status"] = "skipped_timeout"
        return out
    if not reserve_llm():
        out["status"] = "skipped_budget"
        return out
    try:
        client = llm_factory(remaining - 1.0)
        after = _section_rewriter.rewrite_section(query, section.text, page_title=title, model=model, client=client)
    except Exception:
        out["status"] = "error"
        return out
    result = _fidelity.check_fidelity(section.text, after)
    if not result.passed:
        out["status"] = "withheld_fidelity"
        out["violations"] = list(result.violations)
        return out
    out["status"] = "shown"
    out["after"] = after
    return out


# --------------------------------------------------------------------------- #
# Entry point
# --------------------------------------------------------------------------- #
def _fetch_optional(url: str, **kw: Any) -> Tuple[Optional[FetchResult], str]:
    try:
        return guarded_fetch(url, **kw), ""
    except AuditError as exc:
        return None, exc.code
    except Exception as exc:  # pragma: no cover - defensive
        return None, type(exc).__name__


def audit_url(
    url: Any,
    query: Any = None,
    *,
    resolver: Optional[Resolver] = None,
    transport: Optional[Transport] = None,
    now: Callable[[], float] = time.monotonic,
    deadline_s: float = DEADLINE_S,
    reserve_llm: Callable[[], bool] = lambda: True,
    llm_factory: Optional[Callable[[float], Any]] = None,
    model: Optional[str] = None,
) -> Dict[str, Any]:
    """Audit one public page. Returns the report body (the service adds id and timestamps).

    Raises an :class:`AuditError` subclass for ``invalid_url``, ``invalid_query``,
    ``blocked_target``, ``fetch_failed`` and ``audit_timeout``.
    """
    target = normalize_url(url)
    visitor_query = normalize_query(query)
    deadline = now() + deadline_s
    fetch_kw = dict(resolver=resolver, transport=transport, now=now, deadline=deadline)

    page = guarded_fetch(target, **fetch_kw)
    if page.status != 200:
        raise FetchFailed(f"The page returned HTTP {page.status}.")
    if "html" not in (page.content_type or "").lower():
        raise FetchFailed(f"The URL is not an HTML page ({page.content_type or 'no content type'}).")

    facts = html_to_markdown(page.text, page.url)
    record = _parse_page(page.url, page.status, page.text)
    title = (record.get("title") or "").strip()

    origin = _origin(page.url)
    robots, robots_err = _fetch_optional(origin + "/robots.txt", **fetch_kw)
    llms, llms_err = _fetch_optional(origin + "/llms.txt", **fetch_kw)

    checks = [
        check_ai_crawler_access(robots, robots_err, page.url),
        check_llms_txt(llms, llms_err),
        *check_page_metadata(record, facts),
        check_visible_text(facts),
    ]
    if now() >= deadline:
        raise AuditTimeout("The audit ran out of time.")

    q, source = effective_query(visitor_query, title, facts.first_h1, page.url)
    rewrite = rewrite_one_section(
        facts.markdown,
        title=title or facts.first_h1,
        query=q,
        now=now,
        deadline=deadline,
        reserve_llm=reserve_llm,
        llm_factory=llm_factory or default_llm_factory,
        model=model or os.environ.get("REWRITER_MODEL", "gpt-4o"),
    )
    return {
        "url": target,
        "final_url": page.url,
        "query": q,
        "query_source": source,
        "checks": checks,
        "features": feature_breakdown(facts.markdown, title),
        "rewrite": rewrite,
    }


__all__ = [
    "AI_CRAWLERS",
    "CHECK_IDS",
    "REWRITE_NOTE",
    "REWRITE_STATUSES",
    "AuditError",
    "AuditTimeout",
    "BlockedTarget",
    "FetchFailed",
    "FetchResult",
    "InvalidQuery",
    "InvalidUrl",
    "PageFacts",
    "RawResponse",
    "audit_url",
    "cache_key",
    "default_resolver",
    "default_transport",
    "guarded_fetch",
    "html_to_markdown",
    "is_public_address",
    "normalize_query",
    "normalize_url",
    "pick_section",
]
