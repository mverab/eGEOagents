# Change: Add Loop Mode — Persistent Workspace, Collectors, and `egeo loop`

## Why

E-GEO is one-shot today. `/geo <url>` (or `egeo optimize <file>`) produces an
audit plus `geo-output/` artifacts and is then forgotten. Three consequences:

- **Nothing accumulates.** Every run starts from zero. There is no position
  history, no record of which optimization was applied to which page, and no
  way to answer "is this page doing better than last month?".
- **Ranking validation is point-in-time and simulated.** `geo-ranker`
  simulates an AI-engine ranking; without repeated ground-truth observations
  the result cannot be corroborated, which is exactly why the repo already
  labels uncorroborated output **Low Confidence**.
- **There is no scheduler seam.** Nothing in the repo can be driven by cron.
  Continuous optimization requires a plain CLI entrypoint any scheduler can
  invoke.

The design for this change was specified in the companion system repo
(`mverab/loopstack`, change `phase-2-egeoagents-loop-integration`); this is the
mirroring implementation change for eGEOagents v2.0.

## What Changes

### New: per-user workspace (loop state outside the repo)

- Vendor `SUBSTRATE.md` (the knowledge-base contract) into the repo root.
- Add `egeo/workspace.py`: single resolution of `$EGEO_HOME`
  (default `~/.egeo/`) plus an **idempotent bootstrap** that creates
  `LOG.md`, `config.yaml`, `signals/`, `docs/`, `data/`, `domains/`,
  `prompts/`, copies `SUBSTRATE.md` into the workspace, and records the
  bootstrap as one `LOG.md` line.
- Add `egeo/substrate_lint.py` (stdlib only, adapted from loopstack's
  `scripts/substrate_lint.py`) so the workspace can be linted mechanically.

### New: deterministic collectors

- `collectors/README.md` — the collector contract.
- `collectors/serp.py` — Brave Search API over direct HTTPS (`BRAVE_API_KEY`,
  stdlib `urllib`), queries from the workspace `config.yaml`; appends top-10
  results plus the target's position to `data/serp/<query-slug>.jsonl`.
- `collectors/page.py` — fetch configured URLs; append content hash, title,
  meta description, JSON-LD `@type`s and word count to
  `data/page/<page-slug>.jsonl`.
- Both support a `--fixture` mode that replays recorded responses from disk, so
  the contract is testable with no network and no API key.

### New: `egeo loop` subcommands (existing CLI, no new binary)

- `egeo loop run <domain> [--dry-run]` — resolve the run plan (charter focus,
  fresh collector deltas since the last run, candidate signals). `--dry-run`
  prints the plan and writes nothing. This is the trigger seam a scheduler
  calls; the interpretive work itself is performed by the loop skill inside an
  agent runtime.
- `egeo loop collect <serp|page> [--fixture ...]` — one collector pass.
- `egeo loop doctor` — workspace self-check (layout, config parse, substrate
  lint, `BRAVE_API_KEY` presence as a warning, budget sanity).

### New: the loop run procedure

- `.claude/skills/geo-loop/SKILL.md` — read charter + fresh collector data +
  recent signals → do **one** unit of work → write/update artifacts (signal
  dedupe by `frequency`, docs cite sources) → append exactly one domain
  `## Timeline` entry ending in `Outcome:` → append exactly one workspace
  `LOG.md` line → verify both writes → exit.
- `.claude/commands/geo-loop.md` — `/geo:loop [domain]` manual trigger.

### Modified

- `geo_eval.py` — **workspace-first prompt resolution**: when
  `$EGEO_HOME/prompts/<name>.txt` exists it is preferred over the repo default,
  for both `evaluate` and `optimize`. In loop mode (a bootstrapped workspace
  exists) `optimize` writes its output prompt into `$EGEO_HOME/prompts/`
  instead of the repo tree. With no workspace, behavior is byte-for-byte
  unchanged.
- `egeo/cli.py` — register the `loop` subcommand group.
- `README.md`, `USAGE.md`, `.claude/CLAUDE.md`, `CHANGELOG.md` — document loop
  mode, `$EGEO_HOME`, the collector contract, and Hermes cron examples.

### Explicitly untouched

`.claude/agents/`, existing `.claude/commands/geo*.md`, existing
`.claude/skills/` (competitive-analysis, content-scoring, schema-generator,
validation-doctor), `prompts/*.txt` defaults, `llm_client.py`,
`egeo/agents.py`, `egeo/pipeline.py`, `egeo/runtimes.py`, and the
`geo-output/` one-shot convention. One-shot `/geo` and `egeo optimize` keep
working with no workspace present.

## Impact

### Affected specs

- New capability: `geo-loop-runtime`.
- New capability: `loop-collectors`.

### Affected files (planned implementation)

- `SUBSTRATE.md` (vendored), `egeo/workspace.py`, `egeo/substrate_lint.py`,
  `egeo/loop.py` (new)
- `egeo/cli.py`, `geo_eval.py` (modified)
- `collectors/README.md`, `collectors/serp.py`, `collectors/page.py`,
  `collectors/fixtures/*` (new)
- `.claude/skills/geo-loop/SKILL.md`, `.claude/commands/geo-loop.md` (new)
- `README.md`, `USAGE.md`, `.claude/CLAUDE.md`, `CHANGELOG.md` (docs)

### External systems

- Brave Search API (`BRAVE_API_KEY`) — direct HTTP, not MCP: collectors are
  plain cron scripts with no agent attached. The Brave MCP remains the
  interactive-session path.
- A scheduler (Hermes cron is the reference) invoking the CLI.

### Success criteria

- `EGEO_HOME=$(mktemp -d) python -m egeo loop doctor` bootstraps a workspace and
  reports it healthy; a second run changes nothing.
- `python collectors/serp.py --fixture <recorded.json>` and
  `python collectors/page.py --fixture <html-dir>` append schema-valid JSONL
  with no network access, and re-running appends without corrupting prior lines.
- `python -m egeo loop run <domain> --dry-run` prints a plan and modifies no
  file in the workspace or the repo.
- `GEO_EVAL_MOCK=1 python geo_eval.py evaluate --dataset eval/datasets/geo_smoke.jsonl --limit 5`
  still passes, and `python scripts/validate_skills.py --root .` passes with the
  new skill.
- With `$EGEO_HOME/prompts/rewriter_user.txt` present it is the prompt actually
  used; with no workspace the repo defaults are used exactly as before.
