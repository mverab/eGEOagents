"""Keenable SERP collector contract tests."""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from egeo import loop, workspace


ROOT = Path(__file__).resolve().parent.parent
FIXTURE = ROOT / "collectors" / "fixtures" / "serp_keenable_response.json"


class KeenableSerpTests(unittest.TestCase):
    def setUp(self) -> None:
        self.serp = loop.load_collector("serp")
        self.payload = json.loads(FIXTURE.read_text(encoding="utf-8"))

    def test_parse_preserves_index_order_and_caps_results(self) -> None:
        record = self.serp.parse_keenable_response(self.payload, "best geo optimization tool", "example.com")
        self.assertEqual(record["engine"], "keenable")
        self.assertEqual(len(record["results"]), 10)
        self.assertEqual(record["target_position"], 3)
        self.assertEqual(record["results"][2]["domain"], "example.com")
        self.assertEqual(record["results"][2]["position"], 3)

    def test_fetch_keyed_uses_post_search_and_api_key_header(self) -> None:
        with mock.patch.object(
            self.serp.common, "http_post", return_value=(200, json.dumps(self.payload))
        ) as request:
            self.serp.fetch_keenable("best geo tool", "keen_test_secret")
        url = request.call_args.args[0]
        payload = request.call_args.kwargs["payload"]
        headers = request.call_args.kwargs["headers"]
        self.assertEqual(url, "https://api.keenable.ai/v1/search")
        self.assertEqual(payload, {"query": "best geo tool", "max_results": 10})
        self.assertEqual(headers["X-API-Key"], "keen_test_secret")
        self.assertNotIn("X-Keenable-Title", headers)

    def test_fetch_keyless_uses_public_endpoint_and_title_header(self) -> None:
        with mock.patch.object(
            self.serp.common, "http_post", return_value=(200, json.dumps(self.payload))
        ) as request:
            self.serp.fetch_keenable("best geo tool", "")
        url = request.call_args.args[0]
        payload = request.call_args.kwargs["payload"]
        headers = request.call_args.kwargs["headers"]
        self.assertEqual(url, "https://api.keenable.ai/v1/search/public")
        self.assertEqual(payload, {"query": "best geo tool", "max_results": 10})
        self.assertEqual(headers["X-Keenable-Title"], "eGEOagents")
        self.assertNotIn("X-API-Key", headers)

    def test_failed_or_malformed_response_is_rejected(self) -> None:
        with self.assertRaises(self.serp.common.CollectorError):
            self.serp.parse_keenable_response({"error": "rate_limited"}, "q", "example.com")
        with self.assertRaises(self.serp.common.CollectorError):
            self.serp.parse_keenable_response({"results": "bad"}, "q", "example.com")
        with self.assertRaises(self.serp.common.CollectorError):
            self.serp.parse_keenable_response({"results": [{"title": "No URL"}]}, "q", "example.com")

    def test_fixture_mode_needs_no_key_or_network(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            workspace.bootstrap(home)
            with mock.patch.dict(os.environ, {"KEENABLE_API_KEY": ""}), mock.patch.object(
                self.serp.common, "http_post", side_effect=AssertionError("network request")
            ):
                result = self.serp.collect(
                    queries=["best geo optimization tool"],
                    target_domain="example.com",
                    home=home,
                    fixture=FIXTURE,
                    engine="keenable",
                )
            self.assertEqual(result["observations"][0]["target_position"], 3)
            stream = Path(result["observations"][0]["stream"])
            self.assertEqual(json.loads(stream.read_text(encoding="utf-8").splitlines()[0])["engine"], "keenable")

    def test_keyless_network_mode_runs_without_key(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            workspace.bootstrap(home)
            with mock.patch.dict(os.environ, {"KEENABLE_API_KEY": ""}), mock.patch.object(
                self.serp.common, "http_post", return_value=(200, json.dumps(self.payload))
            ) as request:
                result = self.serp.collect(
                    queries=["best geo optimization tool"],
                    target_domain="example.com",
                    home=home,
                    engine="keenable",
                )
            self.assertEqual(request.call_args.args[0], "https://api.keenable.ai/v1/search/public")
            self.assertEqual(result["observations"][0]["target_position"], 3)

    def test_doctor_reports_keenable_keyless_warning_when_key_unset(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            workspace.bootstrap(home)
            config_path = home / workspace.CONFIG_NAME
            config = config_path.read_text(encoding="utf-8")
            config_path.write_text(config.replace("  serp:\n", "  serp:\n    engine: keenable\n"), encoding="utf-8")
            with mock.patch.dict(os.environ, {"BRAVE_API_KEY": "", "KEENABLE_API_KEY": ""}):
                problems, warnings, facts = loop.diagnose(home)
            self.assertFalse(problems)
            self.assertEqual(facts["serp_engine"], "keenable")
            self.assertEqual(facts["serp_api_key_env"], "KEENABLE_API_KEY")
            self.assertFalse(facts["serp_api_key_set"])
            self.assertTrue(any("keyless public tier" in w for w in warnings))


if __name__ == "__main__":
    unittest.main()
