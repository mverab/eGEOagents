"""Tests for ``egeo fix-gaps`` (openspec/changes/add-fix-gaps)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from egeo import gaps, workspace
from egeo.cli import main
from egeo.runtimes import get_runtime


PROJECT_YAML = """schema_version: 1
project:
  id: demo
  name: Demo
  repository: https://github.com/example/demo
  canonical_domain: demo.dev
  canonical_url: https://demo.dev/
  language: en
queries:
  - id: q-aeo
    text: open source AEO tools
    class: generic
    intent: aeo
    target_pages: [compare]
    active: true
  - id: q-geo
    text: best geo tools 2026
    class: generic
    intent: geo
    target_pages: [compare]
    experiment: second-query
    active: true
  - id: q-nopage
    text: geo without page
    class: generic
    intent: nopage
    target_pages: []
    active: true
  - id: q-nosource
    text: llms txt guide
    class: informational
    intent: llms
    target_pages: [llms]
    active: true
  - id: q-missing
    text: missing file query
    class: generic
    intent: missing
    target_pages: [missing]
    active: true
  - id: q-inactive
    text: retired query
    class: generic
    intent: retired
    target_pages: [compare]
    active: false
pages:
  - id: compare
    url: https://demo.dev/compare/
    source: content/compare.md
    active: true
  - id: llms
    url: https://demo.dev/llms/
    active: true
  - id: missing
    url: https://demo.dev/missing/
    source: content/does-not-exist.md
    active: true
measurement:
  engines: [perplexity]
  cadence: weekly
guardrails:
  no_duplicate_query_owners: true
  no_auto_publish_visible_copy: true
  no_fabricated_proof: true
  require_fresh_crawl_before_verdict: true
"""

COMPARE_MD = "# Open-Source GEO Tools\n\nA comparison of open-source GEO and AEO tools.\n"

GOS_RESULT = {
    "checked": True,
    "brand": "Demo",
    "domain": "demo.dev",
    "entries": [
        {"query": "Open source AEO tools?", "platform": "perplexity", "domain_cited": False,
         "cited_sources": ["https://rival.com/x"], "error": None},
        {"query": "best GEO tools 2026", "platform": "perplexity", "domain_cited": False,
         "cited_sources": [], "error": None},
        {"query": "llms txt guide", "platform": "perplexity", "domain_cited": True,
         "cited_sources": ["https://demo.dev/llms/"], "error": None},
        {"query": "missing file query", "platform": "perplexity", "domain_cited": False,
         "cited_sources": [], "error": "timeout"},
    ],
}


@pytest.fixture()
def project(tmp_path: Path) -> Path:
    (tmp_path / "content").mkdir()
    (tmp_path / "content" / "compare.md").write_text(COMPARE_MD, encoding="utf-8")
    path = tmp_path / "project.yaml"
    path.write_text(PROJECT_YAML, encoding="utf-8")
    return path


def _write(tmp_path: Path, name: str, data) -> Path:
    path = tmp_path / name
    path.write_text(data if isinstance(data, str) else json.dumps(data), encoding="utf-8")
    return path


# --- input formats ---------------------------------------------------------- #

def test_geo_optimizer_skill_format(tmp_path: Path) -> None:
    loaded = gaps.load_gaps(_write(tmp_path, "g.json", GOS_RESULT))
    assert loaded.format == "geo-optimizer-skill"
    assert loaded.domain == "demo.dev"
    assert [g.query for g in loaded.gaps] == ["Open source AEO tools?", "best GEO tools 2026"]
    assert loaded.gaps[0].sources == ["https://rival.com/x"]
    assert loaded.skipped == [{"query": "missing file query", "reason": "tracker_error"}]


def test_generic_json_array(tmp_path: Path) -> None:
    rows = [
        {"query": "a", "cited": False},
        {"query": "b", "cited": "no"},
        {"query": "c", "cited": 0},
        {"query": "d", "cited": True},
        {"query": "e", "cited": "yes", "sources": ["x"]},
    ]
    loaded = gaps.load_gaps(_write(tmp_path, "g.json", rows))
    assert loaded.format == "generic"
    assert [g.query for g in loaded.gaps] == ["a", "b", "c"]


def test_generic_csv(tmp_path: Path) -> None:
    csv_text = "query,cited,sources\nopen source AEO tools,false,https://rival.com\nllms txt guide,true,\n"
    loaded = gaps.load_gaps(_write(tmp_path, "g.csv", csv_text))
    assert loaded.format == "generic"
    assert [g.query for g in loaded.gaps] == ["open source AEO tools"]
    assert loaded.gaps[0].sources == ["https://rival.com"]


def test_unknown_shape_names_both_formats(tmp_path: Path) -> None:
    with pytest.raises(gaps.GapsFormatError) as err:
        gaps.load_gaps(_write(tmp_path, "g.json", {"results": []}))
    assert "geo citations --format json" in str(err.value)
    assert "query" in str(err.value) and "cited" in str(err.value)


def test_normalize_query() -> None:
    assert gaps.normalize_query("  Open   Source AEO tools?! ") == "open source aeo tools"


# --- planning ---------------------------------------------------------------- #

def _plan(tmp_path: Path, project: Path, rows):
    loaded = gaps.load_gaps(_write(tmp_path, "g.json", rows))
    return gaps.plan_fixes(loaded, gaps.load_project_file(project), project.parent)


def test_gap_maps_to_page_source(tmp_path: Path, project: Path) -> None:
    plan = _plan(tmp_path, project, GOS_RESULT)
    assert [p.page_id for p in plan.pages] == ["compare"]
    page = plan.pages[0]
    assert page.source == project.parent / "content" / "compare.md"
    assert page.query == "Open source AEO tools?"
    assert page.other_gaps == ["best GEO tools 2026"]
    assert plan.skipped == [{"query": "missing file query", "reason": "tracker_error"}]


@pytest.mark.parametrize(
    "query,reason",
    [
        ("something else", "query_not_in_project"),
        ("retired query", "query_not_in_project"),
        ("geo without page", "no_target_page"),
        ("llms txt guide", "page_has_no_source"),
        ("missing file query", "source_not_found"),
    ],
)
def test_unmatched_reasons(tmp_path: Path, project: Path, query: str, reason: str) -> None:
    plan = _plan(tmp_path, project, [{"query": query, "cited": False}])
    assert plan.pages == []
    assert plan.unmatched == [{"query": query, "reason": reason}]


# --- execution --------------------------------------------------------------- #

def test_run_writes_outputs_and_report_without_touching_source(
    tmp_path: Path, project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("GEO_EVAL_MOCK", "1")
    plan = _plan(tmp_path, project, GOS_RESULT)
    out = tmp_path / "out"
    report = gaps.run_fix_gaps(plan, runtime=get_runtime("python"), out_dir=out)

    assert (project.parent / "content" / "compare.md").read_text(encoding="utf-8") == COMPARE_MD
    assert list((out / "compare" / "optimized").glob("*.md"))
    saved = json.loads((out / "fix-gaps.json").read_text(encoding="utf-8"))
    assert saved == report
    for key in ("format", "pages", "unmatched", "skipped", "remeasure", "note"):
        assert key in saved
    assert saved["pages"][0]["page_id"] == "compare"
    assert saved["pages"][0]["query"] == "Open source AEO tools?"
    assert "rank_before" in saved["pages"][0] and "rank_after" in saved["pages"][0]
    assert saved["remeasure"]["queries"] == ["Open source AEO tools?", "best GEO tools 2026"]
    assert "geo citations" in saved["remeasure"]["command"]
    assert "--domain demo.dev" in saved["remeasure"]["command"]
    assert "proxy" in saved["note"].lower()


def test_cli_dry_run_writes_nothing(tmp_path: Path, project: Path, capsys: pytest.CaptureFixture) -> None:
    gaps_file = _write(tmp_path, "g.json", GOS_RESULT)
    out = tmp_path / "out"
    code = main(["fix-gaps", str(gaps_file), "--project", str(project), "--out-dir", str(out), "--dry-run"])
    assert code == 0
    assert not out.exists()
    printed = capsys.readouterr().out
    assert "compare" in printed and "Open source AEO tools?" in printed


def test_cli_unknown_format_exits_nonzero(tmp_path: Path, project: Path) -> None:
    bad = _write(tmp_path, "g.json", {"results": []})
    assert main(["fix-gaps", str(bad), "--project", str(project), "--dry-run"]) != 0


# --- project contract ---------------------------------------------------------- #

def test_page_source_must_be_a_string() -> None:
    import yaml

    data = yaml.safe_load(PROJECT_YAML)
    assert workspace.validate_project_config(data) == []
    data["pages"][0]["source"] = 42
    assert "pages[0].source must be a non-empty relative path" in workspace.validate_project_config(data)


def test_query_with_one_sourceless_page_still_plans_the_other(tmp_path: Path, project: Path) -> None:
    text = project.read_text(encoding="utf-8").replace(
        "    target_pages: [compare]\n    active: true\n  - id: q-geo",
        "    target_pages: [llms, compare]\n    active: true\n  - id: q-geo",
    )
    project.write_text(text, encoding="utf-8")
    plan = _plan(tmp_path, project, [{"query": "open source AEO tools", "cited": False}])
    assert [p.page_id for p in plan.pages] == ["compare"]
    assert plan.unmatched == []
