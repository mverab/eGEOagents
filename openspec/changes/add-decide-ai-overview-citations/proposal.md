# Change: `egeo loop decide` proposes and grades from AI Overview citations

## Why

The loop's target is being cited in AI answers, but `decide` only reads classic SERP position and JSON-LD presence. The AI Overview collector (#94) already records, per query, whether Google showed an AI Overview and whether it cited the target. `decide` ignores that stream, so a query where the AI Overview exists and names five other sources never produces a proposal, and nothing is graded against citation.

## What Changes

- New action kind `escalate_uncited` (owner gate): an active query whose latest AI Overview observation showed an overview, and whose last 3 observations that showed one all left the target out.
- Observations with `available: false` (Google showed no AI Overview) are not counted as "uncited". A stream older than the project's measurement cadence is not judged.
- The proposal doc and the ledger row list the domains that were cited instead, with the number of observations each appeared in. This is a record of what was shown, not an explanation of why.
- Grading from later AI Overview observations: `verified` when the target is cited after an application the owner recorded, `resolved_unattributed` when it is cited with no recorded application, `unchanged` when overviews were shown and still left it out, and the new grade `unobservable` when every later pass showed no AI Overview.
- Priority among proposals: `escalate_uncited` first, then `escalate_absent`, `propose_page_owner`, `propose_schema`.

## Impact

- Affected capability: `geo-loop-runtime`.
- Affected code: `egeo/decide.py`, `tests/test_decide.py`, docs.
- No new collector, provider, credential, network call or LLM. Workspaces without AI Overview data behave exactly as before: the collector stays optional and is not part of the `collect_fresh` staleness check.
- Scope decision (owner, 2026-11-25): this is the minimal version. It reads only the existing `data/ai_overview/` stream. It does not add answer-engine measurement (Perplexity or others), query-set versioning, or the `error / empty / valid_absent / valid_present` classification; those stay in `validate-evidence-loop-roadmap` Phase 3 behind Gate R.
- Not claimed: Google AI Overview is one surface. A citation there says nothing about ChatGPT, Perplexity or Gemini, and a before/after change is observational, not causal.
