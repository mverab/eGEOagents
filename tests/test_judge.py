"""Contract tests for egeo.judge. A scripted fake Jev client; never the network."""
from __future__ import annotations

import pytest

from egeo import judge
from egeo.jev import ChoiceAnswer, JevResponse
from egeo.judge import Candidate, Selection, diagnose, judge_fidelity, select_best, verify
from egeo.sections import split_sections
from egeo.sources import SourceDoc


class ScriptedJev:
    """Returns queued ChoiceAnswers in order and records every request."""

    def __init__(self, *answers: ChoiceAnswer) -> None:
        self.queue = list(answers)
        self.requests = []

    def ask(self, state, questions):
        self.requests.append((state, questions))
        (qid,) = questions.keys()
        return JevResponse(answers={qid: self.queue.pop(0)}, model="fake", input_tokens=10, output_tokens=1, cost_usd=0.0)


OWN = [Candidate("own_s01", "own", "Intro", "E-GEO rewrites pages."), Candidate("own_s02", "own", "Tools", "A table of tools.")]
SRC = [Candidate("src_1", "source", "libhunt.com", "LibHunt list"), Candidate("src_2", "source", "toolradar.com", "x" * 3000)]


def test_select_best_request_shape_and_result() -> None:
    fake = ScriptedJev(ChoiceAnswer("src_1", 0.3, {"own_s01": 0.1, "own_s02": 0.3, "src_1": 0.5, "src_2": 0.1}))
    sel = select_best("best geo tools", [*OWN, *SRC], fake)
    state, questions = fake.requests[0]
    assert state["query"] == "best geo tools"
    assert state["candidates"]["src_2"] == "x" * judge.MAX_CANDIDATE_CHARS
    q = questions[judge.SELECT_QID]
    assert q["type"] == "choice" and q["instructions"] == judge.SELECT_INSTRUCTIONS
    assert q["criteria"] == {c.id: f"The candidate whose text is candidates.{c.id}" for c in [*OWN, *SRC]}
    assert sel == Selection("src_1", "source", {"own_s01": 0.1, "own_s02": 0.3, "src_1": 0.5, "src_2": 0.1}, 0.3)


def test_select_best_needs_two_unique_candidates() -> None:
    with pytest.raises(ValueError):
        select_best("q", OWN[:1], ScriptedJev())
    with pytest.raises(ValueError):
        select_best("q", [OWN[0], OWN[0]], ScriptedJev())


def test_diagnose_loses_targets_best_own_section() -> None:
    fake = ScriptedJev(ChoiceAnswer("src_1", 0.3, {"own_s01": 0.1, "own_s02": 0.3, "src_1": 0.5, "src_2": 0.1}))
    d = diagnose("q", OWN, SRC, fake)
    assert d.status == "loses" and d.target_id == "own_s02" and d.selection.winner == "src_1"


def test_diagnose_tie_prefers_first_own() -> None:
    fake = ScriptedJev(ChoiceAnswer("src_1", 0.3, {"own_s01": 0.2, "own_s02": 0.2, "src_1": 0.6}))
    assert diagnose("q", OWN, SRC[:1], fake).target_id == "own_s01"


def test_diagnose_already_best() -> None:
    fake = ScriptedJev(ChoiceAnswer("own_s01", 0.5, {"own_s01": 0.7, "own_s02": 0.1, "src_1": 0.2}))
    d = diagnose("q", OWN, SRC[:1], fake)
    assert d.status == "already_best" and d.target_id is None


def test_diagnose_without_own_or_sources_does_not_call_jev() -> None:
    fake = ScriptedJev()
    assert diagnose("q", [], SRC, fake).status == "no_own_candidates"
    assert diagnose("q", OWN, [], fake).status == "no_competitor_sources"
    assert fake.requests == []


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


BEFORE = Selection("src_1", "source", {"own_s01": 0.1, "own_s02": 0.30, "src_1": 0.6}, 0.3)


@pytest.mark.parametrize(
    "after,outcome",
    [
        (ChoiceAnswer("own_s02", 0.5, {"own_s01": 0.1, "own_s02": 0.7, "src_1": 0.2}), "won"),
        (ChoiceAnswer("src_1", 0.2, {"own_s01": 0.1, "own_s02": 0.35, "src_1": 0.55}), "improved"),
        (ChoiceAnswer("src_1", 0.3, {"own_s01": 0.1, "own_s02": 0.32, "src_1": 0.58}), "no_change"),
        (ChoiceAnswer("src_1", 0.5, {"own_s01": 0.1, "own_s02": 0.25, "src_1": 0.65}), "worse"),
    ],
)
def test_verify_outcomes(after: ChoiceAnswer, outcome: str) -> None:
    v = verify("q", OWN, SRC[:1], "own_s02", BEFORE, ScriptedJev(after))
    assert v.outcome == outcome
    assert v.p_before == 0.30 and v.p_after == after.probabilities["own_s02"]
    assert v.winner_after == after.choice


def test_candidate_builders() -> None:
    secs = split_sections("Short intro.\n\n## Tools\n\n" + " ".join(["word"] * 40) + "\n")
    own = judge.own_candidates(secs)
    assert [(c.id, c.kind, c.label) for c in own] == [("own_s01", "own", "Tools")]
    docs = [SourceDoc("https://www.libhunt.com/x", True, "t", "text a"), SourceDoc("https://b.com/", False, error="http_404"),
            SourceDoc("https://c.com/", True, "t", "text c")]
    assert [(c.id, c.label, c.text) for c in judge.source_candidates(docs)] == [
        ("src_1", "libhunt.com", "text a"), ("src_2", "c.com", "text c")]
