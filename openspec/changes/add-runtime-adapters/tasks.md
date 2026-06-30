# Tasks: Add a Runtime Adapter Layer and a Standalone `egeo` CLI

## 1. Runtime-Agnostic Agent Abstractions

- [ ] 1.1 Create the `egeo/` package with a `sys.path` bootstrap so it can import
      the root-level `geo_eval` and `llm_client` modules from any working dir.
- [ ] 1.2 Add `egeo/agents.py` with dataclasses for agent I/O (`AnalysisResult`,
      `RankResult`, `RewriteResult`, `SchemaResult`) and the four agents.
- [ ] 1.3 Implement `Ranker.rank(...)` as a thin wrapper over
      `geo_eval._rank_candidates` (reuse the `prompts/ranker_*.txt` templates).
- [ ] 1.4 Implement `Rewriter.rewrite(...)` as a thin wrapper over
      `geo_eval._rewrite_description` (reuse `prompts/rewriter_*.txt`).
- [ ] 1.5 Implement `Analyzer.analyze(...)` as a deterministic, offline heuristic
      scorer for the 10 GEO features (no LLM, no network).
- [ ] 1.6 Implement `Indexer.generate_schema(...)` by loading a template from
      `geo-output/schema/` and filling `name`/`description` (no network).

## 2. Runtime Adapter Layer

- [ ] 2.1 Add `egeo/runtimes.py` defining the `RuntimeAdapter` contract
      (factory methods for the four agents + `name`/`available()`).
- [ ] 2.2 Implement `PythonRuntime` (names `python`/`cli`) that builds the
      in-process agents using `llm_client.get_client()` and `prompts/`.
- [ ] 2.3 Implement `ClaudeCodeRuntime` (name `claude-code`) as a descriptor that
      maps each agent to its `.claude/agents/*.md` file and slash command, and
      reports `available()` based on the presence of a `.claude/` directory.
- [ ] 2.4 Add a registry: `get_runtime(name)` and `list_runtimes()`.

## 3. Optimize Pipeline

- [ ] 3.1 Add `egeo/pipeline.py` orchestrating analyze → rank(before) →
      rewrite → rank(after) → index for a single input file or string.
- [ ] 3.2 Use a small set of deterministic built-in competitor stubs so ranking
      has a baseline to compare against offline.
- [ ] 3.3 Write artifacts to the output dir: `report.md`, `analysis.json`,
      `optimized/<name>.md`, `schema/<name>.json`.

## 4. CLI

- [ ] 4.1 Add `egeo/cli.py` with subcommands `optimize`, `evaluate`,
      `optimize-prompts`, and `runtimes`.
- [ ] 4.2 Wire `evaluate` and `optimize-prompts` to `geo_eval.evaluate` /
      `geo_eval.optimize` so behavior matches `geo_eval.py` exactly.
- [ ] 4.3 Add `egeo/__main__.py` so `python -m egeo` works.
- [ ] 4.4 Add `pyproject.toml` exposing the `egeo` console script.

## 5. Continuous Integration

- [ ] 5.1 Add a CLI smoke-test step to `.github/workflows/ci.yml` running
      `python -m egeo optimize`, `evaluate`, and `runtimes` with `GEO_EVAL_MOCK=1`.
- [ ] 5.2 Confirm the existing gates (validators, link check, mock evaluate)
      are unchanged and still pass.

## 6. Release Automation

- [ ] 6.1 Add `.github/workflows/release.yml` triggered on `v*` tags and
      `workflow_dispatch`, extracting notes from `CHANGELOG.md` and publishing a
      GitHub Release via `gh release create`/`edit`.

## 7. Documentation

- [ ] 7.1 Add a "Supported Runtimes" section to `README.md` (matrix + status).
- [ ] 7.2 Add CLI usage (`egeo optimize/evaluate/optimize-prompts/runtimes`,
      including the `GEO_EVAL_MOCK=1` offline path) to `README.md`.
- [ ] 7.3 Add an `[Unreleased]` entry to `CHANGELOG.md` summarizing the change.

## 8. Validation

- [ ] 8.1 Run `GEO_EVAL_MOCK=1 python -m egeo optimize examples/sample-input.md`
      and confirm artifacts are written.
- [ ] 8.2 Confirm `egeo evaluate` output matches `geo_eval.py evaluate` for the
      same dataset/flags under the MOCK client.
- [ ] 8.3 Confirm `validate_jsonld.py` passes on the schema the Indexer emits.
- [ ] 8.4 Confirm a default `optimize-prompts` run does not modify
      `prompts/rewriter_user.txt`.
