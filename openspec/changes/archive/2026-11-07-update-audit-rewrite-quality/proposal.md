# Change: Honest rewrite results and content-only section choice in the URL audit

## Why

The 2026-11-05 rewrite-model benchmark (`docs/audit-service.md`, "Rewrite model") and the Kimi go-live smoke test found two problems that visitors see:

1. **"Shown" rewrites that change nothing.** In 4 of 15 Kimi rewrites the model returned the section unchanged. Those rewrites passed the fidelity rules, so the report showed them as a before/after with identical sides. That spends one rewrite of the daily budget and tells the visitor nothing.
2. **Non-content sections get picked.** The section picker takes the lowest-scoring 40–600-word section. On simonwillison.net that was the site header (the site-name link, the newsletter link and a sponsor line). Elsewhere it picks call-to-action blocks and footer link lists. These sections score low because they are not content, and rewriting them is useless.

## What Changes

- **New rewrite status `no_change`.** If the rewrite passes fidelity but equals the original once whitespace is normalized, the status is `no_change` instead of `shown`, and the report has no `after`. The LLM call still counts against the daily cap, because it was made.
- **Section exclusions.** A section can no longer be the rewrite candidate when:
  - its heading is a single Markdown link, such as a site-name header; or
  - at least half of its non-empty body lines are a lone link, optionally a list item or followed by a separator. This covers navigation, footers, tables of contents and CTA blocks.
  Both rules are deterministic.
- **Landing page:** `no_change` shows a plain-language reason: the model found nothing to improve in this section for this query.

## Impact

- Modified specs:
  - `url-audit-api`: "Rewrite Section Selection" and "Rewrite Result Object";
  - `landing-url-audit`: "Rewrite View".
- Code:
  - `egeo/url_audit.py` (`pick_section`, `rewrite_one_section`);
  - `site/src/scripts/url-audit.ts` (status message);
  - tests;
  - `site/src/content/docs/docs/url-audit.md` (status list).
- No API shape change beyond one new `status` value. Clients that render unknown statuses as a generic reason keep working.
