<!--
Vendored from mverab/loopstack SUBSTRATE.md (loop-engineering system repo).
Upstream commit: 9696dd5
Vendored: 2026-07-24. Contents are verbatim; this repo consumes the contract
as-is and copies this file into $EGEO_HOME at bootstrap (see egeo/workspace.py).
Update by re-copying from loopstack, never by editing here.
-->

# Substrate Contract

**Status:** Normative. This file is the single source of truth for the
knowledge-base contract. `ARCHITECTURE.md` §2 explains *why* the model looks
like this; this file defines *what* is valid. Where the two disagree, this
file wins and `ARCHITECTURE.md` is the bug.

**Audience:** every loop (human or agent) that reads or writes substrate, and
`scripts/substrate_lint.py`, which enforces the rules below mechanically.

**Vendoring:** products adopt the substrate by copying this one file into their
workspace at bootstrap. It has no dependencies on the rest of this repo.

---

## 1. Layout

```
<substrate root>/
├── LOG.md                  # global append-only activity feed (one line per event)
├── signals/<slug>.md       # kind: signal — evidence, deduped, frequency-counted
├── docs/<slug>.md          # kind: doc — durable knowledge: analyses, decisions
├── data/<collector>/*.jsonl  # collector output — NOT artifacts, no frontmatter
└── domains/<loop-name>/README.md  # charter, cadence, focus, backlog, ## Timeline
```

Runtime config (`config.yaml`) and, from Phase 4, `proposals/` sit alongside
this layout; they are loop machinery, not artifacts, and are out of scope here.

- Artifacts are foldered by **kind**. `domains` is a frontmatter **field**
  (a list), never a folder for artifacts.
- File and directory names are kebab-case.
- All content is English.
- In `loopstack` (this repo) the substrate root is the repo root — this repo is
  a single-owner meta-repo whose state IS its content (`DECISIONS.md` D3).
  Every other product keeps its substrate in a per-user workspace outside the
  repo (`$<PRODUCT>_HOME`).

## 2. Artifact frontmatter

Every artifact is a markdown file that begins on line 1 with a YAML
frontmatter block delimited by `---`:

```yaml
---
kind: signal
domains: [loopstack-core]
created: 2026-07-24
updated: 2026-07-24
frequency: 1
confidence: high
sources: [ARCHITECTURE.md#2, data/serp/slashstack.jsonl#L120]
---
```

| Field | Required | Type | Rule |
|---|---|---|---|
| `kind` | yes | enum | `signal` or `doc`. No other value is valid today (see §6). |
| `domains` | yes | list | Non-empty. Each entry must be an existing directory under `domains/`. |
| `created` | yes | date | `YYYY-MM-DD`. |
| `updated` | yes | date | `YYYY-MM-DD`, never earlier than `created`. |
| `confidence` | yes | enum | `high`, `medium`, or `low`. |
| `sources` | yes | list | May be empty **only** when `confidence: low`. |
| `frequency` | signals only | integer | `>= 1`. Dedupe counter. Not valid on `doc`. |

The frontmatter subset used here is deliberately small so it can be parsed
without a YAML library: scalars, `YYYY-MM-DD` dates, and single-line inline
lists (`[a, b]`, or `[]` for empty).

## 3. Body shape

- **Body = what is true now.** Everything above `## Timeline` may be rewritten
  freely as understanding improves. There is no history to preserve there.
- **`## Timeline` = what happened.** Append-only, dated entries, newest at the
  bottom. Existing entries are never edited or deleted. A diff that modifies
  or removes an existing Timeline entry is rejected in review.
- **`sources` makes claims auditable.** Docs cite signals and repo paths;
  signals cite collector JSONL lines or vendor source locations. An artifact
  with no sources is `confidence: low`.

## 4. Signal dedupe

Re-observing evidence that matches an existing signal does **not** create a
second file. Instead, on the existing signal:

1. increment `frequency` by one,
2. set `updated` to today,
3. append one dated entry to its `## Timeline`.

A new signal file is created only for genuinely new evidence.

## 5. Domain README (the loop charter)

Each directory under `domains/` contains a `README.md` with these level-2
sections, in this order:

1. `## Charter` — mission, scope, what this loop optimizes for.
2. `## Cadence` — trigger schedule.
3. `## Current focus` — exactly one item.
4. `## Backlog` — ordered list.
5. `## Timeline` — append-only run log, last section in the file.

Every loop run appends one `### <YYYY-MM-DD> run` entry to the Timeline, and
that entry ends with an `Outcome:` line classed as `success`, `partial`,
`failure`, or `no-op`. Those Outcome lines are the raw material of the reflect
loop, so the classes are a closed set.

A domain README is a charter, not an artifact: it has no frontmatter.

## 6. Earning a new kind

`signal` and `doc` are the only kinds today. A new kind is added only through
an approved change proposal that shows it clears all three bars:

- **(a) own status machine** — states and legal transitions the existing kinds
  do not have;
- **(b) queryable fields** — frontmatter fields loops actually filter on;
- **(c) distinct body shape** — a body that cannot be expressed as evidence or
  as durable knowledge.

`learning` and `skill-proposal` clear the bar when the reflect loop ships
(Phase 4). `task` does not clear it: work items live in the domain Backlog and
run outcomes live in the domain Timeline.

## 7. LOG.md

`LOG.md` is the global append-only activity feed: the human's 30-second "what
have my loops been doing" view and the digest source for delivery. New lines
are appended at the **bottom** (oldest first) so concurrent writers merge
cleanly.

Grammar — one event per line, exactly:

```
<ISO-8601 UTC timestamp> [<domain>] <event>: <summary>
```

- timestamp: `YYYY-MM-DDTHH:MMZ` (minute precision, always UTC)
- `<domain>`: a directory name under `domains/`, in square brackets
- `<event>`: a single kebab-case token (`run`, `collect`, `bootstrap`,
  `review`, ...) followed by `: `
- `<summary>`: free text, one line, ending in `outcome=<success|partial|failure|no-op>`
  for events that represent a completed unit of work

Example:

```
2026-07-24T18:20Z [loopstack-core] bootstrap: created substrate skeleton, outcome=success
```

Blank lines, markdown headings (`#`), and HTML comment blocks (`<!-- ... -->`,
including multi-line ones) are ignored by the parser — that is where the file's
own header lives. Every other line must match the grammar.

Every collector pass, loop run, and proposal decision appends exactly one line.

## 8. Enforcement

`scripts/substrate_lint.py` (Python stdlib only) checks everything in §2, §5,
§6, and §7 that is mechanically checkable, and exits non-zero with one
`path:line: message` per violation. CI runs it, plus
`openspec validate --strict`, on every push and pull request. Timeline
append-only (§3) is enforced by review at this stage.
