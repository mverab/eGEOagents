"""Loop-run integration for the ai_overview collector."""
from __future__ import annotations

import json
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "collectors"))

import _common as common  # noqa: E402
from egeo import loop, workspace  # noqa: E402


def _write_record(home: Path, query: str, record: dict) -> None:
    stream = workspace.data_dir("ai_overview", home) / f"{common.slugify(query)}.jsonl"
    stream.parent.mkdir(parents=True, exist_ok=True)
    with stream.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True) + "\n")


def _make_record(query: str, *, available: bool, target_cited: bool, target_position: int | None, citations: list) -> dict:
    return {
        "v": 1,
        "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "query": query,
        "engine": "google-ai-overview",
        "available": available,
        "answer": "answer text",
        "citations": citations,
        "target_domain": "example.com",
        "target_cited": target_cited,
        "target_position": target_position,
        "cost_credits": 3,
        "remaining_credits": 1000,
    }


def test_collector_deltas_surface_ai_overview_fields() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        home = Path(tmp)
        workspace.bootstrap(home)
        record = _make_record(
            "how do solar panels work",
            available=True,
            target_cited=True,
            target_position=1,
            citations=[{"position": 1, "url": "https://example.com", "domain": "example.com", "title": "Example"}],
        )
        _write_record(home, "how do solar panels work", record)

        deltas = loop.collector_deltas(home, since=None)

        assert len(deltas) == 1
        item = deltas[0]
        assert item["collector"] == "ai_overview"
        assert item["available"] is True
        assert item["target_cited"] is True
        assert item["target_position"] == 1
        assert item["citation_count"] == 1


def test_candidate_signals_detect_appearance_and_citation_change() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        home = Path(tmp)
        workspace.bootstrap(home)
        # First observation: no overview, not cited
        first = _make_record(
            "how do solar panels work",
            available=False,
            target_cited=False,
            target_position=None,
            citations=[],
        )
        # Second observation: overview appeared, target cited
        second = _make_record(
            "how do solar panels work",
            available=True,
            target_cited=True,
            target_position=2,
            citations=[
                {"position": 1, "url": "https://other.com", "domain": "other.com", "title": "Other"},
                {"position": 2, "url": "https://example.com", "domain": "example.com", "title": "Example"},
            ],
        )
        _write_record(home, "how do solar panels work", first)
        _write_record(home, "how do solar panels work", second)

        deltas = loop.collector_deltas(home, since=None)
        signals = loop.candidate_signals(deltas)

        assert any("AI Overview appeared" in signal for signal in signals)
        assert any("target now cited (position 2)" in signal for signal in signals)


def test_candidate_signals_detect_disappearance_and_uncitation() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        home = Path(tmp)
        workspace.bootstrap(home)
        first = _make_record(
            "how do solar panels work",
            available=True,
            target_cited=True,
            target_position=1,
            citations=[{"position": 1, "url": "https://example.com", "domain": "example.com", "title": "Example"}],
        )
        second = _make_record(
            "how do solar panels work",
            available=False,
            target_cited=False,
            target_position=None,
            citations=[],
        )
        _write_record(home, "how do solar panels work", first)
        _write_record(home, "how do solar panels work", second)

        deltas = loop.collector_deltas(home, since=None)
        signals = loop.candidate_signals(deltas)

        assert any("AI Overview disappeared" in signal for signal in signals)
        assert any("target no longer cited" in signal for signal in signals)
