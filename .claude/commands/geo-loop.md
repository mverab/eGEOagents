---
name: geo:loop
description: Run one bounded loop iteration over a workspace domain - read the charter and fresh collector data, do ONE unit of work, write substrate artifacts, close the run
arguments:
  - name: domain
    description: Domain directory name under $EGEO_HOME/domains/ (defaults to the only domain when there is exactly one)
    required: false
---

# /geo:loop Command

Execute **one** eGEOagents loop iteration. Loop state lives in the workspace
resolved from `$EGEO_HOME` (default `~/.egeo/`); the repo tree is never written
to. One-shot `/geo <url>` is unaffected.

Follow `.claude/skills/geo-loop/SKILL.md` — it is the authoritative procedure.

## Workflow

0. **Resolve the domain** - Use `$ARGUMENTS.domain`. If omitted and exactly one
   directory exists under `$EGEO_HOME/domains/` (excluding `egeo-core`), use it;
   otherwise list the domains and stop.
1. **Plan** - `egeo loop run <domain> --dry-run`. Writes nothing. Non-zero exit
   means stop and report (`egeo loop doctor` explains why).
2. **Read state** - domain charter, `data/*.jsonl` deltas, existing
   `signals/`, `docs/`, `config.yaml`.
3. **One unit of work** - from `## Current focus`, else the first Backlog item.
   Reuse `content-scoring`, `competitive-analysis`, `schema-generator`. No fresh
   data and nothing actionable = `Outcome: no-op`.
4. **Write artifacts** - `signals/<slug>.md` / `docs/<slug>.md` per
   `SUBSTRATE.md`. Re-observed evidence increments `frequency` on the existing
   signal instead of creating a file.
5. **Close the run** - append exactly one `### YYYY-MM-DD run` Timeline entry
   ending in `Outcome: success|partial|failure|no-op`, and exactly one `LOG.md`
   line. Update `## Current focus` if it was completed.
6. **Verify** - `python -m egeo.substrate_lint` and `egeo loop doctor`, then
   re-read both appends. Violations are fixed before exiting.

## Execution

```
Loop run: $ARGUMENTS.domain

Step 1/6: Plan
→ egeo loop run $ARGUMENTS.domain --dry-run

Step 2/6: Reading workspace state
→ $EGEO_HOME/domains/$ARGUMENTS.domain/README.md, data/, signals/, docs/

Step 3/6: Unit of work
→ <focus item>

Step 4/6: Writing artifacts
→ signals/... / docs/...

Step 5/6: Closing the run
→ Timeline entry + LOG.md line

Step 6/6: Verification
→ substrate_lint + doctor + re-read
```

## Output

Written to `$EGEO_HOME/` (never `geo-output/`):
- `signals/[slug].md` - evidence, deduped and frequency-counted
- `docs/[slug].md` - durable knowledge, citing signals and sources
- `domains/[domain]/README.md` - one appended Timeline entry
- `LOG.md` - one appended line

Then a three-line report: unit of work, artifacts written, outcome.

## Example Usage

```
/geo:loop example-com
/geo:loop                       (single-domain workspace)
```

Prerequisites, if the workspace is not set up yet:

```bash
egeo loop doctor                                  # bootstrap + health check
egeo loop collect serp --query "best geo tool" --target-domain example.com
egeo loop collect page --url https://example.com/pricing
```
