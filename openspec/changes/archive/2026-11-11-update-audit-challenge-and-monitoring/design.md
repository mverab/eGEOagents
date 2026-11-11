# Design

## D1. Challenge detection is conservative

Vendor scripts such as Cloudflare's `/cdn-cgi/challenge-platform/` are injected into normal pages too; crunchbase.com serves one on a 130 KB real page. So a marker alone never triggers detection. Detection requires BOTH:

- a signal:
  - a title, compared case-insensitively after trimming, that equals one of `Just a moment...`, `Attention Required! | Cloudflare`, `Client Challenge`, `Access to this page has been denied`, `Access Denied`, `Pardon Our Interruption`, `DDoS-Guard`, or starts with `Security Check`; or
  - a strong marker in the raw HTML: `_cf_chl_opt` or `cf-chl-` (cloudflare); `px-captcha` or `_pxAppId` (perimeterx); `captcha-delivery.com` (datadome); `_Incapsula_Resource` (imperva); `sec-if-cpt` (akamai);
- AND `visible_words < MIN_VISIBLE_WORDS`.

`vendor` is the vendor of the first matching marker. With only a title match it is the title's vendor: `Just a moment...` and `Attention Required! | Cloudflare` → cloudflare, `Access to this page has been denied` → perimeterx, `Pardon Our Interruption` → imperva, `DDoS-Guard` → ddos-guard. Any other title gives `unknown`.

`evidence` names the signal and the word count, for example `title "Just a moment...", marker _cf_chl_opt, 12 visible words`.

Statuses other than 200/403/429/503, and non-HTML responses, keep today's `fetch_failed` path unchanged.

## D2. Report shape under a challenge

There is no new error code. A report is more useful than an error: robots.txt and llms.txt are still fetched (they are separate requests, and many sites exempt them), and the challenge itself is the finding. Page checks become `unverifiable`, not `fail`, because the page was not observed (the "No Aggregate Score" rule is unchanged). `features.items` is `[]` rather than scores computed on challenge text. The rewrite is skipped before `reserve_llm` is called.

## D3. Site-name stripping

The rule is pure and has no LLM. The hostname's main label is the label before the public suffix: `www.`, `en.` and `m.` prefixes are dropped, then the second-to-last label is taken. So `en.wikipedia.org` → `wikipedia` and `www.bbc.com` → `bbc`. Two-part public suffixes such as `.co.uk` are out of scope: the main label then is `co`, which has fewer than 3 characters, so nothing is stripped. Only labels of 3 or more characters are matched, to avoid false hits. Only the first and last segments are candidates, and at least one segment always remains.

Examples:
- `Generative engine optimization - Wikipedia` → `Generative engine optimization`;
- `Home - BBC News` → `Home`;
- `Plausible Analytics | Simple, privacy-friendly Google Analytics alternative` → `Simple, privacy-friendly Google Analytics alternative`;
- `Acme Analytics` → unchanged.

## D4. Health alert lives on the VPS, GitHub stays as a backstop

The script is plain POSIX `sh` plus `curl`. It has no Python, so it keeps working when the app's venv is broken. It reads:
- `AUDIT_PUBLIC_BASE`, default `https://api.egeoagents.com`;
- `AUDIT_LOCAL_BASE`, default `http://127.0.0.1:8787`;
- `AUDIT_ALERT_CMD`, default `hermes send -t telegram`; the message goes on stdin;
- `AUDIT_HEALTH_STATE`, default `${XDG_STATE_HOME:-$HOME/.local/state}/egeo-audit/health.state`;
- `AUDIT_HEALTH_TRIES` (default 3) and `AUDIT_HEALTH_SLEEP` (default 10 s).

"Up" means the same as the GitHub probe: public `/healthz` is 200 AND an unknown id returns a body containing `"not_found"`. When the public probe fails, the loopback `/healthz` decides the message:
- loopback is up → "tunnel or Cloudflare";
- loopback is down → "app".

The script alerts only on a state change. The first run with no state file records the state and sends nothing. The exit code is 0 when up and 1 when down, so `systemctl --user status` shows the result.

The GitHub workflow can't be made punctual, so it moves to hourly and is documented as best effort.
