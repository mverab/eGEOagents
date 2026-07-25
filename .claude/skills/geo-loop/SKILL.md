---
name: geo-loop
description: Run one bounded eGEOagents loop iteration over a workspace domain - read the charter and fresh collector data, do ONE unit of work, write substrate artifacts, append one Timeline entry and one LOG line. Use for loop mode, /geo:loop, scheduled GEO runs, or continuous monitoring.
---

# GEO Loop Skill

One wake-up = **one bounded unit of work**. This skill governs loop mode only;
one-shot `/geo <url>` is unchanged and needs no workspace.

## Non-negotiables

1. **Never write to the eGEOagents repo tree.** Every write goes to the
   workspace resolved from `$EGEO_HOME` (default `~/.egeo/`).
2. **One unit of work per run.** Take the domain's `## Current focus`, or the
   first Backlog item if focus is already satisfied. Do not batch.
3. **Exactly one Timeline entry and exactly one LOG.md line per run.**
4. **Write, then verify.** Re-read every file you wrote before exiting.
5. **Never fabricate.** Rankings, competitors, and metrics come from collector
   JSONL under `data/` or from a tool call in this session. A claim you cannot
   cite is `confidence: low` with the uncertainty stated in the body.
6. **Append-only history.** Never edit or delete an existing Timeline entry or
   LOG line.

## Procedure

### 1. Resolve the plan

```bash
egeo loop run <domain> --dry-run
```

This is the source of truth for the run: it prints the charter's current focus,
the backlog, collector records added since the last Timeline entry, and
candidate signals. It writes nothing. Use `--json` when you want to parse it.

If it exits non-zero, stop and report — the workspace or the domain charter is
not in a runnable state (`egeo loop doctor` explains why).

### 2. Read the state

- `$EGEO_HOME/domains/<domain>/README.md` — charter, cadence, focus, backlog,
  Timeline (the last entry tells you where the previous run stopped).
- `$EGEO_HOME/data/<collector>/*.jsonl` — fresh ground truth.
- `$EGEO_HOME/signals/` and `$EGEO_HOME/docs/` — what is already known, so you
  dedupe instead of duplicating.
- `$EGEO_HOME/config.yaml` — models, budgets, `reflect.auto_apply`.

### 3. Do the work

Pick the single unit of work and execute it with the existing GEO capability —
the `content-scoring`, `competitive-analysis`, and `schema-generator` skills and
the `geo-*` agents all apply unchanged. Typical units:

| Situation in the plan | Unit of work |
|---|---|
| A target URL moved ≥3 positions | Write/update a signal explaining the move |
| Target absent from top 10 repeatedly | Signal + a doc proposing the fix |
| A tracked page's `content_hash` changed | Signal describing what changed |
| A tracked page has no JSON-LD | Doc with copy-paste JSON-LD for that page |
| No fresh data at all | Outcome `no-op` — do not invent work |

Ranking positions from `data/serp/` are ground truth. Any *simulated* ranking
you produce yourself is `confidence: low` and must say so in the body.

### 4. Write artifacts (SUBSTRATE.md)

`SUBSTRATE.md` in the repo root is the binding contract. In short:

- `signals/<slug>.md` — evidence. `docs/<slug>.md` — durable knowledge.
  Kebab-case filenames, English content, `kind` decides the folder.
- Frontmatter on line 1: `kind`, `domains` (existing dirs under `domains/`),
  `created`, `updated`, `confidence`, `sources`, plus `frequency` on signals.
  `sources` may be empty only when `confidence: low`.
- **Dedupe (§4):** re-observed evidence does **not** get a new file. On the
  existing signal, increment `frequency`, set `updated` to today, and append one
  dated Timeline entry.
- Body above `## Timeline` = what is true now (rewrite freely).
  `## Timeline` = append-only, newest at the bottom.
- Docs cite signals and repo paths; signals cite collector JSONL lines
  (`data/serp/example-com.jsonl#L42`).

### 5. Close the run

Append to `$EGEO_HOME/domains/<domain>/README.md`, at the very bottom:

```markdown
### 2026-07-24 run

Checked serp deltas for example.com; pricing page dropped 3 → 7 for
"best geo tool". Wrote signals/example-com-pricing-drop.md.

Outcome: success
```

`Outcome:` is the last line and one of `success`, `partial`, `failure`, `no-op`.
Then append exactly one line to `$EGEO_HOME/LOG.md`:

```
2026-07-24T18:20Z [example-com] run: wrote signals/example-com-pricing-drop.md, outcome=success
```

Grammar (SUBSTRATE.md §7): `<YYYY-MM-DDTHH:MMZ> [<domain>] <event>: <summary>`,
UTC minute precision, appended at the bottom, summary ending in
`outcome=<class>`.

Keep `## Current focus` accurate: if the focus item is done, promote the next
Backlog item and remove it from the Backlog.

### 6. Verify, then exit

```bash
python -m egeo.substrate_lint            # defaults to $EGEO_HOME
egeo loop doctor
```

Re-read the domain README and the tail of `LOG.md` to confirm your two
appends landed exactly once. Fix violations before exiting; a run that leaves
the substrate invalid is `Outcome: failure`.

Report to the user in three lines: unit of work, artifacts written, outcome.

## Collectors

Collectors are deterministic and LLM-free; run them before a loop run when the
plan shows no fresh data:

```bash
egeo loop collect serp --query "best geo tool" --target-domain example.com
egeo loop collect page --url https://example.com/pricing
```

`serp` needs `BRAVE_API_KEY`; both honour the daily budgets in `config.yaml` and
fail loudly rather than writing partial records. See `collectors/README.md` for
the contract.

## Common mistakes

- Writing into the repo `prompts/`, `geo-output/`, or `signals/` instead of
  `$EGEO_HOME` — loop state never lives in the repo.
- Two Timeline entries (or two LOG lines) for one run.
- A new signal file for evidence that already has one (use `frequency`).
- Claiming a competitor ranking without a `data/serp/` line to cite.
- Doing three units of work because the data looked interesting. One.
