## 1. Bot challenge detection (egeo/url_audit.py)
- [x] 1.1 RED tests in `tests/test_url_audit.py`: the four "Bot Challenge Detection" scenarios plus one test per vendor (cloudflare, perimeterx, datadome, imperva, akamai), using small synthetic HTML fixtures inline (no copied third-party pages). Assert the LLM factory and `reserve_llm` are not called for a challenge.
- [x] 1.2 Implement `detect_bot_challenge(status, html, title, visible_words) -> Optional[dict]` and wire it into `audit_url`. Challenge-eligible statuses (200, 403, 429, 503) with HTML go through detection before the `status != 200` → `FetchFailed` check. Add `challenge` (null or object) to every report. Add `skipped_challenge` to `REWRITE_STATUSES`.
- [x] 1.3 Check that the service layer (`egeo/audit_service.py`) stores and returns `challenge` unchanged, and that a challenged audit does not touch the LLM budget table. Add a service test.

## 2. Site-name stripping (egeo/url_audit.py)
- [x] 2.1 RED tests: the two "Target Query Selection" scenarios, plus `Home - BBC News` on www.bbc.com → `best Home`, the Plausible title on plausible.io → `best Simple, privacy-friendly Google Analytics alternative`, a `.co.uk` host left unchanged, and a visitor query never stripped.
- [x] 2.2 Implement it in `effective_query` (or a helper it calls), following design.md D3.

## 3. Landing page (site/src/scripts/url-audit.ts)
- [ ] 3.1 Challenge banner, empty-features message, and `skipped_challenge` reason, built with `textContent` only (as today). Add the new fields to the TypeScript types.
- [ ] 3.2 Update `site/src/content/docs/docs/url-audit.md`: challenge behavior, new status, and the derived-query rule.

## 4. Health alert (deploy/audit-service)
- [ ] 4.1 RED tests in `tests/test_audit_healthcheck.py`. Run the script with `sh` against a stdlib `http.server` stub on a random loopback port, with `AUDIT_ALERT_CMD` pointing to a tiny script that appends stdin to a file, `AUDIT_HEALTH_SLEEP=0` and a temp state file. Cover: first run records without alerting; up→down alerts once naming tunnel vs app; down→down is silent; down→up alerts once; exit codes. Skip if `sh` or `curl` is missing.
- [ ] 4.2 Implement `deploy/audit-service/healthcheck.sh` (POSIX sh + curl, `set -u`, no secrets) following design.md D4.
- [ ] 4.3 Add `deploy/audit-service/systemd/egeo-audit-health.service` (Type=oneshot) and `egeo-audit-health.timer` (OnBootSec=2min, OnUnitActiveSec=5min).
- [ ] 4.4 `.github/workflows/audit-health.yml`: change the cron to hourly (`17 * * * *`) and make the comment honest (best-effort backstop; GitHub delays schedules).
- [ ] 4.5 `docs/audit-service.md` "Alerts": the local timer (install, test, disable) first, and GitHub as a backstop with its real cadence.

## 5. Wrap-up
- [ ] 5.1 `CHANGELOG.md` Unreleased: the three changes; remove the two fixed items from the known limitations if they are listed there.
- [ ] 5.2 Full verification (commands in the task prompt) passes.
