"""Acceptance tests for the optional Jev citation-gap evaluator.

Uses a scripted HTTP transport. Fixture answers are never labeled live/real.
"""
from __future__ import annotations

import io
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from egeo import decide, workspace
from egeo.citation_gap import (
    DEFAULT_MODEL,
    SYSTEMONE_URL,
    CitationGapError,
    ProviderError,
    api_key_configured,
    evaluate,
    render_proposal,
)
from egeo.cli import build_parser, main

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE_PROJECT = ROOT / "examples" / "project.yaml"


SECRET = "sk-test-secret-do-not-leak"


def _payload(**overrides):
    data = {
        "query": "What is the capital of France?",
        "ai_answer": {
            "text": "The capital of France is Paris.",
            "engine": "imported-test",
            "captured_at": "2026-01-15T12:00:00Z",
            "provenance": "imported",
        },
        "target": {
            "url": "https://example.com/france",
            "text": "France is a country in Europe. Paris is the capital city.",
            "captured_at": "2026-01-15T12:00:00Z",
        },
        "evidence": [
            {
                "id": "wiki-paris",
                "url": "https://example.com/source-paris",
                "text": "Paris is the capital of France.",
                "captured_at": "2026-01-15T12:00:00Z",
                "cited_in_answer": True,
            }
        ],
    }
    data.update(overrides)
    return data


def _choice(choice: str, options: tuple[str, ...], confidence: float = 0.9) -> dict:
    probabilities = {name: (1.0 if name == choice else 0.0) for name in options}
    return {
        "type": "choice",
        "choice": choice,
        "probabilities": probabilities,
        "confidence": confidence,
    }


def _jev_body(
    eid: str,
    *,
    relevance: float = 0.91,
    support: str = "supported",
    coverage: str = "covered",
    model: str = "jev-1.13.0",
    input_tokens: int = 120,
    output_tokens: int = 18,
) -> dict:
    return {
        "model": model,
        "answers": {
            f"{eid}_relevance": {"type": "noul", "noul": relevance},
            f"{eid}_support": _choice(support, ("supported", "contradicted", "insufficient")),
            f"{eid}_coverage": _choice(coverage, ("covered", "actionable_gap", "insufficient")),
        },
        "usage": {"input_tokens": input_tokens, "output_tokens": output_tokens},
    }


class ScriptedTransport:
    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = []

    def post_json(self, url, headers, body):
        self.calls.append({"url": url, "headers": dict(headers), "body": body})
        if not self._responses:
            raise AssertionError("unexpected extra TypeSafe call")
        item = self._responses.pop(0)
        if isinstance(item, BaseException):
            raise item
        return item


class CitationGapEvaluateTests(unittest.TestCase):
    def test_missing_evidence_text_abstains_without_calling_jev(self) -> None:
        transport = ScriptedTransport([])
        result = evaluate(
            _payload(evidence=[{"id": "empty", "url": "https://example.com/x", "text": "  "}]),
            transport=transport,
        )
        self.assertEqual(transport.calls, [])
        self.assertEqual(result["evaluation"]["source"], "none")
        self.assertIsNone(result["evaluation"]["model"])
        self.assertIsNone(result["evaluation"]["usage"])
        self.assertIsNone(result["evaluation"]["cost"])
        finding = result["findings"][0]
        self.assertEqual(finding["group"], "insufficient")
        self.assertTrue(finding["abstained"])
        self.assertEqual(finding["reason"], "missing_text")
        self.assertEqual(result["proposed_actions"], [])
        self.assertFalse(result["auto_apply"])
        self.assertNotIn("evaluation_source", result)

    def test_missing_target_text_abstains_all_evidence(self) -> None:
        transport = ScriptedTransport([])
        result = evaluate(
            _payload(target={"url": "https://example.com/france", "text": ""}),
            transport=transport,
        )
        self.assertEqual(transport.calls, [])
        self.assertEqual(result["findings"][0]["group"], "insufficient")
        self.assertEqual(result["findings"][0]["reason"], "missing_text")
        self.assertEqual(result["proposed_actions"], [])

    def test_empty_ai_answer_abstains_without_calling_jev(self) -> None:
        transport = ScriptedTransport([])
        result = evaluate(
            _payload(ai_answer={"text": "", "provenance": "imported"}),
            transport=transport,
        )
        self.assertEqual(transport.calls, [])
        self.assertTrue(result["findings"][0]["abstained"])

    def test_invalid_evidence_rejected(self) -> None:
        with self.assertRaises(CitationGapError):
            evaluate(_payload(evidence=[{"text": "Paris is the capital of France."}]))
        with self.assertRaises(CitationGapError):
            evaluate(_payload(query=""))
        with self.assertRaises(CitationGapError):
            evaluate(_payload(evidence="not-a-list"))

    def test_covered_finding_keeps_fragments_and_does_not_propose(self) -> None:
        transport = ScriptedTransport([(200, _jev_body("wiki-paris", coverage="covered"))])
        result = evaluate(_payload(), transport=transport)
        finding = result["findings"][0]
        self.assertEqual(finding["group"], "covered")
        self.assertFalse(finding["abstained"])
        self.assertEqual(finding["source_fragment"], "Paris is the capital of France.")
        self.assertIn("Paris is the capital city", finding["target_fragment"])
        self.assertEqual(finding["source_url"], "https://example.com/source-paris")
        self.assertEqual(finding["captured_at"], "2026-01-15T12:00:00Z")
        self.assertEqual(finding["relevance"]["noul"], 0.91)
        self.assertEqual(finding["support"]["choice"], "supported")
        self.assertEqual(finding["coverage"]["choice"], "covered")
        self.assertEqual(result["proposed_actions"], [])
        self.assertEqual(result["evaluation"]["model"], "jev-1.13.0")
        self.assertEqual(result["evaluation"]["requested_model"], DEFAULT_MODEL)
        self.assertEqual(result["evaluation"]["usage"]["input_tokens"], 120)
        self.assertIsInstance(result["evaluation"]["elapsed_ms"], int)
        self.assertGreaterEqual(result["evaluation"]["elapsed_ms"], 0)
        self.assertIsNone(result["evaluation"]["cost"])
        self.assertEqual(result["evaluation"]["source"], "test_transport")
        self.assertNotEqual(result["evaluation"]["source"], "live_api")
        self.assertEqual(transport.calls[0]["url"], SYSTEMONE_URL)
        body = transport.calls[0]["body"]
        self.assertEqual(set(body), {"state", "model", "questions"})
        self.assertEqual(body["model"], DEFAULT_MODEL)
        self.assertEqual(body["questions"]["wiki-paris_relevance"]["type"], "noul")
        self.assertEqual(body["questions"]["wiki-paris_support"]["type"], "choice")
        self.assertEqual(body["questions"]["wiki-paris_coverage"]["type"], "choice")

    def test_actionable_gap_requests_first_party_facts_without_copying_source(self) -> None:
        payload = _payload(
            query_id="generic-geo-evaluation",
            page_id="home",
            target={
                "url": "https://example.com/france",
                "text": "France is a country in Europe.",
                "captured_at": "2026-01-15T12:00:00Z",
            },
        )
        transport = ScriptedTransport(
            [(200, _jev_body("wiki-paris", coverage="actionable_gap", support="supported"))]
        )
        result = evaluate(payload, transport=transport)
        finding = result["findings"][0]
        self.assertEqual(finding["group"], "actionable")
        self.assertFalse(finding["abstained"])
        self.assertEqual(len(result["proposed_actions"]), 1)
        action = result["proposed_actions"][0]
        self.assertEqual(action["kind"], "propose_citation_gap")
        self.assertFalse(action["auto_apply"])
        self.assertEqual(action["next_gate"], "owner")
        self.assertEqual(action["finding_id"], "wiki-paris")
        self.assertEqual(action["query_ids"], ["generic-geo-evaluation"])
        self.assertEqual(action["page_ids"], ["home"])
        self.assertIsNone(action["diff"])
        dumped = json.dumps(action)
        self.assertNotIn("Paris is the capital of France.", dumped)
        self.assertIn("first-party", action["reason"])

    def test_low_relevance_is_insufficient_not_actionable(self) -> None:
        transport = ScriptedTransport(
            [(200, _jev_body("wiki-paris", relevance=0.12, coverage="actionable_gap"))]
        )
        result = evaluate(_payload(), transport=transport)
        finding = result["findings"][0]
        self.assertEqual(finding["group"], "insufficient")
        self.assertTrue(finding["abstained"])
        self.assertEqual(finding["reason"], "irrelevant")
        self.assertEqual(result["proposed_actions"], [])

    def test_contradicted_and_insufficient_support_do_not_propose(self) -> None:
        payload = _payload(
            evidence=[
                {
                    "id": "contra",
                    "url": "https://example.com/a",
                    "text": "Lyon is the capital of France.",
                    "captured_at": "2026-01-15T12:00:00Z",
                    "cited_in_answer": True,
                },
                {
                    "id": "weak",
                    "url": "https://example.com/b",
                    "text": "France has cities.",
                    "captured_at": "2026-01-15T12:00:00Z",
                    "cited_in_answer": True,
                },
            ]
        )
        transport = ScriptedTransport(
            [
                (200, _jev_body("contra", support="contradicted", coverage="actionable_gap")),
                (200, _jev_body("weak", support="insufficient", coverage="actionable_gap")),
            ]
        )
        result = evaluate(payload, transport=transport)
        reasons = {item["id"]: item["reason"] for item in result["findings"]}
        self.assertEqual(reasons["contra"], "contradicted")
        self.assertEqual(reasons["weak"], "insufficient_evidence")
        self.assertTrue(all(item["group"] == "insufficient" for item in result["findings"]))
        self.assertEqual(result["proposed_actions"], [])

    def test_spanish_fragments_are_preserved(self) -> None:
        payload = _payload(
            query="¿Cuál es la capital de Francia?",
            ai_answer={
                "text": "La capital de Francia es París.",
                "engine": "imported-test",
                "captured_at": "2026-01-15T12:00:00Z",
                "provenance": "imported",
            },
            target={
                "url": "https://example.com/francia",
                "text": "Francia es un país de Europa.",
                "captured_at": "2026-01-15T12:00:00Z",
            },
            evidence=[
                {
                    "id": "fuente",
                    "url": "https://example.com/paris",
                    "text": "París es la capital de Francia.",
                    "captured_at": "2026-01-15T12:00:00Z",
                    "cited_in_answer": True,
                }
            ],
        )
        transport = ScriptedTransport(
            [(200, _jev_body("fuente", coverage="actionable_gap"))]
        )
        result = evaluate(payload, transport=transport)
        self.assertEqual(result["query"], "¿Cuál es la capital de Francia?")
        self.assertEqual(result["findings"][0]["source_fragment"], "París es la capital de Francia.")
        self.assertEqual(result["findings"][0]["target_fragment"], "Francia es un país de Europa.")
        self.assertIsNone(result["proposed_actions"][0]["diff"])
        self.assertNotIn("París es la capital de Francia.", json.dumps(result["proposed_actions"]))

    def test_invalid_noul_and_choice_are_provider_failures(self) -> None:
        bad_noul = _jev_body("wiki-paris")
        bad_noul["answers"]["wiki-paris_relevance"]["noul"] = 1.7
        with self.assertRaises(ProviderError):
            evaluate(_payload(), transport=ScriptedTransport([(200, bad_noul)]))

        bad_choice = _jev_body("wiki-paris")
        bad_choice["answers"]["wiki-paris_support"]["choice"] = "maybe"
        with self.assertRaises(ProviderError):
            evaluate(_payload(), transport=ScriptedTransport([(200, bad_choice)]))

        bad_prob = _jev_body("wiki-paris")
        bad_prob["answers"]["wiki-paris_coverage"]["probabilities"] = {
            "covered": 0.2,
            "actionable_gap": 0.2,
            "insufficient": 0.2,
        }
        with self.assertRaises(ProviderError):
            evaluate(_payload(), transport=ScriptedTransport([(200, bad_prob)]))

    def test_http_error_is_provider_failure_without_fallback_scores(self) -> None:
        with self.assertRaises(ProviderError):
            evaluate(_payload(), transport=ScriptedTransport([(401, {"error": "unauthorized"})]))
        with self.assertRaises(ProviderError):
            evaluate(_payload(), transport=ScriptedTransport([(429, {"error": "rate"})]))
        with self.assertRaises(ProviderError):
            evaluate(
                _payload(),
                transport=ScriptedTransport([OSError("connection refused")]),
            )

    def test_missing_key_without_transport_does_not_invent_scores(self) -> None:
        env = {k: v for k, v in os.environ.items() if k != "TYPESAFE_API_KEY"}
        env["GEO_EVAL_MOCK"] = "1"
        with mock.patch.dict(os.environ, env, clear=True):
            self.assertFalse(api_key_configured())
            with self.assertRaises(CitationGapError) as ctx:
                evaluate(_payload())
            self.assertIn("TYPESAFE_API_KEY", str(ctx.exception))

    def test_result_never_contains_credentials(self) -> None:
        transport = ScriptedTransport([(200, _jev_body("wiki-paris"))])
        with mock.patch.dict(os.environ, {"TYPESAFE_API_KEY": SECRET}):
            result = evaluate(_payload(), transport=transport)
        dumped = json.dumps(result)
        self.assertNotIn(SECRET, dumped)
        self.assertNotIn("api_key", dumped.lower())
        self.assertNotIn("authorization", dumped.lower())
        self.assertTrue(result["notes"])
        self.assertFalse(result["auto_apply"])

    def test_proposal_markdown_requires_owner_and_never_applies(self) -> None:
        transport = ScriptedTransport(
            [(200, _jev_body("wiki-paris", coverage="actionable_gap"))]
        )
        result = evaluate(
            _payload(target={"url": "https://example.com/france", "text": "France is in Europe.", "captured_at": "2026-01-15T12:00:00Z"}),
            transport=transport,
        )
        markdown = render_proposal(result)
        self.assertIn("auto_apply: `false`", markdown)
        self.assertIn("Owner must approve", markdown)
        self.assertIn("first-party", markdown)
        self.assertNotIn("Paris is the capital of France.", markdown)
        self.assertNotIn(SECRET, markdown)

    def test_uncertain_relevance_and_low_choice_confidence_abstain(self) -> None:
        body = _jev_body("wiki-paris", relevance=0.5, coverage="actionable_gap")
        body["answers"]["wiki-paris_support"].update(
            probabilities={"supported": 0.34, "contradicted": 0.33, "insufficient": 0.33},
            confidence=0.01,
        )
        body["answers"]["wiki-paris_coverage"].update(
            probabilities={"covered": 0.33, "actionable_gap": 0.34, "insufficient": 0.33},
            confidence=0.01,
        )
        result = evaluate(_payload(), transport=ScriptedTransport([(200, body)]))
        finding = result["findings"][0]
        self.assertEqual(finding["group"], "insufficient")
        self.assertTrue(finding["abstained"])
        self.assertEqual(finding["reason"], "uncertain")
        self.assertEqual(result["proposed_actions"], [])

    def test_boundary_choice_confidence_does_not_clear_gate(self) -> None:
        body = _jev_body("wiki-paris", relevance=0.91, coverage="actionable_gap")
        body["answers"]["wiki-paris_support"]["confidence"] = 0.5
        body["answers"]["wiki-paris_coverage"]["confidence"] = 0.5
        result = evaluate(_payload(), transport=ScriptedTransport([(200, body)]))
        self.assertEqual(result["findings"][0]["group"], "insufficient")
        self.assertEqual(result["findings"][0]["reason"], "uncertain")
        self.assertEqual(result["proposed_actions"], [])

    def test_missing_provenance_never_becomes_actionable(self) -> None:
        transport = ScriptedTransport([])
        result = evaluate(
            {
                "query": "q",
                "ai_answer": {"text": "claim"},
                "target": {"text": "target"},
                "evidence": [{"id": "e", "text": "claim"}],
            },
            transport=transport,
        )
        self.assertEqual(transport.calls, [])
        self.assertEqual(result["findings"][0]["group"], "insufficient")
        self.assertTrue(result["findings"][0]["abstained"])
        self.assertEqual(result["findings"][0]["reason"], "missing_provenance")
        self.assertEqual(result["proposed_actions"], [])

    def test_unlinked_citation_abstains(self) -> None:
        payload = _payload()
        payload["evidence"][0]["cited_in_answer"] = False
        result = evaluate(payload, transport=ScriptedTransport([]))
        self.assertEqual(result["findings"][0]["reason"], "unlinked_citation")
        self.assertEqual(result["findings"][0]["group"], "insufficient")
        self.assertEqual(result["proposed_actions"], [])

    def test_non_http_url_and_bad_timestamp_abstain(self) -> None:
        payload = _payload(
            evidence=[
                {
                    "id": "bad",
                    "url": "javascript:alert(1)",
                    "text": "Paris is the capital of France.",
                    "captured_at": "not-a-timestamp",
                    "cited_in_answer": True,
                }
            ]
        )
        result = evaluate(payload, transport=ScriptedTransport([]))
        self.assertEqual(result["findings"][0]["reason"], "missing_provenance")
        self.assertEqual(result["proposed_actions"], [])

    def test_incomplete_usage_is_unknown_not_partial_sum(self) -> None:
        payload = _payload(
            evidence=[
                {
                    "id": "a",
                    "url": "https://example.com/a",
                    "text": "Paris is the capital of France.",
                    "captured_at": "2026-01-15T12:00:00Z",
                    "cited_in_answer": True,
                },
                {
                    "id": "b",
                    "url": "https://example.com/b",
                    "text": "Paris is the capital of France.",
                    "captured_at": "2026-01-15T12:00:00Z",
                    "cited_in_answer": True,
                },
            ]
        )
        first = _jev_body("a", input_tokens=10, output_tokens=2)
        second = _jev_body("b")
        del second["usage"]
        result = evaluate(payload, transport=ScriptedTransport([(200, first), (200, second)]))
        self.assertIsNone(result["evaluation"]["usage"])

    def test_records_owner_gated_ledger_without_applying(self) -> None:
        payload = _payload(
            query_id="generic-geo-evaluation",
            page_id="home",
            target={
                "url": "https://example.com/france",
                "text": "France is in Europe.",
                "captured_at": "2026-01-15T12:00:00Z",
            },
        )
        transport = ScriptedTransport(
            [(200, _jev_body("wiki-paris", coverage="actionable_gap"))]
        )
        result = evaluate(payload, transport=transport)
        home = Path(tempfile.mkdtemp(prefix="egeo-cg-"))
        try:
            shutil.copy(EXAMPLE_PROJECT, home / workspace.PROJECT_CONFIG_NAME)
            workspace.bootstrap(home)
            project = workspace.load_project_config(home)
            persisted = decide.apply_decision(home, project, result["proposed_actions"][0])
            row = persisted["ledger_row"]
            self.assertEqual(row["kind"], "propose_citation_gap")
            self.assertEqual(row["status"], "proposed")
            self.assertFalse(row["auto_apply"])
            self.assertEqual(row["next_gate"], "owner")
            self.assertEqual(row["query_ids"], ["generic-geo-evaluation"])
            self.assertEqual(row["page_ids"], ["home"])
            self.assertIn("wiki-paris", row["evidence"])
            self.assertTrue(any(str(item).startswith("docs/") for item in persisted["written"]))
            self.assertNotEqual(row["status"], "applied")
        finally:
            shutil.rmtree(home)

    def _record_home(self, tmp_path: Path) -> Path:
        home = tmp_path / "home"
        home.mkdir()
        shutil.copy(EXAMPLE_PROJECT, home / workspace.PROJECT_CONFIG_NAME)
        workspace.bootstrap(home)
        return home

    def test_record_requires_and_validates_project_refs(self) -> None:
        from egeo.citation_gap import run_from_path

        transport = ScriptedTransport(
            [(200, _jev_body("wiki-paris", coverage="actionable_gap"))]
        )
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            home = self._record_home(tmp_path)
            src = tmp_path / "in.json"
            src.write_text(json.dumps(_payload(
                target={"url": "https://example.com/france", "text": "France is in Europe.", "captured_at": "2026-01-15T12:00:00Z"},
            )), encoding="utf-8")
            env = {**os.environ, "EGEO_HOME": str(home), "TYPESAFE_API_KEY": SECRET}
            with mock.patch.dict(os.environ, env, clear=True):
                with mock.patch("egeo.citation_gap.StdlibTransport", return_value=transport):
                    with self.assertRaises(CitationGapError) as ctx:
                        run_from_path(src, record=True)
            self.assertIn("query_id", str(ctx.exception))
            self.assertEqual(decide.load_ledger(home), [])

            src.write_text(json.dumps(_payload(
                query_id="not-in-project",
                page_id="home",
                target={"url": "https://example.com/france", "text": "France is in Europe.", "captured_at": "2026-01-15T12:00:00Z"},
            )), encoding="utf-8")
            transport = ScriptedTransport(
                [(200, _jev_body("wiki-paris", coverage="actionable_gap"))]
            )
            with mock.patch.dict(os.environ, env, clear=True):
                with mock.patch("egeo.citation_gap.StdlibTransport", return_value=transport):
                    with self.assertRaises(CitationGapError) as ctx:
                        run_from_path(src, record=True)
            self.assertIn("query_id", str(ctx.exception))
            self.assertEqual(decide.load_ledger(home), [])

    def test_record_persists_all_actionable_findings_and_dedupes_open_row(self) -> None:
        from egeo.citation_gap import run_from_path

        payload = _payload(
            query_id="generic-geo-evaluation",
            page_id="home",
            target={"url": "https://example.com/france", "text": "France is in Europe.", "captured_at": "2026-01-15T12:00:00Z"},
            evidence=[
                {
                    "id": "a",
                    "url": "https://example.com/a",
                    "text": "Paris is the capital of France.",
                    "captured_at": "2026-01-15T12:00:00Z",
                    "cited_in_answer": True,
                },
                {
                    "id": "b",
                    "url": "https://example.com/b",
                    "text": "Paris has more than two million residents.",
                    "captured_at": "2026-01-15T12:00:00Z",
                    "cited_in_answer": True,
                },
            ],
        )
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            home = self._record_home(tmp_path)
            src = tmp_path / "in.json"
            src.write_text(json.dumps(payload), encoding="utf-8")
            env = {**os.environ, "EGEO_HOME": str(home), "TYPESAFE_API_KEY": SECRET}
            first = ScriptedTransport(
                [
                    (200, _jev_body("a", coverage="actionable_gap")),
                    (200, _jev_body("b", coverage="actionable_gap")),
                ]
            )
            with mock.patch.dict(os.environ, env, clear=True):
                with mock.patch("egeo.citation_gap.StdlibTransport", return_value=first):
                    run_from_path(src, record=True)
            ledger = decide.load_ledger(home)
            self.assertEqual(len(ledger), 1)
            self.assertEqual(ledger[0]["kind"], "propose_citation_gap")
            self.assertEqual(ledger[0]["status"], "proposed")
            self.assertFalse(ledger[0]["auto_apply"])
            self.assertIn("a", ledger[0]["evidence"])
            self.assertIn("b", ledger[0]["evidence"])
            first_id = ledger[0]["id"]
            second = ScriptedTransport(
                [
                    (200, _jev_body("a", coverage="actionable_gap")),
                    (200, _jev_body("b", coverage="actionable_gap")),
                ]
            )
            with mock.patch.dict(os.environ, env, clear=True):
                with mock.patch("egeo.citation_gap.StdlibTransport", return_value=second):
                    run_from_path(src, record=True)
            ledger = decide.load_ledger(home)
            self.assertEqual(len(ledger), 1)
            self.assertEqual(ledger[0]["id"], first_id)


class CitationGapCliTests(unittest.TestCase):
    def test_parser_exposes_citation_gap_entrypoint(self) -> None:
        args = build_parser().parse_args(
            ["citation-gap", "--input", "run.json", "--out", "out.json"]
        )
        self.assertEqual(args.cmd, "citation-gap")
        self.assertEqual(args.input, "run.json")
        self.assertEqual(args.out, "out.json")

    def test_cli_missing_text_writes_result_without_key(self) -> None:
        payload = _payload(evidence=[{"id": "e1", "url": "https://example.com/x", "text": ""}])
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            src = tmp_path / "in.json"
            out = tmp_path / "out.json"
            src.write_text(json.dumps(payload), encoding="utf-8")
            env = {k: v for k, v in os.environ.items() if k != "TYPESAFE_API_KEY"}
            with mock.patch.dict(os.environ, env, clear=True):
                code = main(["citation-gap", "--input", str(src), "--out", str(out)])
            self.assertEqual(code, 0)
            result = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(result["findings"][0]["reason"], "missing_text")
            self.assertEqual(result["evaluation"]["source"], "none")

    def test_cli_missing_key_exits_without_writing_fake_scores(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            src = tmp_path / "in.json"
            out = tmp_path / "out.json"
            src.write_text(json.dumps(_payload()), encoding="utf-8")
            env = {k: v for k, v in os.environ.items() if k != "TYPESAFE_API_KEY"}
            buf = io.StringIO()
            with mock.patch.dict(os.environ, env, clear=True):
                with mock.patch("sys.stderr", buf):
                    code = main(["citation-gap", "--input", str(src), "--out", str(out)])
            self.assertEqual(code, 2)
            self.assertFalse(out.exists())
            self.assertIn("TYPESAFE_API_KEY", buf.getvalue())
            self.assertNotIn(SECRET, buf.getvalue())

    def test_cli_records_into_existing_ledger_when_requested(self) -> None:
        payload = _payload(
            query_id="generic-geo-evaluation",
            page_id="home",
            target={"url": "https://example.com/france", "text": "France is in Europe.", "captured_at": "2026-01-15T12:00:00Z"},
        )
        transport = ScriptedTransport(
            [(200, _jev_body("wiki-paris", coverage="actionable_gap"))]
        )
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            home = tmp_path / "home"
            home.mkdir()
            shutil.copy(EXAMPLE_PROJECT, home / workspace.PROJECT_CONFIG_NAME)
            workspace.bootstrap(home)
            src = tmp_path / "in.json"
            out = tmp_path / "out.json"
            src.write_text(json.dumps(payload), encoding="utf-8")
            env = {k: v for k, v in os.environ.items() if k != "TYPESAFE_API_KEY"}
            env["TYPESAFE_API_KEY"] = SECRET
            env["EGEO_HOME"] = str(home)
            with mock.patch("egeo.citation_gap.StdlibTransport", return_value=transport):
                with mock.patch.dict(os.environ, env, clear=True):
                    code = main(
                        [
                            "citation-gap",
                            "--input",
                            str(src),
                            "--out",
                            str(out),
                            "--record",
                        ]
                    )
            self.assertEqual(code, 0)
            result = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(result["evaluation"]["source"], "test_transport")
            self.assertIsNone(result["proposed_actions"][0]["diff"])
            ledger = decide.load_ledger(home)
            self.assertEqual(len(ledger), 1)
            self.assertEqual(ledger[0]["kind"], "propose_citation_gap")
            self.assertEqual(ledger[0]["status"], "proposed")
            self.assertFalse(ledger[0]["auto_apply"])
            self.assertTrue(list((home / "docs").glob("*.md")))
            self.assertNotIn(SECRET, out.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
