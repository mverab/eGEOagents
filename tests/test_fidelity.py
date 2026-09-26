"""Contract tests for egeo.fidelity. Do not weaken; report if wrong."""
from __future__ import annotations

from egeo.fidelity import check_fidelity, extract_invariants

ORIGINAL = """## The landscape

geo-optimizer-skill has 895 stars and scores sites 0–100 across 47 methods ([repo](https://github.com/Auriti-Labs/geo-optimizer-skill)).
E-GEO had $1,185 in 40% of cases, see https://egeoagents.com/case-study/.

| Tool | Stars |
|---|---|
| E-GEO | 194 |

```bash
pip install egeo==2.1.0
```
"""


def test_extract_invariants() -> None:
    inv = extract_invariants(ORIGINAL)
    assert inv.heading_line == "## The landscape"
    assert inv.links == frozenset({
        "https://github.com/Auriti-Labs/geo-optimizer-skill",
        "https://egeoagents.com/case-study/",
    })
    # numbers come from prose/tables only: URLs and code blocks are excluded ("2.1.0" is in code)
    assert inv.numbers == frozenset({"895", "0", "100", "47", "1185", "40%", "194"})
    assert inv.table_rows == 3
    assert inv.code_blocks == ("```bash\npip install egeo==2.1.0\n```",)


def test_identical_passes() -> None:
    res = check_fidelity(ORIGINAL, ORIGINAL)
    assert res.passed and res.violations == ()


def test_reworded_text_passes() -> None:
    rewritten = ORIGINAL.replace(
        "geo-optimizer-skill has 895 stars and scores sites",
        "The most-starred tool here, geo-optimizer-skill (895 stars), scores sites",
    )
    assert check_fidelity(ORIGINAL, rewritten).passed


def test_each_violation_code() -> None:
    rewritten = (
        ORIGINAL.replace("## The landscape", "## A better landscape")
        .replace("([repo](https://github.com/Auriti-Labs/geo-optimizer-skill))", "")
        .replace("47 methods", "many methods")
        .replace("| E-GEO | 194 |\n", "")
        .replace("egeo==2.1.0", "egeo")
        + "\nSee https://new.example.com for 3x more.\n"
    )
    res = check_fidelity(ORIGINAL, rewritten)
    assert not res.passed
    assert res.violations == (
        "heading_changed",
        "link_removed:https://github.com/Auriti-Labs/geo-optimizer-skill",
        "link_added:https://new.example.com",
        "number_removed:194",
        "number_removed:47",
        "number_added:3",
        "table_rows_decreased",
        "code_block_changed",
    )


def test_length_ratio() -> None:
    long_original = "## H\n\n" + " ".join(f"word{i}" for i in range(40)) + "\n"
    too_short = "## H\n\n" + " ".join(f"word{i}" for i in range(10)) + "\n"
    too_long = "## H\n\n" + " ".join(f"word{i}" for i in range(80)) + "\n"
    assert check_fidelity(long_original, too_short).violations[-1] == "too_short"
    assert check_fidelity(long_original, too_long).violations[-1] == "too_long"


def test_ratio_not_checked_for_tiny_sections() -> None:
    assert check_fidelity("## H\n\nshort text\n", "## H\n\nshort text that is now clearly a lot longer than before\n").passed


def test_no_heading_in_original_skips_heading_rule() -> None:
    assert check_fidelity("plain intro text\n", "plain intro text, reworded\n").passed
