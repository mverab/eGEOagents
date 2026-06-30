# Changelog

All notable changes to E-GEO are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - 2026-06-29

Quality hardening and a transparent, reproducible evaluation harness.

### Added

- **Deterministic MOCK LLM client** (`llm_client.py`) gated by `GEO_EVAL_MOCK=1`,
  enabling the evaluation harness to run offline in CI with no API key.
- **Smoke dataset** `eval/datasets/geo_smoke.jsonl` (7 query/candidate examples).
- **Python validators** under `scripts/`:
  - `validate_skills.py` — validates `SKILL.md` frontmatter (`name`,
    `description`), kebab-case names, and global name uniqueness.
  - `validate_jsonld.py` — structural JSON-LD validation via `jsonschema`.
- **JSON-LD schema templates** in `geo-output/schema/`: `Organization.json`,
  `Product.json`, `Service.json`, `Article.json`, `FAQPage.json` — all pass
  `validate_jsonld.py`.
- **Continuous Integration** (`.github/workflows/ci.yml`): SKILL.md frontmatter
  validation, JSON-LD validation, deprecated-slug link check, a non-blocking
  skills.sh parser smoke test, and `evaluate --limit 5` with the MOCK client.
- **Monthly QA workflow** (`.github/workflows/qa-monthly.yml`): parser
  validation, dead-link scan, metadata completeness, and release/tag freshness.
- **Evaluation documentation** (`docs/evaluation.md`): dataset format, commands,
  metric definitions (`avg_rank_improvement`, `win_rate`,
  `stderr_rank_improvement`), and an explicit proxy-vs-real-measurement
  limitation. Linked from the README with a CI badge and a "Reproducible
  results" section.
- **OpenSpec change** `harden-quality-and-expose-eval` with proposal, tasks,
  design, and the new `quality-gates` capability spec.
- **CHANGELOG.md** (this file).

### Changed

- **`optimize` is now non-destructive by default.** It writes the optimized
  prompt to `prompts/rewriter_user.candidate.txt` instead of overwriting
  `prompts/rewriter_user.txt`. Use the new `--apply` flag to overwrite the
  working prompt in place.
- `README.md` gained a CI badge, an Evaluation Harness docs link, and a
  "Reproducible Results" section.

### Notes

- Evaluation metrics are an **LLM-ranker proxy**, not a measurement of real
  AI-search engine rankings. See `docs/evaluation.md`.

[1.1.0]: https://github.com/mverab/eGEOagents/releases/tag/v1.1.0
