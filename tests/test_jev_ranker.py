import json
import os
import unittest
from unittest.mock import patch

from egeo.jev_ranker import RankerConfigError, RankerProviderError, order_candidates, rank_dataset
from geo_eval import Candidate, _rank_candidates


class ScriptedTransport:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def post_json(self, url, body):
        self.calls.append({"url": url, "body": body})
        status, payload = self.responses.pop(0)
        return status, payload


def _noul_body(scores, model="jev-1.13.0"):
    answers = {cid: {"type": "noul", "noul": value} for cid, value in scores.items()}
    return {
        "model": model,
        "answers": answers,
        "usage": {"input_tokens": 100, "output_tokens": 30},
    }


class JevRankerTests(unittest.TestCase):
    def test_orders_by_noul_descending(self):
        transport = ScriptedTransport(
            [(200, _noul_body({"p1": 0.2, "p2": 0.9, "p3": 0.5}))]
        )
        result = order_candidates(
            "best lightweight laptop",
            [
                {"id": "p1", "title": "heavy", "description": "2kg"},
                {"id": "p2", "title": "light", "description": "900g"},
                {"id": "p3", "title": "mid", "description": "1.4kg"},
            ],
            transport=transport,
        )
        self.assertEqual(result["ordered_ids"], ["p2", "p3", "p1"])
        self.assertEqual(result["source"], "test_transport")
        self.assertEqual(result["scores"]["p2"], 0.9)
        self.assertEqual(len(transport.calls), 1)
        self.assertEqual(len(transport.calls[0]["body"]["questions"]), 3)

    def test_missing_key_without_transport_refuses_to_invent(self):
        env = {k: v for k, v in os.environ.items() if k != "TYPESAFE_API_KEY"}
        with patch.dict(os.environ, env, clear=True):
            with self.assertRaises(RankerConfigError):
                order_candidates("q", [{"id": "a", "title": "t", "description": "d"}])

    def test_http_401_is_provider_error(self):
        transport = ScriptedTransport([(401, {"detail": "nope"})])
        with self.assertRaises(RankerProviderError):
            order_candidates("q", [{"id": "a", "title": "t", "description": "d"}], transport=transport)

    def test_geo_eval_jev_engine_uses_jev_not_client(self):
        class Boom:
            def chat_json(self, **kwargs):
                raise AssertionError("LLM client should not be called")

        transport = ScriptedTransport([(200, _noul_body({"t": 0.8, "c": 0.1}))])
        with patch("egeo.jev_ranker.order_candidates") as mocked:
            mocked.return_value = {"ordered_ids": ["t", "c"]}
            ordered = _rank_candidates(
                client=Boom(),
                model="gpt-4o",
                system_prompt="x",
                user_template="{query} {candidates}",
                query="best chair",
                candidates=[
                    Candidate(id="t", title="Ergo", description="lumbar"),
                    Candidate(id="c", title="Game", description="rgb"),
                ],
                temperature=0.0,
                ranker_engine="jev",
            )
        self.assertEqual(ordered, ["t", "c"])
        mocked.assert_called_once()

    def test_rank_dataset_tracks_target_position(self):
        transport = ScriptedTransport([(200, _noul_body({"a": 0.1, "b": 0.7}))])
        out = rank_dataset(
            [
                {
                    "query_id": "q1",
                    "query": "best",
                    "target_id": "a",
                    "candidates": [
                        {"id": "a", "title": "A", "description": "no"},
                        {"id": "b", "title": "B", "description": "yes"},
                    ],
                }
            ],
            transport=transport,
        )
        self.assertEqual(out["results"][0]["target_position"], 2)
        self.assertEqual(out["query_count"], 1)
        self.assertIsNotNone(out["cost_usd"])


if __name__ == "__main__":
    unittest.main()
