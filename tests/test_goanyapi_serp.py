"""GoAnyAPI SERP provider contract tests."""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock
from urllib.parse import parse_qs, urlparse

from egeo import loop, workspace


ROOT = Path(__file__).resolve().parent.parent
FIXTURE = ROOT / "collectors" / "fixtures" / "serp_goanyapi_response.json"


class GoAnyApiSerpTests(unittest.TestCase):
    def setUp(self) -> None:
        self.serp = loop.load_collector("serp")
        self.payload = json.loads(FIXTURE.read_text(encoding="utf-8"))

    def test_parse_preserves_organic_rank_and_caps_results(self) -> None:
        record = self.serp.parse_goanyapi_response(self.payload, "best geo optimization tool", "example.com")
        self.assertEqual(record["engine"], "goanyapi")
        self.assertEqual(len(record["results"]), 10)
        self.assertEqual(record["target_position"], 3)
        self.assertEqual(record["results"][2]["domain"], "example.com")
        self.assertEqual(record["results"][2]["position"], 3)

    def test_fetch_uses_bearer_header_and_documented_parameters(self) -> None:
        with mock.patch.object(
            self.serp.common, "http_get", return_value=(200, json.dumps(self.payload))
        ) as request:
            self.serp.fetch_goanyapi("best geo tool", "test-secret")
        url = request.call_args.args[0]
        headers = request.call_args.kwargs["headers"]
        self.assertEqual(urlparse(url).path, "/api/v1/serp")
        self.assertEqual(parse_qs(urlparse(url).query), {
            "q": ["best geo tool"], "gl": ["us"], "hl": ["en"], "search_type": ["web"]
        })
        self.assertNotIn("test-secret", url)
        self.assertEqual(headers["Authorization"], "Bearer test-secret")

    def test_failed_or_malformed_response_is_rejected(self) -> None:
        with self.assertRaises(self.serp.common.CollectorError):
            self.serp.parse_goanyapi_response({"code": "insufficient_credits"}, "q", "example.com")
        with self.assertRaises(self.serp.common.CollectorError):
            self.serp.parse_goanyapi_response({"code": "ok", "data": {}}, "q", "example.com")
        with self.assertRaises(self.serp.common.CollectorError):
            self.serp.parse_goanyapi_response(
                {"code": "ok", "data": {"result": {"organic": [{"link": "https://example.com", "rank": "bad"}]}}},
                "q", "example.com"
            )

    def test_fixture_mode_needs_no_key_or_network(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            workspace.bootstrap(home)
            with mock.patch.dict(os.environ, {"GOANYAPI_API_KEY": ""}), mock.patch.object(
                self.serp.common, "http_get", side_effect=AssertionError("network request")
            ):
                result = self.serp.collect(
                    queries=["best geo optimization tool"],
                    target_domain="example.com",
                    home=home,
                    fixture=FIXTURE,
                    engine="goanyapi",
                )
            self.assertEqual(result["observations"][0]["target_position"], 3)
            stream = Path(result["observations"][0]["stream"])
            self.assertEqual(json.loads(stream.read_text(encoding="utf-8").splitlines()[0])["engine"], "goanyapi")

    def test_missing_key_fails_before_writing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            workspace.bootstrap(home)
            with mock.patch.dict(os.environ, {"GOANYAPI_API_KEY": ""}):
                with self.assertRaisesRegex(self.serp.common.CollectorError, "GOANYAPI_API_KEY"):
                    self.serp.collect(
                        queries=["best geo optimization tool"],
                        target_domain="example.com",
                        home=home,
                        engine="goanyapi",
                    )
            self.assertFalse(list((home / "data" / "serp").glob("*.jsonl")))

    def test_doctor_checks_selected_provider_key(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            workspace.bootstrap(home)
            config_path = home / workspace.CONFIG_NAME
            config = config_path.read_text(encoding="utf-8")
            config_path.write_text(config.replace("  serp:\n", "  serp:\n    engine: goanyapi\n"), encoding="utf-8")
            with mock.patch.dict(os.environ, {"BRAVE_API_KEY": "", "GOANYAPI_API_KEY": "test-secret"}):
                problems, warnings, facts = loop.diagnose(home)
            self.assertFalse(problems)
            self.assertEqual(facts["serp_engine"], "goanyapi")
            self.assertEqual(facts["serp_api_key_env"], "GOANYAPI_API_KEY")
            self.assertTrue(facts["serp_api_key_set"])
            self.assertFalse(any("BRAVE_API_KEY is not set" in warning for warning in warnings))


if __name__ == "__main__":
    unittest.main()
