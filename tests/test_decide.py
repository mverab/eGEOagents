"""Tests for the deterministic loop decision layer."""
from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path

from egeo import decide, workspace


ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples" / "project.yaml"
NOW = datetime(2026, 8, 25, 12, 0, tzinfo=timezone.utc)


def _write_jsonl(path: Path, records: list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in records), encoding="utf-8")


class DecideTests(unittest.TestCase):
    def setUp(self) -> None:
        self.home = Path(tempfile.mkdtemp(prefix="egeo-decide-"))
        shutil.copy(EXAMPLE, self.home / workspace.PROJECT_CONFIG_NAME)
        workspace.bootstrap(self.home)
        project = workspace.load_project_config(self.home)
        if not project:
            raise AssertionError("examples/project.yaml must load")
        self.project = project

    def tearDown(self) -> None:
        shutil.rmtree(self.home)

    def _serp(self, query_text: str, positions, start: datetime | None = None) -> None:
        start = start or (NOW - timedelta(days=3))
        records = []
        for index, position in enumerate(positions):
            ts = start + timedelta(days=index)
            records.append(
                {
                    "v": 1,
                    "ts": ts.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "query": query_text,
                    "target_position": position,
                    "results": [],
                }
            )
        _write_jsonl(decide._query_stream(self.home, query_text), records)

    def _page(self, url: str, types, ts: datetime | None = None) -> None:
        ts = ts or NOW
        _write_jsonl(
            decide._page_stream(self.home, url),
            [
                {
                    "v": 1,
                    "ts": ts.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "url": url,
                    "status": 200,
                    "jsonld_types": types,
                    "content_hash": "abc",
                    "word_count": 10,
                }
            ],
        )

    def _fresh_all_pages(self) -> None:
        for page in self.project["pages"]:
            self._page(page["url"], ["WebPage"], NOW)

    def test_escalate_absent_from_three_nulls(self) -> None:
        self._serp("GEO evaluation harness open source", [None, None, None])
        self._fresh_all_pages()
        action = decide.rank_action(self.home, self.project, now=NOW)
        self.assertEqual(action["kind"], "escalate_absent")
        self.assertEqual(action["query_ids"], ["generic-geo-evaluation"])
        self.assertEqual(action["next_gate"], "owner")
        self.assertFalse(action["auto_apply"])

    def test_propose_schema_when_jsonld_empty(self) -> None:
        self._serp("GEO evaluation harness open source", [1, 1, 1])
        self._serp("what is llms.txt", [2, 2, 2])
        self._serp("E-GEO generative engine optimization toolkit", [3, 3, 3])
        for page in self.project["pages"]:
            types = [] if page["id"] == "home" else ["WebPage"]
            self._page(page["url"], types, NOW)
        action = decide.rank_action(self.home, self.project, now=NOW)
        self.assertEqual(action["kind"], "propose_schema")
        self.assertEqual(action["page_ids"], ["home"])

    def test_wait_for_window_when_open_action_is_fresh(self) -> None:
        self._serp("GEO evaluation harness open source", [None, None, None])
        self._fresh_all_pages()
        decide.append_jsonl(
            decide.ledger_path(self.home),
            {
                "v": 1,
                "id": "open-row",
                "ts": (NOW - timedelta(days=2)).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "kind": "escalate_absent",
                "status": "proposed",
                "query_ids": ["generic-geo-evaluation"],
                "page_ids": ["docs-evaluation"],
                "auto_apply": False,
            },
        )
        action = decide.rank_action(self.home, self.project, now=NOW)
        self.assertEqual(action["kind"], "wait_for_window")

    def test_grade_unchanged_after_seven_days(self) -> None:
        created = NOW - timedelta(days=8)
        self._serp("GEO evaluation harness open source", [None, None, None, None], start=created - timedelta(days=2))
        self._fresh_all_pages()
        decide.append_jsonl(
            decide.ledger_path(self.home),
            {
                "v": 1,
                "id": "old-row",
                "ts": created.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "kind": "escalate_absent",
                "status": "proposed",
                "query_ids": ["generic-geo-evaluation"],
                "page_ids": ["docs-evaluation"],
                "grades": {},
                "auto_apply": False,
            },
        )
        action = decide.rank_action(self.home, self.project, now=NOW)
        self.assertEqual(action["kind"], "grade_outcome")
        self.assertEqual(action["grade"], "unchanged")

    def test_dry_run_writes_nothing(self) -> None:
        self._serp("GEO evaluation harness open source", [None, None, None])
        self._fresh_all_pages()
        before_log = (self.home / "LOG.md").read_text(encoding="utf-8")
        action = decide.rank_action(self.home, self.project, now=NOW)
        self.assertEqual(action["kind"], "escalate_absent")
        self.assertFalse(decide.ledger_path(self.home).exists())
        self.assertEqual((self.home / "LOG.md").read_text(encoding="utf-8"), before_log)
        docs = list((self.home / "docs").glob("*.md")) if (self.home / "docs").is_dir() else []
        self.assertEqual(docs, [])

    def test_apply_never_sets_applied(self) -> None:
        self._serp("GEO evaluation harness open source", [None, None, None])
        self._fresh_all_pages()
        action = decide.rank_action(self.home, self.project, now=NOW)
        result = decide.apply_decision(self.home, self.project, action, now=NOW)
        row = result["ledger_row"]
        self.assertEqual(row["status"], "proposed")
        self.assertFalse(row["auto_apply"])
        self.assertNotEqual(row["status"], "applied")
        ledger = decide.load_ledger(self.home)
        self.assertEqual(len(ledger), 1)
        self.assertTrue(any("docs/" in item for item in result["written"]))

    def test_duplicate_open_row_is_not_reproposed(self) -> None:
        self._serp("GEO evaluation harness open source", [None, None, None])
        self._fresh_all_pages()
        first = decide.rank_action(self.home, self.project, now=NOW)
        decide.apply_decision(self.home, self.project, first, now=NOW)
        second = decide.rank_action(self.home, self.project, now=NOW + timedelta(hours=1))
        self.assertEqual(second["kind"], "wait_for_window")
        self.assertEqual(len(decide.load_ledger(self.home)), 1)


if __name__ == "__main__":
    unittest.main()
