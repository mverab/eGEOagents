# Tasks: Add Loop Mode — Workspace, Collectors, and `egeo loop`

## 1. Contract

- [x] 1.1 Scaffold `openspec/changes/add-geo-loop/` (proposal, design, tasks,
      `specs/geo-loop-runtime/spec.md`, `specs/loop-collectors/spec.md`) and
      pass `openspec validate add-geo-loop --strict`.
- [x] 1.2 Vendor `SUBSTRATE.md` from loopstack into the repo root with a header
      comment recording the upstream commit and vendoring date.

## 2. Workspace

- [x] 2.1 Add `egeo/workspace.py`: `resolve_home()` honoring `$EGEO_HOME` with a
      `~/.egeo` default, plus `prompts_dir()`, `data_dir()`, `load_config()`,
      `append_log()`.
- [x] 2.2 Implement idempotent `bootstrap()`: create `LOG.md`, `config.yaml`
      (cadence, models, budgets, `reflect.auto_apply: never`, scaling weights),
      `signals/`, `docs/`, `data/`, `domains/`, `prompts/`; copy `SUBSTRATE.md`;
      append the bootstrap `LOG.md` line. Never overwrite an existing file.
- [x] 2.3 Add `egeo/substrate_lint.py` (stdlib only) adapted from loopstack's
      `scripts/substrate_lint.py`, callable as a library.
- [x] 2.4 Verify: `EGEO_HOME=$(mktemp -d) python -m egeo loop doctor` bootstraps
      then reports healthy; a second run leaves every file byte-identical.

## 3. Collectors

- [x] 3.1 Write `collectors/README.md`: deterministic, zero LLM calls,
      append-only versioned JSONL under `$EGEO_HOME/data/<collector>/`,
      idempotent, no interpretation, one LOG line, non-zero exit on hard
      failure.
- [x] 3.2 Write `collectors/serp.py`: Brave Search API over stdlib `urllib`
      (`BRAVE_API_KEY`), queries from `config.yaml`, records
      `{v, ts, query, results[...], target_position}`; ≤1 qps; enforce
      `budgets.queries_per_day`.
- [x] 3.3 Write `collectors/page.py`: fetch configured URLs, record
      `{v, ts, url, status, content_hash, title, meta_description,
      jsonld_types, word_count}`.
- [x] 3.4 Add `--fixture` mode to both collectors plus recorded fixtures under
      `collectors/fixtures/`; verify both run offline and append valid JSONL
      twice without corrupting earlier lines.

## 4. Loop skill + command

- [x] 4.1 Write `.claude/skills/geo-loop/SKILL.md`: read charter + fresh data +
      recent signals, do ONE unit of work, write artifacts per `SUBSTRATE.md`,
      append one Timeline entry ending in `Outcome:`, append one LOG line,
      write-then-verify, exit.
- [x] 4.2 Write `.claude/commands/geo-loop.md` (`/geo:loop [domain]`) following
      the existing command-file conventions.
- [x] 4.3 Verify `python scripts/validate_skills.py --root .` passes.

## 5. CLI surface

- [x] 5.1 Add `egeo/loop.py` with `run <domain> [--dry-run]`,
      `collect <serp|page>`, `doctor`.
- [x] 5.2 Register the `loop` subcommand group in `egeo/cli.py` following the
      existing parser/dispatch pattern.
- [x] 5.3 Add workspace-first prompt resolution to `geo_eval.py` and route
      `optimize`'s output prompt into `$EGEO_HOME/prompts/` when a workspace
      exists.
- [x] 5.4 Verify: `python -m egeo loop run <domain> --dry-run` prints a plan and
      writes nothing; `GEO_EVAL_MOCK=1` evaluate still passes; a workspace
      `rewriter_user.txt` is the prompt actually used.

## 6. Docs

- [x] 6.1 Document loop mode, `$EGEO_HOME`, and the collector contract in
      `README.md` and `USAGE.md`, including Hermes cron examples (pinned
      provider+model, `deliver=local` + weekly digest).
- [x] 6.2 Update `.claude/CLAUDE.md` with loop mode and state explicitly that
      one-shot `/geo` and `egeo optimize` are unchanged.
- [x] 6.3 Add a `CHANGELOG.md` `[Unreleased] > Added` entry.
