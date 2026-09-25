# Change: Add `egeo fix-gaps` — turn a tracker's citation gaps into page rewrites

## Why

AI-visibility trackers (geo-optimizer-skill `geo citations`, Elmo, hosted tools) tell a site *which queries* do not cite it. None of them rewrite the page that should win those queries. E-GEO already rewrites pages (`egeo optimize`) and verifies the rewrite with its ranking harness, but it has no way to take a tracker's output as input. Users have to read the report, pick pages, and run `optimize` by hand, one query at a time.

`fix-gaps` closes that loop: tracker gaps in → the right local pages rewritten against the losing queries → a re-measure list out. It makes E-GEO the open-source *action layer* for any tracker, which is the project's positioning.

## What Changes

- New CLI command `egeo fix-gaps <gaps-file> [--dry-run] [--json] [--out-dir DIR] [--format markdown|html]`.
- Two input formats, auto-detected:
  - geo-optimizer-skill `geo citations --format json` output (`CitationCheckResult`: `domain`, `entries[].query`, `entries[].domain_cited`, `entries[].cited_sources`).
  - A generic E-GEO gaps file (JSON array or CSV) with `query` and `cited` columns, plus optional `sources`. Any tracker export can be converted to it.
- Gaps (queries where the domain is not cited) are matched to `project.yaml` queries by normalized text, then to `target_pages`, then to a local file via a new optional `pages[].source` path.
- Each page with at least one gap is optimized once through the existing `optimize_content` pipeline, against its first gap query. Outputs go to `--out-dir/<page-id>/`. Source files are never modified.
- A `fix-gaps.json` report lists matched gaps, unmatched gaps (with the reason), per-page results, and a `remeasure` list of the queries to check again. For geo-optimizer-skill input it includes the exact `geo citations` command.
- `--dry-run` prints the plan and writes nothing and calls no model.

## Impact

- New capability: `citation-gap-fixing`.
- Affected code: `egeo/cli.py` (new subcommand), new `egeo/gaps.py`, tests `tests/test_gaps.py`, docs (`USAGE.md`, site CLI reference).
- `project.yaml`: one new optional field, `pages[].source`. Existing files stay valid.
- No new dependencies, no credentials, no network calls in `fix-gaps` itself; the rewrite uses the same runtime and model settings as `egeo optimize` (and `GEO_EVAL_MOCK=1` keeps working).
