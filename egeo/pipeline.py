"""The runtime-agnostic ``optimize`` pipeline.

Orchestrates the four agents for a single piece of content:

    analyze → rank (before) → rewrite → fidelity gate → rank (after) → index → write artifacts

The fidelity gate (openspec ``update-optimize-page-fidelity``) checks the rewrite with the
deterministic rules in :mod:`egeo.fidelity`, asks the rewriter for one repair when they fail, and
keeps a rewrite that still fails out of ``optimized/`` (it goes to ``rejected/``).

Ranking needs something to rank *against*. Because the offline runtime cannot
ask an LLM to invent competitors, the pipeline ranks the target against a small
set of deterministic, clearly-labeled generic competitor stubs. This keeps the
pipeline runnable with no API key (and under ``GEO_EVAL_MOCK=1``) while still
producing a before/after ranking signal.
"""
from __future__ import annotations

import html
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from geo_eval import Candidate

from . import fidelity
from .agents import CONTENT_TYPES, AnalysisResult, RankResult, RewriteResult, SchemaResult
from .runtimes import RuntimeAdapter

__all__ = [
    "OptimizeResult",
    "optimize_content",
    "detect_content_type",
    "check_page_fidelity",
    "DEFAULT_COMPETITORS",
    "ARTICLE_MIN_WORDS",
    "ARTICLE_MIN_HEADINGS",
]

# `--content-type auto`: a body this long, or with this many headings, is an article.
ARTICLE_MIN_WORDS = 150
ARTICLE_MIN_HEADINGS = 3
# Rules of egeo.fidelity that do not apply to a whole page body: the body has no fixed heading
# line (the H1 is handled separately), and a thin page is meant to grow.
_PAGE_IGNORED_RULES = ("heading_changed", "too_long")
_LIST_MARKER = re.compile(r"^(\s*(?:>\s*)*)\d+[.)](?=\s)", re.MULTILINE)
_FENCE = re.compile(r"^\s*(`{3,}|~{3,})")


def detect_content_type(body: str) -> str:
    """``article`` for a body with >= 150 words or >= 3 headings, else ``product``."""
    words, headings, in_code = 0, 0, False
    for line in body.splitlines():
        if _FENCE.match(line):
            in_code = not in_code
            continue
        if in_code:
            continue
        if re.match(r"^#{1,6}[ \t]", line):
            headings += 1
        words += len(re.findall(r"\w+", line))
    return "article" if words >= ARTICLE_MIN_WORDS or headings >= ARTICLE_MIN_HEADINGS else "product"


def _strip_list_markers(text: str) -> str:
    """Drop ordered-list markers (``1.``, ``2)``) outside code blocks: they are layout, not facts."""
    out, in_code = [], False
    for line in text.split("\n"):
        if _FENCE.match(line):
            in_code = not in_code
        out.append(line if in_code else _LIST_MARKER.sub(r"\1-", line))
    return "\n".join(out)


def check_page_fidelity(original: str, rewritten: str) -> fidelity.FidelityResult:
    """Deterministic fidelity rules for a whole page body.

    Same rules as section mode, except ``heading_changed`` and ``too_long`` are not applied and
    ordered-list markers are not counted as numbers.
    """
    result = fidelity.check_fidelity(_strip_list_markers(original), _strip_list_markers(rewritten))
    kept = tuple(v for v in result.violations if v not in _PAGE_IGNORED_RULES)
    return fidelity.FidelityResult(passed=not kept, violations=kept)

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
    content_type: str = "product"
    # {"status": passed|repaired|rejected|lossy_allowed, "violations": [...], "attempts": 1|2,
    #  "first_attempt_violations": [...]}
    fidelity: Optional[Dict[str, Any]] = None

    @property
    def rewrite_accepted(self) -> bool:
        return not self.fidelity or self.fidelity["status"] != "rejected"

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
            "content_type": self.content_type,
            "fidelity": self.fidelity,
            "output_dir": str(self.output_dir),
            "written_files": [str(p) for p in self.written_files],
        }


def _slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or "content"


def _extract_frontmatter(text: str) -> tuple[str, str, Dict[str, Any]]:
    """Extract frontmatter (YAML or TOML), returning (raw_frontmatter, body, parsed_dict)."""
    m = re.match(r"^(---|(?:\+\+\+))\s*\n(.*?)\n\1\s*(?:\n|$)", text, re.DOTALL)
    if not m:
        return "", text, {}

    delimiter = m.group(1)
    content_fm = m.group(2)
    raw = text[:m.end()]
    body = text[m.end():]
    parsed: Dict[str, Any] = {}
    try:
        if delimiter == "+++":
            try:
                import tomllib
                data = tomllib.loads(content_fm)
            except ImportError:
                import tomli as tomllib
                data = tomllib.loads(content_fm)
            if isinstance(data, dict):
                parsed = data
        else:
            import yaml
            data = yaml.safe_load(content_fm)
            if isinstance(data, dict):
                parsed = data
    except Exception:
        pass
    return raw, body, parsed


def _derive_title_and_body(content: str) -> tuple[str, str, str, Dict[str, Any]]:
    raw_frontmatter, body, parsed_fm = _extract_frontmatter(content)
    lines = body.splitlines()
    title = ""
    body_start = 0

    if parsed_fm.get("title"):
        title = str(parsed_fm["title"]).strip()

    for i, ln in enumerate(lines):
        if ln.strip().startswith("#"):
            if not title:
                title = ln.lstrip("#").strip()
            body_start = i + 1
            break
        if ln.strip():
            if not title:
                title = ln.strip()
            body_start = i + 1
            break
    description = "\n".join(lines[body_start:]).strip() or body.strip()
    if not title:
        title = "Untitled"
    return title, description, raw_frontmatter, parsed_fm


def _markdown_to_html(md_text: str, title: str = "", metadata: Optional[Dict[str, Any]] = None) -> str:
    """Convert markdown text to clean semantic HTML while preserving formatting and metadata."""
    try:
        import markdown
        html_body = markdown.markdown(md_text, extensions=["extra", "codehilite"])
    except ImportError:
        html_body = _basic_markdown_to_html(md_text)

    page_title = html.escape(
        str(title or (metadata.get("title") if metadata else None) or "Optimized Content")
    )
    meta_tags = []
    if metadata:
        if metadata.get("description"):
            meta_tags.append(f'  <meta name="description" content="{html.escape(str(metadata["description"]))}">')
        if metadata.get("author"):
            meta_tags.append(f'  <meta name="author" content="{html.escape(str(metadata["author"]))}">')
        if metadata.get("tags"):
            tags_val = ", ".join(metadata["tags"]) if isinstance(metadata["tags"], list) else str(metadata["tags"])
            meta_tags.append(f'  <meta name="keywords" content="{html.escape(tags_val)}">')
        if metadata.get("date"):
            meta_tags.append(f'  <meta name="date" content="{html.escape(str(metadata["date"]))}">')
    meta_tags_str = ("\n" + "\n".join(meta_tags)) if meta_tags else ""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta name="generator" content="eGEOagents">{meta_tags_str}
  <title>{page_title}</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; line-height: 1.6; max-width: 800px; margin: 40px auto; padding: 0 20px; color: #24292e; }}
    h1, h2, h3, h4 {{ margin-top: 24px; margin-bottom: 16px; font-weight: 600; line-height: 1.25; }}
    h1 {{ font-size: 2em; border-bottom: 1px solid #eaecef; padding-bottom: 0.3em; }}
    h2 {{ font-size: 1.5em; border-bottom: 1px solid #eaecef; padding-bottom: 0.3em; }}
    blockquote {{ padding: 0 1em; color: #6a737d; border-left: 0.25em solid #dfe2e5; margin: 16px 0; }}
    code {{ padding: 0.2em 0.4em; margin: 0; font-size: 85%; background-color: rgba(27,31,35,0.05); border-radius: 3px; font-family: monospace; }}
    pre {{ padding: 16px; overflow: auto; font-size: 85%; line-height: 1.45; background-color: #f6f8fa; border-radius: 3px; }}
    pre code {{ background-color: transparent; padding: 0; }}
    table {{ border-collapse: collapse; width: 100%; margin: 16px 0; }}
    th, td {{ border: 1px solid #dfe2e5; padding: 6px 13px; text-align: left; }}
    th {{ background-color: #f6f8fa; font-weight: 600; }}
    ol, ul {{ padding-left: 2em; margin: 16px 0; }}
  </style>
</head>
<body>
<article>
{html_body}
</article>
</body>
</html>
"""


def _basic_markdown_to_html(md_text: str) -> str:
    """Built-in lightweight markdown to HTML converter supporting headings, lists, tables, and blockquotes."""
    lines = md_text.splitlines()
    html_lines = []
    in_ul = False
    in_ol = False
    in_blockquote = False
    in_code_block = False
    in_table = False

    def close_blocks():
        nonlocal in_ul, in_ol, in_blockquote, in_table
        if in_ul:
            html_lines.append("</ul>")
            in_ul = False
        if in_ol:
            html_lines.append("</ol>")
            in_ol = False
        if in_blockquote:
            html_lines.append("</blockquote>")
            in_blockquote = False
        if in_table:
            html_lines.append("</tbody></table>")
            in_table = False

    for line in lines:
        stripped = line.strip()

        if stripped.startswith("```"):
            if in_code_block:
                html_lines.append("</code></pre>")
                in_code_block = False
            else:
                close_blocks()
                html_lines.append("<pre><code>")
                in_code_block = True
            continue

        if in_code_block:
            html_lines.append(line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))
            continue

        if not stripped:
            close_blocks()
            continue

        h_match = re.match(r"^(#{1,6})\s+(.*)$", stripped)
        if h_match:
            close_blocks()
            level = len(h_match.group(1))
            h_content = _inline_md_to_html(h_match.group(2))
            html_lines.append(f"<h{level}>{h_content}</h{level}>")
            continue

        # Tables: | Col 1 | Col 2 |
        if stripped.startswith("|") and stripped.endswith("|"):
            if re.match(r"^\|[\s\-:|]+\|$", stripped):
                # Separator row (|---|---|)
                continue
            cells = [c.strip() for c in stripped.strip("|").split("|")]
            if not in_table:
                close_blocks()
                html_lines.append("<table>")
                html_lines.append("<thead><tr>")
                for cell in cells:
                    html_lines.append(f"<th>{_inline_md_to_html(cell)}</th>")
                html_lines.append("</tr></thead>")
                html_lines.append("<tbody>")
                in_table = True
            else:
                html_lines.append("<tr>")
                for cell in cells:
                    html_lines.append(f"<td>{_inline_md_to_html(cell)}</td>")
                html_lines.append("</tr>")
            continue

        if stripped.startswith(">"):
            if in_ul or in_ol or in_table:
                close_blocks()
            if not in_blockquote:
                html_lines.append("<blockquote>")
                in_blockquote = True
            bq_text = _inline_md_to_html(stripped.lstrip("> ").strip())
            html_lines.append(f"<p>{bq_text}</p>")
            continue

        # Unordered list: - or * or +
        if re.match(r"^[-*+]\s+", stripped):
            if in_blockquote or in_ol or in_table:
                close_blocks()
            if not in_ul:
                html_lines.append("<ul>")
                in_ul = True
            item_text = _inline_md_to_html(re.sub(r"^[-*+]\s+", "", stripped))
            html_lines.append(f"<li>{item_text}</li>")
            continue

        # Ordered list: 1. or 2.
        ol_match = re.match(r"^\d+\.\s+", stripped)
        if ol_match:
            if in_blockquote or in_ul or in_table:
                close_blocks()
            if not in_ol:
                html_lines.append("<ol>")
                in_ol = True
            item_text = _inline_md_to_html(re.sub(r"^\d+\.\s+", "", stripped))
            html_lines.append(f"<li>{item_text}</li>")
            continue

        close_blocks()
        html_lines.append(f"<p>{_inline_md_to_html(stripped)}</p>")

    close_blocks()
    if in_code_block:
        html_lines.append("</code></pre>")

    return "\n".join(html_lines)


def _inline_md_to_html(text: str) -> str:
    """Format inline markdown elements: links, bold, italic, code."""
    t = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    t = re.sub(r"`([^`]+)`", r"<code>\1</code>", t)
    t = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"__([^_]+)__", r"<strong>\1</strong>", t)
    t = re.sub(r"\*([^*]+)\*", r"<em>\1</em>", t)
    t = re.sub(r"_([^_]+)_", r"<em>\1</em>", t)
    t = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', t)
    return t


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
    fid = result.fidelity or {"status": "passed", "violations": [], "attempts": 1}
    fid_lines = [f"- **Status:** `{fid['status']}` ({fid['attempts']} rewrite attempt(s))"]
    if fid["violations"]:
        fid_lines.append("- **Violations:**")
        fid_lines.extend(f"  - `{v}`" for v in fid["violations"])
    if fid["status"] == "rejected":
        fid_lines.append(
            "- The rewrite changed facts or dropped content, so it was **not** written to "
            "`optimized/`. It is in `rejected/` for manual review; merge what is useful by hand. "
            "The rank below is unchanged because no rewrite was accepted."
        )
    elif fid["status"] == "lossy_allowed":
        fid_lines.append("- Written to `optimized/` because `--allow-lossy` was set. Review it against the original.")
    elif fid["status"] == "repaired":
        fid_lines.append("- The first rewrite failed the rules; the repair attempt passed.")
    fidelity_block = "\n".join(fid_lines)
    outputs_first = (
        "- `rejected/` — the rewrite that failed the fidelity rules (not for publishing)"
        if fid["status"] == "rejected"
        else "- `optimized/` — GEO-optimized content (copy-paste ready)"
    )

    return f"""# 🎯 GEO Optimization Report

- **Source:** `{result.source}`
- **Title:** {result.title}
- **Runtime:** `{result.runtime}`
- **Content type:** `{result.content_type}`
- **GEO Score:** {a.total_score}/100

## Rewrite Fidelity

Deterministic rules: no link or number removed or added, tables and code blocks kept, at least
80% of the original length. They cannot see a new unsupported adjective or a dropped sentence
that has no link or number, so still read the rewrite against the original.

{fidelity_block}

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

{outputs_first}
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
    export_format: str = "markdown",
    content_type: str = "auto",
    allow_lossy: bool = False,
) -> OptimizeResult:
    """Run analyze → rank → rewrite → fidelity gate → rank → index and write artifacts."""
    title, description, raw_frontmatter, parsed_fm = _derive_title_and_body(content)
    effective_query = query or f"best {title}".strip()
    if content_type == "auto":
        content_type = detect_content_type(description)
    elif content_type not in CONTENT_TYPES:
        raise ValueError(f"Unknown content type '{content_type}'. Known: auto, {', '.join(CONTENT_TYPES)}")

    analyzer = runtime.make_analyzer()
    ranker = runtime.make_ranker()
    rewriter = runtime.make_rewriter(content_type)
    indexer = runtime.make_indexer()

    analysis = analyzer.analyze(content, title=title)

    competitors = [Candidate(id=c["id"], title=c["title"], description=c["description"]) for c in DEFAULT_COMPETITORS]
    target_before = Candidate(id=_TARGET_ID, title=title, description=description)
    before = ranker.rank(effective_query, [target_before, *competitors])
    rank_before = before.position_of(_TARGET_ID)

    rewrite = rewriter.rewrite(title, description)
    check = check_page_fidelity(description, rewrite.rewritten_description)
    fid: Dict[str, Any] = {"status": "passed", "violations": [], "attempts": 1}
    if not check.passed:
        fid["first_attempt_violations"] = list(check.violations)
        repaired = rewriter.rewrite(
            title, description, previous=rewrite.rewritten_description, violations=check.violations
        )
        recheck = check_page_fidelity(description, repaired.rewritten_description)
        fid["attempts"] = 2
        if recheck.passed:
            rewrite, fid["status"] = repaired, "repaired"
        else:
            # Keep whichever attempt broke fewer rules, for the reviewer.
            if len(recheck.violations) <= len(check.violations):
                rewrite, check = repaired, recheck
            fid["violations"] = list(check.violations)
            fid["status"] = "lossy_allowed" if allow_lossy else "rejected"
    accepted = fid["status"] != "rejected"

    if accepted:
        target_after = Candidate(id=_TARGET_ID, title=title, description=rewrite.rewritten_description)
        after = ranker.rank(effective_query, [target_after, *competitors])
        rank_after = after.position_of(_TARGET_ID)
    else:
        rank_after = rank_before  # nothing was accepted, so nothing changed

    schema = indexer.generate_schema(
        schema_type=schema_type,
        name=title,
        description=_short_description(rewrite.rewritten_description if accepted else description),
    )

    # --- write artifacts --------------------------------------------------- #
    output_dir = Path(output_dir)
    slug = _slugify(title)
    optimized_dir = output_dir / ("optimized" if accepted else "rejected")
    schema_out_dir = output_dir / "schema"
    optimized_dir.mkdir(parents=True, exist_ok=True)
    schema_out_dir.mkdir(parents=True, exist_ok=True)

    written: List[Path] = []

    body_md = f"# {title}\n\n{rewrite.rewritten_description}\n"
    if raw_frontmatter:
        full_md = f"{raw_frontmatter.rstrip()}\n\n{body_md}"
    else:
        full_md = body_md

    if export_format == "html":
        optimized_path = optimized_dir / f"{slug}.html"
        html_content = _markdown_to_html(
            f"# {title}\n\n{rewrite.rewritten_description}",
            title=title,
            metadata=parsed_fm,
        )
        optimized_path.write_text(html_content, encoding="utf-8")
    else:
        optimized_path = optimized_dir / f"{slug}.md"
        optimized_path.write_text(full_md, encoding="utf-8")
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
        "content_type": content_type,
        "fidelity": fid,
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
        content_type=content_type,
        fidelity=fid,
    )

    report_path = output_dir / "report.md"
    report_path.write_text(_build_report(result), encoding="utf-8")
    written.insert(0, report_path)
    result.written_files = written

    return result
