# Collectors — the data layer of loop mode

**Collectors write data. Agents write knowledge.** A collector observes the
world and records what it saw, verbatim and without opinion. Turning those
observations into signals and docs is the agent's job (`.claude/skills/geo-loop/`).
Keeping the two apart is what makes loop mode cheap, deterministic, and auditable.

## The contract

A collector in this directory MUST:

1. **Be deterministic and LLM-free.** No model calls, no prompts, no
   interpretation. Given the same input it produces the same record.
2. **Read configuration from the workspace, credentials from the environment.**
   Inputs come from `$EGEO_HOME/config.yaml` (`collectors.<name>.*`); secrets
   come from env vars (`BRAVE_API_KEY`). Nothing is read from the repo tree and
   secret values are never printed or logged.
3. **Append versioned JSONL.** One JSON object per observation, appended to
   `$EGEO_HOME/data/<collector>/<stream>.jsonl`. Every record carries:
   - `v` — integer schema version,
   - `ts` — ISO-8601 UTC timestamp,
   - a natural key (`query`, `url`, …) sufficient for read-side dedupe.
4. **Never rewrite history.** Append only. Existing lines are never modified,
   reordered, or deleted; the agent dedupes on read.
5. **Be idempotent to re-run.** Running twice is safe: it produces two
   observations with distinct `ts`, never a corrupted stream.
6. **Never write interpretive artifacts.** A collector must not touch
   `signals/`, `docs/`, or any domain `README.md` body.
7. **Log exactly one line per pass.** On success, append one `LOG.md` line
   ending in `outcome=<success|partial|failure|no-op>`.
8. **Fail loudly.** Exit non-zero on hard failure (auth, network, schema,
   budget) and write no record for the failed observation. A collector that
   quietly stops collecting is worse than one that crashes.
9. **Support fixture mode.** `--fixture <path>` replays recorded responses from
   disk so the contract is testable with no network and no API key.
10. **Expose `main(argv)`.** So `egeo loop collect <name>` can invoke the
    collector in-process, with the same behavior as running the file directly.

## Shipped collectors

| Collector | Stream | Record |
|---|---|---|
| `serp.py` | `data/serp/<query-slug>.jsonl` | `{v, ts, query, engine, results[≤10], target_domain, target_position}` |
| `page.py` | `data/page/<page-slug>.jsonl` | `{v, ts, url, status, content_hash, title, meta_description, jsonld_types, word_count}` |

### `serp.py` — position history from the Brave Search API

```bash
export BRAVE_API_KEY=...                  # never printed, never written to disk
python collectors/serp.py                 # all queries from config.yaml
python collectors/serp.py --query "best geo tool"
python collectors/serp.py --fixture collectors/fixtures/serp_brave_response.json
python -m egeo loop collect serp          # equivalent, in-process
```

Brave is called over its **HTTP API directly**, not through the Brave MCP:
collectors run under cron with no agent attached, so an MCP server is not
available to them. The MCP stays the path for interactive agent sessions. Live
passes are paced at ≤1 query/second and refuse to exceed
`budgets.queries_per_day`.

Config:

```yaml
collectors:
  serp:
    target_domain: example.com     # position is reported for this domain
    queries:
      - best geo optimization tool
      - how to rank in chatgpt
```

### `page.py` — content and schema drift on your own pages

```bash
python collectors/page.py
python collectors/page.py --url https://example.com/pricing
python collectors/page.py --fixture collectors/fixtures/pages/
python -m egeo loop collect page
```

`content_hash` is a SHA-256 of the canonical extraction (title, meta
description, JSON-LD @types, normalized visible text) — not of the raw body,
whose invisible churn (script nonces, dynamic attributes) changes on every
fetch. An unchanged page therefore produces an unchanged hash across passes,
which is how the agent detects drift. HTML is parsed with the standard
library only (`html.parser`); there is no `requests` or `beautifulsoup4`
dependency anywhere in loop mode.

Config:

```yaml
collectors:
  page:
    urls:
      - https://example.com/
      - https://example.com/pricing
```

## Fixtures

`fixtures/serp_brave_response.json` is a recorded Brave `/res/v1/web/search`
response body; `fixtures/pages/*.html` are recorded page bodies whose file names
encode the URL slug. Fixture mode is what CI runs: no network, no key, same code
path, same schema.

## Adding a collector

1. Copy the shape of `page.py` (argparse, `main(argv)`, `--fixture`, stdlib only).
2. Write records through `egeo.workspace` helpers so `$EGEO_HOME` is resolved in
   exactly one place.
3. Add a fixture and a `--fixture` path that never touches the network.
4. Register it in `egeo/loop.py`'s collector table and document it above.
5. Re-read this contract before opening the PR — points 1, 3, 6, and 8 are the
   ones reviewers reject changes over.
