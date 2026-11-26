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


# --------------------------------------------------------------------------- #
# Page fidelity gate + content type (openspec update-optimize-page-fidelity)
# --------------------------------------------------------------------------- #
import json  # noqa: E402

import pytest  # noqa: E402

from egeo.agents import RewriteResult, Rewriter  # noqa: E402
from egeo.pipeline import check_page_fidelity, detect_content_type  # noqa: E402
from egeo.runtimes import PythonRuntime  # noqa: E402

GUIDE = """# How to Get Cited

**Last verified: 2026-08-11.** Projects with 17 stars appeared while one with 147 did not.

See the [paper](https://arxiv.org/abs/2511.20867) for the method.

| Source | Share |
|---|---|
| LibHunt | 40% |

```bash
pip install egeo
```
"""
GUIDE_BODY = GUIDE.split("\n", 2)[2].strip()
GOOD = GUIDE_BODY.replace("for the method", "for the full method")
LOSSY = "Projects with 17 stars appeared while one with 147 did not.\n\n| Source | Share |\n|---|---|\n| LibHunt | 40% |"


class _ScriptedRuntime(PythonRuntime):
    """PythonRuntime whose rewriter returns scripted outputs, one per call."""

    def __init__(self, outputs):
        super().__init__()
        self.outputs = list(outputs)
        self.calls = []
        self.content_types = []

    def make_rewriter(self, content_type="product"):
        runtime = self
        runtime.content_types.append(content_type)

        class _R:
            def rewrite(self, title, description, *, previous=None, violations=()):
                runtime.calls.append({"previous": previous, "violations": tuple(violations)})
                return RewriteResult(title, description, runtime.outputs.pop(0))

        return _R()


def _run(tmp_path, monkeypatch, outputs, content=GUIDE, **kwargs):
    monkeypatch.setenv("GEO_EVAL_MOCK", "1")
    runtime = _ScriptedRuntime(outputs)
    result = optimize_content(runtime=runtime, content=content, source="guide.md", output_dir=tmp_path, **kwargs)
    return runtime, result


def test_detect_content_type():
    assert detect_content_type("We help businesses understand their data.\n\n- Dashboard\n- Reports") == "product"
    assert detect_content_type("word " * 150) == "article"
    assert detect_content_type("word " * 149) == "product"
    assert detect_content_type("## A\nx\n## B\ny\n## C\nz") == "article"
    # headings and words inside code fences do not count
    assert detect_content_type("```\n# a\n# b\n# c\n" + "word " * 200 + "\n```") == "product"


def test_page_rules_ignore_list_markers_heading_and_growth():
    original = "First do this. Then do that. It costs $99."
    rewritten = "## Steps\n\n1. First do this.\n2. Then do that.\n\nIt costs $99. " + "More helpful context here. " * 20
    assert check_page_fidelity(original, rewritten).passed
    assert check_page_fidelity("1. one\n2. two", "- one\n- two").passed


def test_page_rules_catch_lost_and_invented_facts():
    result = check_page_fidelity(GUIDE_BODY, LOSSY)
    assert not result.passed
    assert "link_removed:https://arxiv.org/abs/2511.20867" in result.violations
    assert "number_removed:2026" in result.violations  # the "Last verified" date
    assert "code_block_changed" in result.violations
    assert "too_short" in result.violations
    added = check_page_fidelity("It costs $99.", "It costs $99 and is rated 4.9 by 10,000 users.")
    assert {"number_added:4.9", "number_added:10000"} <= set(added.violations)


def test_passing_rewrite_is_written_once(tmp_path, monkeypatch):
    runtime, result = _run(tmp_path, monkeypatch, [GOOD])
    assert result.fidelity == {"status": "passed", "violations": [], "attempts": 1}
    assert len(runtime.calls) == 1
    assert (tmp_path / "optimized" / "how-to-get-cited.md").is_file()
    assert not (tmp_path / "rejected").exists()


def test_repair_attempt_gets_violations_and_is_accepted(tmp_path, monkeypatch):
    runtime, result = _run(tmp_path, monkeypatch, [LOSSY, GOOD])
    assert result.fidelity["status"] == "repaired"
    assert result.fidelity["attempts"] == 2
    assert result.fidelity["violations"] == []
    assert "link_removed:https://arxiv.org/abs/2511.20867" in result.fidelity["first_attempt_violations"]
    assert runtime.calls[1]["previous"] == LOSSY
    assert "link_removed:https://arxiv.org/abs/2511.20867" in runtime.calls[1]["violations"]
    assert "full method" in (tmp_path / "optimized" / "how-to-get-cited.md").read_text(encoding="utf-8")


def test_failing_rewrite_is_rejected_not_published(tmp_path, monkeypatch):
    runtime, result = _run(tmp_path, monkeypatch, [LOSSY, LOSSY])
    assert len(runtime.calls) == 2  # exactly one repair attempt
    assert result.fidelity["status"] == "rejected"
    assert not result.rewrite_accepted
    assert not (tmp_path / "optimized").exists()
    assert (tmp_path / "rejected" / "how-to-get-cited.md").is_file()
    assert result.rank_after == result.rank_before
    analysis = json.loads((tmp_path / "analysis.json").read_text(encoding="utf-8"))
    assert analysis["fidelity"]["status"] == "rejected"
    assert "link_removed:https://arxiv.org/abs/2511.20867" in analysis["fidelity"]["violations"]
    report = (tmp_path / "report.md").read_text(encoding="utf-8")
    assert "`rejected`" in report and "link_removed:https://arxiv.org/abs/2511.20867" in report
    # the schema must not describe content that was rejected
    schema = (tmp_path / "schema" / "how-to-get-cited.json").read_text(encoding="utf-8")
    assert "Last verified" in schema


def test_allow_lossy_writes_and_still_reports(tmp_path, monkeypatch):
    _, result = _run(tmp_path, monkeypatch, [LOSSY, LOSSY], allow_lossy=True)
    assert result.fidelity["status"] == "lossy_allowed"
    assert result.fidelity["violations"]
    assert (tmp_path / "optimized" / "how-to-get-cited.md").is_file()


def test_auto_content_type_selects_prompt(tmp_path, monkeypatch):
    runtime, result = _run(tmp_path / "a", monkeypatch, [GOOD])
    assert (runtime.content_types, result.content_type) == (["product"], "product")  # short body
    long_guide = GUIDE + "\n" + "Extra explanatory sentence for length. " * 40
    body = long_guide.split("\n", 2)[2].strip()
    runtime, result = _run(tmp_path / "b", monkeypatch, [body], content=long_guide)
    assert (runtime.content_types, result.content_type) == (["article"], "article")
    runtime, result = _run(tmp_path / "c", monkeypatch, [GOOD], content_type="article")
    assert runtime.content_types == ["article"]
    with pytest.raises(ValueError):
        _run(tmp_path / "d", monkeypatch, [GOOD], content_type="poem")


def test_rewriter_loads_prompt_pair_and_repair_suffix():
    captured = {}

    class _Client:
        def chat_json(self, *, model, system, user, temperature):
            captured.update(system=system, user=user)
            return {"rewritten_description": "ok"}

    prompts = Path(__file__).resolve().parents[1] / "prompts"
    Rewriter(client=_Client(), model="m", prompts_dir=prompts, content_type="article").rewrite("T", "Body {{title}}")
    assert "informational web page" in captured["system"]
    assert "Best for ..." in captured["system"] and "Do not add" in captured["system"]
    assert "previous rewrite was rejected" not in captured["user"]

    Rewriter(client=_Client(), model="m", prompts_dir=prompts).rewrite(
        "T", "Body", previous="old {{description}}", violations=("link_removed:https://x.y",)
    )
    assert "product description" in captured["system"]
    assert "link_removed:https://x.y" in captured["user"]
    assert "old {{description}}" in captured["user"]  # suffix is not re-rendered as a template
    with pytest.raises(ValueError):
        Rewriter(client=_Client(), model="m", prompts_dir=prompts, content_type="poem")


def test_mock_end_to_end_cli_passes_gate(tmp_path, monkeypatch, capsys):
    from egeo.cli import main

    monkeypatch.setenv("GEO_EVAL_MOCK", "1")
    sample = Path(__file__).resolve().parents[1] / "examples" / "sample-input.md"
    assert main(["optimize", str(sample), "--out-dir", str(tmp_path), "--json"]) == 0
    summary = json.loads(capsys.readouterr().out)
    assert summary["fidelity"]["status"] == "passed"
    assert summary["content_type"] == "product"
    assert list((tmp_path / "optimized").glob("*.md"))


def test_no_aggregate_score_in_any_output(tmp_path, monkeypatch, capsys):
    """openspec update-optimize-remove-aggregate-score: the ten signals stay, the total goes."""
    from egeo.cli import main

    monkeypatch.setenv("GEO_EVAL_MOCK", "1")
    sample = Path(__file__).resolve().parents[1] / "examples" / "sample-input.md"

    assert main(["optimize", str(sample), "--out-dir", str(tmp_path)]) == 0
    text = capsys.readouterr().out
    assert "/100" not in text and "GEO score" not in text
    assert "keyword heuristic, not a ranking score" in text

    report = (tmp_path / "report.md").read_text(encoding="utf-8")
    assert "/100" not in report and "GEO Score" not in report
    assert "## GEO Signals (keyword heuristic)" in report
    assert report.count("/10 |") == 10  # the ten signals are still listed

    analysis = json.loads((tmp_path / "analysis.json").read_text(encoding="utf-8"))
    assert "total_score" not in analysis["analysis"]
    assert len(analysis["analysis"]["scores"]) == 10

    assert main(["optimize", str(sample), "--out-dir", str(tmp_path), "--json"]) == 0
    summary = json.loads(capsys.readouterr().out)
    assert "geo_score" not in summary and "total_score" not in summary
    assert len(summary["signals"]) == 10


def test_frontmatter_title_keeps_opening_paragraph_and_first_section_heading():
    """The first body line was dropped when the title came from frontmatter (lost before the gate)."""
    page = '---\ntitle: "What is GEO"\n---\n\n**GEO** is the practice of X. Last verified: 2026-08-11.\n\n## Why\n\nBecause.\n'
    title, body, _, _ = _derive_title_and_body(page)
    assert title == "What is GEO"
    assert body.startswith("**GEO** is the practice of X. Last verified: 2026-08-11.")

    title, body, _, _ = _derive_title_and_body('---\ntitle: T\n---\n\n## First section\n\nText.\n')
    assert body.startswith("## First section")

    # an H1 in the body is still the title line, with or without a frontmatter title
    title, body, _, _ = _derive_title_and_body('---\ntitle: T\n---\n\n# Body H1\n\nText.\n')
    assert (title, body) == ("T", "Text.")
    title, body, _, _ = _derive_title_and_body("# Only H1\n\nText.\n")
    assert (title, body) == ("Only H1", "Text.")
    title, body, _, _ = _derive_title_and_body("Plain first line\n\nText.\n")
    assert (title, body) == ("Plain first line", "Text.")


def test_opening_paragraph_reaches_rewriter_and_output(tmp_path, monkeypatch):
    page = '---\ntitle: "Guide"\n---\n\n**Last verified: 2026-08-11.** Opening claim.\n\n## Step\n\nDo it.\n'
    body = "**Last verified: 2026-08-11.** Opening claim.\n\n## Step\n\nDo it."
    runtime, result = _run(tmp_path, monkeypatch, [body], content=page)
    assert result.rewrite.original_description == body
    out = (tmp_path / "optimized" / "guide.md").read_text(encoding="utf-8")
    assert "Last verified: 2026-08-11." in out
    # and a rewrite that drops it is now caught by the gate
    runtime, result = _run(tmp_path / "b", monkeypatch, ["## Step\n\nDo it.", "## Step\n\nDo it."], content=page)
    assert result.fidelity["status"] == "rejected"
    assert "number_removed:2026" in result.fidelity["violations"]
