---
name: geo:batch
description: Process multiple content files in a folder
arguments:
  - name: folder
    description: Path to folder containing content files
    required: true
  - name: pattern
    description: File pattern to match (default *.md)
    required: false
---

# /geo:batch Command

Batch process all content files in a folder.

## Workflow

0. **Validate MCPs** - Run `validation-doctor`; if missing, provide setup snippets
1. **Scan** - Find all matching files in folder
2. **Process** - Run `/geo:optimize` on each file (analyzer-based)
3. **Summarize** - Generate batch report

## Output

For each file:
- Optimized version in `geo-output/optimized/`
- Schema in `geo-output/schema/`

Summary report with:
- Files processed
- Average score improvement
- Top priority fixes across all content

## Example Usage

```
/geo:batch ./content
/geo:batch ./pages --pattern "*.html"
/geo:batch ./blog
```
