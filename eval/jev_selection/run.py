"""Does Jev choose sources like Perplexity does?  (validation gate for section-mode fix-gaps)

SCAFFOLD — implement until ``tests/test_jev_selection_eval.py`` passes; then run it live
(plan: docs/plans/2026-09-25-fix-gaps-sections-plan.md, Lane G).

Dataset (JSON list), one item per query, produced on the VPS by the collector described in the plan:
    {"query": str, "egeo_cited": bool, "own_url": str,
     "cited_urls": [str, ...],   # URLs Perplexity cited in its answer  -> label 1
     "serp_urls":  [str, ...]}   # top web results for the same query  -> label 0 unless also cited

Per query:
- ``build_query_candidates(item, docs, own_domain)``: normalize with ``egeo.sources.normalize_source``;
  drop URLs whose host is ``own_domain`` (or a subdomain) from cited/serp; cited = first
  ``MAX_PER_CLASS`` unique cited URLs; uncited = first ``MAX_PER_CLASS`` unique serp URLs not in
  cited. Keep only URLs whose ``docs[url].ok`` is true. Candidate ids: ``src_1..`` in order
  (cited first, then uncited), kind "source", label = host, text = doc text. If ``own_url``
  normalizes to a URL with an ok doc, add ``Candidate("own", "own", host, text)`` LAST.
  Returns ``(candidates, labels)`` where ``labels`` maps source ids to 1/0 (own not included).
- ``score_query``: skip (``{"query", "skipped": reason}``) when there are < 2 candidates
  (``"too_few_candidates"``). Otherwise ``egeo.judge.select_best(query, candidates, client)``;
  ``auc`` over sources = ``auc([p for label 1], [p for label 0])`` (None when a class is empty);
  own: ``own_prob``, ``own_rank`` (1 = highest probability, ties share the better rank),
  ``own_predicted_cited = own_prob >= min(prob of label-1 sources)`` (None without cited sources or
  without own). Return ``{"query", "auc", "n_pos", "n_neg", "own_prob", "own_rank",
  "own_predicted_cited", "egeo_cited", "winner"}``.
- ``run(dataset, client, fetch)``: fetch every URL once through ``fetch(urls) -> {url: SourceDoc}``,
  score each query, then ``mean_auc`` = mean of non-None AUCs (None if none), ``n_scored`` = count
  of non-None AUCs, ``own_accuracy`` = share of queries with non-None ``own_predicted_cited`` where it
  equals ``egeo_cited`` (None if none), ``gate_passed = mean_auc is not None and mean_auc >=
  GATE_MIN_AUC and n_scored >= GATE_MIN_QUERIES``. Also include ``"per_query"``, ``"jev_model"``,
  ``"jev_usage"`` (client.totals) and ``"date"`` (UTC ISO date).
- ``auc(pos, neg)``: Mann-Whitney: (#pairs pos > neg + 0.5 * #ties) / (len(pos) * len(neg)).
- CLI: ``python -m eval.jev_selection.run --dataset D.json --out R.json [--mock] [--own-domain egeoagents.com]``
  (mock: ``egeo.jev.make_client(mock=True)`` and ``egeo.sources.placeholder_sources``; otherwise the
  real client and ``egeo.sources.fetch_sources``). Prints mean AUC, n_scored and GATE PASS/FAIL.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Tuple

MAX_PER_CLASS = 8
GATE_MIN_AUC = 0.65
GATE_MIN_QUERIES = 6


def auc(pos: Sequence[float], neg: Sequence[float]) -> Optional[float]:
    raise NotImplementedError


def build_query_candidates(item: Dict[str, Any], docs: Dict[str, Any], own_domain: str) -> Tuple[List[Any], Dict[str, int]]:
    raise NotImplementedError


def score_query(item: Dict[str, Any], docs: Dict[str, Any], client: Any, own_domain: str) -> Dict[str, Any]:
    raise NotImplementedError


def run(dataset: List[Dict[str, Any]], client: Any, fetch: Any, own_domain: str = "egeoagents.com") -> Dict[str, Any]:
    raise NotImplementedError


def main(argv: Optional[List[str]] = None) -> int:
    raise NotImplementedError


if __name__ == "__main__":
    raise SystemExit(main())
