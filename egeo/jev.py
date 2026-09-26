"""Minimal TypeSafe (Jev) client for section-mode ``fix-gaps``.

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


import json as _json
import os as _os
import re as _re
import urllib.error
import urllib.request


def key_configured() -> bool:
    return bool((_os.environ.get("TYPESAFE_API_KEY") or "").strip())


class HttpTransport:
    def post_json(self, url, body):
        key = (_os.environ.get("TYPESAFE_API_KEY") or "").strip()
        if not key:
            raise JevConfigError("TYPESAFE_API_KEY is not set")
        req = urllib.request.Request(url, data=_json.dumps(body).encode(), method="POST",
                                     headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                status, raw = r.status, r.read().decode()
        except urllib.error.HTTPError as e:
            status, raw = e.code, e.read().decode(errors="replace")
        except urllib.error.URLError as e:
            raise JevProviderError("TypeSafe request failed") from e
        try:
            data = _json.loads(raw) if raw else {}
        except _json.JSONDecodeError as e:
            raise JevProviderError("TypeSafe returned non-JSON") from e
        if not isinstance(data, dict):
            raise JevProviderError("TypeSafe returned a non-object")
        return status, data


def _words(t):
    return set(_re.findall(r"\w+", str(t).lower()))


class MockJevTransport:
    def post_json(self, url, body):
        state = body.get("state"); answers = {}
        for qid, q in body.get("questions", {}).items():
            if q.get("type") == "choice":
                opts = list(q["criteria"])
                cands = state.get("candidates") if isinstance(state, dict) else None
                qw = _words(state.get("query", "")) if isinstance(state, dict) else set()
                scores = [1 + (len(qw & _words(cands[o])) if isinstance(cands, dict) and o in cands else 0) for o in opts]
                tot = sum(scores); raw = [s / tot for s in scores]
                peak = max(raw); best = opts[raw.index(peak)]; n = len(opts)
                conf = 1.0 if n == 1 else max(0.0, min(1.0, (n * peak - 1) / (n - 1)))
                answers[qid] = {"type": "choice", "choice": best, "confidence": round(conf, 4),
                                "probabilities": {o: round(p, 4) for o, p in zip(opts, raw)}}
            else:
                answers[qid] = {"type": "noul", "noul": 0.9}
        return 200, {"model": "mock", "answers": answers, "usage": {"input_tokens": 0, "output_tokens": 0}}


def _unit(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool) and 0.0 <= float(x) <= 1.0


@dataclass
class JevClient:
    transport: Optional[Transport] = None
    model: str = DEFAULT_MODEL
    totals: Dict[str, float] = field(default_factory=lambda: {"requests": 0, "input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0})

    def ask(self, state, questions):
        if not questions:
            raise JevConfigError("questions must be a non-empty dict")
        t = self.transport or HttpTransport()
        status, payload = t.post_json(TYPESAFE_URL, {"model": self.model, "state": state, "questions": questions})
        if status != 200:
            raise JevProviderError(f"TypeSafe HTTP {status}")
        got = payload.get("answers")
        if not isinstance(got, dict):
            raise JevProviderError("missing answers")
        out = {}
        for qid, q in questions.items():
            a = got.get(qid)
            if not isinstance(a, dict) or a.get("type") != q.get("type"):
                raise JevProviderError(f"bad answer for {qid}")
            if q["type"] == "choice":
                crit = q["criteria"]; probs = a.get("probabilities")
                if a.get("choice") not in crit or not _unit(a.get("confidence")) or not isinstance(probs, dict) \
                        or any(k not in crit or not _unit(v) for k, v in probs.items()):
                    raise JevProviderError(f"bad choice answer for {qid}")
                full = {k: float(probs.get(k, 0.0)) for k in crit}
                out[qid] = ChoiceAnswer(a["choice"], float(a["confidence"]), full)
            else:
                if not _unit(a.get("noul")):
                    raise JevProviderError(f"bad noul answer for {qid}")
                out[qid] = NoulAnswer(float(a["noul"]))
        u = payload.get("usage") if isinstance(payload.get("usage"), dict) else {}
        try:
            it, ot = int(u.get("input_tokens", 0)), int(u.get("output_tokens", 0))
        except (TypeError, ValueError):
            it, ot = 0, 0
        cost = it / 1e6 * INPUT_USD_PER_MTOK
        for k, v in (("requests", 1), ("input_tokens", it), ("output_tokens", ot), ("cost_usd", cost)):
            self.totals[k] += v
        m = payload.get("model") if isinstance(payload.get("model"), str) else self.model
        return JevResponse(out, m, it, ot, cost)


def make_client(*, mock: bool, model: str = DEFAULT_MODEL) -> JevClient:
    return JevClient(MockJevTransport(), model="mock") if mock else JevClient(HttpTransport(), model=model)
