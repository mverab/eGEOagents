# Changelog

All notable changes to E-GEO are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed
- `egeo fix-gaps` now defaults to **section mode**: it rewrites only the one section that loses each query, instead of the whole page. The legacy whole-page rewrite stays available via `--mode page`.

### Added
- `fix-gaps` section mode: per-section rewrite with deterministic **fidelity gates** (heading, links, numbers, table rows, code blocks, length), a Jev fidelity judge and a Jev before/after re-check. Rejections (`rejected_fidelity_rules`, `rejected_fidelity_judge`, `rejected_worse`) keep the original text untouched; a rewriter LLM failure marks the page `rewriter_error` and the run continues. Section mode pre-checks `TYPESAFE_API_KEY` and `OPENAI_API_KEY`.
- Jev diagnosis/verification marked **experimental** (`"experimental": true`) with the validation numbers in every report's `jev_validation` block: text-competitiveness only; the same single-choice comparison scored mean AUC 0.62 (95% CI 0.56–0.67, 30 queries, 2026-09-25, full-page excerpts), below the 0.65 bar, with own-page accuracy 0.17. Not a prediction of citation. The Jev fidelity judge is not validated directly.
- `already_best` off-page recommendation: the sources the engine cited, so you can get mentioned or linked by them.
- `eval/jev_selection`: the validation harness (noul + choice scorers, bootstrap CI) and README with the pre-registered method and results.

## [2.1.0] - 2026-09-25

### Added
- `egeo fix-gaps`: reads an AI-visibility tracker's report (geo-optimizer-skill `geo citations --format json`, or a generic `query`/`cited` JSON/CSV), maps each uncited query to its local page through `project.yaml`, and rewrites each losing page once with the `optimize` pipeline. Writes `fix-gaps.json` with unmatched/skipped reasons and a re-measure list. Source files are never modified.
- `project.yaml`: optional `pages[].source` (path to the page's local file).

## [2.0.1] - 2026-09-14

First release where the published PyPI package actually runs the full CLI
outside the repository tree. Includes the loop capabilities merged since
v2.0.0, which the broken 2.0.0 wheel never delivered in working form.

### Fixed

- **Wheel packaging:** the PyPI wheel now ships the runtime resources
  (`prompts/`, `collectors/` incl. fixtures, `SUBSTRATE.md`,
  `examples/project.yaml`) under `egeo/resources/`, and resource resolution
  falls back to the packaged copies when the repository tree is absent
  (`egeo.resource_root()`). The 2.0.0 wheel could not run `optimize`,
  `evaluate`, `loop collect`, `loop decide` or a clean `loop doctor` outside
  the repo (see `docs/baseline-evidence-loop-2026-09-11.md`). A CI wheel
  install smoke test now guards the packaged workflow, and
  `tests/test_resources.py` fails if the packaged copies drift from the
  repo-root canonical files.
- An explicit `PythonRuntime(root=...)` keeps full control of prompt/schema
  locations; `resource_root()` is only the default.

### Added

- **Loop mode** (opt-in): eGEOagents can now run as a continuous loop instead of
  a one-shot pipeline. One-shot behavior is unchanged and never requires a
  workspace.
  - **Workspace** (`egeo/workspace.py`): all loop state resolves from
    `$EGEO_HOME` (default `~/.egeo/`) — `LOG.md`, `config.yaml`, `signals/`,
    `docs/`, `data/`, `domains/`, `prompts/`. Bootstrap is idempotent and never
    overwrites an existing file. The repo tree is never written to by a loop run,
    a collector pass, or a prompt optimization.
  - **`SUBSTRATE.md`** vendored from `loopstack` — the artifact/layout contract —
    plus `egeo/substrate_lint.py` to enforce the mechanically checkable parts
    (frontmatter, domain charters, `LOG.md` grammar).
  - **`egeo loop` command group** (`egeo/loop.py`): `doctor` (bootstrap +
    health check), `collect <serp|page>` (collector pass), `run <domain>`
    (resolve and print the run plan; `--dry-run` writes nothing), and
    `decide` (deterministic next-action ranking over collector data, the
    portable `project.yaml` contract and the append-only outcome ledger).
    LLM-free by design — the interpretive work is performed by the agent.
  - **Portable project contract** (`$EGEO_HOME/project.yaml`, example in
    `examples/project.yaml`): project identity, tracked pages and query
    records move out of the machinery `config.yaml`, validated on load.
  - **Collectors** (`collectors/`): deterministic, budget-aware, append-only
    JSONL senses — `serp` (Brave API, top-10 + target position) and `page`
    (content hash, title, meta description, JSON-LD types, word count), both with
    offline `--fixture` support and a documented 10-point contract.
  - **`geo-loop` skill and `/geo:loop` command**: the run contract — one bounded
    unit of work, exactly one Timeline entry ending in an `Outcome:` class, and
    exactly one `LOG.md` line, verified before exit.
  - **OpenSpec change** `add-geo-loop` with the `geo-loop-runtime` and
    `loop-collectors` specs.

### Changed

- `geo_eval.py` now resolves prompts workspace-first: a file in
  `$EGEO_HOME/prompts/` overrides its repo `prompts/` counterpart, and
  `optimize` writes its result there, so the repo `prompts/` stay pristine in
  loop mode. With no workspace, behavior is identical to before.

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
