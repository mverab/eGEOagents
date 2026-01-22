# Good First Issues for Launch

Create these issues on GitHub before launch to drive early engagement.

---

## Issue 1: Add more schema types

**Title:** [Good First Issue] Add Organization schema type

**Labels:** `good first issue`, `enhancement`, `schema`

**Body:**

Currently, E-GEO generates Product and Article schemas. We'd like to add Organization schema for company pages.

**What's needed:**
1. Add `Organization` schema template to `geo-indexer` agent
2. Include fields: name, description, url, logo, sameAs, address
3. Test with a sample organization page

**Resources:**
- Schema.org Organization docs: https://schema.org/Organization
- Existing schema templates in `.claude/agents/geo-indexer.md`

**Expected outcome:**
`/geo` command generates Organization schema when it detects a company/about page.

---

## Issue 2: Improve local file handling

**Title:** [Good First Issue] Support markdown frontmatter in local files

**Labels:** `good first issue`, `enhancement`

**Body:**

When optimizing local markdown files with `/geo:optimize`, preserve frontmatter (YAML/TOML) instead of treating it as content.

**Example:**

Input:
```markdown
---
title: My Page
description: My description
---

# Content here
```

Expected: Frontmatter preserved, only "Content here" optimized.

**What's needed:**
1. Detect frontmatter in markdown files
2. Parse and preserve it separately
3. Only optimize the content body
4. Reassemble with original frontmatter

**Resources:**
- Python frontmatter library: https://pypi.org/project/frontmatter/
- Current file handling in commands

---

## Issue 3: Add progress indicators

**Title:** [Good First Issue] Add real-time progress feedback for batch processing

**Labels:** `good first issue`, `enhancement`, `UX`

**Body:**

When running `/geo:batch` on multiple files, users don't see progress until all files complete.

**What's needed:**
1. Show progress indicator during batch processing
2. Display "Processing X of Y files..."
3. Show completion status for each file

**Example output:**
```
Processing batch (3 files)...
[1/3] pricing.md ✓
[2/3] about.md ✓
[3/3] contact.md ✓

Complete! Results in geo-output/
```

**Resources:**
- Current batch command: `.claude/commands/geo-batch.md`
- Output style: `.claude/output-styles/geo-optimizer.md`

---

## Issue 4: Export to different formats

**Title:** [Good First Issue] Add HTML export option for optimized content

**Labels:** `good first issue`, `enhancement`

**Body:**

Currently, optimized content is exported as markdown. Add option to export as HTML.

**What's needed:**
1. Add `--format` flag to `/geo:optimize` command
2. Support `markdown` (default) and `html` formats
3. Convert markdown to HTML while preserving formatting

**Example:**
```bash
/geo:optimize content.md --format html
# Creates: geo-output/optimized/content.html
```

**Resources:**
- Python markdown library: https://pypi.org/project/markdown/
- Current export logic in commands

---

## Issue 5: Documentation examples

**Title:** [Good First Issue] Add real-world before/after examples to docs

**Labels:** `good first issue`, `documentation`

**Body:**

The documentation would benefit from real-world before/after examples showing E-GEO optimizations.

**What's needed:**
1. Find 2-3 public pages to use as examples
2. Run `/geo:audit` to save before state
3. Run `/geo` to generate optimized versions
4. Add to `docs/examples.md` with:
   - Original content
   - GEO score before/after
   - What changed
   - Screenshot of output

**Resources:**
- Current examples folder: `examples/`
- Documentation structure in `docs/`

---

## Instructions

1. **Before launch:** Create these 5 issues on GitHub
2. **Tag them:** Apply `good first issue` and `enhancement` labels
3. **Link:** Add to README "Perfect For" section or Contributing
4. **During launch:** Mention in launch posts for community engagement

---

## Timing

- Create issues 1-2 days before launch
- This gives early adopters concrete ways to contribute
- Monitor and respond to issue comments during launch window
