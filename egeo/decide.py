"""Deterministic loop decision layer: rank one next action, never apply.

LLM-free. Reads project.yaml, collector JSONL, and an append-only outcome
ledger. Writes at most one proposed ledger row, one proposal doc, and one
LOG.md line. Never publishes, merges, or sets status ``applied``.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from . import workspace

LEDGER_REL = Path("data") / "outcomes" / "ledger.jsonl"
SCHEMA_VERSION = 1
WINDOWS_DAYS = (7, 14, 28)
OPEN_STATUSES = {"proposed", "applied"}
OWNER_KINDS = {"escalate_absent", "propose_page_owner", "propose_schema"}
_SLUG_RE = re.compile(r"[^a-z0-9]+")


def ledger_path(home: Path) -> Path:
    return home / LEDGER_REL


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_ts(value: Any) -> Optional[datetime]:
    if not value:
        return None
    text = str(value).replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _slug(value: str) -> str:
    return _SLUG_RE.sub("-", value.lower()).strip("-") or "item"


def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    if not path.is_file():
        return []
    records: List[Dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(item, dict):
            records.append(item)
    return records


def append_jsonl(path: Path, record: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True) + "\n")


def load_ledger(home: Path) -> List[Dict[str, Any]]:
    return read_jsonl(ledger_path(home))


def _stream_slug(value: str, max_length: int = 60) -> str:
    value = re.sub(r"^https?://", "", value.strip().lower())
    value = re.sub(r"[^a-z0-9]+", "-", value).strip("-")
    return (value[:max_length].rstrip("-") or "untitled")


def _query_stream(home: Path, text: str) -> Path:
    return workspace.data_dir("serp", home) / f"{_stream_slug(text)}.jsonl"


def _page_stream(home: Path, url: str) -> Path:
    return workspace.data_dir("page", home) / f"{_stream_slug(url)}.jsonl"


def _cadence_days(project: Dict[str, Any]) -> int:
    raw = str((project.get("measurement") or {}).get("cadence") or "weekly").lower()
    if raw.startswith("day") or raw == "daily":
        return 1
    if raw.startswith("month"):
        return 30
    return 7


def _key(kind: str, query_ids: List[str], page_ids: List[str]) -> Tuple[str, Tuple[str, ...], Tuple[str, ...]]:
    return (kind, tuple(query_ids), tuple(page_ids))


def _open_keys(ledger: List[Dict[str, Any]]) -> set:
    return {
        _key(str(row.get("kind") or ""), list(row.get("query_ids") or []), list(row.get("page_ids") or []))
        for row in ledger
        if row.get("status") in OPEN_STATUSES
    }


def _action(
    *,
    kind: str,
    reason: str,
    next_gate: str,
    query_ids: Optional[List[str]] = None,
    page_ids: Optional[List[str]] = None,
    evidence: Optional[List[str]] = None,
    grade: Optional[str] = None,
    ledger_id: Optional[str] = None,
) -> Dict[str, Any]:
    return {
        "kind": kind,
        "reason": reason,
        "next_gate": next_gate,
        "query_ids": query_ids or [],
        "page_ids": page_ids or [],
        "evidence": evidence or [],
        "grade": grade,
        "ledger_id": ledger_id,
        "auto_apply": False,
    }


def rank_action(home: Path, project: Dict[str, Any], now: Optional[datetime] = None) -> Dict[str, Any]:
    """Return exactly one ranked action. Pure read except path resolution."""
    now = now or _now()
    ledger = load_ledger(home)
    open_keys = _open_keys(ledger)
    cadence = _cadence_days(project)
    queries = [q for q in project.get("queries", []) if q.get("active", True)]
    pages = [p for p in project.get("pages", []) if p.get("active", True)]
    page_by_id = {p["id"]: p for p in pages}

    # 1. collect_fresh
    newest: List[datetime] = []
    any_stream = False
    for query in queries:
        records = read_jsonl(_query_stream(home, query["text"]))
        if records:
            any_stream = True
            ts = _parse_ts(records[-1].get("ts"))
            if ts:
                newest.append(ts)
    for page in pages:
        records = read_jsonl(_page_stream(home, page["url"]))
        if records:
            any_stream = True
            ts = _parse_ts(records[-1].get("ts"))
            if ts:
                newest.append(ts)
    if not any_stream or (newest and (now - max(newest)) > timedelta(days=cadence)):
        return _action(
            kind="collect_fresh",
            reason="no collector observations" if not any_stream else f"last observation older than {cadence}d cadence",
            next_gate="scheduler",
        )

    # 2/3. wait_for_window or grade_outcome
    for row in ledger:
        if row.get("status") not in OPEN_STATUSES:
            continue
        created = _parse_ts(row.get("ts"))
        if not created:
            continue
        age_days = (now - created).days
        grades = row.get("grades") or {}
        pending = [d for d in WINDOWS_DAYS if age_days >= d and str(d) not in {str(k) for k in grades}]
        if not pending:
            if age_days < WINDOWS_DAYS[0]:
                return _action(
                    kind="wait_for_window",
                    reason=f"open {row.get('kind')} {row.get('id')} waiting for day {WINDOWS_DAYS[0]}",
                    next_gate="none",
                    query_ids=list(row.get("query_ids") or []),
                    page_ids=list(row.get("page_ids") or []),
                    ledger_id=str(row.get("id")),
                )
            continue
        window = pending[0]
        grade, evidence = _grade_row(home, project, row, created)
        if grade is None:
            return _action(
                kind="wait_for_window",
                reason=f"window {window}d reached but no later observations for {row.get('id')}",
                next_gate="scheduler",
                query_ids=list(row.get("query_ids") or []),
                page_ids=list(row.get("page_ids") or []),
                ledger_id=str(row.get("id")),
            )
        return _action(
            kind="grade_outcome",
            reason=f"window {window}d grade={grade} for {row.get('id')}",
            next_gate="none",
            query_ids=list(row.get("query_ids") or []),
            page_ids=list(row.get("page_ids") or []),
            evidence=evidence,
            grade=grade,
            ledger_id=str(row.get("id")),
        )

    # 4. escalate_absent
    for query in queries:
        stream = _query_stream(home, query["text"])
        records = read_jsonl(stream)
        if len(records) < 3:
            continue
        if all(r.get("target_position") is None for r in records[-3:]):
            key = _key("escalate_absent", [query["id"]], list(query.get("target_pages") or []))
            if key in open_keys:
                continue
            rel = str(stream.relative_to(home)) if stream.is_relative_to(home) else str(stream)
            return _action(
                kind="escalate_absent",
                reason=f"query {query['id']!r} absent from top 10 in last 3 observations",
                next_gate="owner",
                query_ids=[query["id"]],
                page_ids=list(query.get("target_pages") or []),
                evidence=[rel],
            )

    # 5. propose_page_owner
    for query in queries:
        if str(query.get("class") or "") not in {"generic", "informational"}:
            continue
        targets = [tid for tid in (query.get("target_pages") or []) if tid in page_by_id]
        if targets:
            continue
        key = _key("propose_page_owner", [query["id"]], [])
        if key in open_keys:
            continue
        return _action(
            kind="propose_page_owner",
            reason=f"query {query['id']!r} has no canonical target page",
            next_gate="owner",
            query_ids=[query["id"]],
        )

    # 6. propose_schema
    for page in pages:
        stream = _page_stream(home, page["url"])
        records = read_jsonl(stream)
        if not records:
            continue
        types = records[-1].get("jsonld_types") or []
        if types:
            continue
        key = _key("propose_schema", [], [page["id"]])
        if key in open_keys:
            continue
        rel = str(stream.relative_to(home)) if stream.is_relative_to(home) else str(stream)
        return _action(
            kind="propose_schema",
            reason=f"page {page['id']!r} has empty jsonld_types",
            next_gate="owner",
            page_ids=[page["id"]],
            evidence=[rel],
        )

    return _action(kind="no_op", reason="no deterministic action", next_gate="none")


def _grade_row(home: Path, project: Dict[str, Any], row: Dict[str, Any], created: datetime) -> Tuple[Optional[str], List[str]]:
    kind = row.get("kind")
    evidence: List[str] = []
    later = False
    if kind == "escalate_absent":
        query_ids = set(row.get("query_ids") or [])
        for query in project.get("queries", []):
            if query.get("id") not in query_ids:
                continue
            stream = _query_stream(home, query["text"])
            records = read_jsonl(stream)
            after = [r for r in records if (_parse_ts(r.get("ts")) or created) > created]
            if not after:
                continue
            later = True
            rel = str(stream.relative_to(home)) if stream.is_relative_to(home) else str(stream)
            evidence.append(rel)
            if any(r.get("target_position") is not None for r in after):
                return "verified", evidence
        return ("unchanged" if later else None), evidence
    if kind == "propose_schema":
        page_ids = set(row.get("page_ids") or [])
        pages = {p["id"]: p for p in project.get("pages", [])}
        for page_id in page_ids:
            page = pages.get(page_id)
            if not page:
                continue
            stream = _page_stream(home, page["url"])
            records = read_jsonl(stream)
            after = [r for r in records if (_parse_ts(r.get("ts")) or created) > created]
            if not after:
                continue
            later = True
            rel = str(stream.relative_to(home)) if stream.is_relative_to(home) else str(stream)
            evidence.append(rel)
            if after[-1].get("jsonld_types"):
                return "verified", evidence
        return ("unchanged" if later else None), evidence
    return (None, evidence)


def _proposal_markdown(action: Dict[str, Any], project: Dict[str, Any]) -> str:
    ident = project["project"]["id"]
    lines = [
        f"# Decision proposal: {action['kind']}",
        "",
        f"- project: `{ident}`",
        f"- kind: `{action['kind']}`",
        f"- next_gate: `{action['next_gate']}`",
        f"- auto_apply: `false`",
        f"- query_ids: {', '.join(action['query_ids']) or '—'}",
        f"- page_ids: {', '.join(action['page_ids']) or '—'}",
        "",
        "## Reason",
        "",
        action["reason"],
        "",
        "## Evidence",
        "",
    ]
    if action["evidence"]:
        lines.extend(f"- `{path}`" for path in action["evidence"])
    else:
        lines.append("- (none)")
    lines.extend(
        [
            "",
            "## Gate",
            "",
            "Owner must approve before any site edit, PR, merge, or deploy.",
            "Visible copy, prices, and CTAs are never auto-published.",
            "",
        ]
    )
    return "\n".join(lines)


def apply_decision(home: Path, project: Dict[str, Any], action: Dict[str, Any], now: Optional[datetime] = None) -> Dict[str, Any]:
    """Persist the ranked action. Never sets status=applied."""
    now = now or _now()
    result = dict(action)
    result["written"] = []
    stamp = now.strftime("%Y-%m-%dT%H:%MZ")
    if action["kind"] == "no_op":
        line = workspace.append_log("egeo-core", "decide", "no deterministic action, outcome=no-op", home=home)
        result["written"].append("LOG.md")
        result["log"] = line
        return result
    if action["kind"] == "wait_for_window":
        line = workspace.append_log(
            "egeo-core",
            "decide",
            f"{action['kind']}: {action['reason']}, outcome=no-op",
            home=home,
        )
        result["written"].append("LOG.md")
        result["log"] = line
        return result
    if action["kind"] == "grade_outcome":
        row = {
            "v": SCHEMA_VERSION,
            "id": f"{stamp}-grade-{_slug(action.get('ledger_id') or 'row')}",
            "ts": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "project_id": project["project"]["id"],
            "kind": "grade_outcome",
            "status": action.get("grade") or "unchanged",
            "query_ids": action["query_ids"],
            "page_ids": action["page_ids"],
            "evidence": action["evidence"],
            "windows_days": list(WINDOWS_DAYS),
            "grades": {},
            "next_gate": "none",
            "auto_apply": False,
            "graded_id": action.get("ledger_id"),
        }
        append_jsonl(ledger_path(home), row)
        line = workspace.append_log(
            "egeo-core",
            "decide",
            f"graded {action.get('ledger_id')} as {row['status']}, outcome=success",
            home=home,
        )
        result["written"].extend([str(LEDGER_REL), "LOG.md"])
        result["log"] = line
        result["ledger_row"] = row
        return result

    slug = _slug("-".join([action["kind"], *(action["query_ids"] or action["page_ids"] or ["item"])]))
    row = {
        "v": SCHEMA_VERSION,
        "id": f"{stamp}-{slug}",
        "ts": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "project_id": project["project"]["id"],
        "kind": action["kind"],
        "status": "proposed",
        "query_ids": action["query_ids"],
        "page_ids": action["page_ids"],
        "evidence": action["evidence"],
        "windows_days": list(WINDOWS_DAYS),
        "grades": {},
        "next_gate": action["next_gate"],
        "auto_apply": False,
    }
    append_jsonl(ledger_path(home), row)
    result["written"].append(str(LEDGER_REL))
    result["ledger_row"] = row
    if action["kind"] in OWNER_KINDS:
        doc_name = f"{now.strftime('%Y-%m-%d')}-decide-{slug}.md"
        doc_path = home / "docs" / doc_name
        doc_path.parent.mkdir(parents=True, exist_ok=True)
        doc_path.write_text(_proposal_markdown(action, project), encoding="utf-8")
        result["written"].append(f"docs/{doc_name}")
        result["proposal"] = str(doc_path)
    line = workspace.append_log(
        "egeo-core",
        "decide",
        f"{action['kind']} proposed ({row['id']}), outcome=success",
        home=home,
    )
    result["written"].append("LOG.md")
    result["log"] = line
    return result
