"""Contract tests for section-mode fix-gaps (egeo.gaps.run_section_fixes + CLI). No network."""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from egeo import gaps, judge, sources
from egeo.cli import main
from egeo.jev import ChoiceAnswer, JevProviderError, JevResponse, NoulAnswer
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

PROJECT_YAML_TWO_PAGES = PROJECT_YAML.replace(
    "target_pages: [compare], active: true}\n",
    "target_pages: [compare], active: true}\n"
    "  - {id: q-two, text: second query, class: generic, intent: aeo, target_pages: [other], active: true}\n",
).replace(
    "source: content/compare.md, active: true}\n",
    "source: content/compare.md, active: true}\n"
    "  - {id: other, url: https://demo.dev/other/, source: content/other.md, active: true}\n",
)

INTRO ="Short intro.\n\n"
TOOLS = ("## Tools\n\n" + " ".join(["tools"] * 35)
         + " See [LibHunt](https://www.libhunt.com/) for 42 more.\n\n")
FAQ = "## FAQ\n\n" + " ".join(["faq"] * 35) + "\n"
FRONTMATTER = "---\ntitle: Open Source AEO Tools\n---\n"
PAGE = FRONTMATTER + INTRO + TOOLS + FAQ
GOOD_REWRITE = ("## Tools\n\nOpen source AEO tools compared: " + " ".join(["tools"] * 33)
                + " See [LibHunt](https://www.libhunt.com/) for 42 more.\n\n")
BAD_REWRITE = "## Tools\n\nOpen source AEO tools compared: " + " ".join(["tools"] * 36) + " 42 more.\n\n"

GAPS = [{"query": "open source AEO tools", "cited": False, "sources": ["https://toolradar.com/x", "https://demo.dev/y"]}]


SRC_TEXT = "Best AEO tools list"
# label of every candidate text Jev can see (the rewritten Tools section keeps the label own_s01)
LABEL_OF = {TOOLS: "own_s01", GOOD_REWRITE: "own_s01", FAQ: "own_s02", SRC_TEXT: "src_1"}


class ScriptedJev:
    """Queue items: a dict ``{label: noul score}`` answers a Noul (scoring) request, a ChoiceAnswer answers
    the fidelity judge, an Exception is raised."""

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
        if isinstance(nxt, dict):
            labels = {qid: LABEL_OF[state["candidates"][qid]] for qid in questions}
            answers = {qid: NoulAnswer(nxt[label]) for qid, label in labels.items()}
        else:
            (qid,) = questions.keys()
            answers = {qid: nxt}
        return JevResponse(answers=answers, model="fake", input_tokens=1, output_tokens=0, cost_usd=0.0)


LOSES = {"own_s01": 0.30, "own_s02": 0.10, "src_1": 0.60}
FAITHFUL = ChoiceAnswer("faithful", 0.8, {"faithful": 0.9, "drops_facts": 0.05, "adds_claims": 0.05})
WON = {"own_s01": 0.70, "own_s02": 0.10, "src_1": 0.20}


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
    return [SourceDoc(url="https://toolradar.com/x", ok=True, title="toolradar.com", text=SRC_TEXT)]


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
    assert page["diagnosis"]["scorer"] == "noul"
    assert page["diagnosis"]["scores"] == {"own_s01": 0.30, "own_s02": 0.10, "src_1": 0.60}
    assert "probabilities" not in page["diagnosis"] and "confidence" not in page["diagnosis"]
    assert page["fidelity"]["rules"] == {"passed": True, "violations": []}
    assert page["fidelity"]["judge"] == {"verdict": "faithful", "confidence": 0.8, "accepted": True}
    assert page["verification"]["outcome"] == "won"
    assert page["verification"]["score_before"] == 0.30 and page["verification"]["score_after"] == 0.70
    assert page["verification"]["winner_after"] == "own_s01" and page["verification"]["winner_after_kind"] == "own"
    assert "p_before" not in page["verification"]
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
    assert "EXPERIMENTAL" in saved["note"] and "not been validated" in saved["note"]
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

    # the Jev diagnosis saw own sections (intro is < 30 words so excluded) and the fetched source, blind
    state, questions = jev.requests[0]
    assert sorted(LABEL_OF[t] for t in state["candidates"].values()) == ["own_s01", "own_s02", "src_1"]
    assert all(re.match(r"^c\d{2}$", k) for k in [*state["candidates"], *questions])
    blob = repr((state, questions))
    assert "own_" not in blob and "src_" not in blob and "toolradar" not in blob.replace(SRC_TEXT, "")
    # verification used the same ids, with the rewritten text under the target's id
    state_after, _ = jev.requests[2]
    assert list(state_after["candidates"]) == list(state["candidates"])
    target_cid = next(k for k, t in state["candidates"].items() if t == TOOLS)
    assert state_after["candidates"][target_cid] == GOOD_REWRITE[: judge.MAX_CANDIDATE_CHARS]


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
    worse = {"own_s01": 0.20, "own_s02": 0.10, "src_1": 0.70}
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


def test_jev_validation_describes_v4_configuration_without_a_result() -> None:
    # Until the pre-registered v4 run (plan v4 §3-§4) the running configuration has NO validation result;
    # the 2.2.0 figures are kept only under "previous", labeled with the configuration they measured.
    v = gaps.JEV_VALIDATION
    assert (v["protocol"], v["scorer"], v["ids"], v["unit"]) == ("v4", "noul", "blind", "sections")
    assert v["mean_auc"] is None and v["ci95"] is None and v["prereg_sha"] is None
    assert v["status"] == "experimental" and v["gate_passed"] is False
    assert v["gate_auc"] == 0.65 and v["gate_min_queries"] == 25
    prev = v["previous"]
    assert prev["config"] == "choice, leaky ids, page excerpts"
    assert prev["mean_auc"] == 0.619 and prev["ci95"] == [0.561, 0.674] and prev["own_accuracy"] == 0.167
    assert "0.62" not in gaps.SECTIONS_NOTE.split("earlier configuration")[0]


def test_experimental_flags_follow_the_validation_status(project: Path, monkeypatch) -> None:
    monkeypatch.setitem(gaps.JEV_VALIDATION, "status", "validated")
    report = _run(project, ScriptedJev(LOSES, FAITHFUL, WON), lambda *a: GOOD_REWRITE)
    page = report["pages"][0]
    assert page["status"] == "rewritten"
    assert "experimental" not in page["diagnosis"] and "experimental" not in page["verification"]
    assert "not a prediction of citation" in report["note"]


def test_rewriter_error_marks_page_and_run_continues(tmp_path: Path) -> None:
    from llm_client import LLMError

    project = tmp_path
    (project / "content").mkdir()
    (project / "content" / "compare.md").write_text(PAGE, encoding="utf-8")
    (project / "content" / "other.md").write_text(PAGE, encoding="utf-8")
    (project / "project.yaml").write_text(PROJECT_YAML_TWO_PAGES, encoding="utf-8")
    (project / "gaps.json").write_text(json.dumps(GAPS + [{"query": "second query", "cited": False,
                                                           "sources": ["https://toolradar.com/x"]}]), encoding="utf-8")
    plan = _plan(project)
    assert [p.page_id for p in plan.pages] == ["compare", "other"]

    def rewrite(*a):
        raise LLMError("Missing OPENAI_API_KEY")

    report = _run(project, ScriptedJev(LOSES, LOSES), rewrite)
    assert [p["status"] for p in report["pages"]] == ["rewriter_error", "rewriter_error"]
    assert all(p["reasons"] == ["Missing OPENAI_API_KEY"] for p in report["pages"])
    assert all(p["fidelity"] is None and p["verification"] is None for p in report["pages"])
    assert "rewriter_error" in gaps.SECTION_STATUSES
    assert json.loads((project / "out" / "fix-gaps.json").read_text(encoding="utf-8")) == report
    for pid in ("compare", "other"):
        assert not (project / "out" / pid / f"{pid}.md").exists()
        assert not (project / "out" / pid / "section.diff").exists()
        assert (project / "out" / pid / "diagnosis.json").exists()


def test_cli_section_mode_fails_closed_without_rewriter_key(project: Path, monkeypatch, capsys) -> None:
    monkeypatch.setenv("TYPESAFE_API_KEY", "ts-test")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("GEO_EVAL_MOCK", raising=False)
    monkeypatch.setattr(sources, "fetch_sources", lambda *a, **k: pytest.fail("must not fetch without rewriter key"))
    code = main(["fix-gaps", str(project / "gaps.json"), "--project", str(project / "project.yaml"),
                 "--out-dir", str(project / "out"), "--mode", "sections"])
    assert code == 2
    err = capsys.readouterr().err
    assert "OPENAI_API_KEY" in err and "GEO_EVAL_MOCK=1" in err
    assert not (project / "out").exists()


def test_cli_section_mode_fails_closed_without_key(project: Path, monkeypatch, capsys) -> None:
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
    monkeypatch.delenv("GEO_EVAL_MOCK", raising=False)
    code = main(["fix-gaps", str(project / "gaps.json"), "--project", str(project / "project.yaml"),
                 "--out-dir", str(project / "out"), "--mode", "sections"])
    assert code == 2
    err = capsys.readouterr().err
    assert "TYPESAFE_API_KEY" in err and "GEO_EVAL_MOCK=1" in err and "--mode page" in err
    assert not (project / "out").exists()


def test_cli_section_dry_run_needs_no_key_and_fetches_nothing(project: Path, monkeypatch, capsys) -> None:
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
    monkeypatch.delenv("GEO_EVAL_MOCK", raising=False)
    monkeypatch.setattr(sources, "fetch_sources", lambda *a, **k: pytest.fail("dry run must not fetch"))
    code = main(["fix-gaps", str(project / "gaps.json"), "--project", str(project / "project.yaml"),
                 "--out-dir", str(project / "out"), "--mode", "sections", "--dry-run"])
    assert code == 0 and not (project / "out").exists()
    assert "compare" in capsys.readouterr().out


def test_cli_mock_end_to_end_offline(project: Path, monkeypatch, capsys) -> None:
    monkeypatch.setenv("GEO_EVAL_MOCK", "1")
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
    monkeypatch.setattr(sources, "fetch_sources", lambda *a, **k: pytest.fail("mock mode must not fetch"))
    code = main(["fix-gaps", str(project / "gaps.json"), "--project", str(project / "project.yaml"),
                 "--out-dir", str(project / "out"), "--mode", "sections"])
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


def test_cli_default_mode_is_page(project: Path, monkeypatch) -> None:
    # owner decision 2026-09-26: page stays the default until remeasure evidence; sections is opt-in
    monkeypatch.setenv("GEO_EVAL_MOCK", "1")
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
    monkeypatch.setattr(sources, "fetch_sources", lambda *a, **k: pytest.fail("page mode must not fetch sources"))
    code = main(["fix-gaps", str(project / "gaps.json"), "--project", str(project / "project.yaml"),
                 "--out-dir", str(project / "out")])
    assert code == 0
    report = json.loads((project / "out" / "fix-gaps.json").read_text(encoding="utf-8"))
    assert report.get("mode") != "sections" and "jev_validation" not in report
    assert report["pages"][0]["page_id"] == "compare"


def test_cli_page_mode_fails_closed_without_openai_key(project: Path, monkeypatch, capsys) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("GEO_EVAL_MOCK", raising=False)
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
    code = main(["fix-gaps", str(project / "gaps.json"), "--project", str(project / "project.yaml"),
                 "--out-dir", str(project / "out")])
    assert code == 2
    err = capsys.readouterr().err
    assert "OPENAI_API_KEY" in err and "GEO_EVAL_MOCK=1" in err and "TYPESAFE_API_KEY" not in err
    assert not (project / "out").exists()
