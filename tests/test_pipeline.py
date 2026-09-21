"""Tests for pipeline frontmatter preservation and HTML export functionality."""

from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from egeo.pipeline import (
    _extract_frontmatter,
    _derive_title_and_body,
    _markdown_to_html,
    optimize_content,
)
from egeo.runtimes import get_runtime


SAMPLE_YAML_FRONTMATTER = """---
title: Understanding GEO in 2026
description: A comprehensive analysis of Generative Engine Optimization.
author: Jane Doe
tags: [geo, seo, ai]
---

# Understanding GEO in 2026

Generative Engine Optimization structures content to gain authoritative citations in AI answer engines.
"""

SAMPLE_TOML_FRONTMATTER = """+++
title = "TOML Content Guide"
description = "Testing TOML frontmatter preservation."
+++

# TOML Content Guide

Here is the body content after TOML frontmatter.
"""

SAMPLE_NO_FRONTMATTER = """# Plain Markdown Guide

This content contains no frontmatter whatsoever, just direct markdown text.
"""


def test_extract_frontmatter_yaml():
    raw, body, parsed = _extract_frontmatter(SAMPLE_YAML_FRONTMATTER)
    assert raw.startswith("---")
    assert raw.strip().endswith("---")
    assert "Understanding GEO in 2026" in body
    assert parsed.get("title") == "Understanding GEO in 2026"
    assert parsed.get("author") == "Jane Doe"
    assert parsed.get("tags") == ["geo", "seo", "ai"]


def test_extract_frontmatter_toml():
    raw, body, parsed = _extract_frontmatter(SAMPLE_TOML_FRONTMATTER)
    assert raw.startswith("+++")
    assert raw.strip().endswith("+++")
    assert "TOML Content Guide" in body
    assert parsed.get("title") == "TOML Content Guide"
    assert parsed.get("description") == "Testing TOML frontmatter preservation."


def test_extract_frontmatter_mismatched_delimiters():
    # Opening --- with closing +++ must not be extracted as valid frontmatter
    mismatched = "---\ntitle: Broken\n+++\n# Content"
    raw, body, parsed = _extract_frontmatter(mismatched)
    assert raw == ""
    assert body == mismatched
    assert parsed == {}


def test_extract_frontmatter_none():
    raw, body, parsed = _extract_frontmatter(SAMPLE_NO_FRONTMATTER)
    assert raw == ""
    assert body == SAMPLE_NO_FRONTMATTER
    assert parsed == {}


def test_derive_title_and_body_uses_frontmatter_title():
    title, desc, raw, parsed = _derive_title_and_body(SAMPLE_YAML_FRONTMATTER)
    assert title == "Understanding GEO in 2026"
    assert "Generative Engine Optimization" in desc
    assert raw.startswith("---")
    assert parsed.get("author") == "Jane Doe"


def test_derive_title_and_body_uses_toml_frontmatter_title():
    title, desc, raw, parsed = _derive_title_and_body(SAMPLE_TOML_FRONTMATTER)
    assert title == "TOML Content Guide"
    assert "Here is the body content" in desc
    assert raw.startswith("+++")
    assert parsed.get("description") == "Testing TOML frontmatter preservation."


def test_derive_title_and_body_fallback_to_h1():
    title, desc, raw, parsed = _derive_title_and_body(SAMPLE_NO_FRONTMATTER)
    assert title == "Plain Markdown Guide"
    assert "just direct markdown text" in desc
    assert raw == ""
    assert parsed == {}


def test_markdown_to_html_converts_semantic_elements():
    md = """# Main Title

## Sub Heading

This is a paragraph with **bold**, *italic*, and `inline code`.
Here is a [link](https://example.com).

> An authoritative citation quote.

- First item
- Second item

1. Step one
2. Step two

| Feature | Score |
|---------|-------|
| Speed   | 95    |
| Quality | 98    |

```python
def test():
    return 42
```
"""
    html = _markdown_to_html(md, title="Test Document", metadata={"description": "Test doc description", "author": "Test Author"})

    assert "<!DOCTYPE html>" in html
    assert "<title>Test Document</title>" in html
    assert '<meta name="description" content="Test doc description">' in html
    assert '<meta name="author" content="Test Author">' in html
    assert "<h1>Main Title</h1>" in html
    assert "<h2>Sub Heading</h2>" in html
    assert "<strong>bold</strong>" in html
    assert "<em>italic</em>" in html
    assert "<code>inline code</code>" in html
    assert '<a href="https://example.com">link</a>' in html
    assert "<blockquote>" in html
    assert "<ul>" in html
    assert "<li>First item</li>" in html
    assert "<ol>" in html
    assert "<li>Step one</li>" in html
    assert "<table>" in html
    assert "<th>Feature</th>" in html
    assert "<td>Speed</td>" in html
    assert "<pre><code>" in html


def test_optimize_content_preserves_frontmatter_in_markdown(monkeypatch):
    monkeypatch.setenv("GEO_EVAL_MOCK", "1")
    with TemporaryDirectory() as tmp_dir:
        out_dir = Path(tmp_dir)
        runtime = get_runtime("python")

        result = optimize_content(
            runtime=runtime,
            content=SAMPLE_YAML_FRONTMATTER,
            source="test.md",
            output_dir=out_dir,
            export_format="markdown",
        )

        optimized_file = out_dir / "optimized" / "understanding-geo-in-2026.md"
        assert optimized_file.is_file()

        content = optimized_file.read_text(encoding="utf-8")
        # Verify original frontmatter is preserved at the top of the file
        assert content.startswith("---")
        assert "author: Jane Doe" in content
        assert "tags: [geo, seo, ai]" in content
        assert "# Understanding GEO in 2026" in content


def test_optimize_content_exports_html(monkeypatch):
    monkeypatch.setenv("GEO_EVAL_MOCK", "1")
    with TemporaryDirectory() as tmp_dir:
        out_dir = Path(tmp_dir)
        runtime = get_runtime("python")

        result = optimize_content(
            runtime=runtime,
            content=SAMPLE_YAML_FRONTMATTER,
            source="test.md",
            output_dir=out_dir,
            export_format="html",
        )

        html_file = out_dir / "optimized" / "understanding-geo-in-2026.html"
        assert html_file.is_file()

        html_content = html_file.read_text(encoding="utf-8")
        assert "<!DOCTYPE html>" in html_content
        assert "<title>Understanding GEO in 2026</title>" in html_content
        assert '<meta name="author" content="Jane Doe">' in html_content
        assert '<meta name="keywords" content="geo, seo, ai">' in html_content
        assert "<article>" in html_content
        assert "<h1>Understanding GEO in 2026</h1>" in html_content


def test_markdown_to_html_escapes_metadata():
    """Frontmatter values must be HTML-escaped in <title> and meta tags."""
    hostile = {
        "title": 'Poem "The <Best> & Worst"',
        "description": 'Saying "a < b" is not markup',
        "author": 'Vera <hola@example.com> "tester"',
    }
    out = _markdown_to_html("# Heading\n\nBody.", title=hostile["title"], metadata=hostile)
    assert "<title>Poem &quot;The &lt;Best&gt; &amp; Worst&quot;</title>" in out
    assert 'content="Saying &quot;a &lt; b&quot; is not markup' in out
    assert 'content="Vera &lt;hola@example.com&gt; &quot;tester&quot;"' in out
    # The un-escaped raw values must NOT appear in the document.
    assert 'content="Vera <hola@example.com>' not in out
    assert "The <Best>" not in out
