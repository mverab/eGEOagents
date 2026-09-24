## 1. Implementation
- [ ] 1.1 Tests first (`tests/test_gaps.py`): format detection, generic JSON/CSV parsing, geo-optimizer-skill parsing, tracker-error skipping, normalization/matching, unmatched reasons, one-rewrite-per-page, dry-run writes nothing, source never modified, report shape
- [ ] 1.2 `egeo/gaps.py`: load/detect gaps, match against `project.yaml`, plan, execute via `optimize_content`, build `fix-gaps.json`
- [ ] 1.3 Accept optional `pages[].source` in project config validation (relative path string)
- [ ] 1.4 `egeo fix-gaps` subcommand in `egeo/cli.py` (`--dry-run`, `--json`, `--out-dir`, `--format`, `--project`)
- [ ] 1.5 Mock end-to-end run with `GEO_EVAL_MOCK=1` in CI smoke

## 2. Documentation
- [ ] 2.1 `USAGE.md` + site CLI reference: command, both input formats, example with `geo citations --format json`
- [ ] 2.2 `/guides/track-ai-citations/`: link the "Turn measurements into fixes" step to `fix-gaps`
