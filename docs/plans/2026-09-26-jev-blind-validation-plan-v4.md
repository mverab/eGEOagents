# Plan v4 — blind Jev candidates and a pre-registered validation of the shipped path

**Spec:** `openspec/changes/update-jev-blind-validation/` (proposal, design D1–D5, spec delta).
**Base:** `main` at 2.2.0. **Status:** proposal, pending owner approval and the D2 decision. No code yet.

Follows 2.2.0, where section mode shipped with Jev labeled experimental and the validation marked
*provisional* (CHANGELOG "Known limitations"). This plan closes that: Jev stops seeing which candidates
are ours, the eval runs the product's own scoring function on sections, and one fresh pre-registered run
decides the label.

## 0. Golden rules (unchanged from the main plan §0, plus three)

1. Do not edit tests. Contract tests are written first (RED) by the reviewer and verified against a
   private reference implementation. If a test looks wrong, stop and report.
2. Do not change public signatures, constants or dataclass fields given in the stubs.
3. No network in tests; no secrets in output; stdlib only; stay in your lane's files.
4. **No live Jev run before the pre-registration commit exists** (§3 step 1). A run before that
   commit invalidates v4.
5. **Each live step runs once** (§3). A run that dies before writing a result may be restarted; a
   completed run is final, whatever it says.
6. Never touch `site/` content, never publish, never push to `main`.

## 1. Waves

| Wave | Lanes | Gate to next wave |
|---|---|---|
| 0 | Owner approves proposal + D2 · reviewer writes contracts (RED) | contracts pushed |
| 1 | J1 judge + jev (first) → G4 eval · F4 gaps (parallel after J1) | full suite green, reviewer reads diff |
| 2 | V validation protocol (§3), sequential | result recorded |
| 3 | O outcome (§4) | owner decision if FAIL |

## 2. Lanes

### Lane J1 — `egeo/judge.py`, `egeo/jev.py` → `tests/test_judge.py`, `tests/test_jev.py`

- `blind_ids(query, candidates) -> Dict[str, str]` (original id → `cNN`): sort by
  `sha256(f"{query}\n{c.text}".encode()).hexdigest()`, ties by original id; assign `c01`, `c02`, …
- `score_candidates(query, candidates, client, *, id_map=None, ids="blind") -> Scored` with
  `Scored(scores: Dict[str, float], id_map: Dict[str, str])`, where `scores` is keyed by **original**
  id. It sends ONE request: state `{"query", "candidates": {sent_id: text[:MAX_CANDIDATE_CHARS]}}`, one
  Noul question per candidate, question id = sent id, instructions = `NOUL_INSTRUCTIONS.format(cid=sent_id)`.
  With `id_map` given, it uses that map (verify). `ids="leaky"` sends original ids (eval diagnostic only).
  At least 2 candidates with unique ids are required, else `ValueError`.
- `NOUL_INSTRUCTIONS` moves here from `eval/jev_selection/run.py`, text unchanged.
- `diagnose` → `Diagnosis(scored, target_id, status)`: `already_best` iff max own > max source,
  strictly; else target = max own score, ties → first in `own` order. `no_own_candidates` /
  `no_competitor_sources` unchanged (Jev not called).
- `verify(query, own_after, sources, target_id, before: Scored, client)` re-scores with
  `id_map=before.id_map`. `won` iff max own > max source, strictly; else ±`IMPROVE_DELTA` with the
  existing 1e-9 tolerance.
- `select_best` stays only if D2 = Choice; with D2 = Noul it is removed (its only callers are
  diagnose, verify and the eval).
- `jev.MockJevTransport` Noul answer: `round(len(qw & words(candidates[cid])) / max(1, len(qw)), 4)`,
  where `cid` is the question id and it is in candidates, else 0.0 (replaces the constant 0.9).
- Tests: every sent key matches `^c\d{2}$`; no question text contains `own`/`src`; same ids in
  diagnose and verify after a rewrite; strict-tie → not `already_best`; leaky mode sends original ids.

### Lane G4 — `eval/jev_selection/run.py` → `tests/test_jev_selection_eval.py`

- Remove the local Noul scoring; call `judge.score_candidates(..., ids=args.ids)`.
- Dataset item gains optional `own_source` (repo-relative `.md`). When present: own candidates =
  `judge.own_candidates(split_sections(body))` after `pipeline._extract_frontmatter`, unit `sections`.
  Otherwise one own candidate from the fetched `own_url` excerpt, unit `page_excerpt`.
- Per query adds `unit`, `own_best_score`, `src_best_score`, `own_wins`. Run-level: `ids`, `unit_counts`,
  `own_confusion` (`own_wins` × `egeo_cited`, sections items only), `own_accuracy` + Wilson 95% interval,
  `prereg_sha` (from `--prereg-sha`, required when not `--mock`), `gating` = `ids == "blind"`.
- `gate_passed` = unchanged formula **and** `gating`.
- CLI: `--ids {blind,leaky}` (default `blind`), `--prereg-sha SHA`, `--repo-root PATH` (for `own_source`).

### Lane F4 — `egeo/gaps.py` → `tests/test_gaps_sections.py`

- Diagnosis dict: `{"status", "winner", "winner_kind", "scorer": "noul", "scores": {orig_id: float},
  "target_section", "experimental"}` (drop `probabilities`, `confidence`). `winner` = highest score.
- Verification dict: `p_before`/`p_after` renamed to `score_before`/`score_after`; `winner_after`,
  `winner_after_kind`, `outcome`, `experimental`.
- `JEV_VALIDATION` gains `"protocol"`, `"ids"`, `"unit"`, `"prereg_sha"`. Until §4 it describes the v4
  configuration with **no result**: `"protocol": "v4"`, `"ids": "blind"`, `"unit": "sections"`,
  `"mean_auc": None`, `"ci95": None`, `"gate_passed": False`, `"status": "experimental"`, and
  `"previous"` = the 2.2.0 figures labeled `"config": "choice, leaky ids, page excerpts"`. The report
  never presents the old number as a result for the new configuration.
- The PR merges only after §4, so `main` never ships the interim value.
- `experimental` flags stay driven by `JEV_VALIDATION["status"] != "validated"` (one switch, flipped only in §4).

## 3. Validation protocol (lane V, VPS, sequential; design D4)

1. **Pre-register.** Commit `eval/jev_selection/PREREG-v4.md` with: `queries-v3.json` (same ≥ 30
   queries as v2, plus `own_source` per query where a local page exists) and its sha256; scorer `noul`;
   ids `blind`; unit `sections`; gate `mean_auc >= 0.65 AND n_scored >= 25`; design D5 verbatim. Push.
   Every later result quotes this commit's SHA.
2. **Leak diagnostic (non-gating)** on `dataset-v2-2026-09-25.json`: run once with `--ids leaky` and once
   with `--ids blind`. Record Δ own-win rate, Δ mean own rank, Δ mean AUC. It changes nothing in step 1.
3. **Collect** dataset v3 once, on a date after step 1, with the existing collector
   (`~/.hermes/scripts/egeo_jev_selection_collect.py`). Save it as `dataset-v3-<date>.json`.
4. **Evaluate once:** `python -m eval.jev_selection.run --dataset …v3… --out …results-v3… --prereg-sha <SHA>`.
   Budget ≈ $0.01 Jev. Record the exact `model` string the API returned.

## 4. Outcome (lane O; design D5, no discretion)

- **PASS** → `JEV_VALIDATION` = v4 numbers, `"status": "validated"`; experimental flags off; remove the
  2.2.0 "Known limitations" entry; README + docs cite v4 and the prereg SHA. Default mode unchanged.
- **FAIL** → `JEV_VALIDATION` = v4 numbers, `"status": "experimental"`; docs cite v4. Owner chooses:
  keep experimental, or remove the Jev diagnosis/verification (keep the deterministic fidelity rules).

## 5. Hand-back

1. Head SHA; `pytest tests/ -q` output.
2. The prereg commit SHA; both leak-diagnostic result files; the v3 dataset and result files; the
   returned Jev model string; cost.
3. Anything you could not do, and anything you think is wrong in a test or in this plan.
