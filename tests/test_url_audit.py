"""Contract tests for egeo.url_audit (spec: openspec/changes/add-public-url-audit, url-audit-api).

No network: every test injects a resolver and a transport; ``socket`` is patched to fail loudly.
"""
from __future__ import annotations

import socket
from typing import Dict, List, Optional, Tuple

import pytest

from egeo import sections, url_audit as ua

PUBLIC_IP = "93.184.216.34"

LONG_A = (
    "Acme Analytics counts visits without cookies and keeps every record inside the European Union. "
    "Teams install one script tag, open the dashboard and see referrers, pages and campaigns within "
    "a minute, with no consent banner needed for the default setup on most marketing sites."
)
LONG_B = (
    "Pricing starts with a free plan for small sites, and paid plans scale with monthly page views "
    "so you only pay for what you use. Every plan includes the same features, unlimited team members "
    "and email support from the people who build the product every single day."
)
BOILER = " ".join(["word"] * 160)


def page_html(
    *,
    title: str = "Acme Analytics",
    meta: Optional[str] = "Privacy-friendly analytics.",
    h1s: Tuple[str, ...] = ("Acme Analytics",),
    jsonld: Optional[str] = '{"@context":"https://schema.org","@type":"SoftwareApplication","name":"Acme"}',
    body: Optional[str] = None,
) -> str:
    head = f"<title>{title}</title>"
    if meta is not None:
        head += f'<meta name="description" content="{meta}">'
    if jsonld is not None:
        head += f'<script type="application/ld+json">{jsonld}</script>'
    h = "".join(f"<h1>{x}</h1>" for x in h1s)
    if body is None:
        body = (
            f"<h2>Why Acme</h2><p>{LONG_A}</p>"
            f"<h2>Pricing</h2><p>{LONG_B} See <a href=\"/pricing\">pricing</a>.</p>"
            f"<p>{BOILER}</p>"
        )
    return (
        f"<html><head>{head}</head><body><nav>Home | Docs</nav><header>Top bar</header>{h}"
        f"{body}<script>var x = 1;</script><footer>(c) Acme</footer></body></html>"
    )


class Clock:
    def __init__(self) -> None:
        self.t = 1000.0

    def __call__(self) -> float:
        return self.t


class FakeNet:
    """Fake resolver + transport. ``routes``: url -> (status, headers, body) or Exception."""

    def __init__(self, routes: Dict[str, object], *, dns: Optional[Dict[str, List[str]]] = None,
                 clock: Optional[Clock] = None, cost: Optional[Dict[str, float]] = None) -> None:
        self.routes, self.dns = routes, dns or {}
        self.clock, self.cost = clock, cost or {}
        self.calls: List[Tuple[str, str]] = []

    def resolver(self, host: str, port: int) -> List[str]:
        return self.dns.get(host, [PUBLIC_IP])

    def transport(self, ip: str, url: str, timeout: float, deadline: float) -> ua.RawResponse:
        self.calls.append((ip, url))
        if self.clock is not None:
            self.clock.t += self.cost.get(url, 0.0)
        route = self.routes.get(url, (404, {"content-type": "text/html"}, "not found"))
        if isinstance(route, Exception):
            raise route
        status, headers, body = route
        return ua.RawResponse(status=status, headers=headers, body=body.encode("utf-8"))


HTML = {"content-type": "text/html; charset=utf-8"}
TEXT = {"content-type": "text/plain"}


def site(html: str, *, robots=(404, HTML, "nf"), llms=(200, TEXT, "# Acme\n")) -> Dict[str, object]:
    return {
        "https://acme.example/": (200, HTML, html),
        "https://acme.example/robots.txt": robots,
        "https://acme.example/llms.txt": llms,
    }


@pytest.fixture(autouse=True)
def no_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(*a, **k):
        raise AssertionError("network access attempted")

    monkeypatch.setattr(socket, "create_connection", boom)
    monkeypatch.setattr(socket, "getaddrinfo", boom)


@pytest.fixture
def mock_llm(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GEO_EVAL_MOCK", "1")


@pytest.fixture
def real_llm_path(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GEO_EVAL_MOCK", raising=False)


class FakeLLM:
    def __init__(self, reply=None, error: Optional[Exception] = None) -> None:
        self.reply, self.error, self.calls = reply, error, 0

    def chat_text(self, **kwargs) -> str:
        self.calls += 1
        if self.error:
            raise self.error
        user = kwargs["user"]
        return self.reply(user) if callable(self.reply) else self.reply


def run(net: FakeNet, url: str = "https://acme.example/", query=None, **kw):
    return ua.audit_url(url, query, resolver=net.resolver, transport=net.transport, **kw)


# --------------------------------------------------------------------------- #
# Input validation
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "value,expected",
    [
        ("example.com", "https://example.com/"),
        ("  Example.COM/Path?q=1#frag ", "https://example.com/Path?q=1"),
        ("HTTPS://example.com:443", "https://example.com/"),
        ("http://example.com:80/a", "http://example.com/a"),
        ("http://example.com:443/", "http://example.com:443/"),
    ],
)
def test_normalize_url_ok(value: str, expected: str) -> None:
    assert ua.normalize_url(value) == expected


@pytest.mark.parametrize(
    "value",
    [
        "file:///etc/passwd",
        "ftp://example.com/",
        "https://example.com:8443/",
        "https://127.0.0.1/",
        "http://[::1]/",
        "https://user:pw@example.com/",
        "localhost",
        "",
        None,
        "https://example.com/" + "a" * 2050,
        "javascript:alert(1)",
        "not a url",
    ],
)
def test_normalize_url_rejects(value) -> None:
    with pytest.raises(ua.InvalidUrl):
        ua.normalize_url(value)


def test_normalize_query() -> None:
    assert ua.normalize_query(None) is None
    assert ua.normalize_query("  privacy analytics ") == "privacy analytics"
    for bad in ("   ", "x" * 201, 5):
        with pytest.raises(ua.InvalidQuery):
            ua.normalize_query(bad)
    assert ua.normalize_query("x" * 200) == "x" * 200


def test_cache_key_distinguishes_query() -> None:
    u = ua.normalize_url("example.com")
    assert ua.cache_key(u, None) != ua.cache_key(u, "q")
    assert ua.cache_key(u, None) == ua.cache_key(ua.normalize_url("https://EXAMPLE.com#x"), None)


# --------------------------------------------------------------------------- #
# SSRF guard
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "addr",
    ["10.0.0.5", "127.0.0.1", "169.254.169.254", "100.64.0.1", "192.168.1.1", "172.16.0.1",
     "224.0.0.1", "0.0.0.0", "240.0.0.1", "::1", "fe80::1", "fc00::1", "::ffff:10.0.0.1", "::"],
)
def test_non_public_addresses(addr: str) -> None:
    assert not ua.is_public_address(addr)


@pytest.mark.parametrize("addr", [PUBLIC_IP, "1.1.1.1", "2606:4700:4700::1111"])
def test_public_addresses(addr: str) -> None:
    assert ua.is_public_address(addr)


@pytest.mark.parametrize("private", ["10.0.0.5", "127.0.0.1"])
def test_private_resolution_blocked_without_connecting(private: str) -> None:
    net = FakeNet(site(page_html()), dns={"acme.example": [private]})
    with pytest.raises(ua.BlockedTarget):
        run(net)
    assert net.calls == []


def test_any_private_address_in_the_answer_blocks() -> None:
    net = FakeNet(site(page_html()), dns={"acme.example": [PUBLIC_IP, "10.0.0.5"]})
    with pytest.raises(ua.BlockedTarget):
        run(net)
    assert net.calls == []


def test_redirect_to_metadata_ip_is_not_followed() -> None:
    routes = {"https://acme.example/": (302, {"location": "http://169.254.169.254/latest/meta-data/"}, "")}
    net = FakeNet(routes)
    with pytest.raises(ua.BlockedTarget):
        run(net)
    assert [u for _, u in net.calls] == ["https://acme.example/"]


def test_redirect_to_host_resolving_private_is_blocked() -> None:
    routes = {"https://acme.example/": (301, {"location": "https://internal.acme.example/"}, "")}
    net = FakeNet(routes, dns={"internal.acme.example": ["192.168.0.10"]})
    with pytest.raises(ua.BlockedTarget):
        run(net)
    assert len(net.calls) == 1


def test_connects_to_vetted_address_and_follows_redirects() -> None:
    routes = site(page_html())
    routes["https://acme.example/old"] = (301, {"location": "/"}, "")
    net = FakeNet(routes)
    report = run(net, "https://acme.example/old")
    assert report["url"] == "https://acme.example/old"
    assert report["final_url"] == "https://acme.example/"
    assert all(ip == PUBLIC_IP for ip, _ in net.calls)


def test_too_many_redirects() -> None:
    routes = {f"https://acme.example/r{i}": (302, {"location": f"/r{i + 1}"}, "") for i in range(10)}
    net = FakeNet(routes)
    with pytest.raises(ua.FetchFailed):
        run(net, "https://acme.example/r0")
    assert len(net.calls) == 6


def test_page_http_error_is_fetch_failed() -> None:
    net = FakeNet({"https://acme.example/": (403, HTML, "forbidden")})
    with pytest.raises(ua.FetchFailed) as exc:
        run(net)
    assert "403" in exc.value.message and exc.value.status == 502


def test_non_html_is_fetch_failed() -> None:
    net = FakeNet({"https://acme.example/": (200, {"content-type": "application/pdf"}, "%PDF")})
    with pytest.raises(ua.FetchFailed):
        run(net)


# --------------------------------------------------------------------------- #
# HTML -> Markdown
# --------------------------------------------------------------------------- #
def test_html_to_markdown_structure() -> None:
    html = (
        "<html><head><title>T</title><meta name='Description' content=' Desc '></head><body>"
        "<nav><a href='/x'>Nav link</a></nav><h1>Main</h1><p>Hello <a href='/docs'>docs</a> now.</p>"
        "<ul><li>One</li><li>Two</li></ul><table><tr><th>Plan</th><th>Price</th></tr>"
        "<tr><td>Pro</td><td>$19</td></tr></table><h2>Sub</h2><p># not a heading</p>"
        "<script>ignored()</script></body></html>"
    )
    facts = ua.html_to_markdown(html, "https://acme.example/page")
    md = facts.markdown
    assert "# Main" in md and "## Sub" in md
    assert "[docs](https://acme.example/docs)" in md
    assert "- One\n\n- Two" in md
    assert "| Plan | Price |" in md and "| Pro | $19 |" in md
    assert "Nav link" not in md and "ignored" not in md
    assert "\\# not a heading" in md
    assert facts.meta_description == "Desc"
    assert facts.h1_count == 1 and facts.first_h1 == "Main"
    secs = sections.split_sections(md)
    assert [s.heading for s in secs if s.level] == ["Main", "Sub"]
    assert sections.join_sections(secs) == md


# --------------------------------------------------------------------------- #
# Checks
# --------------------------------------------------------------------------- #
def checks_by_id(report) -> Dict[str, dict]:
    return {c["id"]: c for c in report["checks"]}


def test_check_order_and_fix_only_on_fail(mock_llm) -> None:
    report = run(FakeNet(site(page_html(meta=None))))
    assert [c["id"] for c in report["checks"]] == list(ua.CHECK_IDS)
    for c in report["checks"]:
        assert c["status"] in ("pass", "fail", "unverifiable") and c["evidence"]
        assert ("fix" in c) == (c["status"] == "fail")
    assert checks_by_id(report)["meta_description"]["status"] == "fail"


def test_robots_blocking_gptbot(mock_llm) -> None:
    robots = (200, TEXT, "User-agent: GPTBot\nDisallow: /\n\nUser-agent: *\nAllow: /\n")
    c = checks_by_id(run(FakeNet(site(page_html(), robots=robots))))["ai_crawler_access"]
    assert c["status"] == "fail"
    assert "GPTBot" in c["evidence"] and "ClaudeBot" not in c["evidence"]
    assert "GPTBot" in c["fix"] and "robots.txt" in c["fix"]


def test_robots_timeout_is_unverifiable(mock_llm) -> None:
    c = checks_by_id(run(FakeNet(site(page_html(), robots=TimeoutError("slow")))))["ai_crawler_access"]
    assert c["status"] == "unverifiable" and "fix" not in c


@pytest.mark.parametrize("robots,status", [((404, HTML, ""), "pass"), ((500, HTML, ""), "unverifiable"),
                                           ((200, TEXT, "User-agent: *\nDisallow:\n"), "pass")])
def test_robots_statuses(mock_llm, robots, status) -> None:
    assert checks_by_id(run(FakeNet(site(page_html(), robots=robots))))["ai_crawler_access"]["status"] == status


def test_robots_served_as_html_is_unverifiable(mock_llm) -> None:
    # A bot challenge on /robots.txt must not read as "no rules" (live case: theguardian.com).
    challenge = (200, HTML, "<html><head><title>Client Challenge</title></head><body>wait</body></html>")
    c = checks_by_id(run(FakeNet(site(page_html(), robots=challenge))))["ai_crawler_access"]
    assert c["status"] == "unverifiable" and "HTML" in c["evidence"] and "fix" not in c


@pytest.mark.parametrize(
    "llms,status",
    [((200, TEXT, "# x"), "pass"), ((404, HTML, ""), "fail"), ((200, HTML, "<html>"), "fail"),
     ((503, TEXT, ""), "unverifiable")],
)
def test_llms_txt(mock_llm, llms, status) -> None:
    assert checks_by_id(run(FakeNet(site(page_html(), llms=llms))))["llms_txt"]["status"] == status


def test_metadata_checks(mock_llm) -> None:
    c = checks_by_id(run(FakeNet(site(page_html(h1s=("A", "B"), jsonld="{not json", title="")))))
    assert c["single_h1"] == {**c["single_h1"], "status": "fail", "evidence": "2"}
    assert c["json_ld"]["status"] == "fail" and "invalid" in c["json_ld"]["evidence"]
    assert c["title"]["status"] == "fail"
    ok = checks_by_id(run(FakeNet(site(page_html()))))
    assert ok["json_ld"]["status"] == "pass" and "SoftwareApplication" in ok["json_ld"]["evidence"]
    assert ok["title"]["evidence"] == "Acme Analytics"


def test_visible_text_js_rendered_page(mock_llm) -> None:
    body = "<div id='root'>" + " ".join(f"w{i}" for i in range(11)) + "</div>"
    c = checks_by_id(run(FakeNet(site(page_html(body=body, h1s=())))))["visible_text"]
    assert c["status"] == "fail" and c["evidence"] == "11 words"
    body = "<div id='root'>" + " ".join(f"w{i}" for i in range(12)) + "</div>"
    c = checks_by_id(run(FakeNet(site(page_html(body=body, h1s=())))))["visible_text"]
    assert c["evidence"] == "12 words"


# --------------------------------------------------------------------------- #
# Bot challenge detection
# --------------------------------------------------------------------------- #
def challenge_html(title: str = "Just a moment...", marker: str = "") -> str:
    return f"<html><head><title>{title}</title></head><body><p>Checking your browser.</p>{marker}</body></html>"


def assert_challenge_skips_llm(report) -> None:
    checks = checks_by_id(report)
    for check_id in ("json_ld", "title", "meta_description", "single_h1", "visible_text"):
        assert checks[check_id]["status"] == "unverifiable"
        assert "challenge" in checks[check_id]["evidence"].lower()
    assert report["features"]["items"] == []
    assert report["rewrite"]["status"] == "skipped_challenge"


def test_cloudflare_403_returns_challenged_report_without_llm(real_llm_path) -> None:
    html = challenge_html(marker="<script>window._cf_chl_opt = {};</script>")
    net = FakeNet(site(html))
    net.routes["https://acme.example/"] = (403, HTML, html)
    report = run(
        net,
        reserve_llm=lambda: pytest.fail("LLM budget reserved"),
        llm_factory=lambda timeout: pytest.fail("LLM factory called"),
    )
    assert report["challenge"]["vendor"] == "cloudflare"
    assert report["challenge"]["http_status"] == 403
    assert "Just a moment..." in report["challenge"]["evidence"]
    assert "_cf_chl_opt" in report["challenge"]["evidence"]
    assert_challenge_skips_llm(report)
    assert checks_by_id(report)["ai_crawler_access"]["status"] == "pass"
    assert checks_by_id(report)["llms_txt"]["status"] == "pass"


def test_challenge_200_with_unknown_title_returns_report(real_llm_path) -> None:
    report = run(
        FakeNet(site(challenge_html(title="Client Challenge"))),
        reserve_llm=lambda: pytest.fail("LLM budget reserved"),
        llm_factory=lambda timeout: pytest.fail("LLM factory called"),
    )
    assert report["challenge"]["vendor"] == "unknown"
    assert report["challenge"]["http_status"] == 200
    assert_challenge_skips_llm(report)


def test_challenge_platform_script_on_real_page_is_not_a_challenge(mock_llm) -> None:
    html = page_html(body=f"<h2>Why Acme</h2><p>{LONG_A}</p><p>{BOILER}</p>"
                           "<script src='/cdn-cgi/challenge-platform/'></script>")
    report = run(FakeNet(site(html)))
    assert report["challenge"] is None
    assert checks_by_id(report)["visible_text"]["status"] == "pass"
    assert len(report["features"]["items"]) == 10


def test_plain_403_without_challenge_signal_is_fetch_failed() -> None:
    net = FakeNet({"https://acme.example/": (403, HTML, page_html())})
    with pytest.raises(ua.FetchFailed):
        run(net)


@pytest.mark.parametrize(
    "marker,vendor",
    [
        ("_cf_chl_opt", "cloudflare"),
        ("px-captcha", "perimeterx"),
        ("captcha-delivery.com", "datadome"),
        ("_Incapsula_Resource", "imperva"),
        ("sec-if-cpt", "akamai"),
    ],
)
def test_vendor_markers_detect_low_word_challenges(marker: str, vendor: str) -> None:
    detected = ua.detect_bot_challenge(503, challenge_html(title="", marker=marker), "", 4)
    assert detected is not None
    assert detected["vendor"] == vendor
    assert detected["http_status"] == 503
    assert marker in detected["evidence"]
    assert "4 visible words" in detected["evidence"]
    assert ua.detect_bot_challenge(503, challenge_html(title="", marker=marker), "", ua.MIN_VISIBLE_WORDS) is None


def test_challenge_platform_alone_is_not_a_marker() -> None:
    assert ua.detect_bot_challenge(200, "/cdn-cgi/challenge-platform/", "", 4) is None


# --------------------------------------------------------------------------- #
# Features, query, no aggregate score
# --------------------------------------------------------------------------- #
def test_features_breakdown_and_no_aggregate(mock_llm) -> None:
    report = run(FakeNet(site(page_html())))
    feats = report["features"]
    assert feats["method"] == "heuristic" and len(feats["items"]) == 10
    for item in feats["items"]:
        assert isinstance(item["score"], int) and 0 <= item["score"] <= 10
        assert ("recommendation" in item) == (item["score"] < 5)
    for key in ("score", "total_score", "percentile", "benchmark", "ceiling"):
        assert key not in report


def test_query_visitor_and_derived(mock_llm) -> None:
    r = run(FakeNet(site(page_html())), query=" privacy friendly analytics ")
    assert (r["query"], r["query_source"]) == ("privacy friendly analytics", "visitor")
    r = run(FakeNet(site(page_html())))
    assert (r["query"], r["query_source"]) == ("best Acme Analytics", "derived")
    r = run(FakeNet(site(page_html(title=""))))
    assert r["query"] == "best Acme Analytics"  # falls back to the first h1


@pytest.mark.parametrize(
    "title,url,expected",
    [
        (
            "Generative engine optimization - Wikipedia",
            "https://en.wikipedia.org/wiki/Generative_engine_optimization",
            "best Generative engine optimization",
        ),
        ("BBC", "https://www.bbc.com/", "best BBC"),
        ("Home - BBC News", "https://www.bbc.com/", "best Home"),
        (
            "Plausible Analytics | Simple, privacy-friendly Google Analytics alternative",
            "https://plausible.io/",
            "best Simple, privacy-friendly Google Analytics alternative",
        ),
        ("Analytics - Example", "https://www.example.co.uk/", "best Analytics - Example"),
    ],
)
def test_derived_query_strips_site_name(title: str, url: str, expected: str) -> None:
    assert ua.effective_query(None, title, "", url) == (expected, "derived")


def test_visitor_query_is_never_stripped() -> None:
    assert ua.effective_query("Home - BBC News", "", "", "https://www.bbc.com/") == (
        "Home - BBC News", "visitor",
    )


# --------------------------------------------------------------------------- #
# Rewrite
# --------------------------------------------------------------------------- #
def test_mock_mode_end_to_end_without_network(mock_llm) -> None:
    report = run(FakeNet(site(page_html())))
    rw = report["rewrite"]
    # the mock rewriter returns the section unchanged, which is reported honestly as no_change
    assert rw["status"] == "no_change" and "after" not in rw and rw["before"]
    assert rw["note"] == ua.REWRITE_NOTE
    assert set(report) == {"url", "final_url", "query", "query_source", "checks", "features", "rewrite", "challenge"}


def _section_from_prompt(user: str) -> str:
    return user.split("Rewrite this section following every rule:\n\n", 1)[1]


def test_rewrite_shown_one_call_lowest_section(real_llm_path) -> None:
    llm = FakeLLM(reply=lambda user: _section_from_prompt(user).rstrip() + " Clearer.")
    report = run(FakeNet(site(page_html())), llm_factory=lambda t: llm)
    rw = report["rewrite"]
    assert llm.calls == 1
    assert rw["status"] == "shown" and "violations" not in rw
    assert rw["after"].rstrip().endswith("Clearer.")
    expected = ua.pick_section(ua.html_to_markdown(page_html(), "https://acme.example/").markdown)
    assert rw["section_heading"] == expected.heading and rw["before"] == expected.text


def test_unchanged_rewrite_is_no_change_and_uses_budget(real_llm_path) -> None:
    # whitespace-only differences still count as unchanged
    llm, reserved = FakeLLM(reply=lambda user: "  " + _section_from_prompt(user).rstrip() + "\n\n"), []
    report = run(FakeNet(site(page_html())), llm_factory=lambda t: llm, reserve_llm=lambda: reserved.append(1) or True)
    rw = report["rewrite"]
    assert rw["status"] == "no_change" and "after" not in rw and rw["before"]
    assert llm.calls == 1 and reserved == [1]


def test_non_content_sections_are_never_picked() -> None:
    header = "## [Example Weblog](https://example.com/)\n\n" + LONG_A + " Sponsored by: Acme.\n"
    footer = "## Company\n\n" + "\n".join(f"- [{w}](https://example.com/{w.lower()})" for w in
                                           ["About", "Careers", "Blog", "Press", "Contact"]) + "\n" + LONG_A + "\n"
    cta = ("## Ready to start?\n\n" + LONG_A + "\n\n[Start your free trial](https://example.com/trial)\n\n"
           "[Book a demo](https://example.com/demo)\n")
    content = "## How it works\n\n" + LONG_B + "\n"
    md = header + "\n" + footer + "\n" + cta + "\n" + content
    sections = {s.heading: s for s in ua._sections.split_sections(md)}
    assert ua.is_non_content_section(sections["[Example Weblog](https://example.com/)"])
    assert ua.is_non_content_section(sections["Company"])
    assert ua.is_non_content_section(sections["Ready to start?"])
    assert not ua.is_non_content_section(sections["How it works"])
    assert ua.pick_section(md).heading == "How it works"
    # a single inline link inside prose does not make a section non-content
    assert not ua.is_non_content_section(ua._sections.split_sections(
        "## Pricing\n\n" + LONG_B + " See [pricing](https://example.com/pricing).\n")[-1])


def test_pick_section_lowest_score_ties_earliest() -> None:
    md = "## A\n\n" + LONG_A + "\n\n## B\n\n" + LONG_A + "\n"
    assert ua.pick_section(md).heading == "A"
    assert ua.pick_section("## Tiny\n\nShort.\n") is None
    assert ua.pick_section(LONG_A + "\n") is None  # preamble never qualifies


def test_rewrite_withheld_on_fidelity(real_llm_path) -> None:
    llm = FakeLLM(reply=lambda user: _section_from_prompt(user).rstrip() + " Trusted by 5000 teams.")
    report = run(FakeNet(site(page_html())), llm_factory=lambda t: llm)
    rw = report["rewrite"]
    assert rw["status"] == "withheld_fidelity"
    assert "number_added:5000" in rw["violations"]
    assert "after" not in rw


def test_no_candidate_makes_no_llm_call(real_llm_path) -> None:
    llm, reserved = FakeLLM(reply="x"), []
    body = "<p>" + BOILER + "</p><h2>Short</h2><p>Too short.</p>"
    report = run(FakeNet(site(page_html(body=body, h1s=()))), llm_factory=lambda t: llm,
                 reserve_llm=lambda: reserved.append(1) or True)
    assert report["rewrite"]["status"] == "skipped_no_candidate"
    assert llm.calls == 0 and reserved == []


def test_rewriter_error_keeps_report(real_llm_path) -> None:
    report = run(FakeNet(site(page_html())), llm_factory=lambda t: FakeLLM(error=RuntimeError("provider down")))
    assert report["rewrite"]["status"] == "error"
    assert len(report["checks"]) == 7 and len(report["features"]["items"]) == 10


def test_budget_exhausted_skips_rewrite(real_llm_path) -> None:
    llm = FakeLLM(reply="x")
    report = run(FakeNet(site(page_html())), llm_factory=lambda t: llm, reserve_llm=lambda: False)
    assert report["rewrite"]["status"] == "skipped_budget" and llm.calls == 0
    assert len(report["checks"]) == 7


def test_slow_page_leaves_no_time_to_rewrite(real_llm_path) -> None:
    clock = Clock()
    net = FakeNet(site(page_html()), clock=clock, cost={"https://acme.example/": 20.0})
    llm = FakeLLM(reply="x")
    report = run(net, now=clock, llm_factory=lambda t: llm)
    assert report["rewrite"]["status"] == "skipped_timeout" and llm.calls == 0


def test_llm_timeout_is_remaining_minus_one(real_llm_path) -> None:
    clock = Clock()
    net = FakeNet(site(page_html()), clock=clock, cost={"https://acme.example/": 5.0})
    seen = []

    def factory(timeout: float):
        seen.append(timeout)
        return FakeLLM(error=RuntimeError("x"))

    run(net, now=clock, llm_factory=factory)
    assert seen == [pytest.approx(24.0)]


def test_page_fetch_past_deadline_is_audit_timeout() -> None:
    clock = Clock()
    routes = site(page_html())
    routes["https://acme.example/"] = TimeoutError("slow")
    net = FakeNet(routes, clock=clock, cost={"https://acme.example/": 31.0})
    with pytest.raises(ua.AuditTimeout):
        run(net, now=clock)


def test_checks_past_deadline_is_audit_timeout() -> None:
    clock = Clock()
    net = FakeNet(site(page_html()), clock=clock, cost={"https://acme.example/llms.txt": 31.0})
    with pytest.raises(ua.AuditTimeout):
        run(net, now=clock)


# --- rewriter request options (REWRITER_TEMPERATURE / REWRITER_EXTRA_BODY) ---------------


def test_rewriter_request_options_parsing() -> None:
    assert ua.rewriter_request_options({}) == {}
    opts = ua.rewriter_request_options(
        {"REWRITER_TEMPERATURE": "0.6", "REWRITER_EXTRA_BODY": '{"thinking": {"type": "disabled"}}'}
    )
    assert opts == {"temperature": 0.6, "extra_body": {"thinking": {"type": "disabled"}}}


@pytest.mark.parametrize("env", [{"REWRITER_TEMPERATURE": "hot"}, {"REWRITER_TEMPERATURE": "3"},
                                 {"REWRITER_EXTRA_BODY": "[1]"}, {"REWRITER_EXTRA_BODY": "{bad"}])
def test_rewriter_request_options_rejects_bad_values(env) -> None:
    with pytest.raises(ValueError):
        ua.rewriter_request_options(env)


def test_one_shot_client_sends_options_in_the_request(monkeypatch) -> None:
    import io
    import json as _json

    import llm_client

    sent = {}

    class Resp(io.BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    def fake_urlopen(req, timeout=None):
        sent["body"] = _json.loads(req.data)
        sent["timeout"] = timeout
        return Resp(b'{"choices": [{"message": {"content": "ok"}}]}')

    monkeypatch.setattr(llm_client.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setenv("OPENAI_API_KEY", "k")
    monkeypatch.setenv("REWRITER_TEMPERATURE", "0.6")
    monkeypatch.setenv("REWRITER_EXTRA_BODY", '{"thinking": {"type": "disabled"}, "model": "evil"}')
    out = ua._OneShotClient(7).chat_text(model="kimi-k3.1-pro-highspeed", system="s", user="u", temperature=0.0)
    assert out == "ok"
    body = sent["body"]
    assert body["temperature"] == 0.6
    assert body["thinking"] == {"type": "disabled"}
    assert body["model"] == "kimi-k3.1-pro-highspeed"  # extra_body cannot replace the model
    assert sent["timeout"] == 7


def test_one_shot_client_defaults_unchanged(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "k")
    monkeypatch.delenv("REWRITER_TEMPERATURE", raising=False)
    monkeypatch.delenv("REWRITER_EXTRA_BODY", raising=False)
    assert ua._OneShotClient(5)._options == {}
