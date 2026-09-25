"""Contract tests for eval/jev_selection/run.py — v2 (noul scorer, rank-based own metric, CI, n>=25). No network."""
from __future__ import annotations

import pytest

from egeo import judge
from egeo.jev import ChoiceAnswer, JevResponse, NoulAnswer
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
# candidates built from ITEM: src_1 libhunt (cited), src_2 toolradar (cited), src_3 frase (uncited), own


def test_build_query_candidates() -> None:
    cands, labels = ev.build_query_candidates(ITEM, DOCS, "egeoagents.com")
    assert [(c.id, c.kind, c.label) for c in cands] == [
        ("src_1", "source", "libhunt.com"), ("src_2", "source", "toolradar.com"),
        ("src_3", "source", "frase.io"), ("own", "own", "egeoagents.com"),
    ]
    assert labels == {"src_1": 1, "src_2": 1, "src_3": 0}


class FixedJev:
    """Answers Choice questions with the given probabilities and Noul questions with the same numbers."""

    model = "fake"

    def __init__(self, scores):
        self.scores = scores
        self.requests = []
        self.totals = {"requests": 0, "input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0}

    def ask(self, state, questions):
        self.requests.append((state, questions))
        self.totals["requests"] += 1
        answers = {}
        for qid, q in questions.items():
            if q["type"] == "noul":
                answers[qid] = NoulAnswer(self.scores.get(qid, 0.0))
            else:
                ids = list(q["criteria"])
                probs = {i: self.scores.get(i, 0.0) for i in ids}
                answers[qid] = ChoiceAnswer(max(ids, key=lambda i: probs[i]), 0.5, probs)
        return JevResponse(answers=answers, model="fake", input_tokens=0, output_tokens=0, cost_usd=0.0)


def test_score_candidates_noul_one_request_one_question_per_candidate() -> None:
    cands = [judge.Candidate("src_1", "source", "a.com", "x" * 3000), judge.Candidate("own", "own", "b.com", "own text")]
    fake = FixedJev({"src_1": 0.8, "own": 0.3})
    assert ev.score_candidates_noul("best geo tools", cands, fake) == {"src_1": 0.8, "own": 0.3}
    assert len(fake.requests) == 1
    state, questions = fake.requests[0]
    assert state == {"query": "best geo tools", "candidates": {"src_1": "x" * judge.MAX_CANDIDATE_CHARS, "own": "own text"}}
    assert questions == {
        "src_1": {"type": "noul", "instructions": ev.NOUL_INSTRUCTIONS.format(cid="src_1")},
        "own": {"type": "noul", "instructions": ev.NOUL_INSTRUCTIONS.format(cid="own")},
    }


def test_score_candidates_noul_needs_candidates() -> None:
    with pytest.raises(ValueError):
        ev.score_candidates_noul("q", [], FixedJev({}))


def test_score_query_noul() -> None:
    res = ev.score_query(ITEM, DOCS, FixedJev({"src_1": 0.9, "src_2": 0.2, "src_3": 0.5, "own": 0.6}), "egeoagents.com")
    assert res == {
        "query": ITEM["query"], "scorer": "noul", "auc": 0.5, "n_pos": 2, "n_neg": 1,
        "own_score": 0.6, "own_rank": 2, "own_predicted_cited": True,  # rank 2 <= 2 cited sources present
        "egeo_cited": False, "winner": "src_1",
    }


def test_own_not_in_top_k_is_predicted_uncited() -> None:
    res = ev.score_query(ITEM, DOCS, FixedJev({"src_1": 0.9, "src_2": 0.2, "src_3": 0.5, "own": 0.4}), "egeoagents.com")
    assert res["own_rank"] == 3 and res["own_predicted_cited"] is False


def test_score_query_choice_scorer() -> None:
    res = ev.score_query(ITEM, DOCS, FixedJev({"src_1": 0.4, "src_2": 0.1, "src_3": 0.2, "own": 0.3}),
                         "egeoagents.com", scorer="choice")
    assert res["scorer"] == "choice" and res["auc"] == 0.5
    assert res["own_score"] == 0.3 and res["own_rank"] == 2 and res["own_predicted_cited"] is True
    assert res["winner"] == "src_1"


def test_unknown_scorer() -> None:
    with pytest.raises(ValueError):
        ev.score_query(ITEM, DOCS, FixedJev({}), "egeoagents.com", scorer="vibes")


def test_score_query_too_few_candidates() -> None:
    item = dict(ITEM, cited_urls=[], serp_urls=[], own_url="")
    assert ev.score_query(item, DOCS, FixedJev({}), "egeoagents.com") == {
        "query": ITEM["query"], "scorer": "noul", "skipped": "too_few_candidates"}


def test_bootstrap_ci() -> None:
    assert ev.bootstrap_ci([]) is None and ev.bootstrap_ci([0.5]) is None
    assert ev.bootstrap_ci([0.7] * 5) == (0.7, 0.7)
    values = [0.4, 0.9, 0.6, 0.55, 0.8, 0.3, 0.7]
    low, high = ev.bootstrap_ci(values)
    assert ev.bootstrap_ci(values) == (low, high)  # deterministic (seed 0)
    assert low <= sum(values) / len(values) <= high and low < high


def _fetch_factory(calls):
    def fetch(urls):
        calls.append(sorted(urls))
        return {u: DOCS.get(u, _doc(u, ok=False)) for u in urls}
    return fetch


def test_run_noul_aggregates_and_gate() -> None:
    calls = []
    dataset = [dict(ITEM, query=f"q{i}") for i in range(25)]
    client = FixedJev({"src_1": 0.9, "src_2": 0.6, "src_3": 0.1, "own": 0.2})
    out = ev.run(dataset, client, _fetch_factory(calls), own_domain="egeoagents.com")
    assert len(calls) == 1
    assert out["scorer"] == "noul"
    assert out["mean_auc"] == 1.0 and out["n_scored"] == 25 and out["gate_passed"] is True
    assert out["mean_auc_ci"] == [1.0, 1.0]
    assert out["own_accuracy"] == 1.0  # own rank 3 > 2 cited -> predicted uncited == egeo_cited False
    assert out["jev_usage"]["requests"] == 25 and out["jev_model"] == "fake"
    assert len(out["per_query"]) == 25 and "date" in out


def test_gate_needs_25_queries() -> None:
    dataset = [dict(ITEM, query=f"q{i}") for i in range(24)]
    out = ev.run(dataset, FixedJev({"src_1": 0.9, "src_2": 0.6, "src_3": 0.1}), _fetch_factory([]), own_domain="egeoagents.com")
    assert out["mean_auc"] == 1.0 and out["gate_passed"] is False


def test_gate_fails_on_low_auc() -> None:
    dataset = [dict(ITEM, query=f"q{i}") for i in range(25)]
    out = ev.run(dataset, FixedJev({"src_1": 0.1, "src_2": 0.1, "src_3": 0.5}), _fetch_factory([]), own_domain="egeoagents.com")
    assert out["mean_auc"] == 0.0 and out["gate_passed"] is False


def test_run_choice_scorer() -> None:
    dataset = [dict(ITEM, query=f"q{i}") for i in range(3)]
    out = ev.run(dataset, FixedJev({"src_1": 0.5, "src_2": 0.3, "src_3": 0.1}), _fetch_factory([]),
                 own_domain="egeoagents.com", scorer="choice")
    assert out["scorer"] == "choice" and out["n_scored"] == 3 and out["gate_passed"] is False
