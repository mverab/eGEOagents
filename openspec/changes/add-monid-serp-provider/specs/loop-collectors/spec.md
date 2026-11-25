## ADDED Requirements

### Requirement: Optional Monid SERP Provider
The SERP collector SHALL accept `monid` as an explicit engine, read `MONID_API_KEY` from the environment in network mode, and run Search1API's `/search` endpoint for Google web results through Monid's `POST /v1/run` API. It SHALL preserve the existing versioned JSONL record shape and identify the provider in the `engine` field. Selecting any other engine SHALL NOT read `MONID_API_KEY`.

#### Scenario: Successful run
- **WHEN** a Monid run reports `status=COMPLETED`, an integer `providerResponse.httpStatus` below 400, and results under `output.results`
- **THEN** the collector records up to ten results in the order returned, with their position, URL, domain, and title
- **AND** it reports the tracked domain's first matching position

#### Scenario: Unfinished run
- **WHEN** Monid answers the run request with a run that has not ended
- **THEN** the collector reads it again from `GET /v1/runs/<runId>` until it ends, and exits non-zero if it has not ended within the run timeout

#### Scenario: Missing credentials
- **WHEN** network mode selects `monid` without `MONID_API_KEY`
- **THEN** the collector exits non-zero with an actionable message before making a request or writing an observation

#### Scenario: Failed or malformed response
- **WHEN** Monid returns a non-success HTTP status, invalid JSON, a run that did not complete, a provider status of 400 or above or of a non-integer type, or a missing result list
- **THEN** the collector exits non-zero with a message naming Monid or Search1API, without writing an observation for that query

#### Scenario: Brave selected with only a Monid key
- **WHEN** network mode selects `brave` with `MONID_API_KEY` set and `BRAVE_API_KEY` unset
- **THEN** the collector exits non-zero as in "Brave API key missing" and makes no Monid request

#### Scenario: Offline fixture
- **WHEN** `--engine monid --fixture <path>` is used without network access or an API key
- **THEN** the collector writes the same record shape using only the fixture
