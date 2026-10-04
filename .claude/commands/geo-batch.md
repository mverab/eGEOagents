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
1. **Scan** - Find all matching files in folder; announce the count before starting
2. **Process** - Run `/geo:optimize` on each file (analyzer-based), reporting progress after each one
3. **Summarize** - Generate batch report

## Progress

Report progress as you go, never only at the end:

1. Before processing, print `Processing batch (N files)...` with the total found.
2. After **each** file finishes, print one line `[i/N] <file> ✓` (or `✗ <short reason>` if it failed). Do not hold lines back to print them together.
3. A failed file does not stop the batch: record it, continue with the next file, and list failures in the summary.
4. Finish with `Complete! Results in geo-output/` (or `Complete with K failure(s). Results in geo-output/`).

```
Processing batch (3 files)...
[1/3] pricing.md ✓
[2/3] about.md ✓
[3/3] contact.md ✗ empty file, skipped

Complete with 1 failure. Results in geo-output/
```

If no files match, print `No files matching <pattern> in <folder>.` and stop.

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
