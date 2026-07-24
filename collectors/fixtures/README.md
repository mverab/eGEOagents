# Collector fixtures

Recorded responses so collector contract tests run with no network and no API
key. Content is synthetic; the *shape* mirrors the real responses.

| Fixture | Replayed by |
|---|---|
| `serp_brave_response.json` | `python collectors/serp.py --fixture collectors/fixtures/serp_brave_response.json` |
| `pages/<page-slug>.html` | `python collectors/page.py --fixture collectors/fixtures/pages/` |

Page fixtures are matched by slug: `https://example.com/pricing` resolves to
`pages/example-com-pricing.html` (see `_common.slugify`). To record a new one,
save the real response body under the slug name and never commit private data.
