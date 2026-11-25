# Change: Add Monid as a SERP collector provider

## Why

The loop-mode SERP collector already supports several HTTP providers, each chosen with `--engine`. Monid gives access to Search1API's web search with one `MONID_API_KEY`, which is another provider choice for users who already hold that key, without changing the collector's append-only observation contract.

## What Changes

- Add `monid` to the SERP collector's `--engine` and workspace configuration choices, with its own entry in `ENGINES` and `API_KEY_ENVS` and its own `fetch_monid` / `parse_monid_response` pair.
- Authenticate with `MONID_API_KEY` from the environment and run Search1API's `/search` endpoint, pinned to Google web results, through Monid's `POST /v1/run`; read an unfinished run from `GET /v1/runs/<runId>` until it ends.
- Name Monid, Search1API and `MONID_API_KEY` in every error the provider raises.
- Add a recorded fixture, contract tests, packaged-resource mirror, and setup documentation that says queries are sent to a third-party intermediary.

## Impact

- Affected spec: `loop-collectors`.
- Affected code: `collectors/serp.py`, mirrored packaged collector, fixture, collector docs, and tests.
- The `brave` engine, the other providers, the default engine and the JSONL record shape remain unchanged.
