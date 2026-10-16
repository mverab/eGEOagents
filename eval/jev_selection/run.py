"""Does Jev judge sources like Perplexity cites them?  (validation gate for section-mode fix-gaps)

v4 CONTRACT (openspec ``update-jev-blind-validation``, plan docs/plans/2026-09-26-jev-blind-validation-plan-v4.md).
Implement until ``tests/test_jev_selection_eval.py`` passes.

Why v4: v2 scored with its own copy of the Noul question, on full-page excerpts, with ids that told Jev which
candidate was ours (``own`` next to ``src_N``). v4 scores with the product's function,
``egeo.judge.score_candidates``, on the product's unit (sections) and with blind ids, so the gate measures
what section mode ships.

Dataset (JSON list), one item per query, produced on the VPS by the collector described in the plan:
    {"query": str, "egeo_cited": bool, "own_url": str | "" | null,
     "own_source": str (optional),  # repo-relative .md of the own page -> unit "sections"
     "cited_urls": [str, ...],   # URLs Perplexity cited in its answer  -> label 1
     "serp_urls":  [str, ...]}   # top web results for the same query  -> label 0 unless also cited

- ``build_query_candidates(item, docs, own_domain, repo_root=None) -> (candidates, labels, unit)``:
  sources as in v2 (cited first, then uncited SERP, own domain dropped, at most MAX_PER_CLASS each,
  ``src_N`` over ok docs). Own: with ``own_source``, read ``repo_root / own_source`` (missing file ->
  ``FileNotFoundError``; never a silent fallback), drop frontmatter (``pipeline._extract_frontmatter``),
  ``judge.own_candidates(split_sections(body))``, unit ``"sections"``. Else, when ``own_url`` was fetched
  ok, one ``Candidate("own", "own", host, text)``, unit ``"page_excerpt"``. Else unit None.
- ``score_query(item, docs, client, own_domain, *, ids="blind", repo_root=None)``: ``ids`` not in
  ``judge.IDS_MODES`` -> ``ValueError``. Fewer than 2 candidates -> ``{"query", "scorer", "ids",
  "skipped": "too_few_candidates"}``. Otherwise ``scored = judge.score_candidates(query, cands, client,
  ids=ids)`` and, with ``score = scored.scores``:
    auc            = auc(scores of label-1 sources, scores of label-0 sources)  (None if a class is empty)
    own_best_score = max own score; src_best_score = max source score            (None when absent)
    own_rank       = 1 + number of sources scoring strictly above own_best_score (None without own)
    own_wins       = own_best_score > src_best_score, strictly: the product's ``already_best`` rule
                     (None without own or without sources)
    winner         = id with the highest score (ties -> earliest candidate)
  Return ``{"query", "scorer": "noul", "ids", "unit", "auc", "n_pos", "n_neg", "own_best_score",
  "src_best_score", "own_rank", "own_wins", "egeo_cited", "winner", "jev_model"}`` (``jev_model`` = the
  model string the API returned for that request).
- ``bootstrap_ci``: unchanged. ``wilson_ci(k, n, z=1.96)``: Wilson score interval, None when n == 0.
- ``run(dataset, client, fetch, own_domain="egeoagents.com", *, ids="blind", repo_root=None,
  prereg_sha=None)``: one ``fetch`` call for every unique normalized URL (``own_url`` is skipped for
  items with ``own_source``). Adds ``ids``, ``gating = ids == "blind" and bool(prereg_sha)`` (a run
  without a pre-registration can never pass), ``prereg_sha``, ``unit_counts``
  (scored items per unit), ``own_confusion`` (``own_wins`` x ``egeo_cited``: tp/fp/fn/tn; ``sections``
  items only), ``own_n``, ``own_accuracy`` and ``own_accuracy_ci95`` (Wilson), ``jev_models_returned``.
  ``gate_passed = gating and mean_auc is not None and mean_auc >= GATE_MIN_AUC and n_scored >=
  GATE_MIN_QUERIES``. Own metrics never gate.
- ``auc``: unchanged (Mann-Whitney with 0.5 for ties).
- CLI: ``--ids {blind,leaky}`` (default blind), ``--prereg-sha SHA`` (required unless ``--mock``; exit 2
  without it), ``--repo-root PATH`` (default ``.``, for ``own_source``).

Pre-registration lives in ``eval/jev_selection/PREREG-v4.md`` and is committed before any live v4 run.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Tuple

MAX_PER_CLASS = 8
GATE_MIN_AUC = 0.65
GATE_MIN_QUERIES = 25


import argparse
import datetime
import json
import math
import random
from pathlib import Path

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


def _own_sections(path):
    from egeo.pipeline import _extract_frontmatter
    from egeo.sections import split_sections

    body = _extract_frontmatter(Path(path).read_text(encoding="utf-8"))[1]
    return _judge.own_candidates(split_sections(body))


def build_query_candidates(item, docs, own_domain, repo_root=None):
    cited = _uniq(item.get("cited_urls", []), own_domain)[:MAX_PER_CLASS]
    unc = [u for u in _uniq(item.get("serp_urls", []), own_domain) if u not in cited][:MAX_PER_CLASS]
    cands, labels = [], {}
    for u, lab in [*[(u, 1) for u in cited], *[(u, 0) for u in unc]]:
        d = docs.get(u)
        if d is None or not d.ok:
            continue
        cid = f"src_{len(cands) + 1}"
        cands.append(_judge.Candidate(cid, "source", host_of(u), d.text)); labels[cid] = lab
    if item.get("own_source"):
        cands.extend(_own_sections(Path(repo_root or ".") / item["own_source"]))
        return cands, labels, "sections"
    ou = normalize_source(item.get("own_url", ""))
    if ou and docs.get(ou) is not None and docs[ou].ok:
        cands.append(_judge.Candidate("own", "own", host_of(ou), docs[ou].text))
        return cands, labels, "page_excerpt"
    return cands, labels, None


def bootstrap_ci(values: Sequence[float], *, n: int = 2000, seed: int = 0, alpha: float = 0.05) -> Optional[Tuple[float, float]]:
    if len(values) < 2:
        return None
    rng = random.Random(seed)
    means = sorted(sum(rng.choices(values, k=len(values))) / len(values) for _ in range(n))
    return means[int(alpha / 2 * n)], means[int((1 - alpha / 2) * n) - 1]


def wilson_ci(k: int, n: int, z: float = 1.96) -> Optional[Tuple[float, float]]:
    if n == 0:
        return None
    p = k / n
    den = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return centre - half, centre + half


def score_query(item, docs, client, own_domain, *, ids="blind", repo_root=None):
    if ids not in _judge.IDS_MODES:
        raise ValueError(f"unknown ids mode: {ids}")
    cands, labels, unit = build_query_candidates(item, docs, own_domain, repo_root=repo_root)
    if len(cands) < 2:
        return {"query": item["query"], "scorer": "noul", "ids": ids, "skipped": "too_few_candidates"}
    scored = _judge.score_candidates(item["query"], cands, client, ids=ids)
    score = scored.scores
    pos = [score[i] for i, l in labels.items() if l == 1]
    neg = [score[i] for i, l in labels.items() if l == 0]
    own = [score[c.id] for c in cands if c.kind == "own"]
    src = [score[c.id] for c in cands if c.kind == "source"]
    own_best = max(own) if own else None
    src_best = max(src) if src else None
    own_rank = 1 + sum(1 for v in src if v > own_best) if own else None
    own_wins = own_best > src_best if own and src else None
    winner = None
    for c in cands:
        if winner is None or score[c.id] > score[winner]:
            winner = c.id
    return {"query": item["query"], "scorer": "noul", "ids": ids, "unit": unit, "auc": auc(pos, neg),
            "n_pos": len(pos), "n_neg": len(neg), "own_best_score": own_best, "src_best_score": src_best,
            "own_rank": own_rank, "own_wins": own_wins, "egeo_cited": item.get("egeo_cited"), "winner": winner,
            "jev_model": scored.model}


def run(dataset, client, fetch, own_domain="egeoagents.com", *, ids="blind", repo_root=None, prereg_sha=None):
    urls = []
    for it in dataset:
        own_url = [] if it.get("own_source") else [it.get("own_url", "")]
        for v in [*it.get("cited_urls", []), *it.get("serp_urls", []), *own_url]:
            u = normalize_source(v)
            if u and u not in urls:
                urls.append(u)
    docs = fetch(urls)
    per = [score_query(it, docs, client, own_domain, ids=ids, repo_root=repo_root) for it in dataset]
    models = sorted({p["jev_model"] for p in per if p.get("jev_model")})
    aucs = [p["auc"] for p in per if p.get("auc") is not None]
    mean = sum(aucs) / len(aucs) if aucs else None
    ci = bootstrap_ci(aucs)
    units = {}
    for p in per:
        if "skipped" not in p and p["unit"]:
            units[p["unit"]] = units.get(p["unit"], 0) + 1
    conf = {"tp": 0, "fp": 0, "fn": 0, "tn": 0}
    for p in per:
        if p.get("unit") == "sections" and p["own_wins"] is not None and isinstance(p["egeo_cited"], bool):
            conf[("t" if p["own_wins"] == p["egeo_cited"] else "f") + ("p" if p["own_wins"] else "n")] += 1
    own_n = sum(conf.values())
    acc_ci = wilson_ci(conf["tp"] + conf["tn"], own_n)
    gating = ids == "blind" and bool(prereg_sha)
    return {"per_query": per, "scorer": "noul", "ids": ids, "gating": gating, "prereg_sha": prereg_sha,
            "unit_counts": units, "mean_auc": mean, "mean_auc_ci": list(ci) if ci else None, "n_scored": len(aucs),
            "own_confusion": conf, "own_n": own_n,
            "own_accuracy": (conf["tp"] + conf["tn"]) / own_n if own_n else None,
            "own_accuracy_ci95": list(acc_ci) if acc_ci else None,
            "gate_passed": gating and mean is not None and mean >= GATE_MIN_AUC and len(aucs) >= GATE_MIN_QUERIES,
            "jev_model": client.model, "jev_models_returned": models, "jev_usage": dict(client.totals),
            "date": datetime.date.today().isoformat()}


def main(argv=None):
    import sys

    parser = argparse.ArgumentParser(description="Does Jev choose sources like Perplexity does?")
    parser.add_argument("--dataset", required=True, help="Dataset JSON (see module docstring).")
    parser.add_argument("--out", required=True, help="Where to write the results JSON.")
    parser.add_argument("--mock", action="store_true", help="Offline deterministic run (no TypeSafe, no network).")
    parser.add_argument("--ids", default="blind", choices=list(_judge.IDS_MODES),
                        help="blind (default, gating) or leaky (2.2.0 ids, leak diagnostic only, never gates).")
    parser.add_argument("--prereg-sha", default=None, help="Commit SHA of PREREG-v4.md (required unless --mock).")
    parser.add_argument("--repo-root", default=".", help="Root that dataset `own_source` paths are relative to.")
    parser.add_argument("--own-domain", default="egeoagents.com")
    args = parser.parse_args(argv)
    if not args.mock and not args.prereg_sha:
        print("error: a live run needs --prereg-sha <commit of eval/jev_selection/PREREG-v4.md>", file=sys.stderr)
        return 2

    from egeo import jev as _jev
    from egeo import sources as _sources

    dataset = json.loads(Path(args.dataset).read_text(encoding="utf-8"))
    client = _jev.make_client(mock=args.mock)
    source_fn = _sources.placeholder_sources if args.mock else _sources.fetch_sources
    fetch = lambda urls: {d.url: d for d in source_fn(urls, limit=len(urls))}  # noqa: E731
    result = run(dataset, client, fetch, own_domain=args.own_domain, ids=args.ids, repo_root=Path(args.repo_root),
                 prereg_sha=args.prereg_sha)
    Path(args.out).write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"ids: {result['ids']} ({'gating' if result['gating'] else 'NON-GATING diagnostic'})")
    print(f"unit_counts: {result['unit_counts']}")
    print(f"mean_auc: {result['mean_auc']}")
    print(f"mean_auc_ci: {result['mean_auc_ci']}")
    print(f"n_scored: {result['n_scored']}")
    print(f"own_accuracy (sections): {result['own_accuracy']} {result['own_accuracy_ci95']}")
    print(f"jev_models_returned: {result['jev_models_returned']}")
    print("GATE PASS" if result["gate_passed"] else "GATE FAIL")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
