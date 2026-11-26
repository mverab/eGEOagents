"""Deterministic loop decision layer: rank one next action, never apply.

LLM-free. Reads project.yaml, collector JSONL, and an append-only outcome
ledger. Writes at most one proposed ledger row, one proposal doc, and one
LOG.md line. Never publishes, merges, or sets status ``applied``.

The ledger is never rewritten. A proposal's effective state (applied time,
grades, closed) is derived by :func:`ledger_state`, which folds later event
lines (``grade_outcome``, ``mark_applied``, ``mark_withdrawn``) onto it. Only
the owner records ``applied``, through :func:`mark_row` (``egeo loop mark``).
"""
from __future__ import annotations

import json
import re
import shlex
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from . import workspace

LEDGER_REL = Path("data") / "outcomes" / "ledger.jsonl"
SCHEMA_VERSION = 1
WINDOWS_DAYS = (7, 14, 28)
OPEN_STATUSES = {"proposed", "applied"}
OWNER_KINDS = {"escalate_uncited", "escalate_absent", "propose_page_owner", "propose_schema"}
# escalate_uncited: how many consecutive AI Overview observations must leave the target out,
# and how many competing domains the proposal lists.
UNCITED_MIN_OBSERVATIONS = 3
CITED_INSTEAD_LIMIT = 5
GRADE_KIND = "grade_outcome"
MARK_KINDS = {"applied": "mark_applied", "withdrawn": "mark_withdrawn"}
# Grades that end a proposal before its last window.
TERMINAL_GRADES = {"verified", "resolved_unattributed"}
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


class LedgerError(ValueError):
    """Raised when an owner mark cannot be recorded."""


def _legacy_window(anchor: Optional[datetime], graded_at: Optional[datetime]) -> int:
    """Window for a 2.4.0 grade line, which has no ``window`` field."""
    if not anchor or not graded_at:
        return WINDOWS_DAYS[0]
    age = (graded_at - anchor).days
    reached = [d for d in WINDOWS_DAYS if age >= d]
    return reached[-1] if reached else WINDOWS_DAYS[0]


def ledger_state(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Fold event lines onto their proposals. Returns one state per proposal, in file order.

    Each state is a copy of the proposal line with the effective ``status`` and ``grades``
    plus ``created``, ``applied_ts``, ``anchor`` (datetimes) and ``closed``.
    """
    states: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        kind = row.get("kind")
        if kind in OWNER_KINDS:
            ident = str(row.get("id") or "")
            if not ident or ident in states:
                continue
            state = dict(row)
            created = _parse_ts(row.get("ts"))
            status = str(row.get("status") or "proposed")
            applied_ts = _parse_ts(row.get("applied_ts")) or (created if status == "applied" else None)
            state.update(
                status=status,
                grades={int(k): v for k, v in (row.get("grades") or {}).items() if str(k).isdigit()},
                created=created,
                applied_ts=applied_ts,
            )
            states[ident] = state
            continue
        if kind == GRADE_KIND:
            state = states.get(str(row.get("graded_id") or ""))
            if state is None:
                continue
            window = row.get("window")
            if not isinstance(window, int) or isinstance(window, bool):
                window = _legacy_window(state["applied_ts"] or state["created"], _parse_ts(row.get("ts")))
            state["grades"][window] = str(row.get("status") or "unchanged")
            continue
        if kind in MARK_KINDS.values():
            state = states.get(str(row.get("target_id") or ""))
            if state is None or state["status"] == "withdrawn":
                continue
            if kind == MARK_KINDS["withdrawn"]:
                state["status"] = "withdrawn"
            elif state["applied_ts"] is None:
                state["status"] = "applied"
                state["applied_ts"] = _parse_ts(row.get("ts"))
                # Grades recorded before the application measured the untouched page.
                state["pre_application_grades"] = state["grades"]
                state["grades"] = {}
    out = []
    for state in states.values():
        grades = state["grades"]
        state["anchor"] = state["applied_ts"] or state["created"]
        final = next((g for _, g in sorted(grades.items()) if g in TERMINAL_GRADES), None)
        if final is None and WINDOWS_DAYS[-1] in grades:
            final = grades[WINDOWS_DAYS[-1]]
        if state["status"] in OPEN_STATUSES and final is not None:
            state["status"] = final
        state["closed"] = state["status"] not in OPEN_STATUSES
        out.append(state)
    return out


def _due_window(state: Dict[str, Any], now: datetime) -> Optional[int]:
    """Latest window reached and not yet covered by a grade, or None."""
    anchor = state.get("anchor")
    if not anchor:
        return None
    age = (now - anchor).days
    done = max(state["grades"], default=0)
    due = [d for d in WINDOWS_DAYS if d <= age and d > done]
    return due[-1] if due else None


def _stream_slug(value: str, max_length: int = 60) -> str:
    value = re.sub(r"^https?://", "", value.strip().lower())
    value = re.sub(r"[^a-z0-9]+", "-", value).strip("-")
    return (value[:max_length].rstrip("-") or "untitled")


def _query_stream(home: Path, text: str) -> Path:
    return workspace.data_dir("serp", home) / f"{_stream_slug(text)}.jsonl"


def _overview_stream(home: Path, text: str) -> Path:
    return workspace.data_dir("ai_overview", home) / f"{_stream_slug(text)}.jsonl"


def _cited_instead(records: List[Dict[str, Any]], target_domain: str) -> List[Dict[str, Any]]:
    """Domains cited across ``records``, most frequent first. Counts observations, not links."""
    target = (target_domain or "").lower()
    counts: Dict[str, int] = {}
    for record in records:
        seen = set()
        for citation in record.get("citations") or []:
            domain = str((citation or {}).get("domain") or "").lower()
            if not domain or domain in seen or (target and (domain == target or domain.endswith("." + target))):
                continue
            seen.add(domain)
            counts[domain] = counts.get(domain, 0) + 1
    ranked = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:CITED_INSTEAD_LIMIT]
    return [{"domain": domain, "observations": count} for domain, count in ranked]


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


def _open_keys(states: List[Dict[str, Any]]) -> set:
    return {
        _key(str(row.get("kind") or ""), list(row.get("query_ids") or []), list(row.get("page_ids") or []))
        for row in states
        if not row["closed"]
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
    window: Optional[int] = None,
    details: Optional[Dict[str, Any]] = None,
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
        "window": window,
        "details": details or {},
        "auto_apply": False,
    }


def rank_action(home: Path, project: Dict[str, Any], now: Optional[datetime] = None) -> Dict[str, Any]:
    """Return exactly one ranked action. Pure read except path resolution."""
    now = now or _now()
    states = ledger_state(load_ledger(home))
    open_keys = _open_keys(states)
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

    # 2. grade_outcome. An open proposal that is still waiting does not stop new proposals:
    # it only keeps its own kind+query/page from being proposed again (open_keys). The first
    # waiting one is reported as wait_for_window if nothing else is found below.
    waiting: Optional[Dict[str, Any]] = None
    for row in states:
        if row["closed"] or not row.get("anchor"):
            continue
        ids = dict(
            query_ids=list(row.get("query_ids") or []),
            page_ids=list(row.get("page_ids") or []),
            ledger_id=str(row.get("id")),
        )
        window = _due_window(row, now)
        if window is None:
            age = (now - row["anchor"]).days
            nxt = next((d for d in WINDOWS_DAYS if d > max(age, max(row["grades"], default=0))), None)
            if waiting is None and nxt is not None:
                waiting = _action(
                    kind="wait_for_window",
                    reason=f"open {row.get('kind')} {row.get('id')} waiting for day {nxt}",
                    next_gate="none",
                    **ids,
                )
            continue
        grade, evidence = _grade_row(home, project, row)
        if grade is None:
            if waiting is None:
                waiting = _action(
                    kind="wait_for_window",
                    reason=f"window {window}d reached but no later observations for {row.get('id')}",
                    next_gate="scheduler",
                    **ids,
                )
            continue
        return _action(
            kind="grade_outcome",
            reason=f"window {window}d grade={grade} for {row.get('id')}",
            next_gate="none",
            evidence=evidence,
            grade=grade,
            window=window,
            **ids,
        )

    # 3. escalate_uncited: Google shows an AI Overview for the query and leaves the target out.
    # Observations with `available: false` (no AI Overview shown) say nothing about citation and
    # are skipped. A stream older than the cadence is stale and is not judged.
    for query in queries:
        stream = _overview_stream(home, query["text"])
        records = read_jsonl(stream)
        if not records or not records[-1].get("available"):
            continue
        latest = _parse_ts(records[-1].get("ts"))
        if latest is None or (now - latest) > timedelta(days=cadence):
            continue
        shown = [r for r in records if r.get("available")][-UNCITED_MIN_OBSERVATIONS:]
        if len(shown) < UNCITED_MIN_OBSERVATIONS or any(r.get("target_cited") for r in shown):
            continue
        key = _key("escalate_uncited", [query["id"]], list(query.get("target_pages") or []))
        if key in open_keys:
            continue
        rel = str(stream.relative_to(home)) if stream.is_relative_to(home) else str(stream)
        return _action(
            kind="escalate_uncited",
            reason=(
                f"query {query['id']!r} has an AI Overview that did not cite the target "
                f"in the last {UNCITED_MIN_OBSERVATIONS} observations that showed one"
            ),
            next_gate="owner",
            query_ids=[query["id"]],
            page_ids=list(query.get("target_pages") or []),
            evidence=[rel],
            details={
                "cited_instead": _cited_instead(shown, str(shown[-1].get("target_domain") or "")),
                "observations": [str(r.get("ts")) for r in shown],
            },
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

    if waiting is not None:
        return waiting
    return _action(kind="no_op", reason="no deterministic action", next_gate="none")


def _grade_row(home: Path, project: Dict[str, Any], row: Dict[str, Any]) -> Tuple[Optional[str], List[str]]:
    """Grade one folded proposal from observations after its anchor.

    ``verified`` needs an owner-recorded application, or an observation that is itself the
    proposed change. A metric that moved with no recorded application is ``resolved_unattributed``.
    Returns ``(None, evidence)`` when there is nothing to grade from yet.
    """
    kind = row.get("kind")
    anchor: datetime = row["anchor"]
    applied = row.get("applied_ts") is not None
    evidence: List[str] = []
    later = False

    def _after(stream: Path) -> List[Dict[str, Any]]:
        found = [r for r in read_jsonl(stream) if (_parse_ts(r.get("ts")) or anchor) > anchor]
        if found:
            evidence.append(str(stream.relative_to(home)) if stream.is_relative_to(home) else str(stream))
        return found

    if kind == "escalate_uncited":
        query_ids = set(row.get("query_ids") or [])
        shown_later = False
        for query in project.get("queries", []):
            if query.get("id") not in query_ids:
                continue
            after = _after(_overview_stream(home, query["text"]))
            if not after:
                continue
            later = True
            if any(r.get("available") and r.get("target_cited") for r in after):
                return ("verified" if applied else "resolved_unattributed"), evidence
            shown_later = shown_later or any(r.get("available") for r in after)
        if not later:
            return None, evidence
        # Every later pass showed no AI Overview at all: citation could not be observed.
        return ("unchanged" if shown_later else "unobservable"), evidence
    if kind == "escalate_absent":
        query_ids = set(row.get("query_ids") or [])
        for query in project.get("queries", []):
            if query.get("id") not in query_ids:
                continue
            after = _after(_query_stream(home, query["text"]))
            if not after:
                continue
            later = True
            if any(r.get("target_position") is not None for r in after):
                return ("verified" if applied else "resolved_unattributed"), evidence
        return ("unchanged" if later else None), evidence
    if kind == "propose_schema":
        pages = {p["id"]: p for p in project.get("pages", [])}
        for page_id in row.get("page_ids") or []:
            page = pages.get(page_id)
            if not page:
                continue
            after = _after(_page_stream(home, page["url"]))
            if not after:
                continue
            later = True
            if after[-1].get("jsonld_types"):
                return "verified", evidence
        return ("unchanged" if later else None), evidence
    if kind == "propose_page_owner":
        active_pages = {p["id"] for p in project.get("pages", []) if p.get("active", True)}
        query_ids = set(row.get("query_ids") or [])
        for query in project.get("queries", []):
            if query.get("id") in query_ids and any(t in active_pages for t in (query.get("target_pages") or [])):
                return "verified", [workspace.PROJECT_CONFIG_NAME]
        return "unchanged", [workspace.PROJECT_CONFIG_NAME]
    return (None, evidence)


def _proposal_markdown(action: Dict[str, Any], project: Dict[str, Any], ledger_id: str = "") -> str:
    ident = project["project"]["id"]
    lines = [
        f"# Decision proposal: {action['kind']}",
        "",
        f"- project: `{ident}`",
        f"- kind: `{action['kind']}`",
        f"- ledger_id: `{ledger_id or '—'}`",
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
    cited = (action.get("details") or {}).get("cited_instead") or []
    if action["kind"] == "escalate_uncited":
        lines.extend(["", "## Cited instead", ""])
        if cited:
            lines.append("Domains the AI Overview cited in those observations (number of observations):")
            lines.append("")
            lines.extend(f"- `{item['domain']}` ({item['observations']})" for item in cited)
        else:
            lines.append("- (the observations list no other cited domain)")
        lines.extend(
            [
                "",
                "This is what Google's AI Overview showed, as recorded by the collector. It does not say",
                "why those sources were chosen. Compare them with your page before changing anything.",
            ]
        )
    lines.extend(
        [
            "",
            "## Gate",
            "",
            "Owner must approve before any site edit, PR, merge, or deploy.",
            "Visible copy, prices, and CTAs are never auto-published.",
            "",
            "## After you act",
            "",
            "Record what happened so the outcome is graded from the right date:",
            "",
            "```bash",
            f"egeo loop mark {shlex.quote(ledger_id or '<ledger-id>')} applied     # you made the change",
            f"egeo loop mark {shlex.quote(ledger_id or '<ledger-id>')} withdrawn   # you decided not to",
            "```",
            "",
            "Without a recorded application, a later improvement is graded `resolved_unattributed`.",
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
            "id": f"{stamp}-grade-{action.get('window') or 0}d-{_slug(action.get('ledger_id') or 'row')}",
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
            "window": action.get("window"),
        }
        append_jsonl(ledger_path(home), row)
        line = workspace.append_log(
            "egeo-core",
            "decide",
            f"graded {action.get('ledger_id')} window {action.get('window')}d as {row['status']}, outcome=success",
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
    if action.get("details"):
        row["details"] = action["details"]
    append_jsonl(ledger_path(home), row)
    result["written"].append(str(LEDGER_REL))
    result["ledger_row"] = row
    if action["kind"] in OWNER_KINDS:
        doc_name = f"{now.strftime('%Y-%m-%d')}-decide-{slug}.md"
        doc_path = home / "docs" / doc_name
        doc_path.parent.mkdir(parents=True, exist_ok=True)
        doc_path.write_text(_proposal_markdown(action, project, row["id"]), encoding="utf-8")
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


def mark_row(
    home: Path,
    ledger_id: str,
    status: str,
    *,
    at: Optional[datetime] = None,
    note: str = "",
    now: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Owner action: record that a proposal was applied or withdrawn. Appends, never rewrites.

    ``at`` backdates an application; it must lie between the proposal time and ``now``.
    """
    now = now or _now()
    if status not in MARK_KINDS:
        raise LedgerError(f"status must be one of: {', '.join(sorted(MARK_KINDS))}")
    states = {str(s.get("id")): s for s in ledger_state(load_ledger(home))}
    state = states.get(ledger_id)
    if state is None:
        open_ids = [i for i, s in states.items() if not s["closed"]]
        hint = f" Open proposals: {', '.join(open_ids)}." if open_ids else " The ledger has no open proposals."
        raise LedgerError(f"no proposal with id {ledger_id!r}.{hint}")
    if state["closed"]:
        raise LedgerError(f"proposal {ledger_id!r} is already closed (status {state['status']})")
    if status == "applied" and state["applied_ts"] is not None:
        raise LedgerError(f"proposal {ledger_id!r} is already marked applied")
    when = now
    if at is not None:
        if status != "applied":
            raise LedgerError("--at only applies to `applied`")
        if at > now:
            raise LedgerError("--at is in the future")
        if state["created"] and at < state["created"]:
            raise LedgerError("--at is earlier than the proposal itself")
        when = at
    row = {
        "v": SCHEMA_VERSION,
        "id": f"{now.strftime('%Y-%m-%dT%H:%MZ')}-mark-{status}-{_slug(ledger_id)}",
        "ts": when.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "recorded_ts": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "project_id": state.get("project_id"),
        "kind": MARK_KINDS[status],
        "status": status,
        "target_id": ledger_id,
        "query_ids": list(state.get("query_ids") or []),
        "page_ids": list(state.get("page_ids") or []),
        "evidence": [],
        "note": note,
        "next_gate": "none",
        "auto_apply": False,
    }
    append_jsonl(ledger_path(home), row)
    line = workspace.append_log("egeo-core", "mark", f"{ledger_id} marked {status} by owner, outcome=success", home=home)
    return {"ledger_row": row, "written": [str(LEDGER_REL), "LOG.md"], "log": line}
