## 1. Implementation
- [x] 1.1 `egeo/agents.py`: `to_dict()` no longer serializes `total_score`.
- [x] 1.2 `egeo/pipeline.py`: summary carries `signals` instead of `geo_score`; report drops the total and relabels the table.
- [x] 1.3 `egeo/cli.py`: signals line instead of "GEO score: N/100".

## 2. Tests
- [x] 2.1 `tests/test_pipeline.py`: no `/100`, `geo_score` or `total_score` in CLI text, `report.md`, `analysis.json` or `--json`; ten signals still present.

## 3. Docs
- [x] 3.1 `README.md`, `docs/examples.md` (note), `eval/jev_selection/README.md` (decision), `CHANGELOG.md`.
- [x] 3.2 Full suite, `openspec validate update-optimize-remove-aggregate-score --strict`.
