"""Runtime-agnostic abstractions for the four GEO agents.

The four agents mirror the Claude Code definitions in ``.claude/agents/`` but are
expressed here as plain Python objects so *any* runtime can construct and run
them:

- :class:`Analyzer`  — deterministic, offline GEO-signal scorer (no LLM).
- :class:`Ranker`    — thin wrapper over ``geo_eval._rank_candidates``.
- :class:`Rewriter`  — thin wrapper over ``geo_eval._rewrite_description``.
- :class:`Indexer`   — deterministic JSON-LD template filler (no LLM).

The Ranker and Rewriter deliberately delegate to ``geo_eval`` so there is a
single source of truth for ranking/rewriting logic and prompts. Analyzer and
Indexer are deterministic and offline, so the full pipeline runs without an API
key (and therefore under ``GEO_EVAL_MOCK=1`` in CI).
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

# Reuse the harness rather than re-implementing it. The package __init__ has
# already placed the repo root on sys.path so these imports resolve.
import geo_eval
from geo_eval import Candidate

__all__ = [
    "GEO_FEATURES",
    "AnalysisResult",
    "RankResult",
    "RewriteResult",
    "SchemaResult",
    "Analyzer",
    "Ranker",
    "Rewriter",
    "Indexer",
]

# The 10 universal GEO features (see openspec/project.md and AGENTS.md).
GEO_FEATURES: List[str] = [
    "ranking_emphasis",
    "user_intent",
    "competitive_diff",
    "social_proof",
    "narrative",
    "authority",
    "usps",
    "urgency",
    "scannable",
    "factual",
]

# Human-readable remediation copy used when a feature scores low.
_RECOMMENDATIONS: Dict[str, str] = {
    "ranking_emphasis": "Frame the content as a top/leading choice (e.g. 'best for ...').",
    "user_intent": "Open by directly answering the user's likely question or use case.",
    "competitive_diff": "Call out concrete advantages over typical alternatives (no competitor names needed).",
    "social_proof": "Add trust signals: customer counts, ratings, or testimonials (never fabricated).",
    "narrative": "Tighten the flow into a persuasive, benefit-led story.",
    "authority": "Add expert, confident phrasing and verifiable credentials or specifics.",
    "usps": "Make the unique selling points explicit and scannable as bullets.",
    "urgency": "Add a genuine urgency or scarcity signal where appropriate.",
    "scannable": "Add headings, bullet lists, and short paragraphs for easy parsing.",
    "factual": "Keep concrete, verifiable facts (numbers, units) and avoid vague hype.",
}


@dataclass
class AnalysisResult:
    """Output of :class:`Analyzer` — GEO-signal scores and gap analysis."""

    title: str
    content_length: int
    scores: Dict[str, int]
    total_score: int
    gaps: List[Dict[str, str]] = field(default_factory=list)
    strengths: List[str] = field(default_factory=list)
    priority_actions: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "content_length": self.content_length,
            "scores": self.scores,
            "total_score": self.total_score,
            "gaps": self.gaps,
            "strengths": self.strengths,
            "priority_actions": self.priority_actions,
        }


@dataclass
class RankResult:
    """Output of :class:`Ranker` — an ordering of candidate ids."""

    query: str
    ordered_ids: List[str]

    def position_of(self, candidate_id: str) -> int:
        """1-based position of ``candidate_id`` in the ordering."""
        return self.ordered_ids.index(candidate_id) + 1


@dataclass
class RewriteResult:
    """Output of :class:`Rewriter` — the optimized description."""

    title: str
    original_description: str
    rewritten_description: str


@dataclass
class SchemaResult:
    """Output of :class:`Indexer` — a JSON-LD document."""

    schema_type: str
    json_ld: Dict[str, Any]

    def to_json(self, *, indent: int = 2) -> str:
        return json.dumps(self.json_ld, indent=indent, ensure_ascii=False)


# --------------------------------------------------------------------------- #
# Analyzer (deterministic, offline)
# --------------------------------------------------------------------------- #


def _strip_frontmatter(text: str) -> str:
    """Remove a leading YAML/TOML frontmatter block if present."""
    m = re.match(r"^---\s*\n.*?\n---\s*(?:\n|$)", text, re.DOTALL)
    if m:
        return text[m.end():]
    m = re.match(r"^\+\+\+\s*\n.*?\n\+\+\+\s*(?:\n|$)", text, re.DOTALL)
    if m:
        return text[m.end():]
    return text


def _clamp(value: int, low: int = 0, high: int = 10) -> int:
    return max(low, min(high, value))


class Analyzer:
    """Score content against the 10 GEO features with a transparent heuristic.

    This is an *offline proxy* for the Claude ``geo-analyzer`` agent: it never
    calls an LLM, so it is deterministic and runs with no API key. It looks for
    the same signals the analyzer prompt describes (superlatives, intent, social
    proof, structure, etc.).
    """

    _RANKING_WORDS = ("best", "top", "#1", "number one", "leading", "premier", "ultimate", "trusted", "award")
    _INTENT_WORDS = ("best for", "ideal for", "designed for", "perfect for", "how to", "what is", "use case", "for businesses", "for teams")
    _DIFF_WORDS = ("unlike", "compared to", "vs ", "versus", "alternative", "unique", "differentiat", "better than", "outperform")
    _PROOF_WORDS = ("customer", "users", "rated", "rating", "review", "testimonial", "trusted by", "case study", "%", "stars")
    _AUTHORITY_WORDS = ("expert", "certified", "proven", "industry", "research", "years", "award-winning", "official", "data shows")
    _URGENCY_WORDS = ("now", "today", "limited", "offer", "hurry", "deadline", "while supplies", "act fast", "don't miss", "ends ")
    _NARRATIVE_WORDS = ("because", "so that", "imagine", "whether", "that's why", "which means", "helps you", "you can")

    def analyze(self, content: str, *, title: Optional[str] = None) -> AnalysisResult:
        body = _strip_frontmatter(content)
        lower = body.lower()
        lines = [ln for ln in body.splitlines()]
        non_empty = [ln for ln in lines if ln.strip()]
        words = re.findall(r"[A-Za-z0-9#%']+", lower)
        word_count = len(words)

        if not title:
            heading = next((ln for ln in lines if ln.strip().startswith("#")), "")
            title = heading.lstrip("#").strip() or (non_empty[0].strip() if non_empty else "Untitled")

        def keyword_score(keywords: Sequence[str], cap: int = 3) -> int:
            hits = sum(lower.count(k) for k in keywords)
            return _clamp(min(hits, cap) * (10 // cap) + (2 if hits else 0))

        bullets = sum(1 for ln in lines if ln.strip().startswith(("-", "*", "•")) or re.match(r"^\s*\d+\.", ln))
        headings = sum(1 for ln in lines if ln.strip().startswith("#"))
        numbers = len(re.findall(r"\b\d[\d,\.]*\b", body))

        scores: Dict[str, int] = {
            "ranking_emphasis": keyword_score(self._RANKING_WORDS),
            "user_intent": keyword_score(self._INTENT_WORDS),
            "competitive_diff": keyword_score(self._DIFF_WORDS),
            "social_proof": _clamp(keyword_score(self._PROOF_WORDS) + (2 if numbers >= 2 else 0)),
            "narrative": _clamp(keyword_score(self._NARRATIVE_WORDS) + (2 if word_count > 80 else 0)),
            "authority": keyword_score(self._AUTHORITY_WORDS),
            "usps": _clamp((6 if bullets >= 3 else bullets * 2) + (2 if "feature" in lower or "benefit" in lower else 0)),
            "urgency": keyword_score(self._URGENCY_WORDS),
            "scannable": _clamp((4 if headings >= 1 else 0) + (4 if bullets >= 2 else bullets * 2) + (2 if len(non_empty) >= 4 else 0)),
            "factual": _clamp(3 + min(numbers, 5) + (2 if numbers >= 3 else 0)),
        }

        total = sum(scores.values())
        gaps = [
            {
                "feature": feat,
                "current": f"Low signal (score {scores[feat]}/10)",
                "recommendation": _RECOMMENDATIONS[feat],
            }
            for feat in GEO_FEATURES
            if scores[feat] < 5
        ]
        strengths = [feat for feat in GEO_FEATURES if scores[feat] >= 7]
        priority = sorted(GEO_FEATURES, key=lambda f: scores[f])[:3]
        priority_actions = [_RECOMMENDATIONS[f] for f in priority]

        return AnalysisResult(
            title=title,
            content_length=len(body),
            scores=scores,
            total_score=total,
            gaps=gaps,
            strengths=strengths,
            priority_actions=priority_actions,
        )


# --------------------------------------------------------------------------- #
# Ranker / Rewriter (reuse geo_eval; the only LLM-backed agents)
# --------------------------------------------------------------------------- #


class Ranker:
    """Simulate AI-engine ranking by delegating to ``geo_eval._rank_candidates``."""

    def __init__(self, *, client: Any, model: str, prompts_dir: Path, temperature: float = 0.0):
        self._client = client
        self._model = model
        self._system = geo_eval._read_text(prompts_dir / "ranker_system.txt")
        self._user = geo_eval._read_text(prompts_dir / "ranker_user.txt")
        self._temperature = temperature

    def rank(self, query: str, candidates: Sequence[Candidate]) -> RankResult:
        ordered = geo_eval._rank_candidates(
            client=self._client,
            model=self._model,
            system_prompt=self._system,
            user_template=self._user,
            query=query,
            candidates=candidates,
            temperature=self._temperature,
        )
        return RankResult(query=query, ordered_ids=list(ordered))


class Rewriter:
    """Optimize a description by delegating to ``geo_eval._rewrite_description``."""

    def __init__(self, *, client: Any, model: str, prompts_dir: Path, temperature: float = 0.0):
        self._client = client
        self._model = model
        self._system = geo_eval._read_text(prompts_dir / "rewriter_system.txt")
        self._user = geo_eval._read_text(prompts_dir / "rewriter_user.txt")
        self._temperature = temperature

    def rewrite(self, title: str, description: str) -> RewriteResult:
        rewritten = geo_eval._rewrite_description(
            client=self._client,
            model=self._model,
            system_prompt=self._system,
            user_template=self._user,
            title=title,
            description=description,
            temperature=self._temperature,
        )
        return RewriteResult(
            title=title,
            original_description=description,
            rewritten_description=rewritten,
        )


# --------------------------------------------------------------------------- #
# Indexer (deterministic, offline)
# --------------------------------------------------------------------------- #


class Indexer:
    """Generate JSON-LD schema by filling a template shipped in ``geo-output/schema``.

    This mirrors the Claude ``geo-indexer`` agent's job but is deterministic and
    offline. Known ``name``/``description`` fields are filled; remaining
    ``[FILL: ...]`` placeholders are left intact so users complete them. The
    output still passes ``scripts/validate_jsonld.py``.
    """

    # Map a logical content type to a shipped template file.
    _TEMPLATE_BY_TYPE = {
        "Organization": "Organization.json",
        "Product": "Product.json",
        "Service": "Service.json",
        "Article": "Article.json",
        "FAQPage": "FAQPage.json",
    }

    def __init__(self, *, schema_dir: Path):
        self._schema_dir = schema_dir

    def available_types(self) -> List[str]:
        return [t for t, f in self._TEMPLATE_BY_TYPE.items() if (self._schema_dir / f).exists()]

    def generate_schema(self, *, schema_type: str, name: str, description: str) -> SchemaResult:
        filename = self._TEMPLATE_BY_TYPE.get(schema_type)
        if not filename:
            raise ValueError(
                f"Unknown schema type '{schema_type}'. Known: {sorted(self._TEMPLATE_BY_TYPE)}"
            )
        template_path = self._schema_dir / filename
        doc: Dict[str, Any] = json.loads(template_path.read_text(encoding="utf-8"))

        # Fill the two fields we can confidently populate from the pipeline.
        name_key = "headline" if schema_type == "Article" else "name"
        if name_key in doc:
            doc[name_key] = name
        if "description" in doc:
            doc["description"] = description

        return SchemaResult(schema_type=schema_type, json_ld=doc)
