## 1. Prompts
- [x] 1.1 `prompts/rewriter_article_system.txt` and `rewriter_article_user.txt`, mirrored in `egeo/resources/prompts/` and listed in `tests/test_resources.py`.

## 2. Pipeline
- [x] 2.1 `geo_eval._rewrite_description`: optional `suffix` appended after the rendered template.
- [x] 2.2 `egeo/agents.py`: `Rewriter(content_type=...)` picks the prompt pair; `rewrite(..., repair=...)`.
- [x] 2.3 `egeo/runtimes.py`: `make_rewriter(content_type="product")`.
- [x] 2.4 `egeo/pipeline.py`: `detect_content_type`, `check_page_fidelity`, one repair attempt, `rejected/` output, `allow_lossy`, fidelity in `analysis.json` and `report.md`.
- [x] 2.5 `egeo/cli.py`: `--content-type`, `--allow-lossy`, output lines and `--json` fields.
- [x] 2.6 `egeo/gaps.py`: page-mode entries carry `content_type` and `fidelity`.

## 3. Tests
- [x] 3.1 `tests/test_pipeline.py`: content-type detection; page rules (list markers, ignored rules); passed, repaired, rejected and lossy paths with a scripted rewriter; article prompt selected for long pages; mock end-to-end still writes `optimized/`.
- [x] 3.2 `tests/test_gaps.py`: page-mode entry reports fidelity.

## 4. Docs and verification
- [x] 4.1 `README.md`, `USAGE.md`, `site/src/content/docs/docs/cli.md`, `docs/examples.md` (note only; recorded runs unchanged), `CHANGELOG.md`.
- [x] 4.2 Full suite, CI smoke commands under `GEO_EVAL_MOCK=1`, `openspec validate update-optimize-page-fidelity --strict`.
