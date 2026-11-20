## ADDED Requirements

### Requirement: Optional GoAnyAPI SERP Provider
The SERP collector SHALL accept `goanyapi` as an explicit engine, read `GOANYAPI_API_KEY` from the environment in network mode, and request web results from the documented GoAnyAPI Google SERP endpoint. It SHALL preserve the existing versioned JSONL record shape and identify the provider in the `engine` field.

#### Scenario: Successful Google SERP response
- **WHEN** a GoAnyAPI response reports `code=ok` and contains organic results under `data.result.organic`
- **THEN** the collector records up to ten results with their organic rank, URL, domain, and title
- **AND** it reports the tracked domain's first matching organic position

#### Scenario: Missing credentials
- **WHEN** network mode selects `goanyapi` without `GOANYAPI_API_KEY`
- **THEN** the collector exits non-zero with an actionable message before making a request or writing an observation

#### Scenario: Failed or malformed response
- **WHEN** GoAnyAPI returns a non-success response, invalid JSON, or a missing result object
- **THEN** the collector exits non-zero without writing an observation for that query

#### Scenario: Offline fixture
- **WHEN** `--engine goanyapi --fixture <path>` is used without network access or an API key
- **THEN** the collector writes the same record shape using only the fixture
