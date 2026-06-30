# Design: Runtime Adapter Layer and `egeo` CLI

## Context

E-GEO's four agents (Analyzer, Ranker, Rewriter, Indexer) are defined only as
Claude Code artifacts: `.claude/agents/*.md` prompts and `.claude/commands/*.md`
slash commands. The repository topics advertise `cursor`, `codex`, and
`windsurf`, but none of those runtimes can execute the pipeline — the agent
*logic* is welded to the Claude Code *runtime*.

Meanwhile, the Python harness already contains runtime-neutral building blocks:
`geo_eval._rank_candidates` and `geo_eval._rewrite_description` drive the ranker
and rewriter via `prompts/*.txt` and a pluggable `llm_client.get_client()` that
already supports an offline `MockClient` (`GEO_EVAL_MOCK=1`).

**Stakeholders:** maintainers (one contract to maintain), non-Claude users
(a real entry point), and evaluators (an honest, reproducible offline path).

**Constraints:** reuse `geo_eval.py`/`llm_client.py` (do not fork their logic),
keep dependencies tiny (no new runtime deps beyond the stdlib for the CLI),
preserve all existing CI gates, and keep the offline `GEO_EVAL_MOCK=1` path
working end-to-end.

## Goals / Non-Goals

### Goals
- Define the four-agent contract **once**, decoupled from any runtime.
- Ship a standalone `egeo` CLI that runs the pipeline outside Claude Code.
- Reuse the existing ranker/rewriter logic and prompts verbatim.
- Keep everything runnable offline in CI via the MOCK client.
- Automate GitHub Releases from `CHANGELOG.md` on `v*` tags.

### Non-Goals
- Re-implementing Claude Code's orchestration in Python (the `claude-code`
  runtime stays a descriptor; Claude Code still executes it).
- Live web scraping / MCP validation in the CLI (the CLI optimizes local files
  and uses deterministic competitor stubs; MCP-backed validation remains a
  Claude Code feature).
- Changing prompt contents or the `geo_eval` metrics.

## Decisions

### 1. A four-agent contract with pluggable runtimes

**Decision:** `egeo/runtimes.py` defines a `RuntimeAdapter` base class with
factory methods `make_analyzer/ranker/rewriter/indexer()` plus `name` and
`available()`. Two adapters implement it:

| Runtime | `name` | Agents execute… | `available()` |
|---------|--------|-----------------|---------------|
| Python/CLI | `python` (alias `cli`) | in-process via `llm_client` + `prompts/` | always |
| Claude Code | `claude-code` | in the Claude Code host (descriptor only) | `.claude/` exists |

`ClaudeCodeRuntime` exposes the file path and slash command for each agent and
raises a clear "run via Claude Code (`/geo`)" error if a caller tries to invoke
it in-process. This makes the separation explicit without pretending Python can
drive Claude Code.

**Alternatives considered:**
- *One monolithic CLI with no adapter layer*: rejected — it would re-entangle
  agent logic with a single runtime and not address the multi-runtime promise.
- *A plugin/entry-point system*: rejected as premature; two adapters and a small
  registry are enough today.

### 2. Reuse `geo_eval` for Ranker and Rewriter

**Decision:** `Ranker.rank()` calls `geo_eval._rank_candidates(...)` and
`Rewriter.rewrite()` calls `geo_eval._rewrite_description(...)`, passing the
prompts loaded from `prompts/`. The agents are thin adapters over these
functions, so the CLI and the harness share one code path and one set of
prompts.

**Rationale:** zero logic duplication; the MOCK client already understands these
prompts, so the CLI inherits the offline behavior for free.

### 3. Deterministic, offline Analyzer and Indexer

**Decision:** The Analyzer scores the 10 GEO features with a transparent keyword
/ structure heuristic (no LLM). The Indexer loads a template from
`geo-output/schema/` and fills `name`/`description`, leaving `[FILL: ...]`
placeholders intact so the emitted schema still passes `validate_jsonld.py`.

**Rationale:** keeps `egeo optimize` runnable with no API key and makes the
report deterministic for CI. Heuristic scoring is honest about being a proxy and
mirrors the signals the Claude analyzer prompt looks for.

### 4. `optimize` pipeline with built-in competitor stubs

**Decision:** `egeo/pipeline.py` runs analyze → rank(before) → rewrite →
rank(after) → index for a single input. Because the offline runtime cannot ask
an LLM to invent competitors, the pipeline ranks the target against a small set
of deterministic generic competitor stubs, yielding a before/after rank delta.
Artifacts: `report.md`, `analysis.json`, `optimized/<name>.md`,
`schema/<name>.json`.

### 5. Packaging: console script + `python -m egeo`

**Decision:** Add `pyproject.toml` declaring the `egeo` package, the root
modules `geo_eval`/`llm_client` as py-modules, and a console script
`egeo = "egeo.cli:main"`. `egeo/__init__.py` also bootstraps `sys.path` with the
repo root, so `python -m egeo` works without installation. CI uses
`python -m egeo` to avoid an install step.

### 6. Release automation from CHANGELOG

**Decision:** `.github/workflows/release.yml` triggers on `v*` tags and
`workflow_dispatch`. It resolves the tag, extracts the matching
`## [VERSION]` section from `CHANGELOG.md` with `awk`, and publishes via
`gh release create --verify-tag --latest` (falling back to `gh release edit`).
`permissions: contents: write` is required to create releases.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Heuristic analyzer diverges from the Claude analyzer | Documented as an offline proxy; the Claude runtime remains the high-fidelity path. |
| Competitor stubs are synthetic | Clearly labeled in the report; users can supply real competitors via the harness dataset. |
| `claude-code` runtime can't run in Python | By design — it is a descriptor; calling it in-process raises a helpful error. |
| Editable install exposing root modules | Scoped via explicit `py-modules`; `python -m egeo` path needs no install. |
| Release workflow needs write permission | `permissions: contents: write` set at the workflow level only. |

## Migration Plan

1. Land the `egeo/` package, `pyproject.toml`, CI smoke step, release workflow,
   and docs on `release/v2.0-runtime-adapters`.
2. Verify CI green (existing gates + new CLI smoke) on the PR.
3. After merge, finalize the `[Unreleased]` CHANGELOG section as `v2.0.0` and
   tag `v2.0.0` to exercise `release.yml`.

Rollback: the change is additive. Removing `egeo/`, `pyproject.toml`, the CI
smoke step, and `release.yml` restores prior behavior; `geo_eval.py` and
`llm_client.py` are untouched.

## Open Questions

- Should `egeo optimize` gain a `--competitors <file>` flag to supply real
  candidates instead of stubs? (Deferred to a future change.)
- Should additional descriptor runtimes (`cursor`, `windsurf`) ship generated
  rule files, or is documenting the `python` CLI entry point sufficient for
  now? (Deferred; the CLI already unblocks those runtimes.)
