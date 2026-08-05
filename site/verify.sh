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

if grep -q '"@type": *"SoftwareApplication"' "$DIST/index.html" 2>/dev/null; then
  echo "PASS  SoftwareApplication JSON-LD in index.html"
else
  echo "FAIL  SoftwareApplication JSON-LD missing from index.html"
  fail=1
fi

if [ "$fail" -ne 0 ]; then
  echo "verify.sh: FAILED"
  exit 1
fi
echo "verify.sh: all checks passed"
