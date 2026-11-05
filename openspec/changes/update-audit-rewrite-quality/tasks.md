## 1. API (`egeo/url_audit.py`)
- [x] 1.1 Add the non-content exclusions (link-only heading; ≥ 50% lone-link body lines) to `pick_section`, with tests for a site header, a footer list, a CTA block and a normal content section.
- [x] 1.2 Add the `no_change` status (whitespace-normalized equality after fidelity passes) to `rewrite_one_section`, with tests; confirm the LLM budget is still consumed.

## 2. Landing page (`site/`)
- [x] 2.1 Render `no_change` with its plain-language reason and the more-specific-query suggestion.
- [x] 2.2 Update `site/src/content/docs/docs/url-audit.md` (statuses and section choice).

## 3. Verification and rollout
- [x] 3.1 Run `pytest`, and `npm run build && ./verify.sh` in `site/`.
- [ ] 3.2 After merge, redeploy the service and re-audit simonwillison.net and basecamp.com: confirm a content section is chosen and `no_change` appears when the model changes nothing.
