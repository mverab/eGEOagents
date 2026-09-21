"""Jev-backed ranker: score candidates for a query, sort in code.

Replaces the LLM `ordered_ids` judge used by ``geo_eval._rank_candidates``.
Does not rewrite copy. Does not invent scores when TypeSafe is unavailable.
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

SYSTEMONE_URL = "https://api.typesafe.ai/v1/systemone"
DEFAULT_MODEL = "jev-latest"
INPUT_USD_PER_MTOK = 0.042


class RankerConfigError(ValueError):
    """Missing credentials or invalid input. Not a substitute judge."""


class RankerProviderError(RuntimeError):
    """TypeSafe/Jev failed. Callers MUST NOT fall back to heuristic ranks."""


def api_key_configured() -> bool:
    return bool((os.environ.get("TYPESAFE_API_KEY") or "").strip())


class StdlibTransport:
    def post_json(self, url: str, body: Dict[str, Any]) -> Tuple[int, Dict[str, Any]]:
        key = (os.environ.get("TYPESAFE_API_KEY") or "").strip()
        if not key:
            raise RankerConfigError("TYPESAFE_API_KEY is not set; refusing to invent ranks.")
        payload = json.dumps(body).encode("utf-8")
        request = urllib.request.Request(
            url,
            data=payload,
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        raw = ""
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                status = int(response.status)
                raw = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            status = int(exc.code)
            raw = exc.read().decode("utf-8", errors="replace")
        except urllib.error.URLError as exc:
            raise RankerProviderError("TypeSafe request failed") from exc
        try:
            parsed = json.loads(raw) if raw else {}
        except json.JSONDecodeError as exc:
            raise RankerProviderError("TypeSafe returned non-JSON") from exc
        if not isinstance(parsed, dict):
            raise RankerProviderError("TypeSafe returned a non-object")
        return status, parsed


def _row(candidate: Any) -> Dict[str, str]:
    if isinstance(candidate, Mapping):
        cid = str(candidate.get("id") or "").strip()
        title = str(candidate.get("title") or "")
        description = str(candidate.get("description") or "")
    else:
        cid = str(getattr(candidate, "id", "") or "").strip()
        title = str(getattr(candidate, "title", "") or "")
        description = str(getattr(candidate, "description", "") or "")
    if not cid:
        raise RankerConfigError("every candidate needs an id")
    return {"id": cid, "title": title, "description": description}


def _validate_usage(payload: Mapping[str, Any]) -> Optional[Dict[str, int]]:
    usage = payload.get("usage")
    if not isinstance(usage, Mapping):
        return None
    try:
        inp = int(usage["input_tokens"])
        out = int(usage["output_tokens"])
    except (KeyError, TypeError, ValueError):
        return None
    if inp < 0 or out < 0:
        return None
    return {"input_tokens": inp, "output_tokens": out}


def _cost_usd(usage: Optional[Mapping[str, int]]) -> Optional[float]:
    if not usage:
        return None
    return usage["input_tokens"] / 1_000_000 * INPUT_USD_PER_MTOK


def order_candidates(
    query: str,
    candidates: Sequence[Any],
    *,
    model: str = DEFAULT_MODEL,
    transport: Optional[Any] = None,
) -> Dict[str, Any]:
    """Return ordered ids plus per-candidate noul scores from one Jev request."""
    q = (query or "").strip()
    if not q:
        raise RankerConfigError("query is required")
    rows = [_row(c) for c in candidates]
    if not rows:
        raise RankerConfigError("at least one candidate is required")
    ids = [r["id"] for r in rows]
    if len(set(ids)) != len(ids):
        raise RankerConfigError("candidate ids must be unique")

    state = {
        "query": q,
        "candidates": {r["id"]: {"title": r["title"], "description": r["description"]} for r in rows},
    }
    questions: Dict[str, Any] = {}
    for r in rows:
        cid = r["id"]
        questions[cid] = {
            "type": "noul",
            "instructions": (
                f"Would an AI answer engine rank candidates.{cid} highly for `query` "
                "and cite it as a useful source? Answer yes only if the provided title "
                "and description match the constraints in `query`. Use only state text."
            ),
        }
    body = {"model": model, "state": state, "questions": questions}
    client = transport or StdlibTransport()
    started = time.perf_counter()
    status, payload = client.post_json(SYSTEMONE_URL, body)
    duration_ms = int((time.perf_counter() - started) * 1000)
    if status == 401:
        raise RankerProviderError("TypeSafe HTTP 401")
    if status == 429:
        raise RankerProviderError("TypeSafe HTTP 429")
    if status >= 400:
        raise RankerProviderError(f"TypeSafe HTTP {status}")

    answers = payload.get("answers")
    if not isinstance(answers, Mapping):
        raise RankerProviderError("TypeSafe response missing answers")
    scores: Dict[str, float] = {}
    for cid in ids:
        ans = answers.get(cid)
        if not isinstance(ans, Mapping) or ans.get("type") != "noul":
            raise RankerProviderError(f"missing noul answer for {cid}")
        try:
            noul = float(ans["noul"])
        except (KeyError, TypeError, ValueError) as exc:
            raise RankerProviderError(f"invalid noul for {cid}") from exc
        if noul < 0 or noul > 1:
            raise RankerProviderError(f"noul out of range for {cid}")
        scores[cid] = noul

    ordered = sorted(ids, key=lambda cid: (-scores[cid], cid))
    usage = _validate_usage(payload)
    source = "test_transport" if transport is not None else "live_api"
    resolved_model = payload.get("model") if isinstance(payload.get("model"), str) else model
    return {
        "query": q,
        "ordered_ids": ordered,
        "scores": scores,
        "model": resolved_model,
        "usage": usage,
        "cost_usd": _cost_usd(usage),
        "duration_ms": duration_ms,
        "source": source,
        "candidate_ids": ids,
    }


def rank_dataset(
    examples: Iterable[Mapping[str, Any]],
    *,
    model: str = DEFAULT_MODEL,
    transport: Optional[Any] = None,
) -> Dict[str, Any]:
    results: List[Dict[str, Any]] = []
    total_in = 0
    total_out = 0
    usage_complete = True
    t0 = time.perf_counter()
    for ex in examples:
        ranked = order_candidates(
            str(ex.get("query") or ""),
            list(ex.get("candidates") or []),
            model=model,
            transport=transport,
        )
        target_id = ex.get("target_id")
        position = None
        if isinstance(target_id, str) and target_id in ranked["ordered_ids"]:
            position = ranked["ordered_ids"].index(target_id) + 1
        results.append(
            {
                "query_id": ex.get("query_id") or ex.get("id"),
                "query": ranked["query"],
                "target_id": target_id,
                "target_position": position,
                "ordered_ids": ranked["ordered_ids"],
                "scores": ranked["scores"],
                "model": ranked["model"],
                "usage": ranked["usage"],
                "cost_usd": ranked["cost_usd"],
                "duration_ms": ranked["duration_ms"],
                "source": ranked["source"],
            }
        )
        if ranked["usage"] is None:
            usage_complete = False
        else:
            total_in += ranked["usage"]["input_tokens"]
            total_out += ranked["usage"]["output_tokens"]
    usage = {"input_tokens": total_in, "output_tokens": total_out} if usage_complete and results else None
    return {
        "results": results,
        "usage": usage,
        "cost_usd": _cost_usd(usage),
        "duration_ms": int((time.perf_counter() - t0) * 1000),
        "source": results[0]["source"] if results else "none",
        "model": results[0]["model"] if results else model,
        "query_count": len(results),
    }
