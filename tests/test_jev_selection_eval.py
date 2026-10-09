"""Contract tests for eval/jev_selection/run.py — v4 (product scoring path, blind ids, sections). No network."""
from __future__ import annotations

import json
import re
from pathlib import Path

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


OWN_URL = "https://egeoagents.com/compare/geo-tools-2026/"
ITEM = {
    "query": "best geo tools 2026",
    "egeo_cited": False,
    "own_url": OWN_URL,
    "cited_urls": ["https://libhunt.com/", "https://egeoagents.com/x", "https://toolradar.com/best", "https://libhunt.com/"],
    "serp_urls": ["https://toolradar.com/best", "https://frase.io/blog", "https://down.example.com/", "https://www.egeoagents.com/"],
}
DOCS = {u: _doc(u) for u in ["https://libhunt.com/", "https://toolradar.com/best", "https://frase.io/blog", OWN_URL]}
DOCS["https://down.example.com/"] = _doc("https://down.example.com/", ok=False)
# candidates built from ITEM: src_1 libhunt (cited), src_2 toolradar (cited), src_3 frase (uncited), own (excerpt)
TEXT_OF = {"src_1": DOCS["https://libhunt.com/"].text, "src_2": DOCS["https://toolradar.com/best"].text,
           "src_3": DOCS["https://frase.io/blog"].text, "own": DOCS[OWN_URL].text}

SEC_A = "## Tools\n\n" + " ".join(["tools"] * 35) + "\n\n"
SEC_B = "## FAQ\n\n" + " ".join(["faq"] * 35) + "\n"
PAGE_MD = "---\ntitle: GEO tools\n---\nShort intro.\n\n" + SEC_A + SEC_B


class FixedJev:
    """Answers each Noul question with the score of the candidate *text* it points at: ``scores`` is keyed
    by a label (``src_1``, ``own``, ``own_s01`` …) and ``texts`` maps label -> text."""

    def __init__(self, scores, texts=None, model="fake"):
        self.model = model
        self.scores = scores
        self.by_text = {t: scores.get(k, 0.0) for k, t in (texts or TEXT_OF).items()}
        self.requests = []
        self.totals = {"requests": 0, "input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0}

    def ask(self, state, questions):
        self.requests.append((state, questions))
        self.totals["requests"] += 1
        answers = {}
        for qid, q in questions.items():
            if q["type"] == "noul":
                answers[qid] = NoulAnswer(self.by_text.get(state["candidates"][qid], 0.0))
            else:
                answers[qid] = ChoiceAnswer(next(iter(q["criteria"])), 0.5, {})
        return JevResponse(answers=answers, model="jev-1.13.0", input_tokens=0, output_tokens=0, cost_usd=0.0)


def _write_page(root: Path) -> str:
    (root / "content").mkdir(exist_ok=True)
    (root / "content" / "geo-tools.md").write_text(PAGE_MD, encoding="utf-8")
    return "content/geo-tools.md"


def _sections_texts(root: Path):
    cands, _, _ = ev.build_query_candidates(dict(ITEM, own_source="content/geo-tools.md"), DOCS, "egeoagents.com", repo_root=root)
    return {c.id: c.text for c in cands}


def test_build_query_candidates_page_excerpt() -> None:
    cands, labels, unit = ev.build_query_candidates(ITEM, DOCS, "egeoagents.com")
    assert [(c.id, c.kind, c.label) for c in cands] == [
        ("src_1", "source", "libhunt.com"), ("src_2", "source", "toolradar.com"),
        ("src_3", "source", "frase.io"), ("own", "own", "egeoagents.com"),
    ]
    assert labels == {"src_1": 1, "src_2": 1, "src_3": 0}
    assert unit == "page_excerpt"


def test_build_query_candidates_own_source_uses_product_sections(tmp_path: Path) -> None:
    rel = _write_page(tmp_path)
    cands, labels, unit = ev.build_query_candidates(dict(ITEM, own_source=rel), DOCS, "egeoagents.com", repo_root=tmp_path)
    assert unit == "sections"
    assert [(c.id, c.kind, c.label) for c in cands] == [
        ("src_1", "source", "libhunt.com"), ("src_2", "source", "toolradar.com"), ("src_3", "source", "frase.io"),
        ("own_s01", "own", "Tools"), ("own_s02", "own", "FAQ"),  # intro < MIN_SECTION_WORDS, frontmatter removed
    ]
    assert all("title:" not in c.text for c in cands)
    assert labels == {"src_1": 1, "src_2": 1, "src_3": 0}


def test_build_query_candidates_without_own(tmp_path: Path) -> None:
    _, _, unit = ev.build_query_candidates(dict(ITEM, own_url=""), DOCS, "egeoagents.com")
    assert unit is None


def test_missing_own_source_fails_loudly(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        ev.build_query_candidates(dict(ITEM, own_source="content/nope.md"), DOCS, "egeoagents.com", repo_root=tmp_path)


def test_score_query_blind_uses_product_scoring() -> None:
    fake = FixedJev({"src_1": 0.9, "src_2": 0.2, "src_3": 0.5, "own": 0.6})
    res = ev.score_query(ITEM, DOCS, fake, "egeoagents.com")
    assert res == {
        "query": ITEM["query"], "scorer": "noul", "ids": "blind", "unit": "page_excerpt",
        "auc": 0.5, "n_pos": 2, "n_neg": 1,
        "own_best_score": 0.6, "src_best_score": 0.9, "own_rank": 2, "own_wins": False,
        "egeo_cited": False, "winner": "src_1", "jev_model": "jev-1.13.0",
    }
    state, questions = fake.requests[0]
    assert len(fake.requests) == 1
    assert all(re.match(r"^c\d{2}$", k) for k in [*state["candidates"], *questions])
    assert {q["instructions"] for q in questions.values()} == {judge.NOUL_INSTRUCTIONS.format(cid=k) for k in questions}


def test_score_query_leaky_sends_original_ids() -> None:
    fake = FixedJev({"src_1": 0.9})
    res = ev.score_query(ITEM, DOCS, fake, "egeoagents.com", ids="leaky")
    assert res["ids"] == "leaky"
    assert list(fake.requests[0][0]["candidates"]) == ["src_1", "src_2", "src_3", "own"]


def test_own_wins_is_strict_and_uses_best_section(tmp_path: Path) -> None:
    rel = _write_page(tmp_path)
    texts = {**TEXT_OF, **_sections_texts(tmp_path)}
    item = dict(ITEM, own_source=rel)
    win = ev.score_query(item, DOCS, FixedJev({"src_1": 0.7, "own_s01": 0.2, "own_s02": 0.8}, texts), "egeoagents.com",
                         repo_root=tmp_path)
    assert win["unit"] == "sections" and win["own_best_score"] == 0.8 and win["own_wins"] is True
    assert win["own_rank"] == 1 and win["winner"] == "own_s02"
    tie = ev.score_query(item, DOCS, FixedJev({"src_1": 0.8, "own_s01": 0.8}, texts), "egeoagents.com", repo_root=tmp_path)
    assert tie["own_wins"] is False and tie["own_rank"] == 1


def test_score_query_too_few_candidates() -> None:
    item = dict(ITEM, cited_urls=[], serp_urls=[], own_url="")
    assert ev.score_query(item, DOCS, FixedJev({}), "egeoagents.com") == {
        "query": ITEM["query"], "scorer": "noul", "ids": "blind", "skipped": "too_few_candidates"}


def test_unknown_ids_mode() -> None:
    with pytest.raises(ValueError):
        ev.score_query(ITEM, DOCS, FixedJev({}), "egeoagents.com", ids="vibes")


def test_bootstrap_ci() -> None:
    assert ev.bootstrap_ci([]) is None and ev.bootstrap_ci([0.5]) is None
    assert ev.bootstrap_ci([0.7] * 5) == (0.7, 0.7)
    values = [0.4, 0.9, 0.6, 0.55, 0.8, 0.3, 0.7]
    low, high = ev.bootstrap_ci(values)
    assert ev.bootstrap_ci(values) == (low, high)  # deterministic (seed 0)
    assert low <= sum(values) / len(values) <= high and low < high


def test_wilson_ci() -> None:
    assert ev.wilson_ci(0, 0) is None
    low, high = ev.wilson_ci(5, 10)
    assert low == pytest.approx(0.2366, abs=1e-4) and high == pytest.approx(0.7634, abs=1e-4)
    low, high = ev.wilson_ci(0, 4)
    assert low == pytest.approx(0.0, abs=1e-12) and 0 < high < 1


def _fetch_factory(calls):
    def fetch(urls):
        calls.append(sorted(urls))
        return {u: DOCS.get(u, _doc(u, ok=False)) for u in urls}
    return fetch


def test_run_aggregates_and_gate() -> None:
    calls = []
    dataset = [dict(ITEM, query=f"q{i}") for i in range(25)]
    client = FixedJev({"src_1": 0.9, "src_2": 0.6, "src_3": 0.1, "own": 0.2})
    out = ev.run(dataset, client, _fetch_factory(calls), own_domain="egeoagents.com", prereg_sha="abc123")
    assert len(calls) == 1
    assert out["scorer"] == "noul" and out["ids"] == "blind" and out["gating"] is True
    assert out["prereg_sha"] == "abc123"
    assert out["mean_auc"] == 1.0 and out["n_scored"] == 25 and out["gate_passed"] is True
    assert out["mean_auc_ci"] == [1.0, 1.0]
    assert out["unit_counts"] == {"page_excerpt": 25}
    # own metrics count sections items only
    assert out["own_n"] == 0 and out["own_accuracy"] is None and out["own_accuracy_ci95"] is None
    assert out["own_confusion"] == {"tp": 0, "fp": 0, "fn": 0, "tn": 0}
    assert out["jev_usage"]["requests"] == 25 and out["jev_model"] == "fake"
    assert out["jev_models_returned"] == ["jev-1.13.0"]
    assert len(out["per_query"]) == 25 and "date" in out


def test_run_own_confusion_on_sections(tmp_path: Path) -> None:
    rel = _write_page(tmp_path)
    texts = {**TEXT_OF, **_sections_texts(tmp_path)}
    dataset = ([dict(ITEM, query=f"w{i}", own_source=rel, egeo_cited=True) for i in range(3)]
               + [dict(ITEM, query="l", own_source=rel, egeo_cited=True)])
    calls = []
    client = FixedJev({"src_1": 0.5, "src_2": 0.4, "src_3": 0.1, "own_s01": 0.9}, texts)
    # the last query loses: make its own text score low by giving it a different page
    (tmp_path / "content" / "low.md").write_text("## Other\n\n" + " ".join(["other"] * 35) + "\n", encoding="utf-8")
    dataset[-1]["own_source"] = "content/low.md"
    out = ev.run(dataset, client, _fetch_factory(calls), own_domain="egeoagents.com", repo_root=tmp_path, prereg_sha="s")
    assert OWN_URL not in calls[0]  # own_url is not fetched when the page comes from own_source
    assert out["unit_counts"] == {"sections": 4}
    assert out["own_confusion"] == {"tp": 3, "fp": 0, "fn": 1, "tn": 0}
    assert out["own_n"] == 4 and out["own_accuracy"] == 0.75
    low, high = out["own_accuracy_ci95"]
    assert low < 0.75 < high


def test_leaky_run_never_gates() -> None:
    dataset = [dict(ITEM, query=f"q{i}") for i in range(25)]
    out = ev.run(dataset, FixedJev({"src_1": 0.9, "src_2": 0.6, "src_3": 0.1}), _fetch_factory([]),
                 own_domain="egeoagents.com", ids="leaky", prereg_sha="abc123")
    assert out["mean_auc"] == 1.0 and out["gating"] is False and out["gate_passed"] is False


def test_run_without_prereg_never_gates() -> None:
    dataset = [dict(ITEM, query=f"q{i}") for i in range(25)]
    out = ev.run(dataset, FixedJev({"src_1": 0.9, "src_2": 0.6, "src_3": 0.1}), _fetch_factory([]), own_domain="egeoagents.com")
    assert out["mean_auc"] == 1.0 and out["prereg_sha"] is None and out["gating"] is False and out["gate_passed"] is False


def test_gate_needs_25_queries() -> None:
    dataset = [dict(ITEM, query=f"q{i}") for i in range(24)]
    out = ev.run(dataset, FixedJev({"src_1": 0.9, "src_2": 0.6, "src_3": 0.1}), _fetch_factory([]), own_domain="egeoagents.com")
    assert out["mean_auc"] == 1.0 and out["gate_passed"] is False


def test_gate_fails_on_low_auc() -> None:
    dataset = [dict(ITEM, query=f"q{i}") for i in range(25)]
    out = ev.run(dataset, FixedJev({"src_1": 0.1, "src_2": 0.1, "src_3": 0.5}), _fetch_factory([]), own_domain="egeoagents.com")
    assert out["mean_auc"] == 0.0 and out["gate_passed"] is False


def test_main_live_run_requires_prereg_sha(tmp_path: Path, capsys) -> None:
    ds = tmp_path / "ds.json"; ds.write_text(json.dumps([ITEM]), encoding="utf-8")
    out = tmp_path / "out.json"
    assert ev.main(["--dataset", str(ds), "--out", str(out)]) == 2
    assert "--prereg-sha" in capsys.readouterr().err and not out.exists()


def test_main_mock_writes_result(tmp_path: Path) -> None:
    ds = tmp_path / "ds.json"; ds.write_text(json.dumps([ITEM]), encoding="utf-8")
    out = tmp_path / "out.json"
    assert ev.main(["--dataset", str(ds), "--out", str(out), "--mock", "--ids", "leaky"]) == 0
    res = json.loads(out.read_text(encoding="utf-8"))
    assert res["ids"] == "leaky" and res["gating"] is False and res["jev_model"] == "mock"
