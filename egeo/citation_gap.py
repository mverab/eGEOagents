"""Optional TypeSafe/Jev citation-gap evaluator.

Compares an imported AI answer to a target page using evidence text supplied
in the input JSON. This module does not crawl, does not invent scores when the
provider is unavailable, and never applies proposed edits.
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

SYSTEMONE_URL = "https://api.typesafe.ai/v1/systemone"
DEFAULT_MODEL = "jev-latest"
SCHEMA_VERSION = 1
# Actionable/covered only if relevance and both Choice confidences strictly exceed these.
RELEVANCE_MIN = 0.5
CHOICE_CONFIDENCE_MIN = 0.5
PROBABILITY_SUM_TOLERANCE = 0.02
SUPPORT_OPTIONS = ("supported", "contradicted", "insufficient")
COVERAGE_OPTIONS = ("covered", "actionable_gap", "insufficient")
REVIEW_REASON = (
    "Target appears to omit a claim that a cited source supports. "
    "Owner must supply verified first-party facts before any rewrite. "
    "Cited source text is not copied into the page."
)
NOTES = (
    "Source and target texts are taken from the input; this command does not crawl.",
    "Model confidence is not future citation probability.",
    "Proposed actions are never applied automatically.",
    "Cited source text is never copied into a page rewrite.",
    "Actionable/covered requires relevance > 0.5 and both Choice confidences > 0.5.",
)


class CitationGapError(ValueError):
    """Invalid input or missing configuration. Not a substitute evaluator."""


class ProviderError(RuntimeError):
    """TypeSafe/Jev failed. Callers MUST NOT fall back to heuristic scores."""


def api_key_configured() -> bool:
    return bool((os.environ.get("TYPESAFE_API_KEY") or "").strip())


class StdlibTransport:
    """POST JSON to TypeSafe with stdlib urllib. Auth never leaves this class."""

    def post_json(self, url: str, headers: Mapping[str, str], body: Dict[str, Any]) -> Tuple[int, Dict[str, Any]]:
        key = (os.environ.get("TYPESAFE_API_KEY") or "").strip()
        if not key:
            raise CitationGapError("TYPESAFE_API_KEY is not set; refusing to invent scores.")
        payload = json.dumps(body).encode("utf-8")
        req_headers = {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        }
        request = urllib.request.Request(url, data=payload, headers=req_headers, method="POST")
        raw = ""
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                status = int(response.status)
                raw = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            status = int(exc.code)
            raw = exc.read().decode("utf-8", errors="replace")
        except urllib.error.URLError as exc:
            raise ProviderError("TypeSafe request failed") from exc
        try:
            parsed = json.loads(raw) if raw else {}
        except json.JSONDecodeError as exc:
            raise ProviderError("TypeSafe returned non-JSON") from exc
        if not isinstance(parsed, dict):
            raise ProviderError("TypeSafe returned non-object JSON")
        return status, parsed


def _present(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _require_mapping(value: Any, field: str) -> Dict[str, Any]:
    if not isinstance(value, dict):
        raise CitationGapError(f"{field} must be an object")
    return value


def _validate_input(payload: Any) -> Dict[str, Any]:
    data = _require_mapping(payload, "input")
    query = data.get("query")
    if not _present(query):
        raise CitationGapError("query must be a non-empty string")
    query = str(query).strip()
    ai_answer = _require_mapping(data.get("ai_answer"), "ai_answer")
    target = _require_mapping(data.get("target"), "target")
    evidence = data.get("evidence")
    if not isinstance(evidence, list):
        raise CitationGapError("evidence must be a list")
    seen = set()
    cleaned: List[Dict[str, Any]] = []
    for index, item in enumerate(evidence):
        row = _require_mapping(item, f"evidence[{index}]")
        ident = row.get("id")
        if not _present(ident):
            raise CitationGapError("each evidence item needs a non-empty id")
        if ident in seen:
            raise CitationGapError(f"duplicate evidence id: {ident}")
        seen.add(ident)
        cleaned.append(row)
    out = {
        "query": query,
        "ai_answer": ai_answer,
        "target": target,
        "evidence": cleaned,
    }
    if _present(data.get("query_id")):
        out["query_id"] = str(data["query_id"]).strip()
    if _present(data.get("page_id")):
        out["page_id"] = str(data["page_id"]).strip()
    return out


def _questions(evidence_id: str) -> Dict[str, Any]:
    return {
        f"{evidence_id}_relevance": {
            "type": "noul",
            "instructions": "Is this cited source relevant to the user query and the imported AI answer?",
            "criteria": {
                "true": "The source is on-topic for the query and the answer's claim.",
                "false": "The source is off-topic or unrelated.",
            },
        },
        f"{evidence_id}_support": {
            "type": "choice",
            "instructions": "Does the cited source text support the imported AI answer's claim?",
            "criteria": {
                "supported": "The cited source text supports the imported AI answer's claim.",
                "contradicted": "The cited source text contradicts the imported AI answer's claim.",
                "insufficient": "The cited source text is too weak or missing to decide.",
            },
        },
        f"{evidence_id}_coverage": {
            "type": "choice",
            "instructions": (
                "Does the TARGET page already cover the claim that this source supports, "
                "relative to the imported AI answer?"
            ),
            "criteria": {
                "covered": "The target page already states the same factual claim.",
                "actionable_gap": (
                    "The target page omits a specific claim that the source supports "
                    "and that could be added without inventing facts."
                ),
                "insufficient": "Not enough target or source text to decide coverage.",
            },
        },
    }


def _as_unit_interval(value: Any, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ProviderError(f"invalid {field}")
    number = float(value)
    if number < 0.0 or number > 1.0:
        raise ProviderError(f"invalid {field}")
    return number


def _validate_noul(answer: Any, key: str) -> Dict[str, Any]:
    row = _require_provider_object(answer, key)
    if row.get("type") != "noul":
        raise ProviderError(f"invalid {key} type")
    noul = _as_unit_interval(row.get("noul"), f"{key}.noul")
    return {"type": "noul", "noul": noul}


def _require_provider_object(value: Any, field: str) -> Dict[str, Any]:
    if not isinstance(value, dict):
        raise ProviderError(f"invalid {field}")
    return value


def _validate_choice(answer: Any, key: str, options: Sequence[str]) -> Dict[str, Any]:
    row = _require_provider_object(answer, key)
    if row.get("type") != "choice":
        raise ProviderError(f"invalid {key} type")
    choice = row.get("choice")
    if choice not in options:
        raise ProviderError(f"invalid {key} choice")
    probabilities = row.get("probabilities")
    if not isinstance(probabilities, dict):
        raise ProviderError(f"invalid {key} probabilities")
    cleaned: Dict[str, float] = {}
    for option in options:
        if option not in probabilities:
            raise ProviderError(f"invalid {key} probabilities")
        cleaned[option] = _as_unit_interval(probabilities[option], f"{key}.probabilities.{option}")
    total = sum(cleaned.values())
    if abs(total - 1.0) > PROBABILITY_SUM_TOLERANCE:
        raise ProviderError(f"invalid {key} probabilities")
    confidence = _as_unit_interval(row.get("confidence"), f"{key}.confidence")
    return {
        "type": "choice",
        "choice": choice,
        "probabilities": cleaned,
        "confidence": confidence,
    }


def _validate_usage(raw: Any) -> Optional[Dict[str, int]]:
    if not isinstance(raw, dict):
        return None
    try:
        input_tokens = int(raw["input_tokens"])
        output_tokens = int(raw["output_tokens"])
    except (KeyError, TypeError, ValueError):
        return None
    if input_tokens < 0 or output_tokens < 0:
        return None
    return {"input_tokens": input_tokens, "output_tokens": output_tokens}


def _http_url(value: Any) -> bool:
    if not _present(value):
        return False
    parsed = urllib.parse.urlparse(str(value).strip())
    return parsed.scheme in ("http", "https") and bool(parsed.netloc)


def _timestamp(value: Any) -> bool:
    if not _present(value):
        return False
    text = str(value).strip().replace("Z", "+00:00")
    try:
        datetime.fromisoformat(text)
    except ValueError:
        return False
    return True


def _answer_ok(answer: Mapping[str, Any]) -> bool:
    return _present(answer.get("engine")) and _present(answer.get("provenance")) and _timestamp(answer.get("captured_at"))


def _target_ok(target: Mapping[str, Any]) -> bool:
    return _http_url(target.get("url")) and _timestamp(target.get("captured_at"))


def _evidence_ok(item: Mapping[str, Any]) -> bool:
    return _http_url(item.get("url")) and _timestamp(item.get("captured_at"))


def _classify(
    relevance: float,
    support: str,
    coverage: str,
    support_confidence: float,
    coverage_confidence: float,
) -> Tuple[str, bool, str]:
    if relevance < RELEVANCE_MIN:
        return "insufficient", True, "irrelevant"
    if (
        relevance <= RELEVANCE_MIN
        or support_confidence <= CHOICE_CONFIDENCE_MIN
        or coverage_confidence <= CHOICE_CONFIDENCE_MIN
    ):
        return "insufficient", True, "uncertain"
    if support == "contradicted":
        return "insufficient", True, "contradicted"
    if support == "insufficient" or coverage == "insufficient":
        return "insufficient", True, "insufficient_evidence"
    if coverage == "covered":
        return "covered", False, "covered"
    if coverage == "actionable_gap" and support == "supported":
        return "actionable", False, "actionable_gap"
    return "insufficient", True, "abstained"


def _abstained_finding(item: Mapping[str, Any], target_text: str, reason: str) -> Dict[str, Any]:
    return {
        "id": item.get("id"),
        "group": "insufficient",
        "abstained": True,
        "reason": reason,
        "source_fragment": item.get("text") if _present(item.get("text")) else "",
        "target_fragment": target_text,
        "source_url": item.get("url") or "",
        "captured_at": item.get("captured_at"),
        "relevance": None,
        "support": None,
        "coverage": None,
    }


def _transport_kind(transport: Any) -> str:
    if transport is None:
        return "none"
    if type(transport).__name__ == "StdlibTransport":
        return "live_api"
    return "test_transport"


def _parse_answers(body: Dict[str, Any], evidence_id: str) -> Tuple[str, Dict[str, Any], Dict[str, Any], Dict[str, Any], Optional[Dict[str, int]]]:
    model = body.get("model")
    if not _present(model):
        raise ProviderError("TypeSafe response missing model")
    answers = body.get("answers")
    if not isinstance(answers, dict):
        raise ProviderError("TypeSafe response missing answers")
    relevance = _validate_noul(answers.get(f"{evidence_id}_relevance"), f"{evidence_id}_relevance")
    support = _validate_choice(answers.get(f"{evidence_id}_support"), f"{evidence_id}_support", SUPPORT_OPTIONS)
    coverage = _validate_choice(
        answers.get(f"{evidence_id}_coverage"), f"{evidence_id}_coverage", COVERAGE_OPTIONS
    )
    return str(model).strip(), relevance, support, coverage, _validate_usage(body.get("usage"))


def evaluate(
    payload: Any,
    *,
    transport: Any = None,
    model: str = DEFAULT_MODEL,
) -> Dict[str, Any]:
    data = _validate_input(payload)
    target_text = data["target"].get("text") if isinstance(data["target"].get("text"), str) else ""
    target_text_present = _present(target_text)
    answer_text = data["ai_answer"].get("text") if isinstance(data["ai_answer"].get("text"), str) else ""
    answer_present = _present(answer_text)
    slots: List[Optional[Dict[str, Any]]] = [None] * len(data["evidence"])
    proposed: List[Dict[str, Any]] = []
    jev_needed = False
    pending_indexes: List[int] = []
    for index, item in enumerate(data["evidence"]):
        if not target_text_present or not answer_present or not _present(item.get("text")):
            slots[index] = _abstained_finding(item, target_text if target_text_present else "", "missing_text")
            continue
        if not (_answer_ok(data["ai_answer"]) and _target_ok(data["target"]) and _evidence_ok(item)):
            slots[index] = _abstained_finding(item, target_text, "missing_provenance")
            continue
        if item.get("cited_in_answer") is not True:
            slots[index] = _abstained_finding(item, target_text, "unlinked_citation")
            continue
        jev_needed = True
        pending_indexes.append(index)

    if jev_needed and transport is None:
        if not api_key_configured():
            raise CitationGapError("TYPESAFE_API_KEY is not set; refusing to invent scores.")
        transport = StdlibTransport()
    kind = _transport_kind(transport)

    usage_total = {"input_tokens": 0, "output_tokens": 0}
    usage_complete = True
    models: List[str] = []
    elapsed_ms = 0
    called = False
    query_ids = [data["query_id"]] if data.get("query_id") else []
    page_ids = [data["page_id"]] if data.get("page_id") else []
    for index in pending_indexes:
        item = data["evidence"][index]
        evidence_id = str(item["id"])
        body = {
            "state": {
                "query": data["query"],
                "ai_answer": answer_text,
                "target": {"url": data["target"].get("url") or "", "text": target_text},
                "evidence": {
                    "id": evidence_id,
                    "url": item.get("url") or "",
                    "text": item.get("text"),
                },
            },
            "model": model,
            "questions": _questions(evidence_id),
        }
        started = time.monotonic()
        try:
            status, response = transport.post_json(SYSTEMONE_URL, {"Content-Type": "application/json"}, body)
        except CitationGapError:
            raise
        except ProviderError:
            raise
        except Exception as exc:
            raise ProviderError("TypeSafe request failed") from exc
        elapsed_ms += int(round((time.monotonic() - started) * 1000))
        called = True
        if status != 200:
            raise ProviderError(f"TypeSafe HTTP {status}")
        response_model, relevance, support, coverage, usage = _parse_answers(response, evidence_id)
        models.append(response_model)
        if usage:
            usage_total["input_tokens"] += usage["input_tokens"]
            usage_total["output_tokens"] += usage["output_tokens"]
        else:
            usage_complete = False
        group, abstained, reason = _classify(
            relevance["noul"],
            support["choice"],
            coverage["choice"],
            support["confidence"],
            coverage["confidence"],
        )
        finding = {
            "id": evidence_id,
            "group": group,
            "abstained": abstained,
            "reason": reason,
            "source_fragment": str(item.get("text") or ""),
            "target_fragment": target_text,
            "source_url": item.get("url") or "",
            "captured_at": item.get("captured_at"),
            "relevance": relevance,
            "support": support,
            "coverage": coverage,
        }
        slots[index] = finding
        if group == "actionable":
            proposed.append(
                {
                    "kind": "propose_citation_gap",
                    "finding_id": evidence_id,
                    "next_gate": "owner",
                    "auto_apply": False,
                    "query_ids": list(query_ids),
                    "page_ids": list(page_ids),
                    "evidence": [evidence_id, item.get("url") or ""],
                    "reason": REVIEW_REASON,
                    "diff": None,
                }
            )

    findings = [row for row in slots if row is not None]
    evaluation = {
        "provider": "typesafe",
        "endpoint": SYSTEMONE_URL,
        "requested_model": model,
        "model": models[-1] if models else None,
        "usage": usage_total if (called and usage_complete) else None,
        "elapsed_ms": elapsed_ms if called else None,
        "cost": None,
        "source": kind if called else "none",
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "query": data["query"],
        "ai_answer": data["ai_answer"],
        "target": data["target"],
        "findings": findings,
        "proposed_actions": proposed,
        "auto_apply": False,
        "evaluation": evaluation,
        "notes": list(NOTES),
        "run_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


def render_proposal(result: Mapping[str, Any]) -> str:
    lines = [
        "# Decision proposal: propose_citation_gap",
        "",
        "- kind: `propose_citation_gap`",
        "- next_gate: `owner`",
        "- auto_apply: `false`",
        "",
        "## Reason",
        "",
        REVIEW_REASON,
        "",
        "## Proposed rewrite",
        "",
        "None. Cited source text is not copied onto the page. Owner must supply verified first-party facts.",
        "",
    ]
    for action in result.get("proposed_actions") or []:
        lines.append(f"- finding `{action.get('finding_id')}` (diff omitted)")
    lines.extend(
        [
            "",
            "## Gate",
            "",
            "Owner must approve before any site edit, PR, merge, or deploy.",
            "Visible copy is never auto-published. Do not invent facts.",
            "",
        ]
    )
    return "\n".join(lines)


def run_from_path(
    path: Path,
    *,
    out: Optional[Path] = None,
    record: bool = False,
    model: str = DEFAULT_MODEL,
    transport: Any = None,
) -> Dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise CitationGapError(f"invalid JSON in {path}") from exc
    result = evaluate(payload, transport=transport, model=model)
    if out is not None:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if record and result["proposed_actions"]:
        from . import workspace

        home = workspace.resolve_home()
        workspace.bootstrap(home)
        project = workspace.load_project_config(home)
        if project is None:
            raise CitationGapError("project.yaml is required to record a citation-gap proposal")
        _record_proposed(result, home, project)
    return result


def _project_ids(project: Mapping[str, Any], field: str) -> set:
    return {str(item["id"]) for item in project.get(field, []) if item.get("id")}


def _record_proposed(result: Dict[str, Any], home: Path, project: Dict[str, Any]) -> None:
    from . import decide

    actions = list(result.get("proposed_actions") or [])
    query_ids = list(actions[0].get("query_ids") or [])
    page_ids = list(actions[0].get("page_ids") or [])
    if len(query_ids) != 1 or len(page_ids) != 1:
        raise CitationGapError("query_id and page_id are required to --record")
    query_id, page_id = query_ids[0], page_ids[0]
    if query_id not in _project_ids(project, "queries"):
        raise CitationGapError(f"unknown query_id: {query_id}")
    if page_id not in _project_ids(project, "pages"):
        raise CitationGapError(f"unknown page_id: {page_id}")
    evidence: List[str] = []
    seen = set()
    for action in actions:
        if list(action.get("query_ids") or []) != query_ids or list(action.get("page_ids") or []) != page_ids:
            raise CitationGapError("multiple citation-gap actions must share query_id and page_id")
        for item in action.get("evidence") or []:
            if item in seen:
                continue
            seen.add(item)
            evidence.append(str(item))
    merged = {
        "kind": "propose_citation_gap",
        "reason": actions[0]["reason"],
        "next_gate": "owner",
        "auto_apply": False,
        "query_ids": query_ids,
        "page_ids": page_ids,
        "evidence": evidence,
        "diff": None,
    }
    open_keys = decide._open_keys(decide.load_ledger(home))
    if decide._key("propose_citation_gap", query_ids, page_ids) in open_keys:
        result["recorded"] = "skipped_open"
        return
    persisted = decide.apply_decision(home, project, merged)
    result["recorded"] = "proposed"
    result["ledger_row"] = persisted.get("ledger_row")
