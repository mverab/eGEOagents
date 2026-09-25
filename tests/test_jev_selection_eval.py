"""Contract tests for eval/jev_selection/run.py (validation gate). No network."""
from __future__ import annotations

import pytest

from egeo.jev import ChoiceAnswer, JevResponse
from egeo.sources import SourceDoc
from eval.jev_selection import run as ev


def test_auc() -> None:
    assert ev.auc([0.9, 0.8], [0.1, 0.2]) == 1.0
    assert ev.auc([0.1], [0.9]) == 0.0
    assert ev.auc([0.5], [0.5]) == 0.5
    assert ev.auc([0.9, 0.3], [0.5, 0.1]) == 0.75
    assert ev.auc([], [0.1]) is None and ev.auc([0.1], []) is None


def _doc(url: str, ok: bool = True) -> SourceDoc:
    return SourceDoc(url=url, ok=ok, title=url, text=f"text of {url}", error="" if ok else "http_404")


ITEM = {
    "query": "best geo tools 2026",
    "egeo_cited": False,
    "own_url": "https://egeoagents.com/compare/geo-tools-2026/",
    "cited_urls": ["https://libhunt.com/", "https://egeoagents.com/x", "https://toolradar.com/best", "https://libhunt.com/"],
    "serp_urls": ["https://toolradar.com/best", "https://frase.io/blog", "https://down.example.com/", "https://www.egeoagents.com/"],
}
DOCS = {u: _doc(u) for u in [
    "https://libhunt.com/", "https://toolradar.com/best", "https://frase.io/blog",
    "https://egeoagents.com/compare/geo-tools-2026/",
]}
DOCS["https://down.example.com/"] = _doc("https://down.example.com/", ok=False)


def test_build_query_candidates() -> None:
    cands, labels = ev.build_query_candidates(ITEM, DOCS, "egeoagents.com")
    assert [(c.id, c.kind, c.label) for c in cands] == [
        ("src_1", "source", "libhunt.com"), ("src_2", "source", "toolradar.com"),
        ("src_3", "source", "frase.io"), ("own", "own", "egeoagents.com"),
    ]
    assert labels == {"src_1": 1, "src_2": 1, "src_3": 0}


class FixedJev:
    model = "fake"

    def __init__(self, probs):
        self.probs = probs
        self.totals = {"requests": 0, "input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0}

    def ask(self, state, questions):
        self.totals["requests"] += 1
        (qid,) = questions.keys()
        ids = list(questions[qid]["criteria"])
        probs = {i: self.probs.get(i, 0.0) for i in ids}
        best = max(ids, key=lambda i: probs[i])
        return JevResponse(answers={qid: ChoiceAnswer(best, 0.5, probs)}, model="fake",
                           input_tokens=0, output_tokens=0, cost_usd=0.0)


def test_score_query() -> None:
    res = ev.score_query(ITEM, DOCS, FixedJev({"src_1": 0.4, "src_2": 0.1, "src_3": 0.2, "own": 0.3}), "egeoagents.com")
    assert res["auc"] == 0.5  # 0.4 > 0.2 (win), 0.1 < 0.2 (loss)
    assert (res["n_pos"], res["n_neg"]) == (2, 1)
    assert res["own_prob"] == 0.3 and res["own_rank"] == 2
    assert res["own_predicted_cited"] is True  # 0.3 >= min(0.4, 0.1)
    assert res["egeo_cited"] is False and res["winner"] == "src_1"


def test_score_query_too_few_candidates() -> None:
    item = dict(ITEM, cited_urls=[], serp_urls=[], own_url="")
    assert ev.score_query(item, DOCS, FixedJev({}), "egeoagents.com") == {"query": ITEM["query"], "skipped": "too_few_candidates"}


def test_run_aggregates_and_gate() -> None:
    fetched = []

    def fetch(urls):
        fetched.append(sorted(urls))
        return {u: DOCS.get(u, _doc(u, ok=False)) for u in urls}

    dataset = [dict(ITEM, query=f"q{i}") for i in range(6)]
    client = FixedJev({"src_1": 0.5, "src_2": 0.3, "src_3": 0.1, "own": 0.1})
    out = ev.run(dataset, client, fetch, own_domain="egeoagents.com")
    assert len(fetched) == 1  # every URL fetched once, in one call
    assert out["mean_auc"] == 1.0 and out["n_scored"] == 6
    assert out["gate_passed"] is True
    assert out["own_accuracy"] == 1.0  # own 0.1 < min cited 0.3 -> predicted not cited == egeo_cited False
    assert out["jev_model"] == "fake" and out["jev_usage"]["requests"] == 6
    assert len(out["per_query"]) == 6 and "date" in out

    few = ev.run(dataset[:5], FixedJev({"src_1": 0.5, "src_2": 0.3, "src_3": 0.1}), fetch, own_domain="egeoagents.com")
    assert few["gate_passed"] is False  # only 5 scored queries


@pytest.mark.parametrize("probs,passed", [({"src_1": 0.1, "src_2": 0.1, "src_3": 0.5}, False)])
def test_gate_fails_on_low_auc(probs, passed) -> None:
    dataset = [dict(ITEM, query=f"q{i}") for i in range(6)]
    out = ev.run(dataset, FixedJev(probs), lambda urls: {u: DOCS.get(u, _doc(u, ok=False)) for u in urls},
                 own_domain="egeoagents.com")
    assert out["mean_auc"] == 0.0 and out["gate_passed"] is passed
