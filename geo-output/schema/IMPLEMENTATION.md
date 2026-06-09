# Flowork Schema Markup Implementation Guide

## Overview

Complete JSON-LD schema markup package for Flowork (https://aiflowork.com). These schemas optimize the site for AI-powered search engines (ChatGPT, Perplexity, Claude, Gemini) and traditional search engines.

## Files Generated

| File | Purpose | Schema Types |
|------|---------|--------------|
| `flowork-organization.jsonld` | Company details | Organization |
| `flowork-software.jsonld` | Product details | SoftwareApplication |
| `flowork-product.jsonld` | Offer details | Product, Offer, Review |
| `flowork-faq.jsonld` | FAQ content | FAQPage |
| `flowork-reviews.jsonld` | Customer reviews | Review, AggregateRating |
| `flowork-article.jsonld` | About/founder story | Article |
| `flowork-webpage.jsonld` | Homepage metadata | WebPage |
| `flowork-combined.jsonld` | **RECOMMENDED** | All schemas in one |

## Implementation Options

### Option 1: Combined Schema (RECOMMENDED)

Add the combined schema to your website's `<head>` section:

```html
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@graph": [
    // Full combined schema content from flowork-combined.jsonld
  ]
}
</script>
```

**Advantages:**
- Single HTTP request
- All entities properly linked via @id references
- Easier to maintain
- Best for AI understanding

### Option 2: Modular Schema

Use individual schema files on relevant pages:

```html
<!-- Homepage -->
<script type="application/ld+json" src="/schema/flowork-webpage.jsonld"></script>

<!-- About page -->
<script type="application/ld+json" src="/schema/flowork-article.jsonld"></script>

<!-- Pricing page -->
<script type="application/ld+json" src="/schema/flowork-product.jsonld"></script>

<!-- FAQ page -->
<script type="application/ld+json" src="/schema/flowork-faq.jsonld"></script>
```

## Required Actions

### 1. Fill in Placeholder Data

Search for `[FILL:` tags in the schema files and replace with actual data:

**Critical Placeholders:**
- Founder name and social profiles
- Actual aggregate rating (e.g., 4.8)
- Actual review count
- Individual review content
- Company founding date
- Social media URLs (Discord, YouTube)

### 2. Update Asset URLs

Replace placeholder URLs with actual assets:
- Logo: `https://aiflowork.com/logo.png`
- Hero image: `https://aiflowork.com/hero-image.png`
- Screenshots: `https://aiflowork.com/screenshot-*.png`
- Founder photo: `https://aiflowork.com/about/founder.jpg`

### 3. Verify Social Profiles

Update `sameAs` array in Organization schema:
```json
"sameAs": [
  "https://twitter.com/aiflowork",
  "https://linkedin.com/company/flowork",
  "https://github.com/flowork",
  "https://discord.gg/flowork",    // Add actual
  "https://youtube.com/@flowork"   // Add actual
]
```

## HTML Meta Tags (Additional)

Add to `<head>` for complete optimization:

```html
<!-- Primary Meta Tags -->
<title>Flowork - AI-Powered n8n Workflow Builder | Ship 10x Faster</title>
<meta name="description" content="Launch production-ready n8n workflows in under 45 minutes. The only AI platform with real-time n8n validation, automated blueprints, and client-ready QA packets. Trusted by 150+ agencies.">
<meta name="keywords" content="n8n workflow builder, AI automation, workflow automation, n8n development, automation agency tools">
<link rel="canonical" href="https://aiflowork.com">

<!-- Open Graph -->
<meta property="og:type" content="website">
<meta property="og:url" content="https://aiflowork.com">
<meta property="og:title" content="Flowork - Ship n8n Workflows 10x Faster">
<meta property="og:description" content="AI-powered n8n workflow builder. Production-ready workflows in 45 minutes with real-time validation and client-ready deliverables.">
<meta property="og:image" content="https://aiflowork.com/og-image.png">
<meta property="og:site_name" content="Flowork">
<meta property="og:locale" content="en_US">

<!-- Twitter Card -->
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:url" content="https://aiflowork.com">
<meta name="twitter:title" content="Flowork - AI-Powered n8n Workflow Builder">
<meta name="twitter:description" content="Ship production-ready n8n workflows in under 45 minutes. Trusted by 150+ automation agencies.">
<meta name="twitter:image" content="https://aiflowork.com/twitter-card.png">
<meta name="twitter:site" content="@aiflowork">
<meta name="twitter:creator" content="@aiflowork">

<!-- Additional SEO -->
<meta name="author" content="Flowork">
<meta name="robots" content="index, follow">
<meta name="googlebot" content="index, follow">
<meta name="theme-color" content="#FF6D5A">

<!-- Product Specific -->
<meta name="product:price:amount" content="9.00">
<meta name="product:price:currency" content="USD">
```

## Validation Checklist

- [ ] Schema validates at https://validator.schema.org/
- [ ] Rich snippets test passes at Google Rich Results Test
- [ ] All placeholder `[FILL:]` tags replaced
- [ ] All asset URLs return 200 status
- [ ] Social profile URLs are correct
- [ ] AggregateRating has actual values
- [ ] Review content is authentic (not placeholder text)
- [ ] Founder information is complete
- [ ] Pricing data is current
- [ ] Contact email addresses are active

## GEO Optimization Benefits

These schemas enable:

1. **AI Engine Understanding**
   - ChatGPT/Claude can extract: pricing, features, comparison vs alternatives
   - Perplexity can cite: stats (247 workflows, 150+ teams)
   - Gemini can recommend: based on use case matching

2. **Rich Search Results**
   - Star ratings in search
   - Pricing display
   - FAQ dropdown in SERP
   - Software badges

3. **Knowledge Graph**
   - Organization entity links to founder
   - Product linked to brand
   - Reviews linked to software

4. **Voice Search Optimization**
   - FAQ schema enables voice answer extraction
   - Structured data for "How much is Flowork?" queries
   - Comparison data for "Flowork vs ChatGPT" queries

## Technical Notes

- All schemas use `@id` for cross-referencing entities
- Combined schema uses `@graph` for multiple entity types
- ISO 8601 date format required: `2024-11-15`
- Currency codes follow ISO 4217: `USD`
- Rating scale: 1-5 (bestRating: 5, worstRating: 1)

## Dynamic Data Sources

For production, consider pulling data from:

```javascript
// Example: Dynamic rating injection
const aggregateRating = {
  ratingValue: product.averageRating,    // From database
  reviewCount: product.totalReviews      // From database
};

// Example: Dynamic pricing
const offers = {
  price: pricing.proPlanPrice,           // From pricing engine
  priceCurrency: 'USD'
};

// Example: Dynamic reviews
const reviews = customerReviews.map(r => ({ // From reviews API
  reviewRating: { ratingValue: r.rating },
  author: { name: r.customerName },
  reviewBody: r.comment
}));
```

## File Locations

All schema files: `/Users/mverab/eGEOagents/geo-output/schema/`

Upload to your web server at: `https://aiflowork.com/schema/`

Or embed directly in HTML `<head>` section.

## Support

For schema validation issues:
- Google Structured Data Testing Tool
- Schema.org Validator
- Rich Results Test

For GEO optimization questions, refer to E-GEO documentation.
