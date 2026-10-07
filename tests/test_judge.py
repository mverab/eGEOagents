"""Contract tests for egeo.judge (v4: blind ids, Noul scoring). A scripted fake Jev client; never the network."""
from __future__ import annotations

import hashlib
import re

import pytest

from egeo import judge
from egeo.jev import ChoiceAnswer, JevResponse, NoulAnswer
from egeo.judge import Candidate, Scored, blind_ids, diagnose, judge_fidelity, score_candidates, verify
from egeo.sections import split_sections
from egeo.sources import SourceDoc

BLIND_ID = re.compile(r"^c\d{2}$")


class ScriptedJev:
    """Choice questions: pops the next queued ChoiceAnswer. Noul questions: looks up the score of the
    candidate text the question points at, via ``by_text`` (a function text -> score). Records requests."""

    def __init__(self, *answers: ChoiceAnswer, by_text=None) -> None:
        self.queue = list(answers)
        self.by_text = by_text or (lambda text: 0.0)
        self.requests = []

    def ask(self, state, questions):
        self.requests.append((state, questions))
        answers = {}
        for qid, q in questions.items():
            if q["type"] == "noul":
                answers[qid] = NoulAnswer(self.by_text(state["candidates"][qid]))
            else:
                answers[qid] = self.queue.pop(0)
        return JevResponse(answers=answers, model="jev-test", input_tokens=10, output_tokens=1, cost_usd=0.0)


def scores_by_text(table):
    """Fake Noul: score = table[text] (texts are unique in these tests)."""
    return lambda text: table[text]


OWN = [Candidate("own_s01", "own", "Intro", "E-GEO rewrites pages."), Candidate("own_s02", "own", "Tools", "A table of tools.")]
SRC = [Candidate("src_1", "source", "libhunt.com", "LibHunt list"), Candidate("src_2", "source", "toolradar.com", "x" * 3000)]
ALL = [*OWN, *SRC]


def _expected_order(query, cands):
    return sorted(cands, key=lambda c: (hashlib.sha256(f"{query}\n{c.text}".encode()).hexdigest(), c.id))


def test_blind_ids_order_depends_only_on_query_and_text() -> None:
    m = blind_ids("best geo tools", ALL)
    assert m == {c.id: f"c{i:02d}" for i, c in enumerate(_expected_order("best geo tools", ALL), 1)}
    assert blind_ids("best geo tools", list(reversed(ALL))) == m  # input order does not matter
    assert sorted(m.values()) == ["c01", "c02", "c03", "c04"]


def test_blind_ids_ties_break_on_original_id() -> None:
    twins = [Candidate("src_2", "source", "b", "same"), Candidate("src_1", "source", "a", "same")]
    assert blind_ids("q", twins) == {"src_1": "c01", "src_2": "c02"}


def test_score_candidates_blind_request_shape() -> None:
    table = {c.text: s for c, s in zip(ALL, (0.1, 0.3, 0.5, 0.2))}
    fake = ScriptedJev(by_text=scores_by_text({**table, "x" * judge.MAX_CANDIDATE_CHARS: 0.2}))
    scored = score_candidates("best geo tools", ALL, fake)
    assert len(fake.requests) == 1
    state, questions = fake.requests[0]
    m = blind_ids("best geo tools", ALL)
    assert scored == Scored({"own_s01": 0.1, "own_s02": 0.3, "src_1": 0.5, "src_2": 0.2}, m, "jev-test")
    assert state["query"] == "best geo tools"
    assert all(BLIND_ID.match(k) for k in state["candidates"])
    assert list(state["candidates"]) == sorted(state["candidates"])  # sent in blind order
    assert state["candidates"][m["src_2"]] == "x" * judge.MAX_CANDIDATE_CHARS
    assert questions == {m[c.id]: {"type": "noul", "instructions": judge.NOUL_INSTRUCTIONS.format(cid=m[c.id])} for c in ALL}
    # no original id, host or heading reaches Jev
    blob = repr((state, questions))
    for c in ALL:
        assert c.id not in blob and c.label not in blob


def test_score_candidates_leaky_sends_original_ids() -> None:
    fake = ScriptedJev(by_text=lambda t: 0.5)
    scored = score_candidates("q", ALL, fake, ids="leaky")
    state, questions = fake.requests[0]
    assert list(state["candidates"]) == [c.id for c in ALL] and list(questions) == [c.id for c in ALL]
    assert scored.id_map == {c.id: c.id for c in ALL}


def test_score_candidates_reuses_given_id_map() -> None:
    m = {"own_s01": "c02", "src_1": "c01"}
    fake = ScriptedJev(by_text=lambda t: 0.4)
    scored = score_candidates("q", [OWN[0], SRC[0]], fake, id_map=m)
    assert set(fake.requests[0][0]["candidates"]) == {"c01", "c02"}
    assert scored.id_map == m
    with pytest.raises(ValueError):
        score_candidates("q", [OWN[0], SRC[0]], fake, id_map={"own_s01": "c01"})  # map misses a candidate


def test_score_candidates_validates_input() -> None:
    with pytest.raises(ValueError):
        score_candidates("q", OWN[:1], ScriptedJev())
    with pytest.raises(ValueError):
        score_candidates("q", [OWN[0], OWN[0]], ScriptedJev())
    with pytest.raises(ValueError):
        score_candidates("q", ALL, ScriptedJev(), ids="vibes")


def test_diagnose_loses_targets_best_own_section() -> None:
    fake = ScriptedJev(by_text=scores_by_text({OWN[0].text: 0.1, OWN[1].text: 0.3, SRC[0].text: 0.5, "x" * 1500: 0.1}))
    d = diagnose("q", OWN, SRC, fake)
    assert d.status == "loses" and d.target_id == "own_s02"
    assert d.scored.scores == {"own_s01": 0.1, "own_s02": 0.3, "src_1": 0.5, "src_2": 0.1}


def test_diagnose_tie_prefers_first_own() -> None:
    fake = ScriptedJev(by_text=scores_by_text({OWN[0].text: 0.2, OWN[1].text: 0.2, SRC[0].text: 0.6}))
    assert diagnose("q", OWN, SRC[:1], fake).target_id == "own_s01"


def test_diagnose_already_best_needs_strictly_higher_score() -> None:
    fake = ScriptedJev(by_text=scores_by_text({OWN[0].text: 0.7, OWN[1].text: 0.1, SRC[0].text: 0.2}))
    d = diagnose("q", OWN, SRC[:1], fake)
    assert d.status == "already_best" and d.target_id is None
    tie = ScriptedJev(by_text=scores_by_text({OWN[0].text: 0.6, OWN[1].text: 0.1, SRC[0].text: 0.6}))
    d = diagnose("q", OWN, SRC[:1], tie)
    assert d.status == "loses" and d.target_id == "own_s01"


def test_diagnose_without_own_or_sources_does_not_call_jev() -> None:
    fake = ScriptedJev()
    assert diagnose("q", [], SRC, fake).status == "no_own_candidates"
    assert diagnose("q", OWN, [], fake).status == "no_competitor_sources"
    assert diagnose("q", [], SRC, fake).scored is None
    assert fake.requests == []


def test_leader() -> None:
    scores = {"own_s01": 0.4, "own_s02": 0.4, "src_1": 0.4, "src_2": 0.1}
    assert judge.leader(Scored(scores, {}), OWN, SRC) == SRC[0]  # tie is not an own win
    assert judge.leader(Scored(dict(scores, own_s02=0.5), {}), OWN, SRC) == OWN[1]


@pytest.mark.parametrize(
    "answer,accepted",
    [
        (ChoiceAnswer("faithful", 0.8, {"faithful": 0.9}), True),
        (ChoiceAnswer("faithful", 0.6, {"faithful": 0.7}), True),
        (ChoiceAnswer("faithful", 0.59, {"faithful": 0.6}), False),
        (ChoiceAnswer("adds_claims", 0.9, {"adds_claims": 0.95}), False),
    ],
)
def test_judge_fidelity_gate(answer: ChoiceAnswer, accepted: bool) -> None:
    fake = ScriptedJev(answer)
    v = judge_fidelity("orig", "new", fake)
    state, questions = fake.requests[0]
    assert state == {"original": "orig", "rewrite": "new"}
    assert questions[judge.FIDELITY_QID]["criteria"] == judge.FIDELITY_CRITERIA
    assert (v.verdict, v.confidence, v.accepted) == (answer.choice, answer.confidence, accepted)


REWRITE = "A comparison table of the best GEO tools."


@pytest.mark.parametrize(
    "after_score,src_score,outcome",
    [
        (0.70, 0.60, "won"),
        (0.60, 0.60, "improved"),  # a tie is not a win
        (0.35, 0.60, "improved"),  # exactly +IMPROVE_DELTA
        (0.32, 0.60, "no_change"),
        (0.25, 0.60, "worse"),  # exactly -IMPROVE_DELTA
    ],
)
def test_verify_outcomes(after_score: float, src_score: float, outcome: str) -> None:
    before_fake = ScriptedJev(by_text=scores_by_text({OWN[0].text: 0.1, OWN[1].text: 0.30, SRC[0].text: 0.6}))
    before = diagnose("q", OWN, SRC[:1], before_fake).scored
    own_after = [OWN[0], Candidate("own_s02", "own", "Tools", REWRITE)]
    fake = ScriptedJev(by_text=scores_by_text({OWN[0].text: 0.1, REWRITE: after_score, SRC[0].text: src_score}))
    v = verify("q", own_after, SRC[:1], "own_s02", before, fake)
    assert v.outcome == outcome
    assert v.score_before == 0.30 and v.score_after == after_score
    assert v.winner_after == ("own_s02" if outcome == "won" else "src_1")
    assert v.winner_after_kind == ("own" if outcome == "won" else "source")
    # same ids as the diagnosis, even though the target text changed
    state_before, _ = before_fake.requests[0]
    state_after, _ = fake.requests[0]
    assert list(state_after["candidates"]) == list(state_before["candidates"])
    assert state_after["candidates"][before.id_map["own_s02"]] == REWRITE


def test_candidate_builders() -> None:
    secs = split_sections("Short intro.\n\n## Tools\n\n" + " ".join(["word"] * 40) + "\n")
    own = judge.own_candidates(secs)
    assert [(c.id, c.kind, c.label) for c in own] == [("own_s01", "own", "Tools")]
    docs = [SourceDoc("https://www.libhunt.com/x", True, "t", "text a"), SourceDoc("https://b.com/", False, error="http_404"),
            SourceDoc("https://c.com/", True, "t", "text c")]
    assert [(c.id, c.label, c.text) for c in judge.source_candidates(docs)] == [
        ("src_1", "libhunt.com", "text a"), ("src_2", "c.com", "text c")]


def test_select_best_is_gone() -> None:
    # D2 = Noul (owner decision 2026-10-07): the single Choice comparison no longer exists.
    assert not hasattr(judge, "select_best") and not hasattr(judge, "Selection")
