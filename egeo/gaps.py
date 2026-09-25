"""``egeo fix-gaps``: turn a tracker's citation gaps into page rewrites.

Reads a tracker export (geo-optimizer-skill ``geo citations --format json`` or a
generic ``query``/``cited`` JSON/CSV), maps each uncited query to a local page
through ``project.yaml`` (``queries[].target_pages`` → ``pages[].source``) and
optimizes each affected page once with :func:`egeo.pipeline.optimize_content`.
Source files are never modified. See ``openspec/changes/add-fix-gaps``.
"""
from __future__ import annotations

import csv
import json
import re
import shlex
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from . import workspace

GEO_OPTIMIZER_SKILL = "geo-optimizer-skill"
GENERIC = "generic"

REPORT_NAME = "fix-gaps.json"
PROXY_NOTE = (
    "rank_before/rank_after come from E-GEO's LLM-ranker proxy, not from a live answer engine. "
    "Re-check the queries in `remeasure` with your tracker to confirm real citation changes."
)
_FORMAT_HELP = (
    "Unsupported gaps file. Expected either geo-optimizer-skill output "
    "(`geo citations --format json`: an object with `entries[]` holding `query` and `domain_cited`) "
    "or a generic gaps file (JSON array or CSV with `query` and `cited` fields, optional `sources`)."
)
_FALSE = {"false", "0", "no", "n", ""}


class GapsFormatError(ValueError):
    """Raised when a gaps file matches neither supported format."""


@dataclass
class Gap:
    query: str
    sources: List[str] = field(default_factory=list)


@dataclass
class GapsInput:
    format: str
    gaps: List[Gap]
    skipped: List[Dict[str, str]]
    domain: str = ""
    brand: str = ""


@dataclass
class PagePlan:
    page_id: str
    source: Path
    query: str
    other_gaps: List[str] = field(default_factory=list)


@dataclass
class FixPlan:
    input: GapsInput
    pages: List[PagePlan]
    unmatched: List[Dict[str, str]]

    @property
    def skipped(self) -> List[Dict[str, str]]:
        return self.input.skipped


def normalize_query(text: str) -> str:
    """Lowercase, trim, collapse whitespace and drop trailing punctuation."""
    text = re.sub(r"\s+", " ", str(text or "").strip().lower())
    return re.sub(r"[\s?!.,;:¿¡]+$", "", text)


def _is_cited(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    return str(value).strip().lower() not in _FALSE


def _sources(value: Any) -> List[str]:
    if isinstance(value, list):
        return [str(v) for v in value if str(v).strip()]
    return [s for s in re.split(r"[\s;|]+", str(value or "")) if s]


def _generic_rows(rows: List[Dict[str, Any]]) -> GapsInput:
    found = [
        Gap(query=str(row["query"]), sources=_sources(row.get("sources")))
        for row in rows
        if str(row.get("query") or "").strip() and not _is_cited(row.get("cited", False))
    ]
    return GapsInput(format=GENERIC, gaps=found, skipped=[])


def load_gaps(path: Path) -> GapsInput:
    """Load and auto-detect a gaps file."""
    path = Path(path)
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".csv":
        rows = list(csv.DictReader(text.splitlines()))
        if not rows or "query" not in rows[0] or "cited" not in rows[0]:
            raise GapsFormatError(_FORMAT_HELP)
        return _generic_rows(rows)
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise GapsFormatError(f"{_FORMAT_HELP} ({exc})") from exc

    if isinstance(data, dict) and isinstance(data.get("entries"), list) and all(
        isinstance(e, dict) and "query" in e and "domain_cited" in e for e in data["entries"]
    ):
        found: List[Gap] = []
        skipped: List[Dict[str, str]] = []
        for entry in data["entries"]:
            if entry.get("error"):
                skipped.append({"query": str(entry["query"]), "reason": "tracker_error"})
            elif not entry.get("domain_cited"):
                found.append(Gap(query=str(entry["query"]), sources=_sources(entry.get("cited_sources"))))
        return GapsInput(
            format=GEO_OPTIMIZER_SKILL, gaps=found, skipped=skipped,
            domain=str(data.get("domain") or ""), brand=str(data.get("brand") or ""),
        )
    if isinstance(data, list) and data and all(isinstance(r, dict) and "query" in r for r in data):
        return _generic_rows(data)
    raise GapsFormatError(_FORMAT_HELP)


def load_project_file(path: Path) -> Dict[str, Any]:
    """Load and validate a ``project.yaml`` at an explicit path."""
    return workspace.load_project_file(Path(path))


def plan_fixes(gaps_input: GapsInput, project: Dict[str, Any], project_dir: Path) -> FixPlan:
    """Map gaps to pages. Never guesses: unmapped gaps carry a reason."""
    queries = {
        normalize_query(q.get("text", "")): q
        for q in project.get("queries", [])
        if q.get("active", True) and q.get("text")
    }
    pages = {p["id"]: p for p in project.get("pages", []) if p.get("active", True)}
    planned: Dict[str, PagePlan] = {}
    unmatched: List[Dict[str, str]] = []

    for gap in gaps_input.gaps:
        query = queries.get(normalize_query(gap.query))
        if query is None:
            unmatched.append({"query": gap.query, "reason": "query_not_in_project"})
            continue
        target_ids = [pid for pid in query.get("target_pages", []) if pid in pages]
        if not target_ids:
            unmatched.append({"query": gap.query, "reason": "no_target_page"})
            continue
        matched = False
        reason = "page_has_no_source"
        for page_id in target_ids:
            source = pages[page_id].get("source")
            if not source:
                continue
            source_path = (Path(project_dir) / source).resolve()
            if not source_path.is_file():
                reason = "source_not_found"
                continue
            matched = True
            if page_id in planned:
                planned[page_id].other_gaps.append(gap.query)
            else:
                planned[page_id] = PagePlan(page_id=page_id, source=source_path, query=gap.query)
        if not matched:
            unmatched.append({"query": gap.query, "reason": reason})
    return FixPlan(input=gaps_input, pages=list(planned.values()), unmatched=unmatched)


def _remeasure(plan: FixPlan) -> Dict[str, Any]:
    queries = [g.query for g in plan.input.gaps]
    command = ""
    if plan.input.format == GEO_OPTIMIZER_SKILL and queries:
        parts = ["geo", "citations"]
        if plan.input.brand:
            parts += ["--brand", plan.input.brand]
        if plan.input.domain:
            parts += ["--domain", plan.input.domain]
        for q in queries:
            parts += ["--query", q]
        parts += ["--format", "json"]
        command = " ".join(shlex.quote(p) for p in parts)
    return {"queries": queries, "command": command}


def run_fix_gaps(
    plan: FixPlan,
    *,
    runtime: Any,
    out_dir: Path,
    export_format: str = "markdown",
    schema_type: str = "Article",
) -> Dict[str, Any]:
    """Optimize each planned page once and write ``fix-gaps.json``."""
    from .pipeline import optimize_content

    out_dir = Path(out_dir)
    results: List[Dict[str, Any]] = []
    for page in plan.pages:
        result = optimize_content(
            runtime=runtime,
            content=page.source.read_text(encoding="utf-8"),
            source=str(page.source),
            output_dir=out_dir / page.page_id,
            query=page.query,
            schema_type=schema_type,
            export_format=export_format,
        )
        summary = result.summary()
        results.append({
            "page_id": page.page_id,
            "source": str(page.source),
            "query": page.query,
            "other_gaps": page.other_gaps,
            "rank_before": summary["rank_before"],
            "rank_after": summary["rank_after"],
            "written_files": summary["written_files"],
        })
    report = {
        "format": plan.input.format,
        "pages": results,
        "unmatched": plan.unmatched,
        "skipped": plan.skipped,
        "remeasure": _remeasure(plan),
        "note": PROXY_NOTE,
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / REPORT_NAME).write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return report


def describe_plan(plan: FixPlan) -> str:
    lines = [f"Input format: {plan.input.format} — {len(plan.input.gaps)} gap(s)"]
    for page in plan.pages:
        extra = f" (+{len(page.other_gaps)} more: {', '.join(page.other_gaps)})" if page.other_gaps else ""
        lines.append(f"  optimize {page.page_id} ← {page.source} for \"{page.query}\"{extra}")
    for item in plan.unmatched:
        lines.append(f"  unmatched \"{item['query']}\": {item['reason']}")
    for item in plan.skipped:
        lines.append(f"  skipped \"{item['query']}\": {item['reason']}")
    return "\n".join(lines)


def default_project_path() -> Path:
    local = Path("project.yaml")
    return local if local.is_file() else workspace.project_config_path()


def cli(args: Any) -> int:
    import sys

    try:
        loaded = load_gaps(Path(args.gaps_file))
    except (GapsFormatError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    project_path = Path(args.project) if args.project else default_project_path()
    try:
        project = load_project_file(project_path)
    except (workspace.ProjectConfigError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    plan = plan_fixes(loaded, project, project_path.parent)

    if args.dry_run:
        if args.json:
            print(json.dumps({
                "format": loaded.format,
                "pages": [{"page_id": p.page_id, "source": str(p.source), "query": p.query,
                           "other_gaps": p.other_gaps} for p in plan.pages],
                "unmatched": plan.unmatched,
                "skipped": plan.skipped,
            }, indent=2, ensure_ascii=False))
        else:
            print(describe_plan(plan))
        return 0

    from .runtimes import get_runtime

    runtime = get_runtime(
        args.runtime, ranker_model=args.ranker_model,
        rewriter_model=args.rewriter_model, temperature=args.temperature,
    )
    if not runtime.executes_in_process:
        print(f"ERROR: runtime '{runtime.name}' does not execute in-process. Use --runtime python.", file=sys.stderr)
        return 2
    report = run_fix_gaps(plan, runtime=runtime, out_dir=Path(args.out_dir), export_format=args.format)
    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return 0
    print(describe_plan(plan))
    for page in report["pages"]:
        print(f"✓ {page['page_id']}: rank #{page['rank_before']} → #{page['rank_after']} (proxy)")
    print(f"Report: {Path(args.out_dir) / REPORT_NAME}")
    if report["remeasure"]["command"]:
        print(f"Re-measure: {report['remeasure']['command']}")
    return 0


def add_parser(sub: Any) -> None:
    import os

    p = sub.add_parser("fix-gaps", help="Rewrite the pages that lose queries in a tracker's citation report.")
    p.add_argument("gaps_file", help="geo-optimizer-skill `geo citations --format json` output, or a generic JSON/CSV gaps file.")
    p.add_argument("--project", default=None, help="Path to project.yaml (default: ./project.yaml, else $EGEO_HOME/project.yaml).")
    p.add_argument("--out-dir", default="fix-gaps-output", help="Output directory (default: fix-gaps-output).")
    p.add_argument("--format", default="markdown", choices=["markdown", "html"], help="Export format for optimized pages.")
    p.add_argument("--dry-run", action="store_true", help="Print the plan; write nothing and call no model.")
    p.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    p.add_argument("--runtime", default="python", help="Runtime to use (default: python).")
    p.add_argument("--ranker-model", default=os.environ.get("RANKER_MODEL", "gpt-4o"))
    p.add_argument("--rewriter-model", default=os.environ.get("REWRITER_MODEL", "gpt-4o"))
    p.add_argument("--temperature", type=float, default=0.0)
