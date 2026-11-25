# Change: Fidelity gate and an article prompt for page-mode `egeo optimize`

## Why

`egeo optimize` (and page-mode `egeo fix-gaps`, the default) writes whatever the rewriter returns. `docs/examples.md` records what that does to good pages (real runs, 2026-10-04, gpt-4o):

- The two long site pages shrank by about a third (609 → 352 and 517 → 377 words).
- The rewrite dropped the "Last verified" date, both research links, the GitHub link, named data points, and the one-sentence definition that answered the query.
- On the thin page it added "real-time", a claim the source does not make.

Two causes. The deterministic fidelity rules (`egeo/fidelity.py`) only run in experimental section mode. And the only rewriter prompt is written for a product description ("Lead with … 'Best for …'"), yet it is applied to guides and concept pages.

## What Changes

- **Fidelity gate in page mode.** After the rewrite, the body is checked with the existing rules: links and numbers neither removed nor added, table rows not reduced, code blocks unchanged, length not below 80% of the original. `heading_changed` and `too_long` do not apply to a whole page (thin pages are meant to grow), and ordered-list markers are not counted as numbers.
- **One repair attempt.** If the rules fail, the rewriter is called once more with the list of violations. No further retries.
- **A failing rewrite is not written to `optimized/`.** It goes to `rejected/<slug>.md` for manual review, the report lists the violations, and the simulated rank is reported as unchanged. `--allow-lossy` restores the old behavior (write it anyway, still reported).
- **Content type.** `--content-type auto|product|article` (default `auto`: `article` when the body has at least 150 words or 3 headings, else `product`). `article` uses new prompts `rewriter_article_system.txt` / `rewriter_article_user.txt`: answer first, no "Best for" line, no superlatives, keep every link, number, date, table and code block, keep caveats.
- `analysis.json`, `report.md`, the CLI output, `--json` and each page entry of page-mode `fix-gaps.json` report `content_type` and `fidelity` (`status`: `passed` | `repaired` | `rejected` | `lossy_allowed`, `violations`, `attempts`).

## Impact

- Affected capability: `runtime-adapters` (the `egeo optimize` pipeline; defined by the unarchived `add-runtime-adapters`). This delta only adds requirements.
- Affected code: `egeo/pipeline.py`, `egeo/agents.py`, `egeo/runtimes.py`, `egeo/cli.py`, `egeo/gaps.py`, `geo_eval.py` (one optional argument), `prompts/` and its packaged mirror, tests, docs.
- **Behavior change for users:** a rewrite that loses links or numbers no longer lands in `optimized/`, and long pages get a different prompt. `geo_eval evaluate` / `optimize-prompts` and section mode are untouched; the product prompts are unchanged.
- Cost: at most one extra rewriter call per page (only on a violation), and one ranker call fewer when the rewrite is rejected.
- Not claimed: the gate checks what can be checked mechanically. It cannot detect a new unverified adjective ("real-time") or a dropped sentence that has no link or number. The article prompt has not been measured against a live engine; no effectiveness claim is made.
