# Design: `egeo fix-gaps`

## Decisions

1. **Query → page mapping comes from `project.yaml`, not from guessing.** Trackers report per query; E-GEO rewrites per page. The project contract already maps `queries[].target_pages → pages[]`. We add only `pages[].source` (a path relative to the project file) to reach a local file. No fuzzy/LLM matching: a gap whose query is not in `project.yaml` is reported as `unmatched: query_not_in_project`, never rewritten.
2. **Normalization for matching:** lowercase, trim, collapse whitespace, strip trailing `?` and punctuation. Exact match after normalization only.
3. **One rewrite per page per run.** A page that loses several queries is optimized against the first gap (tracker order); the others are listed in the report. Rationale: `optimize_content` takes one query; running several rewrites on the same page would produce conflicting outputs. Multi-query rewriting is out of scope.
4. **"Verify" means the existing harness plus a re-measure list.** The pipeline already reports rank before/after in the LLM-ranker proxy. Real answer-engine verification needs the user's tracker and keys, so `fix-gaps` emits `remeasure` (queries to re-check) instead of calling engines itself. The report says the rank is a proxy.
5. **Input detection:** JSON object with `entries` list whose items have `query` and `domain_cited` → geo-optimizer-skill. JSON array or `.csv` with a `query` column → generic. Anything else → error with the expected shapes. For the generic format, `cited` accepts true/false/1/0/yes/no.
6. **Errored tracker entries are skipped**, not treated as gaps (geo-optimizer-skill sets `error` when the engine call failed). They are reported as `skipped: tracker_error`. A failed measurement must not trigger a rewrite.

## Non-goals

- Calling answer engines or trackers from E-GEO.
- Editing, committing, or publishing the source pages.
- Adapters for hosted trackers' private APIs (they can export to the generic format).
