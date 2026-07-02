# Changelog

All notable changes to E-GEO are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

### Changed

### Fixed

## [2.0.0] - 2026-06-30

Runtime-agnostic execution: a standalone `egeo` CLI and a pluggable runtime
adapter layer, so the same GEO engine runs outside Claude Code without
duplicating any optimization logic.

### Added

- **Runtime adapter layer** (`egeo/runtimes.py`): a `RuntimeAdapter` interface
  with a `python` (aliases `cli`, `local`) in-process adapter and a
  `claude-code` (alias `claude`) host-executed descriptor, plus a small registry
  (`get_runtime`, `list_runtimes`, `runtime_status`). New `egeo runtimes`
  command prints live adapter status.
- **Standalone `egeo` CLI** (`egeo/cli.py`, `python -m egeo`) exposing:
  - `optimize <file>` — full pipeline (analyze → rank → rewrite → schema) that
    writes `report.md`, `optimized/*.md`, `schema/*.json`, and `analysis.json`.
  - `evaluate` — the evaluation harness, delegating to `geo_eval.py` with
    byte-identical output.
  - `optimize-prompts` — meta-optimizes the rewriter prompt (non-destructive by
    default, mirroring `geo_eval.py optimize`).
  - `runtimes` — list available runtime adapters.
- **Agent wrappers** (`egeo/agents.py`) and **pipeline** (`egeo/pipeline.py`)
  that reuse `geo_eval.py` (`_rank_candidates`, `_rewrite_description`) and
  `llm_client.py` — **no duplicated optimization logic**. The whole CLI honors
  `GEO_EVAL_MOCK=1` for deterministic, offline runs (no API key).
- **Packaging** (`pyproject.toml`): installs the `egeo` package alongside the
  existing `geo_eval`/`llm_client` modules and registers the `egeo` console
  script (`pip install -e .`).
- **Release automation** (`.github/workflows/release.yml`): on `v*` tags (or
  manual `workflow_dispatch`), extracts the matching `CHANGELOG.md` section and
  publishes a GitHub Release via `gh`, using the GitHub-injected token (no PAT).
- **OpenSpec change** `add-runtime-adapters` with proposal, tasks, design, and a
  new `runtime-adapters` capability spec.

### Changed

- **CI** (`.github/workflows/ci.yml`): added a CLI smoke test that runs
  `egeo runtimes`, `egeo evaluate`, and a full `egeo optimize` under
  `GEO_EVAL_MOCK=1`, then validates the emitted JSON-LD. Existing quality gates
  are unchanged.
- **README.md**: new "Standalone CLI (`egeo`)" and "Supported Runtimes" sections
  documenting installation, commands, offline mode, and the runtime matrix.

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

[Unreleased]: https://github.com/mverab/eGEOagents/compare/v1.1.0...HEAD
[1.1.0]: https://github.com/mverab/eGEOagents/releases/tag/v1.1.0
