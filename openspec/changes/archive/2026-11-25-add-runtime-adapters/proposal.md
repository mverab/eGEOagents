# Change: Add a Runtime Adapter Layer and a Standalone `egeo` CLI

## Why

E-GEO advertises broad runtime support — the repository topics include
`claude-code`, `cursor`, `codex`, and `windsurf` — but the product is only
actually executable inside **Claude Code**. The four agents (Analyzer, Ranker,
Rewriter, Indexer) exist solely as Claude-Code-specific definitions in
`.claude/agents/*.md`, the pipeline is a set of Claude slash commands
(`.claude/commands/*.md`), and the only thing a non-Claude user can run is the
low-level evaluation harness (`geo_eval.py`).

This creates three problems:

- **The multi-runtime promise is unmet.** Cursor/Codex/Windsurf users who
  install the repo (or `npx skills add ...`) get agent prompts they cannot
  execute as a pipeline. The agent *logic* is entangled with the Claude Code
  *runtime*.
- **No runtime-agnostic entry point.** There is no way to run "optimize this
  file" outside Claude Code, even though the building blocks (the ranker and
  rewriter prompts plus `llm_client.py`) are already runtime-neutral Python.
- **The harness is hard to discover.** `geo_eval.py evaluate/optimize` is
  powerful but undocumented as a product surface; new users do not know it
  exists or how the commands map to the agents.

## What Changes

- Add a **runtime adapter abstraction** (`egeo/runtimes.py`) that defines the
  four-agent contract once and lets concrete runtimes plug in implementations:
  - `python` (a.k.a. `cli`) — runs the agents in-process using `llm_client.py`
    and the prompts in `prompts/`. This is the runtime the CLI uses.
  - `claude-code` — a descriptor adapter that points at the existing
    `.claude/` agent definitions and slash commands; it documents the mapping
    and is executed by the Claude Code host, not in Python.
- Add **runtime-agnostic agent abstractions** (`egeo/agents.py`) for Analyzer,
  Ranker, Rewriter, and Indexer. Ranker and Rewriter **reuse** the existing
  `geo_eval._rank_candidates` / `geo_eval._rewrite_description` functions and
  the `prompts/` templates — no logic is duplicated. Analyzer and Indexer are
  deterministic, offline implementations (heuristic GEO scoring + JSON-LD
  template filling) so the pipeline runs without an API key.
- Add a standalone **`egeo` CLI** (`egeo/cli.py`, runnable as `egeo` or
  `python -m egeo`) exposing:
  - `egeo optimize <file>` — run the analyze → rank → rewrite → index pipeline
    and write `geo-output/` artifacts.
  - `egeo evaluate` — thin wrapper over `geo_eval.evaluate`.
  - `egeo optimize-prompts` — thin wrapper over `geo_eval.optimize`
    (the meta-optimizer; non-destructive by default).
  - `egeo runtimes` — list available runtimes and their status.
- The CLI honors **`GEO_EVAL_MOCK=1`** end-to-end (via the shared
  `llm_client.get_client()`), so it runs offline in CI with no secrets.
- Add a minimal `pyproject.toml` exposing the `egeo` console script (editable
  install) while keeping `python -m egeo` working without installation.
- **CI:** add a CLI smoke-test step to `.github/workflows/ci.yml`
  (`GEO_EVAL_MOCK=1 python -m egeo ...`) without changing existing gates.
- **Release automation:** add `.github/workflows/release.yml` that publishes a
  GitHub Release from `CHANGELOG.md` on `v*` tags (and via `workflow_dispatch`).
- **Docs:** add a "Supported Runtimes" section and CLI usage to `README.md`;
  add an `[Unreleased]` entry to `CHANGELOG.md`.

## Impact

### Affected specs

- New capability: `runtime-adapters`.

### Affected files (planned implementation)

- `egeo/__init__.py`, `egeo/__main__.py`, `egeo/agents.py`, `egeo/runtimes.py`,
  `egeo/pipeline.py`, `egeo/cli.py` (new package)
- `pyproject.toml` (new; console script `egeo`)
- `geo_eval.py`, `llm_client.py` (reused, not modified)
- `.github/workflows/ci.yml` (add CLI smoke step)
- `.github/workflows/release.yml` (new)
- `README.md` ("Supported Runtimes" + CLI usage)
- `CHANGELOG.md` (`[Unreleased]` entry)

### External systems

- GitHub Actions (CI smoke step + Release workflow)
- OpenAI-compatible API (real runs only; CI uses the MOCK client)

### Success criteria

- `GEO_EVAL_MOCK=1 python -m egeo optimize examples/sample-input.md` completes
  offline and writes a report, optimized content, and a JSON-LD schema file.
- `GEO_EVAL_MOCK=1 python -m egeo evaluate --dataset eval/datasets/geo_smoke.jsonl --limit 3`
  prints a summary with `avg_rank_improvement`, `win_rate`, and
  `stderr_rank_improvement` (identical numbers to `geo_eval.py evaluate`).
- `egeo runtimes` lists `python` (available) and `claude-code` (available when a
  `.claude/` directory is present).
- The Ranker and Rewriter agents call into `geo_eval` — no ranking/rewriting
  logic is re-implemented in `egeo/`.
- Pushing a `v*` tag publishes a GitHub Release whose body is the matching
  `CHANGELOG.md` section.
