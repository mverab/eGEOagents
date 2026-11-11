# Change: Judge AI crawler access by search crawlers, not training crawlers

## Why

`ai_crawler_access` checks training crawlers (`GPTBot`, `ClaudeBot`, `Google-Extended`) and search/answer crawlers (`OAI-SearchBot`, `ChatGPT-User`, `PerplexityBot`) in one list, and fails if any of them is blocked. Cloudflare's default for new zones ("Bot Preference Sync") adds `Disallow: /` for training crawlers only. Search crawlers are left alone, so the site can still be cited by ChatGPT, Claude and Perplexity.

On 2026-11-11, appsclavitud.com was in exactly that state, and the audit told the visitor that AI crawlers could not read the page. That is a false negative, and every site on Cloudflare's default would get it.

## What Changes

- `ai_crawler_access` judges only search/answer crawlers: `OAI-SearchBot`, `ChatGPT-User`, `Claude-SearchBot`, `Claude-User`, `PerplexityBot` and `Perplexity-User`. It is `fail` only when one of them is disallowed.
- Training crawlers (`GPTBot`, `ClaudeBot`, `Google-Extended`) are still evaluated. When any of them is blocked, the evidence says so, labeled as not affecting AI search citations, and the status does not change.
- The fix text names only the blocked search crawlers.

## Impact

- Modified spec: `url-audit-api`, "AI Crawler Access Check".
- Code:
  - `egeo/url_audit.py` (`AI_CRAWLERS` is split into `SEARCH_CRAWLERS` and `TRAINING_CRAWLERS`; `AI_CRAWLERS` stays as their union for compatibility);
  - tests;
  - `site/src/content/docs/docs/url-audit.md`;
  - `CHANGELOG.md`.
- There is no change to the API shape.
