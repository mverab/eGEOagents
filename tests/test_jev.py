"""Contract tests for egeo.jev. Fake transports only; never the network."""
from __future__ import annotations

import pytest

from egeo import jev
from egeo.jev import (
    ChoiceAnswer,
    JevClient,
    JevConfigError,
    JevProviderError,
    MockJevTransport,
    NoulAnswer,
    choice_question,
    noul_question,
)

QUESTIONS = {
    "best": choice_question("Which?", {"a": "A", "b": "B", "c": "C"}),
    "exists": noul_question("Is there an answer?"),
}


class FakeTransport:
    def __init__(self, status: int, payload: dict) -> None:
        self.status, self.payload, self.calls = status, payload, []

    def post_json(self, url, body):
        self.calls.append((url, body))
        return self.status, self.payload


def ok_payload(**overrides):
    payload = {
        "model": "jev-1.13.0",
        "answers": {
            "best": {"type": "choice", "choice": "b", "confidence": 0.4, "probabilities": {"a": 0.2, "b": 0.6}},
            "exists": {"type": "noul", "noul": 0.73},
        },
        "usage": {"input_tokens": 452, "output_tokens": 59},
    }
    payload.update(overrides)
    return payload


def test_ask_parses_answers_usage_and_cost() -> None:
    t = FakeTransport(200, ok_payload())
    client = JevClient(transport=t, model="jev-latest")
    res = client.ask({"q": "x"}, QUESTIONS)
    url, body = t.calls[0]
    assert url == jev.TYPESAFE_URL
    assert body == {"model": "jev-latest", "state": {"q": "x"}, "questions": QUESTIONS}
    assert res.answers["best"] == ChoiceAnswer(choice="b", confidence=0.4, probabilities={"a": 0.2, "b": 0.6, "c": 0.0})
    assert res.answers["exists"] == NoulAnswer(noul=0.73)
    assert res.model == "jev-1.13.0"
    assert (res.input_tokens, res.output_tokens) == (452, 59)
    assert res.cost_usd == pytest.approx(452 / 1e6 * jev.INPUT_USD_PER_MTOK)
    assert client.totals["requests"] == 1 and client.totals["input_tokens"] == 452


def test_totals_accumulate() -> None:
    client = JevClient(transport=FakeTransport(200, ok_payload()))
    client.ask("s", QUESTIONS)
    client.ask("s", QUESTIONS)
    assert client.totals["requests"] == 2
    assert client.totals["output_tokens"] == 118
    assert client.totals["cost_usd"] == pytest.approx(2 * 452 / 1e6 * jev.INPUT_USD_PER_MTOK)


def test_missing_usage_is_zero() -> None:
    payload = ok_payload()
    del payload["usage"]
    res = JevClient(transport=FakeTransport(200, payload)).ask("s", QUESTIONS)
    assert (res.input_tokens, res.output_tokens, res.cost_usd) == (0, 0, 0.0)


@pytest.mark.parametrize(
    "answers",
    [
        {"exists": {"type": "noul", "noul": 0.5}},  # missing "best"
        {"best": {"type": "noul", "noul": 0.5}, "exists": {"type": "noul", "noul": 0.5}},  # wrong type
        {"best": {"type": "choice", "choice": "z", "confidence": 0.4, "probabilities": {"a": 1.0}},
         "exists": {"type": "noul", "noul": 0.5}},  # choice not in criteria
        {"best": {"type": "choice", "choice": "a", "confidence": 1.4, "probabilities": {"a": 1.0}},
         "exists": {"type": "noul", "noul": 0.5}},  # confidence out of range
        {"best": {"type": "choice", "choice": "a", "confidence": 0.4, "probabilities": {"zz": 1.0}},
         "exists": {"type": "noul", "noul": 0.5}},  # unknown probability key
        {"best": {"type": "choice", "choice": "a", "confidence": 0.4, "probabilities": {"a": 1.0}},
         "exists": {"type": "noul", "noul": -0.1}},  # noul out of range
    ],
)
def test_out_of_contract_answers_raise(answers) -> None:
    with pytest.raises(JevProviderError):
        JevClient(transport=FakeTransport(200, ok_payload(answers=answers))).ask("s", QUESTIONS)


@pytest.mark.parametrize("status", [401, 429, 500])
def test_http_errors_raise(status: int) -> None:
    with pytest.raises(JevProviderError, match=str(status)):
        JevClient(transport=FakeTransport(status, {})).ask("s", QUESTIONS)


def test_empty_questions_is_config_error() -> None:
    with pytest.raises(JevConfigError):
        JevClient(transport=FakeTransport(200, ok_payload())).ask("s", {})


def test_http_transport_requires_key(monkeypatch) -> None:
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
    assert jev.key_configured() is False
    with pytest.raises(JevConfigError):
        jev.HttpTransport().post_json(jev.TYPESAFE_URL, {})
    monkeypatch.setenv("TYPESAFE_API_KEY", "  ")
    assert jev.key_configured() is False
    monkeypatch.setenv("TYPESAFE_API_KEY", "ts-test")
    assert jev.key_configured() is True


def test_mock_transport_is_deterministic_word_overlap() -> None:
    state = {"query": "open source geo tools",
             "candidates": {"own_s01": "Open source GEO tools compared", "src_1": "cooking recipes"}}
    questions = {"best": choice_question("Which?", {"own_s01": "x", "src_1": "y"}), "ok": noul_question("?")}
    status, payload = MockJevTransport().post_json(jev.TYPESAFE_URL, {"model": "mock", "state": state, "questions": questions})
    assert status == 200
    best = payload["answers"]["best"]
    # own_s01 overlaps 4 words -> score 5; src_1 -> 1; probabilities 5/6, 1/6
    assert best["choice"] == "own_s01"
    assert best["probabilities"] == {"own_s01": 0.8333, "src_1": 0.1667}
    assert best["confidence"] == pytest.approx(0.6667, abs=1e-4)
    assert payload["answers"]["ok"] == {"type": "noul", "noul": 0.9}
    assert payload["model"] == "mock"
    assert MockJevTransport().post_json(jev.TYPESAFE_URL, {"model": "mock", "state": state, "questions": questions}) == (status, payload)


def test_make_client() -> None:
    mock = jev.make_client(mock=True)
    assert isinstance(mock.transport, MockJevTransport) and mock.model == "mock"
    real = jev.make_client(mock=False, model="jev-1.13.0")
    assert isinstance(real.transport, jev.HttpTransport) and real.model == "jev-1.13.0"
