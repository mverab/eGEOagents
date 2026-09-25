"""Contract tests for section-mode fix-gaps (egeo.gaps.run_section_fixes + CLI). No network."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from egeo import gaps, judge, sources
from egeo.cli import main
from egeo.jev import ChoiceAnswer, JevProviderError, JevResponse
from egeo.sources import SourceDoc

PROJECT_YAML = """schema_version: 1
project:
  id: demo
  name: Demo
  repository: https://github.com/example/demo
  canonical_domain: demo.dev
  canonical_url: https://demo.dev/
  language: en
queries:
  - {id: q-aeo, text: open source AEO tools, class: generic, intent: aeo, target_pages: [compare], active: true}
pages:
  - {id: compare, url: https://demo.dev/compare/, source: content/compare.md, active: true}
measurement: {engines: [perplexity], cadence: weekly}
guardrails: {no_duplicate_query_owners: true, no_auto_publish_visible_copy: true, no_fabricated_proof: true, require_fresh_crawl_before_verdict: true}
"""

INTRO = "Short intro.\n\n"
TOOLS = ("## Tools\n\n" + " ".join(["tools"] * 35)
         + " See [LibHunt](https://www.libhunt.com/) for 42 more.\n\n")
FAQ = "## FAQ\n\n" + " ".join(["faq"] * 35) + "\n"
FRONTMATTER = "---\ntitle: Open Source AEO Tools\n---\n"
PAGE = FRONTMATTER + INTRO + TOOLS + FAQ
GOOD_REWRITE = ("## Tools\n\nOpen source AEO tools compared: " + " ".join(["tools"] * 33)
                + " See [LibHunt](https://www.libhunt.com/) for 42 more.\n\n")
BAD_REWRITE = "## Tools\n\nOpen source AEO tools compared: " + " ".join(["tools"] * 36) + " 42 more.\n\n"

GAPS = [{"query": "open source AEO tools", "cited": False, "sources": ["https://toolradar.com/x", "https://demo.dev/y"]}]


class ScriptedJev:
    def __init__(self, *answers) -> None:
        self.queue = list(answers)
        self.requests = []
        self.model = "fake"
        self.totals = {"requests": 0, "input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0}

    def ask(self, state, questions):
        self.requests.append((state, questions))
        self.totals["requests"] += 1
        nxt = self.queue.pop(0)
        if isinstance(nxt, Exception):
            raise nxt
        (qid,) = questions.keys()
        return JevResponse(answers={qid: nxt}, model="fake", input_tokens=1, output_tokens=0, cost_usd=0.0)


LOSES = ChoiceAnswer("src_1", 0.3, {"own_s01": 0.30, "own_s02": 0.10, "src_1": 0.60})
FAITHFUL = ChoiceAnswer("faithful", 0.8, {"faithful": 0.9, "drops_facts": 0.05, "adds_claims": 0.05})
WON = ChoiceAnswer("own_s01", 0.5, {"own_s01": 0.70, "own_s02": 0.10, "src_1": 0.20})


@pytest.fixture()
def project(tmp_path: Path) -> Path:
    (tmp_path / "content").mkdir()
    (tmp_path / "content" / "compare.md").write_text(PAGE, encoding="utf-8")
    (tmp_path / "project.yaml").write_text(PROJECT_YAML, encoding="utf-8")
    (tmp_path / "gaps.json").write_text(json.dumps(GAPS), encoding="utf-8")
    return tmp_path


def _plan(project: Path):
    loaded = gaps.load_gaps(project / "gaps.json")
    return gaps.plan_fixes(loaded, gaps.load_project_file(project / "project.yaml"), project)


def fetch_ok(values, *, exclude_domain, limit):
    return [SourceDoc(url="https://toolradar.com/x", ok=True, title="toolradar.com", text="Best AEO tools list")]


def _run(project: Path, jev, rewrite, fetch=fetch_ok):
    return gaps.run_section_fixes(
        _plan(project), out_dir=project / "out", jev_client=jev,
        rewrite_fn=rewrite, fetch_fn=fetch, exclude_domain="demo.dev", max_sources=6,
    )


def test_plan_carries_gap_sources(project: Path) -> None:
    assert _plan(project).pages[0].sources == ["https://toolradar.com/x", "https://demo.dev/y"]


def test_happy_path_rewrites_only_target_section(project: Path) -> None:
    calls = []

    def rewrite(query, text, title):
        calls.append((query, text, title))
        return GOOD_REWRITE

    jev = ScriptedJev(LOSES, FAITHFUL, WON)
    report = _run(project, jev, rewrite)
    page = report["pages"][0]

    assert calls == [("open source AEO tools", TOOLS, "Open Source AEO Tools")]
    assert page["status"] == "rewritten" and page["reasons"] == []
    assert page["diagnosis"]["winner"] == "src_1" and page["diagnosis"]["winner_kind"] == "source"
    assert page["diagnosis"]["target_section"] == {"id": "s01", "heading": "Tools"}
    assert page["fidelity"]["rules"] == {"passed": True, "violations": []}
    assert page["fidelity"]["judge"] == {"verdict": "faithful", "confidence": 0.8, "accepted": True}
    assert page["verification"]["outcome"] == "won"
    assert page["verification"]["p_before"] == 0.30 and page["verification"]["p_after"] == 0.70
    assert page["sources"] == [{"url": "https://toolradar.com/x", "ok": True, "error": ""}]

    written = project / "out" / "compare" / "compare.md"
    assert written.read_text(encoding="utf-8") == FRONTMATTER + INTRO + GOOD_REWRITE + FAQ
    assert page["output_file"] == str(written)
    diff = (project / "out" / "compare" / "section.diff").read_text(encoding="utf-8")
    assert diff.startswith("--- a/compare.md\n+++ b/compare.md\n")
    assert json.loads((project / "out" / "compare" / "diagnosis.json").read_text(encoding="utf-8")) == page
    assert (project / "content" / "compare.md").read_text(encoding="utf-8") == PAGE  # source untouched

    saved = json.loads((project / "out" / "fix-gaps.json").read_text(encoding="utf-8"))
    assert saved == report
    assert saved["mode"] == "sections" and saved["jev_model"] == "fake"
    assert saved["note"] == gaps.SECTIONS_NOTE
    assert "not a prediction of citation" in saved["note"]
    assert "EXPERIMENTAL" in saved["note"] and "0.64" in saved["note"]
    assert saved["jev_validation"] == gaps.JEV_VALIDATION
    assert saved["jev_validation"]["status"] == "experimental" and saved["jev_validation"]["gate_passed"] is False
    assert page["diagnosis"]["experimental"] is True
    assert page["verification"]["experimental"] is True
    assert page["offpage"] is None
    assert saved["jev_usage"]["requests"] == 3
    assert saved["thresholds"] == {
        "fidelity_gate": judge.FIDELITY_GATE, "improve_delta": judge.IMPROVE_DELTA,
        "min_section_words": judge.MIN_SECTION_WORDS, "max_candidate_chars": judge.MAX_CANDIDATE_CHARS,
        "max_sources": 6,
    }
    for key in ("format", "unmatched", "skipped", "remeasure"):
        assert key in saved

    # the Jev diagnosis saw own sections (intro is < 30 words so excluded) and the fetched source
    state, _ = jev.requests[0]
    assert set(state["candidates"]) == {"own_s01", "own_s02", "src_1"}
    # verification used the same ids with the rewritten text
    state_after, _ = jev.requests[2]
    assert set(state_after["candidates"]) == {"own_s01", "own_s02", "src_1"}
    assert state_after["candidates"]["own_s01"] == GOOD_REWRITE[: judge.MAX_CANDIDATE_CHARS]


def _no_output(project: Path) -> None:
    assert not (project / "out" / "compare" / "compare.md").exists()
    assert not (project / "out" / "compare" / "section.diff").exists()
    assert (project / "out" / "compare" / "diagnosis.json").exists()


def test_already_best_does_not_rewrite(project: Path) -> None:
    def rewrite(*a):
        raise AssertionError("must not rewrite")

    report = _run(project, ScriptedJev(WON), rewrite)
    page = report["pages"][0]
    assert page["status"] == "already_best"
    assert page["diagnosis"]["target_section"] is None
    assert page["diagnosis"]["experimental"] is True
    assert report["jev_validation"] == gaps.JEV_VALIDATION
    assert page["offpage"] == {"reason": gaps.OFFPAGE_REASON, "message": gaps.OFFPAGE_MESSAGE,
                               "sources": ["https://toolradar.com/x"]}
    saved = json.loads((project / "out" / "compare" / "diagnosis.json").read_text(encoding="utf-8"))
    assert saved["offpage"] == page["offpage"]
    _no_output(project)


def test_no_sources_skips_jev_and_rewrite(project: Path) -> None:
    jev = ScriptedJev()
    report = _run(project, jev, lambda *a: GOOD_REWRITE,
                  fetch=lambda values, **kw: [SourceDoc(url="https://toolradar.com/x", ok=False, error="http_404")])
    page = report["pages"][0]
    assert page["status"] == "no_competitor_sources" and jev.requests == []
    assert page["offpage"] is None
    assert page["sources"] == [{"url": "https://toolradar.com/x", "ok": False, "error": "http_404"}]
    _no_output(project)


def test_identical_rewrite_is_no_change_proposed(project: Path) -> None:
    jev = ScriptedJev(LOSES)
    report = _run(project, jev, lambda q, text, title: text)
    assert report["pages"][0]["status"] == "no_change_proposed" and len(jev.requests) == 1
    _no_output(project)


def test_rule_violation_rejects_before_judge(project: Path) -> None:
    jev = ScriptedJev(LOSES)
    report = _run(project, jev, lambda *a: BAD_REWRITE)
    page = report["pages"][0]
    assert page["status"] == "rejected_fidelity_rules"
    assert "link_removed:https://www.libhunt.com/" in page["fidelity"]["rules"]["violations"]
    assert page["fidelity"]["judge"] is None and len(jev.requests) == 1
    _no_output(project)


def test_judge_rejection(project: Path) -> None:
    adds = ChoiceAnswer("adds_claims", 0.9, {"faithful": 0.05, "drops_facts": 0.05, "adds_claims": 0.9})
    report = _run(project, ScriptedJev(LOSES, adds), lambda *a: GOOD_REWRITE)
    page = report["pages"][0]
    assert page["status"] == "rejected_fidelity_judge"
    assert page["fidelity"]["judge"] == {"verdict": "adds_claims", "confidence": 0.9, "accepted": False}
    _no_output(project)


def test_worse_is_rejected(project: Path) -> None:
    worse = ChoiceAnswer("src_1", 0.5, {"own_s01": 0.20, "own_s02": 0.10, "src_1": 0.70})
    report = _run(project, ScriptedJev(LOSES, FAITHFUL, worse), lambda *a: GOOD_REWRITE)
    page = report["pages"][0]
    assert page["status"] == "rejected_worse" and page["verification"]["outcome"] == "worse"
    assert page["offpage"] is None
    _no_output(project)


def test_jev_error_marks_page(project: Path) -> None:
    report = _run(project, ScriptedJev(JevProviderError("TypeSafe HTTP 500")), lambda *a: GOOD_REWRITE)
    page = report["pages"][0]
    assert page["status"] == "jev_error" and page["reasons"] == ["TypeSafe HTTP 500"]
    assert page["diagnosis"] is None and page["verification"] is None
    _no_output(project)


def test_cli_section_mode_fails_closed_without_key(project: Path, monkeypatch, capsys) -> None:
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
    monkeypatch.delenv("GEO_EVAL_MOCK", raising=False)
    code = main(["fix-gaps", str(project / "gaps.json"), "--project", str(project / "project.yaml"),
                 "--out-dir", str(project / "out")])
    assert code == 2
    err = capsys.readouterr().err
    assert "TYPESAFE_API_KEY" in err and "GEO_EVAL_MOCK=1" in err and "--mode page" in err
    assert not (project / "out").exists()


def test_cli_section_dry_run_needs_no_key_and_fetches_nothing(project: Path, monkeypatch, capsys) -> None:
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
    monkeypatch.delenv("GEO_EVAL_MOCK", raising=False)
    monkeypatch.setattr(sources, "fetch_sources", lambda *a, **k: pytest.fail("dry run must not fetch"))
    code = main(["fix-gaps", str(project / "gaps.json"), "--project", str(project / "project.yaml"),
                 "--out-dir", str(project / "out"), "--dry-run"])
    assert code == 0 and not (project / "out").exists()
    assert "compare" in capsys.readouterr().out


def test_cli_mock_end_to_end_offline(project: Path, monkeypatch, capsys) -> None:
    monkeypatch.setenv("GEO_EVAL_MOCK", "1")
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
    monkeypatch.setattr(sources, "fetch_sources", lambda *a, **k: pytest.fail("mock mode must not fetch"))
    code = main(["fix-gaps", str(project / "gaps.json"), "--project", str(project / "project.yaml"),
                 "--out-dir", str(project / "out")])
    assert code == 0
    report = json.loads((project / "out" / "fix-gaps.json").read_text(encoding="utf-8"))
    assert report["mode"] == "sections" and report["jev_model"] == "mock"
    assert report["pages"][0]["status"] in gaps.SECTION_STATUSES
    # with the deterministic mock, the "Tools" section overlaps the query and wins -> already_best
    assert report["pages"][0]["status"] == "already_best"
    assert "already_best: compare (off-page: 1 cited sources)" in capsys.readouterr().out
    assert (project / "content" / "compare.md").read_text(encoding="utf-8") == PAGE


def test_cli_page_mode_still_works(project: Path, monkeypatch) -> None:
    monkeypatch.setenv("GEO_EVAL_MOCK", "1")
    code = main(["fix-gaps", str(project / "gaps.json"), "--project", str(project / "project.yaml"),
                 "--out-dir", str(project / "out"), "--mode", "page"])
    assert code == 0
    report = json.loads((project / "out" / "fix-gaps.json").read_text(encoding="utf-8"))
    assert report["pages"][0]["page_id"] == "compare"
