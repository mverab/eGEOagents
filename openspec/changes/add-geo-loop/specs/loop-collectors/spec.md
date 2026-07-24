## ADDED Requirements

### Requirement: Collectors Are Deterministic And LLM-Free
A collector SHALL be a deterministic script that makes zero LLM calls, reads its
configuration from the workspace `config.yaml` and environment variables, and
SHALL NOT write to `signals/`, `docs/`, or any other interpretive artifact.
Collectors write data; agents write knowledge.

#### Scenario: Collector attempts interpretation
- **WHEN** review finds a collector writing to `signals/` or `docs/`, or calling an LLM endpoint
- **THEN** the change is rejected against this requirement

#### Scenario: Collector reads its configuration from the workspace
- **WHEN** a collector pass starts
- **THEN** its queries or URLs come from the workspace `config.yaml` and its credentials from the environment
- **AND** no configuration is read from the repository tree

### Requirement: Collector Output Is Append-Only Versioned JSONL
Each collector pass SHALL append one JSON object per observation to
`$EGEO_HOME/data/<collector>/<stream>.jsonl`, where every record carries a schema
version field `v`, an ISO-8601 UTC `ts`, and a natural key sufficient for
read-side deduplication. Existing lines SHALL never be modified or deleted.

#### Scenario: Repeated pass on the same query
- **WHEN** the SERP collector runs twice for the same query
- **THEN** two records with distinct `ts` values exist in the stream
- **AND** every previously written line is byte-identical

#### Scenario: SERP record shape
- **WHEN** the SERP collector records an observation
- **THEN** the record contains `v`, `ts`, `query`, up to ten `results`, and `target_position` which is an integer or `null`

#### Scenario: Page record shape
- **WHEN** the page collector records an observation
- **THEN** the record contains `v`, `ts`, `url`, `status`, `content_hash`, `title`, `meta_description`, `jsonld_types`, and `word_count`

### Requirement: Collectors Fail Loudly And Log Once
A collector pass SHALL exit non-zero on hard failure (authentication, network,
schema, or budget) without writing partial records for the failed observation,
and on success SHALL append exactly one `LOG.md` line summarizing the pass.

#### Scenario: Brave API key missing
- **WHEN** `collectors/serp.py` runs in network mode without `BRAVE_API_KEY`
- **THEN** it exits non-zero with an actionable message
- **AND** it appends no JSONL records and no `LOG.md` line

#### Scenario: Daily query budget exceeded
- **WHEN** a pass would exceed `budgets.queries_per_day` from `config.yaml`
- **THEN** the collector exits non-zero naming the budget and the count
- **AND** it does not silently reduce the query set

#### Scenario: Successful pass logs one line
- **WHEN** a collector pass completes successfully
- **THEN** exactly one `LOG.md` line is appended, naming the collector and the number of observations, ending in an `outcome=` class

### Requirement: Collectors Are Testable Without Network
Every collector SHALL support a fixture mode that replays recorded responses
from disk instead of performing network requests, and the contract SHALL be
verifiable using fixtures only, with no API key present.

#### Scenario: Fixture run with no network and no key
- **WHEN** a collector runs with `--fixture <path>` in an environment without network access or `BRAVE_API_KEY`
- **THEN** the pass succeeds and appends schema-valid JSONL records
- **AND** no outbound request is attempted

#### Scenario: Rate limiting in network mode
- **WHEN** the SERP collector issues multiple queries against the live API
- **THEN** it paces requests at no more than one query per second
