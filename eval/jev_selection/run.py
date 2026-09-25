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


import argparse
import datetime
import json

from egeo import judge as _judge
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


def score_query(item, docs, client, own_domain):
    cands, labels = build_query_candidates(item, docs, own_domain)
    if len(cands) < 2:
        return {"query": item["query"], "skipped": "too_few_candidates"}
    sel = _judge.select_best(item["query"], cands, client)
    pr = sel.probabilities
    pos = [pr.get(i, 0.0) for i, l in labels.items() if l == 1]
    neg = [pr.get(i, 0.0) for i, l in labels.items() if l == 0]
    has_own = any(c.id == "own" for c in cands)
    own_prob = pr.get("own", 0.0) if has_own else None
    own_rank = (1 + sum(1 for c in cands if pr.get(c.id, 0.0) > own_prob)) if has_own else None
    pred = (own_prob >= min(pos)) if (has_own and pos) else None
    return {"query": item["query"], "auc": auc(pos, neg), "n_pos": len(pos), "n_neg": len(neg), "own_prob": own_prob,
            "own_rank": own_rank, "own_predicted_cited": pred, "egeo_cited": item.get("egeo_cited"), "winner": sel.winner}


def run(dataset, client, fetch, own_domain="egeoagents.com"):
    urls = []
    for it in dataset:
        for v in [*it.get("cited_urls", []), *it.get("serp_urls", []), it.get("own_url", "")]:
            u = normalize_source(v)
            if u and u not in urls:
                urls.append(u)
    docs = fetch(urls)
    per = [score_query(it, docs, client, own_domain) for it in dataset]
    aucs = [p["auc"] for p in per if p.get("auc") is not None]
    mean = sum(aucs) / len(aucs) if aucs else None
    owns = [p for p in per if p.get("own_predicted_cited") is not None]
    acc = sum(1 for p in owns if p["own_predicted_cited"] == p["egeo_cited"]) / len(owns) if owns else None
    return {"per_query": per, "mean_auc": mean, "n_scored": len(aucs), "own_accuracy": acc,
            "gate_passed": mean is not None and mean >= GATE_MIN_AUC and len(aucs) >= GATE_MIN_QUERIES,
            "jev_model": client.model, "jev_usage": dict(client.totals), "date": datetime.date.today().isoformat()}


def main(argv=None):
    parser = argparse.ArgumentParser(description="Does Jev choose sources like Perplexity does?")
    parser.add_argument("--dataset", required=True, help="Dataset JSON (see module docstring).")
    parser.add_argument("--out", required=True, help="Where to write the results JSON.")
    parser.add_argument("--mock", action="store_true", help="Offline deterministic run (no TypeSafe, no network).")
    parser.add_argument("--own-domain", default="egeoagents.com")
    args = parser.parse_args(argv)

    from pathlib import Path

    from egeo import jev as _jev
    from egeo import sources as _sources

    dataset = json.loads(Path(args.dataset).read_text(encoding="utf-8"))
    client = _jev.make_client(mock=args.mock)
    source_fn = _sources.placeholder_sources if args.mock else _sources.fetch_sources
    fetch = lambda urls: {d.url: d for d in source_fn(urls, limit=len(urls))}  # noqa: E731
    result = run(dataset, client, fetch, own_domain=args.own_domain)
    Path(args.out).write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"mean_auc: {result['mean_auc']}")
    print(f"n_scored: {result['n_scored']}")
    print("GATE PASS" if result["gate_passed"] else "GATE FAIL")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
