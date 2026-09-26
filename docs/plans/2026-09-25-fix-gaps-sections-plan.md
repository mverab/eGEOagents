# Implementation plan — section-mode `fix-gaps` (Jev diagnosis, fidelity gates, verification)

**Spec:** `openspec/changes/update-fix-gaps-section-rewrite/` (proposal, design, spec delta).
**Branch:** `feat/fix-gaps-sections` (draft PR). It already contains the scaffold: module stubs with
exact signatures and behavior in their docstrings, prompts, and **all tests** (currently RED).
**Your job:** make the tests pass without changing them, lane by lane, then hand back for review.

This plan was written for implementer agents that did not design the feature. Everything you need is
here, in the stub docstrings, and in the tests. If something is ambiguous, the tests win; if a test looks
wrong, stop and report — do not edit it.

---

## 0. Golden rules (read twice)

1. **Do not modify any test file** (`tests/test_sections.py`, `test_fidelity.py`, `test_sources.py`,
   `test_jev.py`, `test_judge.py`, `test_section_rewriter.py`, `test_gaps_sections.py`,
   `test_jev_selection_eval.py`, `test_resources.py`, or any pre-existing test). A test was verified
   against a reference implementation; all 148 tests pass together. If you think a test is wrong,
   stop and write why in your hand-back.
2. **Do not change public signatures, dataclass fields or constants** in the stubs. Implement the
   bodies. You may add private helpers (`_name`).
3. **No network in tests.** Never call TypeSafe, OpenRouter/OpenAI, or fetch URLs from tests.
4. **No secrets in output.** Never print or log `TYPESAFE_API_KEY` / `OPENAI_API_KEY` values.
5. **Stdlib only** for new modules (`re`, `json`, `html.parser`, `urllib`, `difflib`, `dataclasses`).
   No new dependencies.
6. **Stay in your lane's files** (section 3). Two lanes never edit the same file.
7. **Never** publish, merge, tag, release, edit `site/` content, or push to `main`. Push only to
   `feat/fix-gaps-sections`.
8. Keep the style of the surrounding code (type hints, small functions, `from __future__ import annotations`).
9. Commits: Conventional Commits in English, one per lane, e.g. `feat(sections): byte-exact markdown section split`.
   End each commit message with the co-author line your harness requires.

## 1. Setup and commands

```bash
cd ~/workspace/projects/github/mverab/eGEOagents
git fetch origin && git checkout feat/fix-gaps-sections && git pull
python3 -m venv /tmp/egeo-venv && /tmp/egeo-venv/bin/pip install -q pytest pyyaml jsonschema -e .
/tmp/egeo-venv/bin/python -m pytest tests/<your_test_file>.py -q     # your lane
/tmp/egeo-venv/bin/python -m pytest tests/ -q                        # everything, before hand-back
```

Done for a lane = its test file(s) pass **and** the full suite has no new failures outside other lanes' files.

## 2. Waves

| Wave | Lanes | Can run in parallel | Gate to next wave |
|---|---|---|---|
| 1 | A sections · B fidelity · C sources · D jev+judge · E section_rewriter | yes, all five | all Wave-1 tests green |
| 2 | G validation eval (code + live run) | single lane | **GATE: report AUC to reviewer; STOP if mean AUC < 0.65** |
| 3 | F gaps integration + CLI · H docs | F first, then H | full suite green + dogfood run handed back |

Lane D depends on nothing; Lane D's `judge.py` imports `jev.py` and `sources.host_of` (Lane C) — if
Lane C is not done yet, `test_judge.py::test_candidate_builders` will fail until it is. That is expected.

---

## 3. Lanes

### Lane A — `egeo/sections.py` → `tests/test_sections.py`

Implement `split_sections`, `join_sections`, `replace_section` exactly as the module docstring says.

Pitfalls found while building the reference:
- Split with `body.splitlines(keepends=True)` so newlines are preserved; join is `"".join(text)`.
- Fences: track the opening fence string (e.g. "````"); a line closes it only if its stripped form is
  the same fence character repeated **at least as many** times and nothing else. A ```` ``` ```` line
  inside a ```` ```` ```` block does not close it.
- Headings are detected on the line **without** its trailing newline (`line.rstrip("\r\n")`).
- `"#hashtag"` (no space) and setext underlines are not headings.
- Empty body → `[]`.

### Lane B — `egeo/fidelity.py` → `tests/test_fidelity.py`

Implement `extract_invariants` and `check_fidelity` per the docstring.

Pitfalls:
- Remove fenced code blocks from the text **before** extracting URLs and numbers (the test has
  `egeo==2.1.0` inside a code block; `2.1.0` must not count as a number).
- Remove every found URL from the prose before extracting numbers (years/ids inside URLs are not facts).
  Replace longer URLs first.
- A bare URL followed by `.` at the end of a sentence must lose the `.` (`strip trailing .,;:`).
- The Markdown link regex and the bare-URL regex will both find the same URL — use a set.
- Sort each violation group alphabetically as **strings** (`"194" < "47"`).
- Word ratio only when the original has ≥ 20 words; report `too_short` / `too_long` last.

### Lane C — `egeo/sources.py` → `tests/test_sources.py`

Implement per the docstring. Tests inject `fetcher`; `default_fetcher` is the only network code.

Pitfalls:
- `html.parser`: count nesting depth for skipped tags (head, script, style, …); only collect body
  text when depth is 0. Collect `<title>` text separately even though it is inside `<head>`.
- Meta attribute names can be mixed case (`name="Description"`).
- Join body chunks with `" "` **then** collapse whitespace; otherwise `"GEO tools</h1><p>E-GEO"` glues words.
- Excerpt = title, description, body joined with `"\n"`, skipping empty parts, then truncate, then `rstrip`.
- `fetch_sources` cache: JSON object keyed by URL; store `SourceDoc.__dict__`; reuse only `ok` entries.
- `placeholder_sources` must not import or call anything network-related.

### Lane D — `egeo/jev.py`, `egeo/judge.py` → `tests/test_jev.py`, `tests/test_judge.py`

`jev.py`: implement `key_configured`, `HttpTransport.post_json`, `MockJevTransport.post_json`,
`JevClient.ask`, `make_client` per the docstring. The API contract in the docstring was verified live.

Pitfalls (jev):
- Fill missing choice probabilities with `0.0` for every criteria key (the test expects `"c": 0.0`).
- Validate numbers with a helper that rejects bools and values outside [0, 1].
- `JevClient` is a dataclass whose `totals` must be a fresh dict per instance (`default_factory`).
- The mock's `confidence` uses the **unrounded** peak probability; round only the outputs.
- HTTP error message must contain the status code (`"TypeSafe HTTP 401"`).

`judge.py`: implement all functions per the docstring.

Pitfalls (judge):
- `select_best` truncates candidate text to `MAX_CANDIDATE_CHARS` in `state`, never the labels.
- Criteria values are neutral: `f"The candidate whose text is candidates.{id}"`.
- `diagnose` tie-break: highest probability, then **earliest** position in `own`.
- `verify` uses a `1e-9` tolerance: `0.35 - 0.30` is `0.04999999999999999` in floating point.
- `diagnose` must not call Jev when there are no own candidates or no sources.

### Lane E — `egeo/section_rewriter.py` → `tests/test_section_rewriter.py`

Prompts are already written (`prompts/section_rewriter_*.txt` + packaged copies) — **do not edit them**
(the resource drift test requires byte-identical copies). Implement `render_prompts`, `clean_output`,
`rewrite_section`.

Pitfalls:
- Load prompts through `egeo.resource_root() / "prompts" / name` so installed wheels work.
- `clean_output`: strip, remove a wrapping fence only when the **first** line starts with ```` ``` ````
  and the **last** line is exactly ```` ``` ````, strip again, then re-append the original's trailing
  whitespace.
- Mock mode check happens **before** touching the client (the test passes a client that explodes).
- Import `llm_client` lazily inside the function (it lives at the repo root as a py-module).

### Lane G — validation eval `eval/jev_selection/run.py` (+ live run) → `tests/test_jev_selection_eval.py`

**Code.** Implement `auc`, `build_query_candidates`, `score_query`, `run`, `main` per the docstring.
`main`: argparse with `--dataset`, `--out`, `--mock`, `--own-domain` (default `egeoagents.com`); build
the client with `egeo.jev.make_client(mock=args.mock)`; fetch adapter:
`lambda urls: {d.url: d for d in fetch_sources(urls, limit=len(urls))}` (real) or the same over
`placeholder_sources` (mock); write the result JSON (indent 2); print `mean_auc`, `n_scored`,
`GATE PASS`/`GATE FAIL`; return 0 either way (the gate is reported, not enforced by exit code).

Pitfalls:
- `run` fetches every normalized URL **once** in a single `fetch` call (the test counts calls).
- `own_rank`: 1 + number of candidates with a strictly higher probability.
- `own_predicted_cited` compares against the **minimum** probability among cited (label 1) sources.

**Live run (VPS only, after the tests pass).** This is the go/no-go for the whole feature.

1. Write the collector **outside the repo** at `~/.hermes/scripts/egeo_jev_selection_collect.py`
   (it uses the owner's infrastructure, which must not ship in the package):
   - Queries: the 10 fixed queries in `~/Sync/mkt/egeo-expansion/query-set.json`.
   - Perplexity: `PerplexitySearchClient().sonar(query)` from
     `~/.hermes/skills/perplexity-search/scripts/perplexity_search_client.py` (reads `AISA_API_KEY`
     from `~/.hermes/.env`). Cited URLs: the first of the keys `search_results`, `sources`,
     `citations`, `results` that is a list; each item is a URL string or a dict with `url`
     (same logic as `extract_source_domains` in `~/.hermes/scripts/egeo_visibility_measure.py`, but
     keep full URLs). `egeo_cited`: the answer text (`answer`, or `choices[0].message.content`)
     mentions `egeo` / `e-geo` / `egeoagents` case-insensitively.
   - SERP: Brave Search API `GET https://api.search.brave.com/res/v1/web/search?q=<query>&count=10`
     with header `X-Subscription-Token: $BRAVE_API_KEY` (key in `~/.egeo_env`); URLs from
     `web.results[].url`.
   - `own_url` per query (E-GEO's page that should win it):

     | Query | own_url |
     |---|---|
     | What are the best open-source generative engine optimization (GEO) tools on GitHub in 2026? | https://egeoagents.com/compare/geo-tools-2026/ |
     | best GEO tools 2026 | https://egeoagents.com/compare/geo-tools-2026/ |
     | open source AEO tools | https://egeoagents.com/compare/geo-tools-2026/ |
     | how to optimize content for Perplexity | https://egeoagents.com/guides/rank-in-perplexity/ |
     | GEO tool with MCP server | https://egeoagents.com/docs/mcp-server/ |
     | eGEOagents GitHub | https://github.com/mverab/eGEOagents |
     | eGEOagents | https://egeoagents.com/ |
     | best answer engine optimization tools for developers | https://egeoagents.com/compare/geo-tools-2026/ |
     | open source tool to rank in ChatGPT and Perplexity | https://egeoagents.com/guides/rank-in-chatgpt-search/ |
     | GEO evaluation harness open source | https://egeoagents.com/docs/evaluation/ |

   - One Perplexity call and one Brave call per query, 2 s apart. Abort (non-zero exit, no dataset
     written) if more than half of the Perplexity answers are empty — the same guard the weekly
     measurement uses.
   - Write `~/Sync/mkt/egeo-expansion/jev-selection/dataset-YYYY-MM-DD.json` (schema in the eval docstring).
2. Run the eval live:
   ```bash
   set -a; . <(grep -E '^TYPESAFE_API_KEY=' ~/.hermes/.env); set +a
   /tmp/egeo-venv/bin/python -m eval.jev_selection.run \
     --dataset ~/Sync/mkt/egeo-expansion/jev-selection/dataset-YYYY-MM-DD.json \
     --out ~/Sync/mkt/egeo-expansion/jev-selection/results-YYYY-MM-DD.json
   ```
3. Add `eval/jev_selection/README.md`: what it measures (Jev's Choice vs. Perplexity's cited sources,
   uncited SERP results as negatives), how to reproduce, the result (mean AUC, n_scored, own_accuracy,
   date, jev model), and the honest caveat (10 queries, one engine, one day).
4. **STOP.** Hand back the results file and README. Do not start Wave 3 until the reviewer says go.

Budget: 10 Perplexity + 10 Brave calls + ~10 Jev requests (Jev ≈ $0.0003 total). Do not loop retries.

### Lane F — integration: `egeo/gaps.py` (+ `egeo/cli.py` only if needed) → `tests/test_gaps_sections.py`

Implement `mock_enabled`, `run_section_fixes`, `PagePlan.sources` population, CLI flags and the
section-mode branch in `gaps.cli`. Existing page-mode behavior and `tests/test_gaps.py` must keep passing.

`plan_fixes`: when a `PagePlan` is created, set `sources=list(gap.sources)` from the gap that created it.

`run_section_fixes` — per `PagePlan`, in this exact order:

1. `content = page.source.read_text()`; `raw_fm, body, _ = pipeline._extract_frontmatter(content)`
   (`raw_fm + body == content`); `title = pipeline._derive_title_and_body(content)[0]`.
2. `secs = sections.split_sections(body)`; `own = judge.own_candidates(secs)`.
3. `docs = fetch_fn(page.sources, exclude_domain=exclude_domain, limit=max_sources)`;
   `srcs = judge.source_candidates(docs)`.
4. `diag = judge.diagnose(page.query, own, srcs, jev_client)`.
   - `no_own_candidates` / `no_competitor_sources` → status = that, `diagnosis: null`, stop.
   - `already_best` → status `already_best`, diagnosis filled with `target_section: null`, stop.
5. Target: `sid = diag.target_id.removeprefix("own_")`; `original = <section sid>.text`.
6. `new = rewrite_fn(page.query, original, title)`; if `new == original` → `no_change_proposed`, stop.
7. `rules = fidelity.check_fidelity(original, new)`; fill `fidelity.rules`; fail → `rejected_fidelity_rules`
   (`fidelity.judge: null`), stop. **Do not call the Jev judge** when rules fail.
8. `v = judge.judge_fidelity(original, new, jev_client)`; not accepted → `rejected_fidelity_judge`, stop.
9. `own_after` = the **same** `own` candidates with only the target's `text` replaced by `new`
   (do not re-split or re-filter — ids must match the diagnosis). `ver = judge.verify(...)`;
   `worse` → `rejected_worse`, stop.
10. Accept: `new_content = raw_fm + join_sections(replace_section(secs, sid, new))`; write
    `<out>/<page_id>/<source file name>` and `<out>/<page_id>/section.diff`
    (`difflib.unified_diff(content.splitlines(keepends=True), new_content.splitlines(keepends=True),
    fromfile=f"a/{name}", tofile=f"b/{name}")`); status `rewritten`.

Any `JevProviderError` or `JevConfigError` in steps 4–9 → status `jev_error`, `reasons=[str(exc)]`, stop
(other pages continue). Always write `<out>/<page_id>/diagnosis.json` (the page dict). Then write
`<out>/fix-gaps.json`.

Page dict keys (JSON-serializable: **lists, not tuples; strings, not Paths**):
`page_id, source, query, other_gaps, status, sources[{url, ok, error}], diagnosis{status, winner,
winner_kind, confidence, probabilities, target_section{id, heading}|null}|null,
fidelity{rules{passed, violations[]}, judge{verdict, confidence, accepted}|null}|null,
verification{p_before, p_after, winner_after, winner_after_kind, outcome}|null,
output_file|null, diff_file|null, reasons[]`.

Report keys: `format, mode ("sections"), pages, unmatched, skipped, remeasure, note (SECTIONS_NOTE),
jev_model (client.model), jev_usage (dict(client.totals)), thresholds{fidelity_gate, improve_delta,
min_section_words, max_candidate_chars, max_sources}`. The returned dict must equal the saved JSON.

CLI (`add_parser` / `cli` in `gaps.py`):
- New flags: `--mode {sections,page}` (default `sections`), `--max-sources` (int, default 6),
  `--jev-model` (default `jev.DEFAULT_MODEL`).
- `--dry-run` in either mode: print `describe_plan(plan)` (plus, in sections mode, one line per page
  with the number of sources), no network, no key needed, write nothing.
- Sections mode, not dry-run: if `not mock_enabled() and not jev.key_configured()` → print to stderr a
  message containing `TYPESAFE_API_KEY`, `GEO_EVAL_MOCK=1` and `--mode page`; return 2 before any
  fetch or file write.
- Mock: `jev.make_client(mock=True)`, `fetch_fn = sources.placeholder_sources`.
  Real: `jev.make_client(mock=False, model=args.jev_model)`, `fetch_fn` = `sources.fetch_sources` with
  `cache_path=<out>/sources-cache.json`.
- `rewrite_fn = lambda q, text, title: section_rewriter.rewrite_section(q, text, page_title=title, model=args.rewriter_model)`.
- `exclude_domain = project["project"]["canonical_domain"]`.
- Output: `--json` prints the report; otherwise one line per page `"<status>: <page_id>"` and the report path.
- `--mode page`: existing behavior, unchanged.

### Lane H — docs (after Lane F is green)

- `site/src/content/docs/docs/cli.md`, section `egeo fix-gaps`: section mode as default, the flow
  (diagnose → rewrite one section → fidelity rules → Jev fidelity → verify), statuses, `--mode page`,
  `TYPESAFE_API_KEY` requirement, mock mode, and the validation result from Lane G (number + date +
  link to `eval/jev_selection/README.md`). Honest wording: Jev's choice is a proxy, not a live engine.
- `USAGE.md`: same section, shorter.
- `CHANGELOG.md` `[Unreleased]`: `Changed` (fix-gaps defaults to section mode) + `Added` (modules, eval).
- `openspec/changes/update-fix-gaps-section-rewrite/tasks.md`: tick completed items.
- Verify: `cd site && npm run build && ./verify.sh`.
- Do **not** bump the version or release.

---

## 4. Dogfood run (end of Wave 3, VPS)

Run section mode for real on E-GEO's own gaps, writing outside the repo:

```bash
set -a; . <(grep -E '^(TYPESAFE_API_KEY|OPENAI_API_KEY|OPENAI_BASE_URL)=' ~/.hermes/.env); set +a
export REWRITER_MODEL=openai/gpt-4o
/tmp/egeo-venv/bin/egeo fix-gaps <gaps.json> --project <dogfood project.yaml> --out-dir /tmp/egeo-dogfood
```

Gaps: convert the newest `~/Sync/mkt/egeo-expansion/measurements/*.json` (non-`.invalid`) to the generic
format (`query`, `cited` = `egeo_mentioned`, `sources` = the Lane-G dataset's `cited_urls` for that query).
Project: the 5 generic gap queries mapped to the site pages under
`site/src/content/docs/` (same mapping as the Lane-G `own_url` table; `source:` = absolute path of the
page's `.md`). Budget: ≤ $1 of LLM spend.

## 5. Hand-back to the reviewer (what to send)

1. Branch name and last commit SHA.
2. `pytest tests/ -q` summary line.
3. Lane G: `results-*.json`, `eval/jev_selection/README.md`, mean AUC / n_scored / own_accuracy.
4. Dogfood: `fix-gaps.json`, every `section.diff`, and your one-line read of each page's status.
5. Anything you could not do and why. Anything in a test or this plan you believe is wrong.

The reviewer validates, then either approves the PR for owner review or returns a list of fixes.
Loop until approved.
