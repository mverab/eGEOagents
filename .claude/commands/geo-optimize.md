---
name: geo:optimize
description: Optimize a local content file for GEO without full audit
arguments:
  - name: file
    description: Path to content file to optimize
    required: true
  - name: format
    description: Output format (markdown or html, default is markdown)
    required: false
---

# /geo:optimize Command

Quick optimization of local content files.

## Workflow

0. **Validate MCPs** - Run `validation-doctor`; if missing, provide setup snippets
1. **Frontmatter Extraction** - If the input file contains frontmatter (YAML block between `---` or TOML block between `+++`), extract and preserve this block completely. Do not pass the frontmatter to the analyzer or rewriter agents. Only pass the content body.
2. **Analyze** - Read and score the content body (source of truth)
3. **Rewrite** - Apply GEO optimization to the content body based on analyzer output
4. **Schema** - Generate appropriate markup based on analyzer output
5. **Reassemble & Export** - Output the optimized version to the `geo-output/optimized/` directory:
   - **markdown**: Reassemble the file by prepending the original, unmodified frontmatter to the optimized content body. Save as `[name].md`.
   - **html**: Convert the optimized content body to HTML (preserving all headers, tables, lists, and formatting). Insert the original frontmatter properties into appropriate HTML metadata tags (`<meta>` or structured header) inside a clean, modern HTML document template. Save as `[name].html`.

## Output

- Optimized content (with frontmatter preserved or converted to HTML metadata)
- Schema markup if applicable
- Change summary with impact estimates

## Example Usage

```
/geo:optimize ./content/homepage.md
/geo:optimize ./content/homepage.md html
/geo:optimize ./blog/new-post.md markdown
```
