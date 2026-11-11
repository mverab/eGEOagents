## MODIFIED Requirements

### Requirement: AI Crawler Access Check

`ai_crawler_access` SHALL evaluate the `robots.txt` at the final page's origin for the audited path. The status SHALL depend only on these search crawlers: `OAI-SearchBot`, `ChatGPT-User`, `Claude-SearchBot`, `Claude-User`, `PerplexityBot` and `Perplexity-User`.
- `pass`: no search crawler is disallowed. A `robots.txt` that returns 404 also counts as `pass`.
- `fail`: at least one search crawler is disallowed. The evidence and `fix` name only those crawlers.
- `unverifiable`: the fetch failed or returned any other status.

The training crawlers `GPTBot`, `ClaudeBot` and `Google-Extended` SHALL also be evaluated. Blocking them SHALL NOT change the status. When any is blocked, the evidence SHALL add a note naming them and saying that this does not affect AI search citations.

#### Scenario: Crawlers blocked in robots.txt

- **WHEN** the site's `robots.txt` contains `User-agent: OAI-SearchBot` followed by `Disallow: /`
- **THEN** `ai_crawler_access` is `fail` with evidence naming `OAI-SearchBot` and a `fix` that says which rule to change

#### Scenario: Only training crawlers blocked

- **WHEN** the site's `robots.txt` disallows `GPTBot`, `ClaudeBot` and `Google-Extended`, and allows everything else
- **THEN** `ai_crawler_access` is `pass`
- **AND** the evidence names the three training crawlers and says this does not affect AI search citations

#### Scenario: robots.txt cannot be fetched

- **WHEN** fetching `robots.txt` times out
- **THEN** `ai_crawler_access` is `unverifiable` and has no `fix`
