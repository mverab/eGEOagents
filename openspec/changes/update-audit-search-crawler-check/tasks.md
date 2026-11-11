## 1. Check
- [ ] 1.1 RED tests in `tests/test_url_audit.py` for the three scenarios. For "only training crawlers blocked", use a robots.txt shaped like Cloudflare's managed block: `User-agent: *` / `Allow: /`, then GPTBot, ClaudeBot and Google-Extended each with `Disallow: /`. Also: a blocked `Claude-SearchBot` → `fail`; search and training both blocked → `fail`, with the fix naming only search crawlers. Update the existing GPTBot-blocked test, which must now be `pass`.
- [ ] 1.2 Implement it in `egeo/url_audit.py`: add `SEARCH_CRAWLERS` and `TRAINING_CRAWLERS`, keep `AI_CRAWLERS = SEARCH_CRAWLERS + TRAINING_CRAWLERS` (export all three), and rewrite `check_ai_crawler_access` per the spec. Fix text: say "so AI search crawlers can read the page", as today.

## 2. Docs
- [ ] 2.1 `site/src/content/docs/docs/url-audit.md`: describe the check as search crawlers, with training crawlers as information only.
- [ ] 2.2 `CHANGELOG.md` Unreleased → Fixed: one line.
