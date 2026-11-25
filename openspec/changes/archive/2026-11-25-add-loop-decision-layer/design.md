## Context

`egeo loop run` currently prints candidate signals. The agent still has to invent the next action. Self-enforcing requires a deterministic decision function and a durable outcome record.

## Goals / Non-Goals

- Goals:
  - Rank exactly one next action per wake-up.
  - Persist proposed/applied/verified/withdrawn outcomes with 7/14/28-day windows.
  - Fail closed when project.yaml is invalid.
  - Keep the command LLM-free.
- Non-goals:
  - Auto-publishing visible copy.
  - Auto-merging PRs.
  - Calling answer engines or Search Console from this command.
  - Replacing collectors or the geo-loop skill.

## Decisions

### Command

`egeo loop decide` is the scheduler seam for decisions. It reads:

1. validated `project.yaml` (required; legacy config is not enough for ranking)
2. collector JSONL under `$EGEO_HOME/data/`
3. `$EGEO_HOME/data/outcomes/ledger.jsonl`

It writes at most:

- one new ledger row (`status: proposed`)
- one proposal markdown under `$EGEO_HOME/docs/`
- one LOG.md line

`--dry-run` writes nothing.

### Action kinds (fixed v1)

| kind | trigger | next_gate |
|---|---|---|
| `collect_fresh` | no collector records, or last observation older than measurement cadence | run collectors |
| `wait_for_window` | a proposed/applied action has not reached its next window | do nothing; grade later |
| `grade_outcome` | an open ledger row has reached 7/14/28 days and new observations exist | mark improved / unchanged / worse / withdrawn |
| `escalate_absent` | active query target_position is null across ≥3 observations | owner: indexing / discovery, not more pages |
| `propose_page_owner` | active generic/informational query has no target_pages | owner: assign or create one canonical page |
| `propose_schema` | tracked page has empty `jsonld_types` | owner: additive JSON-LD only |
| `no_op` | none of the above | record no-op |

Priority is the table order. Exactly one action is emitted.

### Ledger record

```json
{
  "v": 1,
  "id": "2026-08-25T06:00Z-escalate-absent-slashstack",
  "ts": "2026-08-25T06:00:00Z",
  "project_id": "slashstack",
  "kind": "escalate_absent",
  "status": "proposed",
  "query_ids": ["branded-slashstack"],
  "page_ids": ["home"],
  "evidence": ["data/serp/slashstack.jsonl"],
  "windows_days": [7, 14, 28],
  "grades": {},
  "next_gate": "owner",
  "auto_apply": false
}
```

Statuses: `proposed` → `applied` (human) → `verified` | `unchanged` | `worse` | `withdrawn`.
`decide` may set `verified/unchanged/worse/withdrawn` when grading from collector data. It never sets `applied`.

### Proposal document

Written only for kinds that need owner work (`escalate_absent`, `propose_page_owner`, `propose_schema`). Body cites evidence paths, names the gate, and states `auto_apply: false`.

## Risks / Trade-offs

- Ranking too aggressively creates spammy docs → one action per wake-up, dedupe against open ledger rows of the same kind+query/page.
- Grading without enough later observations → `wait_for_window`, never invent improvement.
- Legacy workspaces without project.yaml → decide exits non-zero asking for the portable contract.

## Migration Plan

1. Spec + tests for ranking and ledger append.
2. Implement `decide` as a loop subcommand.
3. Dry-run against the live SlashStack workspace (read-only).
4. PR, no merge without owner gate.
