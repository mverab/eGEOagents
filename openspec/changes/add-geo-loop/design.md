# Design: Loop Mode for E-GEO v2.0

## Context

The upstream design (`loopstack`, `phase-2-egeoagents-loop-integration`) was
written against E-GEO v1, which had no CLI package: it proposed a new top-level
`egeo_loop.py` script. This repo is now v2.0 and already ships the `egeo`
package (`cli.py`, `runtimes.py`, `agents.py`, `pipeline.py`) with an argparse
subcommand pattern and offline `GEO_EVAL_MOCK=1` execution. This design adapts
the upstream contract to that reality; the *requirements* are unchanged, only
their surface is.

## Architecture

```text
scheduler (Hermes cron of record; system cron / manual work identically)
  ├── high-freq:  python -m egeo loop collect serp     # deliver=local
  ├── high-freq:  python -m egeo loop collect page     # deliver=local
  ├── low-freq:   claude -p "/geo:loop <domain>"       # provider+model pinned
  └── weekly:     digest of $EGEO_HOME/LOG.md → owner

repo (code, versioned)                $EGEO_HOME (state, per user, default ~/.egeo/)
  egeo/loop.py       ───────────────►  LOG.md, config.yaml, SUBSTRATE.md,
  egeo/workspace.py                    signals/, docs/, data/<collector>/*.jsonl,
  egeo/substrate_lint.py               domains/<loop>/README.md, prompts/
  collectors/{serp,page}.py
  .claude/skills/geo-loop/SKILL.md
```

## Key decisions

### D1 — No new binary: `loop` is a subcommand group of `egeo`

Upstream specified `egeo_loop.py run|collect|doctor`. v2.0 already has one
entrypoint (`egeo` / `python -m egeo`), a dispatch table, and per-subcommand
parser builders. Adding a second top-level script would fork the entrypoint,
duplicate the mock-mode/`sys.path` bootstrap, and require another `py-modules`
entry in `pyproject.toml`. Instead: `egeo/loop.py` implements
`run|collect|doctor` and `egeo/cli.py` registers a single `loop` parser with a
nested subparser. Command strings become `egeo loop run <domain>` etc.
Consequence: no packaging change at all — the new module lives inside the
already-declared `egeo` package.

### D2 — The CLI is the trigger seam; the agent does the interpreting

A loop run is interpretive work (data → knowledge), which lives in a markdown
skill so it is reviewable and later improvable, not in Python. So
`egeo loop run` deliberately does **not** call an LLM. It resolves and prints
the run plan: the domain charter's current focus, collector deltas since the
last Timeline entry, and candidate signals. `--dry-run` is the read-only
contract test; without it the command additionally guarantees the workspace is
bootstrapped and the domain exists, so the agent invocation that follows
(`claude -p "/geo:loop <domain>"`) starts from a valid state. This keeps the
LLM-free/LLM-bearing split identical to the collector/agent split.

### D3 — Workspace-first prompt resolution instead of an unconditional redirect

Upstream D-N2 said "`optimize()` writes to `$EGEO_HOME/prompts/` instead of the
repo". Half of that hardening already shipped in v2.0: `--apply` gates the
destructive write, and the default is a non-destructive `*.candidate.txt`. What
remains, and what this change adds, is *state location*:

1. `geo_eval` resolves each prompt file through the workspace first
   (`$EGEO_HOME/prompts/<name>` wins over `prompts/<name>`), used by both
   `evaluate` and `optimize`.
2. When a bootstrapped workspace exists, `optimize` writes its result (applied
   or candidate) into `$EGEO_HOME/prompts/`, leaving the repo tree pristine.
3. When no workspace exists, resolution and write paths are exactly the v2.0
   behavior. The change is purely additive for one-shot users.

Rationale: a hard redirect would make `optimize` fail or silently create
`~/.egeo` for users who never opted into loop mode. Gating on "workspace
exists" makes loop mode opt-in while still guaranteeing that loop users never
get their memory clobbered by `git pull`.

### D4 — Collectors are stdlib scripts with a fixture mode

Same style as `llm_client.py`: `urllib.request` for HTTP, `argparse`, JSON out.
No `requests`, no `beautifulsoup4`; `page.py` parses HTML with
`html.parser.HTMLParser`. Brave is called through its HTTP API rather than the
Brave MCP because a cron-launched collector has no agent attached (upstream
D-N3). Each collector exposes `main(argv)` so `egeo loop collect` can invoke it
in-process, and `--fixture` replays recorded responses so CI covers the contract
with no network and no key. Config is read from the workspace `config.yaml`
through `egeo.workspace.load_config()`, which uses the already-declared `pyyaml`
dependency when importable and a small inline parser for the documented config
subset otherwise — so a bare-stdlib environment still runs collectors.

### D5 — Substrate lint is vendored, not re-invented

`egeo/substrate_lint.py` is an adaptation of loopstack's lint (stdlib only,
`path:line: message`, non-zero exit). `egeo loop doctor` calls it as a library
against the workspace root. This keeps a single mechanical definition of "valid
artifact" on both sides of the vendoring boundary.

### D6 — Budgets fail loud

`config.yaml` carries `budgets.queries_per_day`. `serp.py` counts today's
records already in its JSONL streams and refuses to exceed the cap, exiting
non-zero with an actionable message rather than silently truncating — a
collector that quietly stops collecting is worse than one that fails.

## Risks / trade-offs

- **Headless agent runs cost money and can flake.** Mitigated by one unit of
  work per wake-up, `--dry-run`, and low cadence until the loop proves value.
- **Two prompt locations can confuse users.** Mitigated by `doctor` printing
  which prompts are overridden, and by "delete the workspace file to reset".
- **Vendored-file drift.** The vendored `SUBSTRATE.md` carries its upstream
  commit in a header comment, and `doctor` reports when the workspace copy
  differs from the repo copy.
- **Windows.** `Path.home()`, no symlinks, `\n` writes only.

## Rollback

Delete the new files and revert the `geo_eval.py`/`egeo/cli.py` diffs. Nothing
in one-shot mode depends on them, and workspaces are user data: rollback leaves
`$EGEO_HOME` untouched.
