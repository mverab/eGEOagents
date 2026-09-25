## 1. Implementation
- [x] 1.1 Tests first (`tests/test_gaps.py`): format detection, generic JSON/CSV parsing, geo-optimizer-skill parsing, tracker-error skipping, normalization/matching, unmatched reasons, one-rewrite-per-page, dry-run writes nothing, source never modified, report shape
- [x] 1.2 `egeo/gaps.py`: load/detect gaps, match against `project.yaml`, plan, execute via `optimize_content`, build `fix-gaps.json`
- [x] 1.3 Accept optional `pages[].source` in project config validation (relative path string)
- [x] 1.4 `egeo fix-gaps` subcommand in `egeo/cli.py` (`--dry-run`, `--json`, `--out-dir`, `--format`, `--project`)
- [x] 1.5 Mock end-to-end run with `GEO_EVAL_MOCK=1` in CI smoke (covered by `tests/test_gaps.py`, which CI runs via pytest)

## 2. Documentation
- [x] 2.1 `USAGE.md` + site CLI reference: command, both input formats, example with `geo citations --format json`
- [x] 2.2 `/guides/track-ai-citations/`: link the "Turn measurements into fixes" step to `fix-gaps`
