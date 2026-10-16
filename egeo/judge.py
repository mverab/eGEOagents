"""Jev decisions for section-mode ``fix-gaps``: diagnose, fidelity judge, verify.

Jev judges; it never writes. All thresholds are the constants below and must not be tuned per run.
v4 (openspec ``update-jev-blind-validation``; owner decision D2 = Noul, 2026-10-07).

``blind_ids(query, candidates) -> {original id: "cNN"}``: sort candidates by
``sha256(f"{query}\n{c.text}".encode()).hexdigest()``, ties by original id, and number them
``c01``, ``c02``, ... The order depends only on the query and the texts, never on ownership.

``score_candidates(query, candidates, client, *, id_map=None, ids="blind") -> Scored``:
- Requires >= 2 candidates with unique ids, else ``ValueError``; ``ids`` is ``"blind"`` or
  ``"leaky"``, else ``ValueError``.
- Sent id per candidate: ``id_map[c.id]`` when ``id_map`` is given (it must cover every candidate,
  else ``ValueError``); else ``blind_ids(query, candidates)``; with ``ids="leaky"`` (eval leak
  diagnostic only) the original id.
- ONE request. state = ``{"query": query, "candidates": {sent: c.text[:MAX_CANDIDATE_CHARS]}}`` in sent-id
  order; questions = ``{sent: noul_question(NOUL_INSTRUCTIONS.format(cid=sent))}``. Nothing else (no
  label, host or kind) reaches Jev.
- Returns ``Scored(scores={original id: noul}, id_map={original id: sent id}, model=<returned model>)``.

``leader(scored, own, sources) -> Candidate``: the best own candidate (ties -> first in ``own``) when
its score is strictly above every source score; otherwise the best source (ties -> first in
``sources``). A tie is never an own win: ``already_best`` is an off-page claim, so it must be earned.

``diagnose(query, own, sources, client)``:
- no own candidates -> ``Diagnosis(scored=None, target_id=None, status="no_own_candidates")``.
- no sources -> ``Diagnosis(None, None, "no_competitor_sources")`` (Jev is not called).
- otherwise ``scored = score_candidates(query, [*own, *sources], client)``; when the best own score
  is strictly above the best source score -> ``"already_best"``, target None; else ``"loses"``,
  target = own candidate with the highest score (ties -> first in ``own``).

``judge_fidelity(original, rewrite, client)``:
- One Choice question ``FIDELITY_QID`` with ``FIDELITY_INSTRUCTIONS`` and ``FIDELITY_CRITERIA``;
  state = ``{"original": original, "rewrite": rewrite}``.
- ``accepted = verdict == "faithful" and confidence >= FIDELITY_GATE``.
- Not validated directly: ``eval/jev_selection`` measures source *scoring*, not fidelity. The judge
  can only reject, and it runs after the deterministic rules in ``egeo.fidelity``.

``verify(query, own_after, sources, target_id, before, client)``:
- ``after = score_candidates(query, [*own_after, *sources], client, id_map=before.id_map)``: the
  ids are the diagnosis ids, computed once from the original texts.
- ``score_before = before.scores[target_id]``; ``score_after`` likewise from ``after``.
- outcome: best own strictly above best source -> ``"won"``; elif score_after - score_before >=
  IMPROVE_DELTA -> ``"improved"``; elif score_before - score_after >= IMPROVE_DELTA -> ``"worse"``;
  else ``"no_change"``. Compare with a 1e-9 tolerance so that exactly 0.05 counts.
  ``"won"`` means ANY own section wins after the rewrite, not necessarily ``target_id``.
  ``winner_after`` / ``winner_after_kind`` come from ``leader``.

``own_candidates(sections)``: sections with ``word_count >= MIN_SECTION_WORDS`` become
``Candidate(id=f"own_{s.id}", kind="own", label=s.heading or "(intro)", text=s.text)``.
``source_candidates(docs)``: docs with ``ok`` become ``Candidate(id=f"src_{i}", kind="source",
label=host, text=doc.text)`` with i = 1, 2, ... counting only ok docs, host = ``sources.host_of(url)``.
These ids and labels stay in code: Jev only ever sees the blind ids.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
from typing import Dict, List, Optional, Sequence

from .jev import JevClient

# Moved verbatim from eval/jev_selection/run.py (v2), so the eval and the product ask the same question.
NOUL_INSTRUCTIONS = (
    "Would an AI answer engine cite candidates.{cid} as a source when answering `query`? "
    "Answer yes only if that candidate's own text directly and credibly answers `query`."
)
IDS_MODES = ("blind", "leaky")
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
class Scored:
    scores: Dict[str, float]  # original candidate id -> Noul score
    id_map: Dict[str, str]  # original candidate id -> id Jev saw
    model: str = ""  # model string the API returned


@dataclass(frozen=True)
class Diagnosis:
    scored: Optional[Scored]
    target_id: Optional[str]
    status: str  # "loses" | "already_best" | "no_own_candidates" | "no_competitor_sources"


@dataclass(frozen=True)
class FidelityVerdict:
    verdict: str
    confidence: float
    accepted: bool


@dataclass(frozen=True)
class Verification:
    score_before: float
    score_after: float
    winner_after: str
    winner_after_kind: str
    outcome: str  # "won" | "improved" | "no_change" | "worse"


from .jev import choice_question, noul_question
from .sources import host_of


def own_candidates(sections):
    return [Candidate(f"own_{s.id}", "own", s.heading or "(intro)", s.text) for s in sections if s.word_count >= MIN_SECTION_WORDS]


def source_candidates(docs):
    out = []
    for d in docs:
        if d.ok:
            out.append(Candidate(f"src_{len(out) + 1}", "source", host_of(d.url), d.text))
    return out


def blind_ids(query, candidates):
    order = sorted(candidates, key=lambda c: (hashlib.sha256(f"{query}\n{c.text}".encode()).hexdigest(), c.id))
    return {c.id: f"c{i:02d}" for i, c in enumerate(order, 1)}


def score_candidates(query, candidates, client, *, id_map=None, ids="blind"):
    orig = [c.id for c in candidates]
    if len(orig) < 2 or len(set(orig)) != len(orig):
        raise ValueError("need >= 2 unique candidates")
    if ids not in IDS_MODES:
        raise ValueError(f"unknown ids mode: {ids}")
    if id_map is not None:
        if set(id_map) != set(orig) or len(set(id_map.values())) != len(orig):
            raise ValueError("id_map must map every candidate to a unique id")
        m = dict(id_map)
    elif ids == "leaky":
        m = {i: i for i in orig}
    else:
        m = blind_ids(query, candidates)
    sent = sorted(candidates, key=lambda c: m[c.id]) if ids == "blind" or id_map is not None else list(candidates)
    state = {"query": query, "candidates": {m[c.id]: c.text[:MAX_CANDIDATE_CHARS] for c in sent}}
    questions = {m[c.id]: noul_question(NOUL_INSTRUCTIONS.format(cid=m[c.id])) for c in sent}
    resp = client.ask(state, questions)
    return Scored({c.id: resp.answers[m[c.id]].noul for c in candidates}, m, resp.model)


def _best(cands, scores):
    return max(cands, key=lambda c: (scores.get(c.id, 0.0), -cands.index(c)))


def leader(scored, own, sources):
    sc = scored.scores
    bo, bs = _best(own, sc), _best(sources, sc)
    return bo if sc.get(bo.id, 0.0) > sc.get(bs.id, 0.0) else bs


def diagnose(query, own, sources, client):
    if not own:
        return Diagnosis(None, None, "no_own_candidates")
    if not sources:
        return Diagnosis(None, None, "no_competitor_sources")
    scored = score_candidates(query, [*own, *sources], client)
    if leader(scored, own, sources).kind == "own":
        return Diagnosis(scored, None, "already_best")
    return Diagnosis(scored, _best(own, scored.scores).id, "loses")


def judge_fidelity(original, rewrite, client):
    a = client.ask({"original": original, "rewrite": rewrite},
                   {FIDELITY_QID: choice_question(FIDELITY_INSTRUCTIONS, FIDELITY_CRITERIA)}).answers[FIDELITY_QID]
    return FidelityVerdict(a.choice, a.confidence, a.choice == "faithful" and a.confidence >= FIDELITY_GATE)


def verify(query, own_after, sources, target_id, before, client):
    after = score_candidates(query, [*own_after, *sources], client, id_map=before.id_map)
    sb, sa = before.scores.get(target_id, 0.0), after.scores.get(target_id, 0.0)
    lead = leader(after, own_after, sources)
    eps = 1e-9
    if lead.kind == "own":
        o = "won"
    elif sa - sb >= IMPROVE_DELTA - eps:
        o = "improved"
    elif sb - sa >= IMPROVE_DELTA - eps:
        o = "worse"
    else:
        o = "no_change"
    return Verification(sb, sa, lead.id, lead.kind, o)
