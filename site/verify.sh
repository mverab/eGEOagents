#!/usr/bin/env bash
# Post-build verification for the E-GEO docs site.
# Usage: npm run build && ./verify.sh
set -u
cd "$(dirname "$0")"

DIST=dist
fail=0

check() {
  if [ -e "$1" ]; then
    echo "PASS  $2"
  else
    echo "FAIL  $2 (missing: $1)"
    fail=1
  fi
}

check "$DIST/index.html" "landing page built"
check "$DIST/docs/getting-started/index.html" "route /docs/getting-started/"
check "$DIST/docs/cli/index.html" "route /docs/cli/"
check "$DIST/docs/faq/index.html" "route /docs/faq/"
check "$DIST/concepts/what-is-geo/index.html" "route /concepts/what-is-geo/"
check "$DIST/compare/e-geo-vs-geo-optimizer-skill/index.html" "route /compare/e-geo-vs-geo-optimizer-skill/"
check "$DIST/llms.txt" "llms.txt present"
check "$DIST/llms-full.txt" "llms-full.txt present"
check "$DIST/robots.txt" "robots.txt present"
check "$DIST/sitemap-index.xml" "sitemap generated"

grep_check() {
  if grep -q "$1" "$2" 2>/dev/null; then
    echo "PASS  $3"
  else
    echo "FAIL  $3"
    fail=1
  fi
}

grep_check '"@type":"SoftwareApplication"' "$DIST/index.html" "SoftwareApplication JSON-LD in index.html"
grep_check '"@type":"Organization"' "$DIST/index.html" "Organization JSON-LD in index.html"
grep_check 'open-source Generative Engine Optimization (GEO) &amp; Answer Engine Optimization (AEO) toolkit (Python CLI + Claude Code skills), based on published GEO research (arXiv:2511.20867)' "$DIST/index.html" "canonical entity sentence visible on /"
grep_check 'id="answer-block"' "$DIST/index.html" "answer block present on /"
grep_check 'id="answer-card"' "$DIST/index.html" "hero answer-card element present on /"
grep_check '<loc>https://egeoagents.com/</loc>' "$DIST/sitemap-0.xml" "sitemap includes /"

# hero motion graphic (citation field) — persistent animation, not one-shot reveal
grep_check 'id="citation-field"' "$DIST/index.html" "hero motion root #citation-field present"
grep_check '<svg' "$DIST/index.html" "inline SVG graphic present"
grep_check 'data-motion-loop' "$DIST/index.html" "animation implementation marker (data-motion-loop)"
grep_check 'requestAnimationFrame(frame)' "$DIST/index.html" "persistent requestAnimationFrame loop in index.html"
grep_check 'prefers-reduced-motion' "$DIST/index.html" "prefers-reduced-motion handling in index.html"
grep_check 'visibilitychange' "$DIST/index.html" "visibilitychange pause/resume handling in index.html"
grep_check 'id="cite-route"' "$DIST/index.html" "chartreuse citation signal path present"
grep_check 'id="answer-node"' "$DIST/index.html" "answer node present in citation field"

# scroll polish — progressive enhancement, never content hidden by default
grep_check 'scroll-reveal' "$DIST/index.html" "scroll-reveal enhancement present"
grep_check 'sr-in' "$DIST/index.html" "scroll-reveal in-view state class present"
grep_check 'IntersectionObserver' "$DIST/index.html" "IntersectionObserver-driven reveal in index.html"

# answer-engine rail — vendored SVG brand marks, honestly labelled
grep_check 'id="engine-rail"' "$DIST/index.html" "answer-engine rail present"
grep_check 'the surfaces where sources get named' "$DIST/index.html" "engine rail labelled honestly"
grep_check 'rail-track' "$DIST/index.html" "engine rail marquee track present"
grep_check 'aria-label="ChatGPT"' "$DIST/index.html" "ChatGPT mark accessible label present"
grep_check 'aria-label="Perplexity"' "$DIST/index.html" "Perplexity mark accessible label present"
grep_check 'aria-label="Gemini"' "$DIST/index.html" "Gemini mark accessible label present"
grep_check 'aria-label="Claude"' "$DIST/index.html" "Claude mark accessible label present"
grep_check '<svg class="mark' "$DIST/index.html" "SVG brand marks present in rail"
if grep -q '<li>ChatGPT</li>' "$DIST/index.html" 2>/dev/null; then
  echo "FAIL  old plain-text-only rail items still present"
  fail=1
else
  echo "PASS  no old plain-text-only rail items"
fi
for word in partner "official integration" "supported platform"; do
  if grep -qi "$word" "$DIST/index.html" 2>/dev/null; then
    echo "FAIL  forbidden claim '$word' found in index.html"
    fail=1
  else
    echo "PASS  no '$word' claim in index.html"
  fi
done

if grep -qi 'terminal' "$DIST/index.html" 2>/dev/null; then
  echo "FAIL  forbidden string 'terminal' found in index.html"
  fail=1
else
  echo "PASS  no 'terminal' in index.html"
fi

# layout — no horizontal overflow at desktop and mobile viewports
CHROME_BIN="${CHROME_BIN:-}"
if [ -z "$CHROME_BIN" ]; then
  for c in google-chrome chromium chromium-browser; do
    if command -v "$c" >/dev/null 2>&1; then CHROME_BIN="$c"; break; fi
  done
fi
if [ -z "$CHROME_BIN" ]; then
  CHROME_BIN=$(ls "$HOME"/.cache/ms-playwright/chromium_headless_shell-*/chrome-headless-shell-linux64/chrome-headless-shell 2>/dev/null | sort | tail -1)
fi
if [ -n "$CHROME_BIN" ] && [ -x "$CHROME_BIN" ] && command -v python3 >/dev/null 2>&1; then
  SRV_PORT=4173
  python3 -m http.server "$SRV_PORT" --directory "$DIST" >/dev/null 2>&1 &
  SRV_PID=$!
  trap 'kill "$SRV_PID" 2>/dev/null' EXIT
  sleep 1
  cat > "$DIST/__overflow_check.html" <<HTML
<!doctype html><html><head><style>html,body{margin:0}iframe{border:0;width:100vw;height:100vh;display:block}</style></head>
<body><iframe src="index.html"></iframe>
<script>
  const f = document.querySelector('iframe');
  f.addEventListener('load', () => {
    setTimeout(() => {
      const d = f.contentDocument;
      const overflow = d.documentElement.scrollWidth > f.clientWidth;
      const marker = 'OVERFLOW-CHECK:' + (overflow
        ? 'BAD:' + d.documentElement.scrollWidth + '>' + f.clientWidth
        : 'OK');
      document.body.appendChild(document.createTextNode(marker));
    }, 500);
  });
</script></body></html>
HTML
  for vp in 1440,900 390,844; do
    OUT=$("$CHROME_BIN" --headless --disable-gpu --no-sandbox \
      --window-size="$vp" --hide-scrollbars --virtual-time-budget=5000 \
      --dump-dom "http://127.0.0.1:$SRV_PORT/__overflow_check.html" 2>/dev/null)
    if echo "$OUT" | grep -q 'OVERFLOW-CHECK:OK'; then
      echo "PASS  no horizontal overflow at ${vp/,/x}"
    elif echo "$OUT" | grep -q 'OVERFLOW-CHECK:BAD'; then
      echo "FAIL  horizontal overflow at ${vp/,/x} ($(echo "$OUT" | grep -o 'OVERFLOW-CHECK:BAD:[^<]*' | head -1))"
      fail=1
    else
      echo "FAIL  overflow probe did not report at ${vp/,/x}"
      fail=1
    fi
  done
  rm -f "$DIST/__overflow_check.html"
  kill "$SRV_PID" 2>/dev/null
else
  echo "WARN  no headless Chrome/Chromium found; skipped horizontal-overflow checks"
fi

if [ "$fail" -ne 0 ]; then
  echo "verify.sh: FAILED"
  exit 1
fi
echo "verify.sh: all checks passed"
