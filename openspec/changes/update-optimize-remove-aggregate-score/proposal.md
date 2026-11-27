# Change: Remove the aggregate GEO score from `egeo optimize` outputs

## Why

`egeo optimize` prints "GEO score: N/100" and writes it to `report.md`, `analysis.json` and `--json`. The number is the sum of ten keyword-and-structure counts from the offline analyzer in `egeo/agents.py`. `docs/examples.md` shows what that does: a rewrite that deleted the page's opening definition and both research links moved the score from 60 to 61, and adding the word "today" raised urgency from 0 to 8. A total out of 100 reads as a quality or ranking score, and it is neither.

The public URL audit already made this call: its spec forbids "a single aggregate score" and shows the ten signals labeled as a heuristic.

## What Changes

- The CLI prints how many of the ten signals were detected and names the ones not found, labeled "keyword heuristic, not a ranking score". No number out of 100.
- `report.md` drops the "GEO Score" line. The per-signal table stays, retitled "GEO Signals (keyword heuristic)" with a sentence saying what it counts.
- **Breaking for JSON consumers:** `analysis.json` no longer has `analysis.total_score`, and the `--json` summary replaces `geo_score` with `signals` (the ten per-signal values).
- `AnalysisResult.total_score` stays as an internal attribute; the URL audit uses it to order candidate sections and never outputs it.

## Decision recorded: Jev validation (owner, 2026-11-26)

No further Jev validation rounds are planned. The pre-registered v4 run failed the gate (mean AUC 0.559, gate 0.65) and v2 failed before it. Section mode stays experimental and labeled as such (owner decision 2026-10-16); no Jev code is removed by this change. Whether an intervention worked is judged from the loop's outcome ledger and later collector observations, not from Jev scores. `eval/jev_selection/README.md` records this.

## Impact

- Affected capability: `runtime-adapters`.
- Affected code: `egeo/agents.py`, `egeo/pipeline.py`, `egeo/cli.py`, tests, docs.
- Not in scope: the Claude Code runtime (`.claude/` agents, commands and output style) still asks the model for scores out of 100, and `examples/sample-output-report.md` and the README mock-up show them. Those are prompts and labeled mock-ups, not this CLI; changing them is a separate decision.
- `docs/examples.md` keeps its recorded 2026-10-04 totals as history, with a note.
