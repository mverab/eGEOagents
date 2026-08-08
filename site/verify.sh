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

if grep -qi 'terminal' "$DIST/index.html" 2>/dev/null; then
  echo "FAIL  forbidden string 'terminal' found in index.html"
  fail=1
else
  echo "PASS  no 'terminal' in index.html"
fi

if [ "$fail" -ne 0 ]; then
  echo "verify.sh: FAILED"
  exit 1
fi
echo "verify.sh: all checks passed"
