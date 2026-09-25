"""Minimal TypeSafe (Jev) client for section-mode ``fix-gaps``.

SCAFFOLD — implement until ``tests/test_jev.py`` passes. Tests inject a fake transport; never
call the network in tests.

API contract (verified live 2026-09-25, model ``jev-1.13.0``):
    POST https://api.typesafe.ai/v1/systemone
    headers: Authorization: Bearer $TYPESAFE_API_KEY, Content-Type: application/json
    body:    {"model": str, "state": <str|object|array>, "questions": {qid: question}}
    choice question: {"type": "choice", "instructions": str, "criteria": {option: description}}
    noul question:   {"type": "noul", "instructions": str}
    200 response:    {"model": "jev-1.13.0",
                      "answers": {qid: {"type": "choice", "choice": str, "confidence": float,
                                        "probabilities": {option: float}}
                                  | {"type": "noul", "noul": float}},
                      "usage": {"input_tokens": int, "output_tokens": int}}

``JevClient.ask`` rules:
- ``questions`` must be a non-empty dict, else ``JevConfigError``.
- POST ``{"model": self.model, "state": state, "questions": questions}`` to ``TYPESAFE_URL``.
- status != 200 -> ``JevProviderError(f"TypeSafe HTTP {status}")``.
- For every asked qid: the answer must exist and its ``type`` must equal the question's type.
  Choice: ``choice`` must be a key of the question's ``criteria``; ``confidence`` in [0, 1];
  ``probabilities`` a dict whose keys are a subset of the criteria keys and whose values are in
  [0, 1]; missing criteria keys are filled with 0.0. Noul: ``noul`` in [0, 1]. Any violation ->
  ``JevProviderError`` naming the qid.
- Usage: missing/invalid -> 0 tokens. ``cost_usd = input_tokens / 1e6 * INPUT_USD_PER_MTOK``
  (output tokens are free).
- ``model`` in the response: use the response's ``model`` if it is a string, else ``self.model``.
- ``self.totals`` accumulates ``requests``, ``input_tokens``, ``output_tokens``, ``cost_usd``.

``HttpTransport.post_json(url, body) -> (status, dict)`` reads ``TYPESAFE_API_KEY`` at call time
(``JevConfigError`` if unset/blank), uses urllib with a 60 s timeout, returns HTTP error statuses
instead of raising, raises ``JevProviderError`` on network errors, non-JSON or non-object bodies.

``MockJevTransport`` (offline, deterministic) answers without network:
- choice: if ``state`` is a dict with ``"query"`` and a dict ``"candidates"``, score each option
  ``o`` as ``1 + |words(query) ∩ words(candidates[o])|`` (lowercase ``\\w+`` words; options not in
  candidates score 1); otherwise every option scores 1. Probabilities = scores / sum, rounded
  to 4 decimals. ``choice`` = highest probability (ties -> first option in criteria order).
  ``confidence = max(0, min(1, (n * peak - 1) / (n - 1)))`` with n options (n == 1 -> 1.0), where
  ``peak`` is the UNROUNDED highest probability; round the confidence to 4 decimals.
- noul: 0.9.
- model "mock", usage zeros. Returns status 200.

``make_client(mock=..., model=...)``: mock -> ``JevClient(MockJevTransport(), model="mock")``;
else ``JevClient(HttpTransport(), model=model)``.
``key_configured()``: True when ``TYPESAFE_API_KEY`` is set and not blank.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Mapping, Optional, Protocol, Tuple, Union

TYPESAFE_URL = "https://api.typesafe.ai/v1/systemone"
DEFAULT_MODEL = "jev-latest"
INPUT_USD_PER_MTOK = 0.042


class JevConfigError(ValueError):
    """Missing key or invalid request. Never a reason to invent answers."""


class JevProviderError(RuntimeError):
    """TypeSafe failed or answered out of contract. Callers must not fall back to heuristics."""


@dataclass(frozen=True)
class ChoiceAnswer:
    choice: str
    confidence: float
    probabilities: Dict[str, float]


@dataclass(frozen=True)
class NoulAnswer:
    noul: float


Answer = Union[ChoiceAnswer, NoulAnswer]


@dataclass
class JevResponse:
    answers: Dict[str, Answer]
    model: str
    input_tokens: int
    output_tokens: int
    cost_usd: float


class Transport(Protocol):
    def post_json(self, url: str, body: Dict[str, Any]) -> Tuple[int, Dict[str, Any]]: ...


def choice_question(instructions: str, criteria: Mapping[str, str]) -> Dict[str, Any]:
    return {"type": "choice", "instructions": instructions, "criteria": dict(criteria)}


def noul_question(instructions: str) -> Dict[str, Any]:
    return {"type": "noul", "instructions": instructions}


def key_configured() -> bool:
    raise NotImplementedError


class HttpTransport:
    def post_json(self, url: str, body: Dict[str, Any]) -> Tuple[int, Dict[str, Any]]:
        raise NotImplementedError


class MockJevTransport:
    def post_json(self, url: str, body: Dict[str, Any]) -> Tuple[int, Dict[str, Any]]:
        raise NotImplementedError


@dataclass
class JevClient:
    transport: Optional[Transport] = None
    model: str = DEFAULT_MODEL
    totals: Dict[str, float] = field(
        default_factory=lambda: {"requests": 0, "input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0}
    )

    def ask(self, state: Any, questions: Mapping[str, Mapping[str, Any]]) -> JevResponse:
        raise NotImplementedError


def make_client(*, mock: bool, model: str = DEFAULT_MODEL) -> JevClient:
    raise NotImplementedError
