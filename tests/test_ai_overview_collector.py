"""Contract tests for collectors/ai_overview.py. No network: fixture mode only."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURES = REPO_ROOT / "collectors" / "fixtures"


def _load_collector():
    """Import collectors/ai_overview.py the way ``egeo loop collect`` does."""
    collector_path = REPO_ROOT / "collectors" / "ai_overview.py"
    spec = importlib.util.spec_from_file_location("egeo_collector_ai_overview", collector_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


ai_overview = _load_collector()


@pytest.fixture()
def workspace_home(tmp_path, monkeypatch):
    monkeypatch.setenv("EGEO_HOME", str(tmp_path))
    return tmp_path


def _fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def test_domain_of_strips_www_and_port() -> None:
    assert ai_overview._domain_of("https://www.Example.com:443/a") == "example.com"
    assert ai_overview._domain_of("https://docs.example.com/a") == "docs.example.com"
    assert ai_overview._domain_of("not a url") == ""


def test_citation_key_ignores_tracking_params_and_trailing_slash() -> None:
    left = ai_overview._citation_key("https://www.energysage.com/solar/?utm_source=x&gclid=1")
    right = ai_overview._citation_key("https://energysage.com/solar")

    assert left == right
    assert left == "https://energysage.com/solar"


def test_parse_merges_and_dedupes_citations() -> None:
    record = ai_overview.parse_ai_overview_response(
        _fixture("ai_overview_goanyapi_response.json"),
        "how do solar panels work",
        "energysage.com",
    )

    assert record["v"] == 1
    assert record["engine"] == "google-ai-overview"
    assert record["available"] is True
    assert "photovoltaic" in record["answer"]
    # results[].links + serp_features[].links, EnergySage counted once.
    assert [item["position"] for item in record["citations"]] == [1, 2, 3]
    assert [item["domain"] for item in record["citations"]] == [
        "energysage.com",
        "reddit.com",
        "nationalgrid.com",
    ]
    assert record["target_domain"] == "energysage.com"
    assert record["target_cited"] is True
    assert record["target_position"] == 1
    assert record["cost_credits"] == 3
    assert record["remaining_credits"] == 1234


def test_parse_reports_absent_overview_as_valid_observation() -> None:
    record = ai_overview.parse_ai_overview_response(
        _fixture("ai_overview_goanyapi_response_empty.json"),
        "site:example.com inurl:goanyapi-overview-no-result-20261110",
        "example.com",
    )

    assert record["available"] is False
    assert record["answer"] == ""
    assert record["citations"] == []
    assert record["target_cited"] is False
    assert record["target_position"] is None
    # 402-free empty responses still bill, and the record keeps the evidence.
    assert record["cost_credits"] == 3


def test_parse_uncited_target_is_recorded_as_negative_evidence() -> None:
    record = ai_overview.parse_ai_overview_response(
        _fixture("ai_overview_goanyapi_response.json"),
        "how do solar panels work",
        "goanyapi.com",
    )

    assert record["target_cited"] is False
    assert record["target_position"] is None
    assert len(record["citations"]) == 3


def test_parse_rejects_business_error_envelope() -> None:
    with pytest.raises(Exception) as excinfo:
        ai_overview.parse_ai_overview_response({"code": "insufficient_credits"}, "q", "example.com")

    assert "insufficient_credits" in str(excinfo.value)


def test_collect_fixture_mode_appends_one_record_per_query(workspace_home) -> None:
    result = ai_overview.collect(
        queries=["how do solar panels work"],
        target_domain="energysage.com",
        home=workspace_home,
        fixture=FIXTURES / "ai_overview_goanyapi_response.json",
    )

    stream = workspace_home / "data" / "ai_overview" / "how-do-solar-panels-work.jsonl"
    lines = stream.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    assert json.loads(lines[0])["target_position"] == 1
    assert "target cited in 1/1" in result["log"]
    assert (workspace_home / "LOG.md").exists()


def test_collect_is_idempotent_to_rerun(workspace_home) -> None:
    for _ in range(2):
        ai_overview.collect(
            queries=["how do solar panels work"],
            target_domain="energysage.com",
            home=workspace_home,
            fixture=FIXTURES / "ai_overview_goanyapi_response.json",
        )

    stream = workspace_home / "data" / "ai_overview" / "how-do-solar-panels-work.jsonl"
    assert len(stream.read_text(encoding="utf-8").strip().splitlines()) == 2


def test_collect_refuses_budget_overflow(workspace_home) -> None:
    with pytest.raises(Exception) as excinfo:
        ai_overview.collect(
            queries=["a", "b"],
            target_domain="example.com",
            home=workspace_home,
            fixture=FIXTURES / "ai_overview_goanyapi_response.json",
            budget=1,
        )

    assert "budgets.queries_per_day" in str(excinfo.value)


def test_collect_without_key_or_fixture_fails_loudly(workspace_home, monkeypatch) -> None:
    monkeypatch.delenv("GOANYAPI_API_KEY", raising=False)

    with pytest.raises(Exception) as excinfo:
        ai_overview.collect(queries=["q"], target_domain="example.com", home=workspace_home)

    assert "GOANYAPI_API_KEY" in str(excinfo.value)


def test_main_prints_summary_in_fixture_mode(workspace_home, capsys) -> None:
    exit_code = ai_overview.main(
        [
            "--query",
            "how do solar panels work",
            "--target-domain",
            "energysage.com",
            "--fixture",
            str(FIXTURES / "ai_overview_goanyapi_response.json"),
        ]
    )

    assert exit_code == 0
    out = capsys.readouterr().out
    assert "AI Overview" in out
    assert "target citation 1" in out
    assert "outcome=success" in out
