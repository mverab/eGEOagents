"""The runtime-agnostic ``optimize`` pipeline.

Orchestrates the four agents for a single piece of content:

    analyze → rank (before) → rewrite → rank (after) → index → write artifacts

Ranking needs something to rank *against*. Because the offline runtime cannot
ask an LLM to invent competitors, the pipeline ranks the target against a small
set of deterministic, clearly-labeled generic competitor stubs. This keeps the
pipeline runnable with no API key (and under ``GEO_EVAL_MOCK=1``) while still
producing a before/after ranking signal.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from geo_eval import Candidate

from .agents import AnalysisResult, RankResult, RewriteResult, SchemaResult
from .runtimes import RuntimeAdapter

__all__ = ["OptimizeResult", "optimize_content", "DEFAULT_COMPETITORS"]

# Deterministic, generic competitor stubs. They are intentionally plausible but
# synthetic; the report labels them as such. They never contain the "Best for"
# intent marker, so a rewritten target reliably gains a ranking edge offline.
DEFAULT_COMPETITORS: List[Dict[str, str]] = [
    {
        "id": "competitor_a",
        "title": "Established Market Leader",
        "description": (
            "A widely-used option in this category with broad feature coverage, "
            "long market presence, and a large existing customer base. Generalist "
            "positioning that targets many segments at once rather than a specific use case."
        ),
    },
    {
        "id": "competitor_b",
        "title": "Budget Alternative",
        "description": (
            "A low-cost entry-level alternative covering the basics. Limited depth, "
            "minimal differentiation, and generic messaging aimed at price-sensitive buyers."
        ),
    },
    {
        "id": "competitor_c",
        "title": "Niche Specialist",
        "description": (
            "A specialist tool focused on one narrow workflow. Strong in its niche "
            "but with gaps outside it and a steeper learning curve for new users."
        ),
    },
]

_TARGET_ID = "target"


@dataclass
class OptimizeResult:
    """Aggregated output of :func:`optimize_content`."""

    source: str
    title: str
    runtime: str
    analysis: AnalysisResult
    query: str
    rank_before: int
    rank_after: int
    rewrite: RewriteResult
    schema: SchemaResult
    output_dir: Path
    written_files: List[Path]

    @property
    def rank_improvement(self) -> int:
        return self.rank_before - self.rank_after

    def summary(self) -> Dict[str, Any]:
        return {
            "source": self.source,
            "title": self.title,
            "runtime": self.runtime,
            "query": self.query,
            "geo_score": self.analysis.total_score,
            "rank_before": self.rank_before,
            "rank_after": self.rank_after,
            "rank_improvement": self.rank_improvement,
            "output_dir": str(self.output_dir),
            "written_files": [str(p) for p in self.written_files],
        }


def _slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or "content"


def _strip_frontmatter_keep(text: str) -> str:
    m = re.match(r"^---\s*\n.*?\n---\s*(?:\n|$)", text, re.DOTALL)
    if m:
        return text[m.end():]
    return text


def _derive_title_and_body(content: str) -> tuple[str, str]:
    body = _strip_frontmatter_keep(content)
    lines = body.splitlines()
    title = ""
    body_start = 0
    for i, ln in enumerate(lines):
        if ln.strip().startswith("#"):
            title = ln.lstrip("#").strip()
            body_start = i + 1
            break
        if ln.strip():
            title = ln.strip()
            body_start = i + 1
            break
    description = "\n".join(lines[body_start:]).strip() or body.strip()
    if not title:
        title = "Untitled"
    return title, description


def _short_description(text: str, *, limit: int = 280) -> str:
    flat = re.sub(r"\s+", " ", text).strip()
    if len(flat) <= limit:
        return flat
    cut = flat[:limit]
    last_period = cut.rfind(". ")
    if last_period > 60:
        return cut[: last_period + 1]
    return cut.rstrip() + "…"


def _build_report(result: "OptimizeResult") -> str:
    a = result.analysis
    score_rows = "\n".join(
        f"| {feat.replace('_', ' ').title()} | {a.scores[feat]}/10 |" for feat in a.scores
    )
    gaps = "\n".join(f"- **{g['feature']}** — {g['recommendation']}" for g in a.gaps) or "- None 🎉"
    strengths = "\n".join(f"- {s.replace('_', ' ').title()}" for s in a.strengths) or "- (none detected)"
    actions = "\n".join(f"{i}. {act}" for i, act in enumerate(result.analysis.priority_actions, 1)) or "1. (none)"
    delta = result.rank_improvement
    delta_str = f"+{delta}" if delta > 0 else str(delta)

    return f"""# 🎯 GEO Optimization Report

- **Source:** `{result.source}`
- **Title:** {result.title}
- **Runtime:** `{result.runtime}`
- **GEO Score:** {a.total_score}/100

## Ranking Simulation

Simulated against {len(DEFAULT_COMPETITORS)} generic competitor stubs (synthetic, for illustration).

- **Query:** {result.query}
- **Rank before optimization:** #{result.rank_before}
- **Rank after optimization:** #{result.rank_after}
- **Improvement:** {delta_str} position(s)

## GEO Feature Scores

| Feature | Score |
|---------|-------|
{score_rows}

## Strengths

{strengths}

## Gaps & Recommendations

{gaps}

## Priority Actions

{actions}

## Outputs

- `optimized/` — GEO-optimized content (copy-paste ready)
- `schema/` — JSON-LD markup (`{result.schema.schema_type}`)
- `analysis.json` — raw analysis data

> **Honest scope:** competitor stubs and the analyzer score are an offline
> proxy, not a measurement of real AI-engine rankings. Use the Claude Code
> runtime with MCP validation, or the evaluation harness, for higher fidelity.
"""


def optimize_content(
    *,
    runtime: RuntimeAdapter,
    content: str,
    source: str,
    output_dir: Path,
    query: Optional[str] = None,
    schema_type: str = "Article",
) -> OptimizeResult:
    """Run analyze → rank → rewrite → rank → index and write artifacts."""
    title, description = _derive_title_and_body(content)
    effective_query = query or f"best {title}".strip()

    analyzer = runtime.make_analyzer()
    ranker = runtime.make_ranker()
    rewriter = runtime.make_rewriter()
    indexer = runtime.make_indexer()

    analysis = analyzer.analyze(content, title=title)

    competitors = [Candidate(id=c["id"], title=c["title"], description=c["description"]) for c in DEFAULT_COMPETITORS]
    target_before = Candidate(id=_TARGET_ID, title=title, description=description)
    before = ranker.rank(effective_query, [target_before, *competitors])
    rank_before = before.position_of(_TARGET_ID)

    rewrite = rewriter.rewrite(title, description)

    target_after = Candidate(id=_TARGET_ID, title=title, description=rewrite.rewritten_description)
    after = ranker.rank(effective_query, [target_after, *competitors])
    rank_after = after.position_of(_TARGET_ID)

    schema = indexer.generate_schema(
        schema_type=schema_type,
        name=title,
        description=_short_description(rewrite.rewritten_description),
    )

    # --- write artifacts --------------------------------------------------- #
    output_dir = Path(output_dir)
    slug = _slugify(title)
    optimized_dir = output_dir / "optimized"
    schema_out_dir = output_dir / "schema"
    optimized_dir.mkdir(parents=True, exist_ok=True)
    schema_out_dir.mkdir(parents=True, exist_ok=True)

    written: List[Path] = []

    optimized_path = optimized_dir / f"{slug}.md"
    optimized_path.write_text(
        f"# {title}\n\n{rewrite.rewritten_description}\n", encoding="utf-8"
    )
    written.append(optimized_path)

    schema_path = schema_out_dir / f"{slug}.json"
    schema_path.write_text(schema.to_json() + "\n", encoding="utf-8")
    written.append(schema_path)

    analysis_path = output_dir / "analysis.json"
    analysis_payload = {
        "source": source,
        "title": title,
        "runtime": runtime.name,
        "query": effective_query,
        "rank_before": rank_before,
        "rank_after": rank_after,
        "rank_improvement": rank_before - rank_after,
        "analysis": analysis.to_dict(),
    }
    analysis_path.write_text(json.dumps(analysis_payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    written.append(analysis_path)

    result = OptimizeResult(
        source=source,
        title=title,
        runtime=runtime.name,
        analysis=analysis,
        query=effective_query,
        rank_before=rank_before,
        rank_after=rank_after,
        rewrite=rewrite,
        schema=schema,
        output_dir=output_dir,
        written_files=written,
    )

    report_path = output_dir / "report.md"
    report_path.write_text(_build_report(result), encoding="utf-8")
    written.insert(0, report_path)
    result.written_files = written

    return result
