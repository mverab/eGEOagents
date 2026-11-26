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


class LedgerLifecycleTests(DecideTests):
    """openspec update-loop-ledger-lifecycle: the ledger closes, and grades need attribution."""

    Q = "GEO evaluation harness open source"
    T0 = NOW - timedelta(days=40)

    def _obs(self, position, when: datetime) -> None:
        decide.append_jsonl(
            decide._query_stream(self.home, self.Q),
            {"v": 1, "ts": when.strftime("%Y-%m-%dT%H:%M:%SZ"), "query": self.Q, "target_position": position, "results": []},
        )

    def _pages_at(self, when: datetime, types=("WebPage",)) -> None:
        for page in self.project["pages"]:
            decide.append_jsonl(
                decide._page_stream(self.home, page["url"]),
                {"v": 1, "ts": when.strftime("%Y-%m-%dT%H:%M:%SZ"), "url": page["url"], "jsonld_types": list(types)},
            )

    def _step(self, when: datetime) -> dict:
        action = decide.rank_action(self.home, self.project, now=when)
        return decide.apply_decision(self.home, self.project, action, now=when)

    def _propose(self) -> str:
        """Three absent observations, then one decide run at T0+3d. Returns the proposal id."""
        for day in range(3):
            self._obs(None, self.T0 + timedelta(days=day))
        self._pages_at(self.T0 + timedelta(days=2))
        result = self._step(self.T0 + timedelta(days=3))
        self.assertEqual(result["kind"], "escalate_absent")
        return result["ledger_row"]["id"]

    def _day(self, n: float) -> datetime:
        return self.T0 + timedelta(days=n)

    def _grades(self) -> list:
        return [r for r in decide.load_ledger(self.home) if r["kind"] == "grade_outcome"]

    def test_graded_window_is_not_graded_again(self) -> None:
        self._propose()
        self._obs(None, self._day(9))
        self._pages_at(self._day(9))
        first = self._step(self._day(10.5))
        self.assertEqual((first["kind"], first["grade"], first["window"]), ("grade_outcome", "unchanged", 7))
        second = self._step(self._day(10.6))
        self.assertNotEqual(second["kind"], "grade_outcome")
        self.assertEqual(len(self._grades()), 1)
        self.assertEqual(self._grades()[0]["window"], 7)

    def test_next_action_is_ranked_after_grading(self) -> None:
        self._propose()
        self._obs(None, self._day(9))
        for page in self.project["pages"]:
            types = [] if page["id"] == "home" else ["WebPage"]
            decide.append_jsonl(
                decide._page_stream(self.home, page["url"]),
                {"ts": self._day(9).strftime("%Y-%m-%dT%H:%M:%SZ"), "url": page["url"], "jsonld_types": types},
            )
        self._step(self._day(10.5))
        nxt = self._step(self._day(10.6))
        self.assertEqual(nxt["kind"], "propose_schema")

    def test_reappearance_without_application_is_unattributed(self) -> None:
        pid = self._propose()
        self._obs(4, self._day(9))
        self._pages_at(self._day(9))
        result = self._step(self._day(10.5))
        self.assertEqual(result["grade"], "resolved_unattributed")
        self.assertNotIn("verified", [r["status"] for r in decide.load_ledger(self.home)])
        state = {s["id"]: s for s in decide.ledger_state(decide.load_ledger(self.home))}[pid]
        self.assertTrue(state["closed"])
        self.assertEqual(state["status"], "resolved_unattributed")

    def test_reappearance_after_application_is_verified(self) -> None:
        pid = self._propose()
        decide.mark_row(self.home, pid, "applied", now=self._day(5))
        self._obs(4, self._day(12))
        self._pages_at(self._day(12))
        result = self._step(self._day(12.5))
        self.assertEqual((result["kind"], result["grade"]), ("grade_outcome", "verified"))
        self.assertEqual(self._step(self._day(12.6))["kind"], "no_op")

    def test_windows_count_from_applied_time(self) -> None:
        pid = self._propose()
        decide.mark_row(self.home, pid, "applied", now=self._day(8))
        self._obs(4, self._day(7))  # before the application: must not count
        self._obs(None, self._day(10))
        self._pages_at(self._day(10))
        waiting = decide.rank_action(self.home, self.project, now=self._day(11))
        self.assertEqual(waiting["kind"], "wait_for_window")
        self._obs(None, self._day(15))
        self._pages_at(self._day(15))
        graded = decide.rank_action(self.home, self.project, now=self._day(15.5))
        self.assertEqual((graded["kind"], graded["grade"], graded["window"]), ("grade_outcome", "unchanged", 7))

    def test_only_latest_due_window_is_graded_and_row_closes(self) -> None:
        pid = self._propose()
        self._obs(None, self._day(32))
        self._pages_at(self._day(32))
        result = self._step(self._day(33.5))
        self.assertEqual((result["grade"], result["window"]), ("unchanged", 28))
        self.assertEqual(len(self._grades()), 1)
        state = {s["id"]: s for s in decide.ledger_state(decide.load_ledger(self.home))}[pid]
        self.assertTrue(state["closed"])

    def test_closed_proposal_can_be_proposed_again(self) -> None:
        self._propose()
        for day in (30, 31, 32):
            self._obs(None, self._day(day))
        self._pages_at(self._day(32))
        self._step(self._day(33.5))
        again = self._step(self._day(33.6))
        self.assertEqual(again["kind"], "escalate_absent")

    def test_propose_page_owner_is_graded_instead_of_blocking(self) -> None:
        self._fresh_all_pages()
        for query in self.project["queries"]:
            self._serp(query["text"], [1, 1, 1])
        self.project["queries"][0]["target_pages"] = []
        created = NOW - timedelta(days=8)
        proposed = self._step(created)
        self.assertEqual(proposed["kind"], "propose_page_owner")
        still = decide.rank_action(self.home, self.project, now=NOW)
        self.assertEqual((still["kind"], still["grade"]), ("grade_outcome", "unchanged"))
        self.project["queries"][0]["target_pages"] = ["docs-evaluation"]
        fixed = decide.rank_action(self.home, self.project, now=NOW)
        self.assertEqual((fixed["kind"], fixed["grade"]), ("grade_outcome", "verified"))

    def test_legacy_duplicate_grades_collapse_and_file_is_untouched(self) -> None:
        pid = self._propose()
        self._obs(None, self._day(9))
        self._pages_at(self._day(9))
        for hour in (1, 2, 3):  # what 2.4.0 wrote: no `window`, one line per run
            decide.append_jsonl(
                decide.ledger_path(self.home),
                {
                    "v": 1,
                    "id": f"legacy-grade-{hour}",
                    "ts": (self._day(10.5) + timedelta(hours=hour)).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "kind": "grade_outcome",
                    "status": "unchanged",
                    "graded_id": pid,
                    "grades": {},
                },
            )
        before = decide.ledger_path(self.home).read_bytes()
        state = {s["id"]: s for s in decide.ledger_state(decide.load_ledger(self.home))}[pid]
        self.assertEqual(state["grades"], {7: "unchanged"})
        action = decide.rank_action(self.home, self.project, now=self._day(11))
        self.assertNotEqual(action["kind"], "grade_outcome")
        self.assertEqual(decide.ledger_path(self.home).read_bytes(), before)

    def test_open_proposal_does_not_block_other_proposals(self) -> None:
        first = self._propose()
        other = "what is llms.txt"
        for day in range(3):
            decide.append_jsonl(
                decide._query_stream(self.home, other),
                {"ts": self._day(day).strftime("%Y-%m-%dT%H:%M:%SZ"), "query": other, "target_position": None},
            )
        second = self._step(self._day(3.1))  # same day, first proposal 0 days old
        self.assertEqual(second["kind"], "escalate_absent")
        self.assertEqual(second["query_ids"], ["generic-llms-txt"])
        third = self._step(self._day(3.2))  # nothing new left: report the wait, propose nothing twice
        self.assertEqual((third["kind"], third["ledger_id"]), ("wait_for_window", first))
        self.assertEqual(len(decide.load_ledger(self.home)), 2)

    def test_due_grade_goes_before_new_proposals(self) -> None:
        self._propose()
        self._obs(None, self._day(9))
        for page in self.project["pages"]:
            decide.append_jsonl(
                decide._page_stream(self.home, page["url"]),
                {"ts": self._day(9).strftime("%Y-%m-%dT%H:%M:%SZ"), "url": page["url"], "jsonld_types": []},
            )
        self.assertEqual(self._step(self._day(10.5))["kind"], "grade_outcome")
        self.assertEqual(self._step(self._day(10.6))["kind"], "propose_schema")

    def test_mark_applied_appends_one_event_and_one_log_line(self) -> None:
        pid = self._propose()
        log_before = (self.home / "LOG.md").read_text(encoding="utf-8").count("\n")
        result = decide.mark_row(self.home, pid, "applied", note="PR 12", now=self._day(5))
        row = result["ledger_row"]
        self.assertEqual((row["kind"], row["status"], row["target_id"], row["note"]), ("mark_applied", "applied", pid, "PR 12"))
        self.assertFalse(row["auto_apply"])
        self.assertEqual(len(decide.load_ledger(self.home)), 2)
        self.assertEqual((self.home / "LOG.md").read_text(encoding="utf-8").count("\n"), log_before + 1)

    def test_mark_withdrawn_closes_and_unblocks(self) -> None:
        pid = self._propose()
        decide.mark_row(self.home, pid, "withdrawn", now=self._day(4))
        action = decide.rank_action(self.home, self.project, now=self._day(4.1))
        self.assertNotEqual(action["kind"], "wait_for_window")

    def test_mark_rejects_bad_requests(self) -> None:
        pid = self._propose()
        lines = len(decide.load_ledger(self.home))
        with self.assertRaises(decide.LedgerError):
            decide.mark_row(self.home, "nope", "applied", now=self._day(5))
        with self.assertRaises(decide.LedgerError):
            decide.mark_row(self.home, pid, "published", now=self._day(5))
        with self.assertRaises(decide.LedgerError):  # before the proposal
            decide.mark_row(self.home, pid, "applied", at=self._day(1), now=self._day(5))
        with self.assertRaises(decide.LedgerError):  # in the future
            decide.mark_row(self.home, pid, "applied", at=self._day(6), now=self._day(5))
        self.assertEqual(len(decide.load_ledger(self.home)), lines)
        decide.mark_row(self.home, pid, "applied", at=self._day(4), now=self._day(5))
        with self.assertRaises(decide.LedgerError):  # twice
            decide.mark_row(self.home, pid, "applied", now=self._day(5))
        decide.mark_row(self.home, pid, "withdrawn", now=self._day(6))
        with self.assertRaises(decide.LedgerError):  # closed
            decide.mark_row(self.home, pid, "withdrawn", now=self._day(6))

    def test_event_lines_cannot_be_marked(self) -> None:
        pid = self._propose()
        event = decide.mark_row(self.home, pid, "applied", now=self._day(5))["ledger_row"]["id"]
        with self.assertRaises(decide.LedgerError):
            decide.mark_row(self.home, event, "withdrawn", now=self._day(5))

    def test_proposal_doc_names_ledger_id_and_mark_command(self) -> None:
        pid = self._propose()
        doc = next((self.home / "docs").glob("*-decide-*.md")).read_text(encoding="utf-8")
        self.assertIn(pid, doc)
        self.assertIn("egeo loop mark", doc)


class UncitedInAiOverviewTests(unittest.TestCase):
    """openspec add-decide-ai-overview-citations: propose and grade from AI Overview citations."""

    Q = "GEO evaluation harness open source"
    QID = "generic-geo-evaluation"
    T0 = NOW - timedelta(days=40)

    def setUp(self) -> None:
        self.home = Path(tempfile.mkdtemp(prefix="egeo-decide-aio-"))
        shutil.copy(EXAMPLE, self.home / workspace.PROJECT_CONFIG_NAME)
        workspace.bootstrap(self.home)
        self.project = workspace.load_project_config(self.home)

    def tearDown(self) -> None:
        shutil.rmtree(self.home)

    def _day(self, n: float) -> datetime:
        return self.T0 + timedelta(days=n)

    def _fresh(self, when: datetime) -> None:
        """Healthy SERP and page streams, so only the AI Overview data can trigger a proposal."""
        stamp = when.strftime("%Y-%m-%dT%H:%M:%SZ")
        for query in self.project["queries"]:
            decide.append_jsonl(decide._query_stream(self.home, query["text"]), {"ts": stamp, "target_position": 1})
        for page in self.project["pages"]:
            decide.append_jsonl(decide._page_stream(self.home, page["url"]), {"ts": stamp, "jsonld_types": ["WebPage"]})

    def _aio(self, when: datetime, *, available=True, cited=False, domains=("a.com", "b.org")) -> None:
        citations = [{"position": i, "url": f"https://{d}/x", "domain": d} for i, d in enumerate(domains, 1)]
        if cited:
            citations.append({"position": len(citations) + 1, "url": "https://egeoagents.com/", "domain": "egeoagents.com"})
        decide.append_jsonl(
            decide._overview_stream(self.home, self.Q),
            {
                "v": 1,
                "ts": when.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "query": self.Q,
                "available": available,
                "citations": citations if available else [],
                "target_domain": "egeoagents.com",
                "target_cited": bool(cited and available),
            },
        )

    def _rank(self, when: datetime) -> dict:
        return decide.rank_action(self.home, self.project, now=when)

    def _step(self, when: datetime) -> dict:
        return decide.apply_decision(self.home, self.project, self._rank(when), now=when)

    def _propose(self) -> str:
        self._aio(self._day(0), domains=("a.com", "b.org"))
        self._aio(self._day(1), domains=("a.com",))
        self._aio(self._day(2), domains=("a.com", "c.net"))
        self._fresh(self._day(2))
        result = self._step(self._day(3))
        self.assertEqual(result["kind"], "escalate_uncited")
        return result["ledger_row"]["id"]

    def test_three_shown_and_uncited_observations_propose(self) -> None:
        self._aio(self._day(0))
        self._aio(self._day(1))
        self._fresh(self._day(2))
        self.assertEqual(self._rank(self._day(2))["kind"], "no_op")  # two are not enough
        self._aio(self._day(2), domains=("a.com", "c.net"))
        action = self._rank(self._day(3))
        self.assertEqual((action["kind"], action["next_gate"]), ("escalate_uncited", "owner"))
        self.assertEqual(action["query_ids"], [self.QID])
        self.assertEqual(action["page_ids"], ["docs-evaluation"])
        self.assertEqual(action["evidence"], ["data/ai_overview/geo-evaluation-harness-open-source.jsonl"])
        self.assertEqual(
            action["details"]["cited_instead"],
            [{"domain": "a.com", "observations": 3}, {"domain": "b.org", "observations": 2}, {"domain": "c.net", "observations": 1}],
        )

    def test_missing_overview_is_not_counted_as_uncited(self) -> None:
        self._aio(self._day(0))
        self._aio(self._day(1), available=False)
        self._aio(self._day(2))
        self._fresh(self._day(2))
        self.assertEqual(self._rank(self._day(3))["kind"], "no_op")  # only two shown observations
        self._aio(self._day(3))
        self.assertEqual(self._rank(self._day(3.5))["kind"], "escalate_uncited")
        self._aio(self._day(4), available=False)  # latest pass shows no overview: nothing to judge now
        self._fresh(self._day(4))
        self.assertEqual(self._rank(self._day(4.5))["kind"], "no_op")

    def test_one_citation_in_the_last_three_stops_the_proposal(self) -> None:
        self._aio(self._day(0))
        self._aio(self._day(1), cited=True)
        self._aio(self._day(2))
        self._fresh(self._day(2))
        self.assertEqual(self._rank(self._day(3))["kind"], "no_op")

    def test_stale_overview_stream_is_not_judged(self) -> None:
        for day in range(3):
            self._aio(self._day(day))
        self._fresh(self._day(12))  # SERP/page are fresh, the AI Overview stream is 10 days old
        self.assertEqual(self._rank(self._day(12.5))["kind"], "no_op")

    def test_proposal_doc_and_ledger_row_carry_cited_instead(self) -> None:
        pid = self._propose()
        row = decide.load_ledger(self.home)[0]
        self.assertEqual(row["details"]["cited_instead"][0], {"domain": "a.com", "observations": 3})
        doc = next((self.home / "docs").glob("*-decide-escalate-uncited-*.md")).read_text(encoding="utf-8")
        self.assertIn("## Cited instead", doc)
        self.assertIn("`a.com` (3)", doc)
        self.assertIn(f"egeo loop mark {pid} applied", doc)
        self.assertEqual(self._rank(self._day(3.1))["kind"], "wait_for_window")  # not proposed twice

    def test_citation_after_recorded_application_is_verified(self) -> None:
        pid = self._propose()
        decide.mark_row(self.home, pid, "applied", now=self._day(5))
        self._aio(self._day(12), cited=True)
        self._fresh(self._day(12))
        graded = self._step(self._day(12.5))
        self.assertEqual((graded["kind"], graded["grade"], graded["window"]), ("grade_outcome", "verified", 7))

    def test_citation_without_application_is_unattributed(self) -> None:
        self._propose()
        self._aio(self._day(9), cited=True)
        self._fresh(self._day(9))
        self.assertEqual(self._step(self._day(10.5))["grade"], "resolved_unattributed")

    def test_still_uncited_is_unchanged(self) -> None:
        self._propose()
        self._aio(self._day(9))
        self._fresh(self._day(9))
        self.assertEqual(self._step(self._day(10.5))["grade"], "unchanged")

    def test_vanished_overview_is_unobservable_not_unchanged(self) -> None:
        self._propose()
        self._aio(self._day(9), available=False)
        self._fresh(self._day(9))
        graded = self._step(self._day(10.5))
        self.assertEqual(graded["grade"], "unobservable")
        state = decide.ledger_state(decide.load_ledger(self.home))[0]
        self.assertFalse(state["closed"])  # not a result: stays open for the next window

    def test_uncited_goes_before_serp_absence(self) -> None:
        for day in range(3):
            self._aio(self._day(day))
            decide.append_jsonl(
                decide._query_stream(self.home, "what is llms.txt"),
                {"ts": self._day(day).strftime("%Y-%m-%dT%H:%M:%SZ"), "target_position": None},
            )
        for page in self.project["pages"]:
            decide.append_jsonl(
                decide._page_stream(self.home, page["url"]),
                {"ts": self._day(2).strftime("%Y-%m-%dT%H:%M:%SZ"), "jsonld_types": ["WebPage"]},
            )
        self.assertEqual(self._step(self._day(3))["kind"], "escalate_uncited")
        self.assertEqual(self._step(self._day(3.1))["kind"], "escalate_absent")


if __name__ == "__main__":
    unittest.main()
