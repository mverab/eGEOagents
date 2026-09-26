"""Does Jev judge sources like Perplexity cites them?  (validation gate for section-mode fix-gaps)

v2 CONTRACT (2026-09-25 review of the v1 run). Implement until ``tests/test_jev_selection_eval.py``
passes. Plan: docs/plans/2026-09-25-fix-gaps-sections-plan-v2.md.

Why v2: v1 scored candidates with ONE Choice question, which spreads probability over 1-2 candidates;
44% of candidates got p < 0.01, so AUC was dominated by ties at ~0 and ``own_predicted_cited``
(compared against the MINIMUM cited probability, 0.0 in 9/10 queries) was always True. A re-run on
the same data moved mean AUC from 0.6493 to 0.6272, i.e. the 0.65 gate sat inside run-to-run noise.

Dataset (JSON list), one item per query, produced on the VPS by the collector described in the plan:
    {"query": str, "egeo_cited": bool, "own_url": str | "" | null,
     "cited_urls": [str, ...],   # URLs Perplexity cited in its answer  -> label 1
     "serp_urls":  [str, ...]}   # top web results for the same query  -> label 0 unless also cited

- ``build_query_candidates``: unchanged from v1 (see tests).
- ``score_candidates_noul(query, candidates, client) -> {id: float}``: ONE request with one Noul
  question per candidate (question id = candidate id, instructions =
  ``NOUL_INSTRUCTIONS.format(cid=<id>)``). State = ``{"query": query, "candidates":
  {id: text[:egeo.judge.MAX_CANDIDATE_CHARS]}}``. Returns each candidate's ``noul``.
  ``ValueError`` when ``candidates`` is empty.
- ``score_query(item, docs, client, own_domain, scorer="noul")``:
  ``scorer`` is ``"noul"`` (per-candidate scores above) or ``"choice"`` (probabilities from
  ``egeo.judge.select_best``); anything else -> ``ValueError``. Fewer than 2 candidates ->
  ``{"query", "scorer", "skipped": "too_few_candidates"}``. Otherwise, with ``score = {id: float}``:
    auc          = auc(scores of label-1 sources, scores of label-0 sources)   (None if a class is empty)
    own_score    = score["own"] if an own candidate exists else None
    own_rank     = 1 + number of candidates with a strictly higher score        (None without own)
    own_predicted_cited = own_rank <= n_pos   # "would own make the top-k", k = cited sources present
                          (None without own or when n_pos == 0)
    winner       = id with the highest score (ties -> earliest candidate)
  Return ``{"query", "scorer", "auc", "n_pos", "n_neg", "own_score", "own_rank",
  "own_predicted_cited", "egeo_cited", "winner"}``.
- ``bootstrap_ci(values, *, n=2000, seed=0, alpha=0.05)``: None when fewer than 2 values. Otherwise
  ``rng = random.Random(seed)``; ``n`` times take ``rng.choices(values, k=len(values))`` and record its
  mean; sort; return ``(means[int(alpha / 2 * n)], means[int((1 - alpha / 2) * n) - 1])``.
- ``run(dataset, client, fetch, own_domain="egeoagents.com", scorer="noul")``: as v1 (one ``fetch``
  call for every unique normalized URL) plus ``"scorer"`` and ``"mean_auc_ci"`` =
  ``bootstrap_ci(<non-None per-query AUCs>)`` (a list ``[low, high]`` or None).
  ``gate_passed = mean_auc is not None and mean_auc >= GATE_MIN_AUC and n_scored >= GATE_MIN_QUERIES``.
- ``auc``: unchanged (Mann-Whitney with 0.5 for ties).
- CLI: add ``--scorer {noul,choice}`` (default ``noul``); also print the CI.

Pre-registration (do not change after seeing results): scorer ``noul``, GATE_MIN_AUC 0.65,
GATE_MIN_QUERIES 25, dataset v2 collected once, evaluated once.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Tuple

MAX_PER_CLASS = 8
GATE_MIN_AUC = 0.65
GATE_MIN_QUERIES = 25
NOUL_INSTRUCTIONS = (
    "Would an AI answer engine cite candidates.{cid} as a source when answering `query`? "
    "Answer yes only if that candidate's own text directly and credibly answers `query`."
)
SCORERS = ("noul", "choice")


import argparse
import datetime
import json
import random

from egeo import judge as _judge
from egeo.jev import noul_question
from egeo.sources import host_of, normalize_source


def auc(pos, neg):
    if not pos or not neg:
        return None
    w = sum(1.0 if p > n else 0.5 if p == n else 0.0 for p in pos for n in neg)
    return w / (len(pos) * len(neg))


def _own(u, dom):
    h = host_of(u)
    return bool(dom) and (h == dom or h.endswith("." + dom))


def _uniq(urls, dom):
    out = []
    for v in urls:
        u = normalize_source(v)
        if u and u not in out and not _own(u, dom):
            out.append(u)
    return out


def build_query_candidates(item, docs, own_domain):
    cited = _uniq(item.get("cited_urls", []), own_domain)[:MAX_PER_CLASS]
    unc = [u for u in _uniq(item.get("serp_urls", []), own_domain) if u not in cited][:MAX_PER_CLASS]
    cands, labels = [], {}
    for u, lab in [*[(u, 1) for u in cited], *[(u, 0) for u in unc]]:
        d = docs.get(u)
        if d is None or not d.ok:
            continue
        cid = f"src_{len(cands) + 1}"
        cands.append(_judge.Candidate(cid, "source", host_of(u), d.text)); labels[cid] = lab
    ou = normalize_source(item.get("own_url", ""))
    if ou and docs.get(ou) is not None and docs[ou].ok:
        cands.append(_judge.Candidate("own", "own", host_of(ou), docs[ou].text))
    return cands, labels


def score_candidates_noul(query: str, candidates: Sequence[Any], client: Any) -> Dict[str, float]:
    if not candidates:
        raise ValueError("need at least one candidate")
    state = {"query": query, "candidates": {c.id: c.text[:_judge.MAX_CANDIDATE_CHARS] for c in candidates}}
    questions = {c.id: noul_question(NOUL_INSTRUCTIONS.format(cid=c.id)) for c in candidates}
    answers = client.ask(state, questions).answers
    return {c.id: answers[c.id].noul for c in candidates}


def bootstrap_ci(values: Sequence[float], *, n: int = 2000, seed: int = 0, alpha: float = 0.05) -> Optional[Tuple[float, float]]:
    if len(values) < 2:
        return None
    rng = random.Random(seed)
    means = sorted(sum(rng.choices(values, k=len(values))) / len(values) for _ in range(n))
    return means[int(alpha / 2 * n)], means[int((1 - alpha / 2) * n) - 1]


def score_query(item, docs, client, own_domain, scorer="noul"):
    if scorer not in SCORERS:
        raise ValueError(f"unknown scorer: {scorer}")
    cands, labels = build_query_candidates(item, docs, own_domain)
    if len(cands) < 2:
        return {"query": item["query"], "scorer": scorer, "skipped": "too_few_candidates"}
    if scorer == "noul":
        score = score_candidates_noul(item["query"], cands, client)
    else:
        score = dict(_judge.select_best(item["query"], cands, client).probabilities)
    pos = [score.get(i, 0.0) for i, l in labels.items() if l == 1]
    neg = [score.get(i, 0.0) for i, l in labels.items() if l == 0]
    has_own = any(c.id == "own" for c in cands)
    if has_own:
        own_score = score.get("own", 0.0)
        own_rank = 1 + sum(1 for c in cands if score.get(c.id, 0.0) > own_score)
        pred = (own_rank <= len(pos)) if pos else None
    else:
        own_score = own_rank = pred = None
    winner = None
    for c in cands:
        if winner is None or score.get(c.id, 0.0) > score.get(winner, 0.0):
            winner = c.id
    return {"query": item["query"], "scorer": scorer, "auc": auc(pos, neg), "n_pos": len(pos), "n_neg": len(neg),
            "own_score": own_score, "own_rank": own_rank, "own_predicted_cited": pred,
            "egeo_cited": item.get("egeo_cited"), "winner": winner}


def run(dataset, client, fetch, own_domain="egeoagents.com", scorer="noul"):
    urls = []
    for it in dataset:
        for v in [*it.get("cited_urls", []), *it.get("serp_urls", []), it.get("own_url", "")]:
            u = normalize_source(v)
            if u and u not in urls:
                urls.append(u)
    docs = fetch(urls)
    per = [score_query(it, docs, client, own_domain, scorer=scorer) for it in dataset]
    aucs = [p["auc"] for p in per if p.get("auc") is not None]
    mean = sum(aucs) / len(aucs) if aucs else None
    ci = bootstrap_ci(aucs)
    owns = [p for p in per if p.get("own_predicted_cited") is not None]
    acc = sum(1 for p in owns if p["own_predicted_cited"] == p["egeo_cited"]) / len(owns) if owns else None
    return {"per_query": per, "scorer": scorer, "mean_auc": mean, "mean_auc_ci": list(ci) if ci else None,
            "n_scored": len(aucs), "own_accuracy": acc,
            "gate_passed": mean is not None and mean >= GATE_MIN_AUC and len(aucs) >= GATE_MIN_QUERIES,
            "jev_model": client.model, "jev_usage": dict(client.totals), "date": datetime.date.today().isoformat()}


def main(argv=None):
    parser = argparse.ArgumentParser(description="Does Jev choose sources like Perplexity does?")
    parser.add_argument("--dataset", required=True, help="Dataset JSON (see module docstring).")
    parser.add_argument("--out", required=True, help="Where to write the results JSON.")
    parser.add_argument("--mock", action="store_true", help="Offline deterministic run (no TypeSafe, no network).")
    parser.add_argument("--scorer", default="noul", choices=list(SCORERS), help="Candidate scoring (default: noul).")
    parser.add_argument("--own-domain", default="egeoagents.com")
    args = parser.parse_args(argv)

    from pathlib import Path

    from egeo import jev as _jev
    from egeo import sources as _sources

    dataset = json.loads(Path(args.dataset).read_text(encoding="utf-8"))
    client = _jev.make_client(mock=args.mock)
    source_fn = _sources.placeholder_sources if args.mock else _sources.fetch_sources
    fetch = lambda urls: {d.url: d for d in source_fn(urls, limit=len(urls))}  # noqa: E731
    result = run(dataset, client, fetch, own_domain=args.own_domain, scorer=args.scorer)
    Path(args.out).write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"scorer: {result['scorer']}")
    print(f"mean_auc: {result['mean_auc']}")
    print(f"mean_auc_ci: {result['mean_auc_ci']}")
    print(f"n_scored: {result['n_scored']}")
    print("GATE PASS" if result["gate_passed"] else "GATE FAIL")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
