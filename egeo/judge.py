"""Jev decisions for section-mode ``fix-gaps``: diagnose, fidelity judge, verify.

SCAFFOLD — implement until ``tests/test_judge.py`` passes (fake Jev client, no network).

Jev judges; it never writes. All thresholds are the constants below and must not be tuned per run.

``select_best(query, candidates, client)``:
- Requires >= 2 candidates with unique ids, else ``ValueError``.
- One Choice question with id ``SELECT_QID`` and ``SELECT_INSTRUCTIONS``.
- state = ``{"query": query, "candidates": {c.id: c.text[:MAX_CANDIDATE_CHARS] for c}}``.
- criteria = ``{c.id: f"The candidate whose text is candidates.{c.id}"}`` (neutral labels; the
  model must not learn which candidates are ours).
- Returns ``Selection(winner=answer.choice, winner_kind=<kind of that candidate>,
  probabilities=answer.probabilities, confidence=answer.confidence)``.

``diagnose(query, own, sources, client)``:
- no own candidates -> ``Diagnosis(selection=None, target_id=None, status="no_own_candidates")``.
- no sources -> ``Diagnosis(None, None, "no_competitor_sources")`` (Jev is not called).
- otherwise ``sel = select_best(query, [*own, *sources], client)``;
  winner_kind == "own" -> status ``"already_best"``, target None;
  else status ``"loses"``, target = own candidate with the highest probability (ties -> the one
  that comes first in ``own``).

``judge_fidelity(original, rewrite, client)``:
- One Choice question ``FIDELITY_QID`` with ``FIDELITY_INSTRUCTIONS`` and ``FIDELITY_CRITERIA``;
  state = ``{"original": original, "rewrite": rewrite}``.
- ``accepted = verdict == "faithful" and confidence >= FIDELITY_GATE``.

``verify(query, own_after, sources, target_id, before, client)``:
- ``after = select_best(query, [*own_after, *sources], client)`` (same ids as before).
- ``p_before = before.probabilities.get(target_id, 0.0)``; ``p_after`` likewise from ``after``.
- outcome: winner_kind of ``after`` == "own" -> ``"won"``; elif p_after - p_before >= IMPROVE_DELTA
  -> ``"improved"``; elif p_before - p_after >= IMPROVE_DELTA -> ``"worse"``; else ``"no_change"``.
  Compare with a 1e-9 tolerance so that exactly 0.05 counts.

``own_candidates(sections)``: sections with ``word_count >= MIN_SECTION_WORDS`` become
``Candidate(id=f"own_{s.id}", kind="own", label=s.heading or "(intro)", text=s.text)``.
``source_candidates(docs)``: docs with ``ok`` become ``Candidate(id=f"src_{i}", kind="source",
label=host, text=doc.text)`` with i = 1, 2, ... counting only ok docs, host = ``sources.host_of(url)``.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence

from .jev import JevClient

SELECT_QID = "best_source"
SELECT_INSTRUCTIONS = (
    "Which candidate best answers `query`, so that an AI answer engine would quote or cite it "
    "as a source? Judge only the candidate text given in state."
)
FIDELITY_QID = "fidelity"
FIDELITY_INSTRUCTIONS = "Compare `rewrite` with `original`. How does the rewrite relate to the original?"
FIDELITY_CRITERIA: Dict[str, str] = {
    "faithful": (
        "Keeps every fact, number, link and caveat of the original and adds no new factual claims; "
        "only wording, order or emphasis changed."
    ),
    "drops_facts": "Removes, weakens or contradicts a fact, number, link or caveat that the original states.",
    "adds_claims": "Adds a factual claim, statistic, superlative or promise that the original does not support.",
}
FIDELITY_GATE = 0.6
IMPROVE_DELTA = 0.05
MIN_SECTION_WORDS = 30
MAX_CANDIDATE_CHARS = 1500


@dataclass(frozen=True)
class Candidate:
    id: str
    kind: str  # "own" | "source"
    label: str
    text: str


@dataclass(frozen=True)
class Selection:
    winner: str
    winner_kind: str
    probabilities: Dict[str, float]
    confidence: float


@dataclass(frozen=True)
class Diagnosis:
    selection: Optional[Selection]
    target_id: Optional[str]
    status: str  # "loses" | "already_best" | "no_own_candidates" | "no_competitor_sources"


@dataclass(frozen=True)
class FidelityVerdict:
    verdict: str
    confidence: float
    accepted: bool


@dataclass(frozen=True)
class Verification:
    p_before: float
    p_after: float
    winner_after: str
    winner_after_kind: str
    outcome: str  # "won" | "improved" | "no_change" | "worse"


def own_candidates(sections) -> List[Candidate]:
    raise NotImplementedError


def source_candidates(docs) -> List[Candidate]:
    raise NotImplementedError


def select_best(query: str, candidates: Sequence[Candidate], client: JevClient) -> Selection:
    raise NotImplementedError


def diagnose(query: str, own: Sequence[Candidate], sources: Sequence[Candidate], client: JevClient) -> Diagnosis:
    raise NotImplementedError


def judge_fidelity(original: str, rewrite: str, client: JevClient) -> FidelityVerdict:
    raise NotImplementedError


def verify(
    query: str,
    own_after: Sequence[Candidate],
    sources: Sequence[Candidate],
    target_id: str,
    before: Selection,
    client: JevClient,
) -> Verification:
    raise NotImplementedError
