"""Monid (Search1API) SERP provider contract tests."""

from __future__ import annotations

import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

from egeo import loop, workspace


ROOT = Path(__file__).resolve().parent.parent
FIXTURE = ROOT / "collectors" / "fixtures" / "serp_monid_response.json"
QUERY = "generative engine optimization"


class MonidSerpTests(unittest.TestCase):
    def setUp(self) -> None:
        self.serp = loop.load_collector("serp")
        self.payload = json.loads(FIXTURE.read_text(encoding="utf-8"))

    def run_body(self, **changes) -> dict:
        return {**self.payload, **changes}

    def test_parse_keeps_result_order_and_caps_results(self) -> None:
        record = self.serp.parse_monid_response(self.payload, QUERY, "arxiv.org")
        self.assertEqual(record["engine"], "monid")
        self.assertEqual([item["position"] for item in record["results"]], list(range(1, 11)))
        self.assertEqual(record["results"][0]["domain"], "en.wikipedia.org")
        self.assertEqual(record["target_position"], 4)
        many = self.run_body(output={"results": [{"link": f"https://site{i}.example/", "title": ""} for i in range(12)]})
        self.assertEqual(len(self.serp.parse_monid_response(many, QUERY, "")["results"]), 10)

    def test_fetch_runs_search1api_through_monid_with_bearer_key(self) -> None:
        with mock.patch.object(self.serp.common, "http_post", return_value=(200, json.dumps(self.payload))) as post, \
                mock.patch.object(self.serp.common, "http_get", side_effect=AssertionError("unexpected GET")):
            self.assertEqual(self.serp.fetch_monid(QUERY, "test-secret"), self.payload)
        self.assertEqual(post.call_args.args, ("https://api.monid.ai/v1/run",))
        self.assertEqual(post.call_args.kwargs["payload"], {
            "provider": "search1api",
            "endpoint": "/search",
            "input": {"body": {"query": QUERY, "max_results": 10, "search_service": "google"}},
        })
        self.assertEqual(post.call_args.kwargs["headers"]["Authorization"], "Bearer test-secret")
        self.assertNotIn("test-secret", json.dumps(post.call_args.kwargs["payload"]))

    def test_unfinished_run_is_read_until_it_ends(self) -> None:
        with mock.patch.object(self.serp.common, "http_post", return_value=(202, '{"runId": "r 1", "status": "RUNNING"}')), \
                mock.patch.object(self.serp.common, "http_get", side_effect=[
                    (200, '{"runId": "r 1", "status": "RUNNING"}'), (200, json.dumps(self.payload))]) as get, \
                mock.patch.object(self.serp.time, "sleep"):
            self.assertEqual(self.serp.fetch_monid(QUERY, "test-secret")["status"], "COMPLETED")
        self.assertEqual([call.args[0] for call in get.call_args_list], ["https://api.monid.ai/v1/runs/r%201"] * 2)
        with mock.patch.object(self.serp.common, "http_post", return_value=(202, '{"runId": "r1", "status": "RUNNING"}')), \
                mock.patch.object(self.serp, "MONID_RUN_TIMEOUT_SECONDS", 0):
            with self.assertRaisesRegex(self.serp.common.CollectorError, "did not finish"):
                self.serp.fetch_monid(QUERY, "test-secret")

    def test_errors_name_monid_and_its_key(self) -> None:
        cases = [
            ((401, '{"error": "unauthorized"}'), r"Monid API rejected the request \(HTTP 401\)\. Check \$MONID_API_KEY"),
            ((429, "{}"), "Monid API rate limit hit"),
            ((200, json.dumps(self.run_body(providerResponse={"httpStatus": 429}))), "Search1API rate limit hit through Monid"),
            ((200, json.dumps(self.run_body(providerResponse={"httpStatus": 500, "error": "upstream down"}))),
             "Search1API returned HTTP 500 through Monid .*upstream down"),
        ]
        for answer, message in cases:
            with self.subTest(message=message), mock.patch.object(self.serp.common, "http_post", return_value=answer):
                with self.assertRaisesRegex(self.serp.common.CollectorError, message) as raised:
                    self.serp.parse_monid_response(self.serp.fetch_monid(QUERY, "test-secret"), QUERY, "")
                self.assertNotIn("Brave", str(raised.exception))

    def test_failed_or_malformed_run_is_rejected(self) -> None:
        bad = [
            self.run_body(status="FAILED"),
            self.run_body(status="BLOCKED", reason="insufficient wallet balance"),
            self.run_body(providerResponse={"httpStatus": "200"}),
            self.run_body(providerResponse=[]),
            self.run_body(output=None),
            self.run_body(output={"results": {}}),
            self.run_body(output={"results": [{"title": "no link"}]}),
        ]
        for index, payload in enumerate(bad):
            with self.subTest(case=index):
                with self.assertRaises(self.serp.common.CollectorError):
                    self.serp.parse_monid_response(payload, QUERY, "")

    def test_fixture_mode_needs_no_key_or_network(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.dict(os.environ, {"EGEO_HOME": tmp, "MONID_API_KEY": ""}), \
                    mock.patch.object(self.serp.common, "http_post", side_effect=AssertionError("network request")), \
                    mock.patch.object(self.serp.common, "http_get", side_effect=AssertionError("network request")), \
                    redirect_stdout(io.StringIO()):
                code = self.serp.main(["--engine", "monid", "--fixture", str(FIXTURE), "--query", QUERY,
                                       "--target-domain", "arxiv.org"])
            self.assertEqual(code, 0)
            record = json.loads((Path(tmp) / "data" / "serp" / "generative-engine-optimization.jsonl").read_text(encoding="utf-8"))
            self.assertEqual((record["engine"], record["target_position"], len(record["results"])), ("monid", 4, 10))

    def test_missing_key_fails_before_writing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            workspace.bootstrap(home)
            with mock.patch.dict(os.environ, {"MONID_API_KEY": "", "BRAVE_API_KEY": "brave-secret"}):
                with self.assertRaisesRegex(self.serp.common.CollectorError, "MONID_API_KEY"):
                    self.serp.collect(queries=[QUERY], target_domain="example.com", home=home, engine="monid")
            self.assertFalse(list((home / "data" / "serp").glob("*.jsonl")))

    def test_brave_engine_never_uses_the_monid_key(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            workspace.bootstrap(home)
            with mock.patch.dict(os.environ, {"MONID_API_KEY": "monid-secret", "BRAVE_API_KEY": ""}):
                with self.assertRaisesRegex(self.serp.common.CollectorError, "BRAVE_API_KEY"):
                    self.serp.collect(queries=[QUERY], target_domain="example.com", home=home)
            with mock.patch.dict(os.environ, {"MONID_API_KEY": "monid-secret", "BRAVE_API_KEY": "brave-secret"}), \
                    mock.patch.object(self.serp.common, "http_post", side_effect=AssertionError("unexpected POST")), \
                    mock.patch.object(self.serp.common, "http_get", return_value=(200, '{"web": {"results": []}}')) as get:
                self.serp.collect(queries=[QUERY], target_domain="example.com", home=home)
            self.assertTrue(get.call_args.args[0].startswith("https://api.search.brave.com/"))
            record = json.loads((home / "data" / "serp" / "generative-engine-optimization.jsonl").read_text(encoding="utf-8"))
            self.assertEqual(record["engine"], "brave")

    def test_doctor_checks_the_monid_key(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            workspace.bootstrap(home)
            config_path = home / workspace.CONFIG_NAME
            config = config_path.read_text(encoding="utf-8")
            config_path.write_text(config.replace("  serp:\n", "  serp:\n    engine: monid\n"), encoding="utf-8")
            with mock.patch.dict(os.environ, {"BRAVE_API_KEY": "", "MONID_API_KEY": "test-secret"}):
                problems, warnings, facts = loop.diagnose(home)
            self.assertFalse(problems)
            self.assertEqual((facts["serp_engine"], facts["serp_api_key_env"], facts["serp_api_key_set"]),
                             ("monid", "MONID_API_KEY", True))
            self.assertFalse(any("BRAVE_API_KEY is not set" in warning for warning in warnings))
            with mock.patch.dict(os.environ, {"BRAVE_API_KEY": "", "MONID_API_KEY": ""}):
                problems, warnings, facts = loop.diagnose(home)
            self.assertFalse(facts["serp_api_key_set"])
            self.assertTrue(any("MONID_API_KEY is not set" in warning for warning in warnings))


if __name__ == "__main__":
    unittest.main()
