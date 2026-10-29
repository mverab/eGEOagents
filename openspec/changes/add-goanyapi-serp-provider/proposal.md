# Change: Add GoAnyAPI as a SERP collector provider

## Why

The loop-mode SERP collector already supports multiple HTTP providers. GoAnyAPI offers structured Google organic results through a documented GET endpoint, giving users another provider choice without changing the collector's append-only observation contract.

## What Changes

- Add `goanyapi` to the SERP collector's `--engine` and workspace configuration choices.
- Authenticate with `GOANYAPI_API_KEY` from the environment and parse the documented `data.result.organic` response.
- Add an offline fixture, contract tests, packaged-resource mirror, and setup documentation.

## Impact

- Affected spec: `loop-collectors`.
- Affected code: `collectors/serp.py`, mirrored packaged collector, fixture, collector docs, and tests.
- Existing provider defaults and JSONL record shape remain unchanged.
