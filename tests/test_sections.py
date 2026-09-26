"""Contract tests for egeo.sections (section-mode fix-gaps). Do not weaken; report if wrong."""
from __future__ import annotations

import pytest

from egeo.sections import Section, count_words, join_sections, replace_section, split_sections

DOC = """Intro paragraph before any heading.

## First

Text of first.

```bash
# not a heading, inside a fence
echo hi
```

### Nested

Nested text.
## Second ##

Last words
"""


def test_split_ids_levels_headings() -> None:
    secs = split_sections(DOC)
    assert [s.id for s in secs] == ["s00", "s01", "s02", "s03"]
    assert [(s.level, s.heading) for s in secs] == [(0, ""), (2, "First"), (3, "Nested"), (2, "Second")]
    assert secs[0].text == "Intro paragraph before any heading.\n\n"
    assert secs[1].text.startswith("## First\n")
    assert "# not a heading, inside a fence" in secs[1].text
    assert secs[3].text == "## Second ##\n\nLast words\n"


@pytest.mark.parametrize(
    "body",
    [
        DOC,
        "# Only heading",
        "# A\ntext\n# B\n",
        "no headings at all\n\nsecond paragraph",
        "\n\n# Starts after blank lines\nbody\n",
        "~~~\n# fenced with tildes\n~~~\n# Real\n",
        "````\n```\n# still fenced\n```\n````\n## After\nx\n",
        "",
    ],
)
def test_round_trip_is_byte_exact(body: str) -> None:
    assert join_sections(split_sections(body)) == body


def test_no_preamble_when_body_starts_with_heading() -> None:
    secs = split_sections("# Title\nbody\n")
    assert [s.id for s in secs] == ["s00"]
    assert secs[0].level == 1 and secs[0].heading == "Title"


def test_whitespace_preamble_is_kept_for_losslessness() -> None:
    secs = split_sections("\n\n# Starts after blank lines\nbody\n")
    assert secs[0].level == 0 and secs[0].text == "\n\n"


def test_fenced_heading_is_not_a_section() -> None:
    secs = split_sections("~~~\n# fenced with tildes\n~~~\n# Real\n")
    assert [s.heading for s in secs] == ["", "Real"]


def test_setext_and_hashtag_without_space_are_not_headings() -> None:
    secs = split_sections("Title\n=====\n#hashtag is text\n")
    assert len(secs) == 1 and secs[0].level == 0


def test_word_count() -> None:
    secs = split_sections("## Words here\none two three\n")
    assert secs[0].word_count == count_words("## Words here\none two three\n") == 5


def test_replace_section_returns_new_list() -> None:
    secs = split_sections(DOC)
    new = replace_section(secs, "s02", "### Nested\n\nBetter nested text with more words.\n")
    assert new[2].text == "### Nested\n\nBetter nested text with more words.\n"
    assert new[2].id == "s02" and new[2].heading == "Nested" and new[2].level == 3
    assert new[2].word_count == count_words(new[2].text)
    assert secs[2].text.startswith("### Nested\n\nNested text.")  # input untouched
    assert join_sections(new) == DOC.replace("### Nested\n\nNested text.\n", "### Nested\n\nBetter nested text with more words.\n")


def test_replace_unknown_id_raises() -> None:
    with pytest.raises(KeyError):
        replace_section(split_sections(DOC), "s99", "x")


def test_section_is_frozen_dataclass() -> None:
    s = Section(id="s00", heading="", level=0, text="x", word_count=1)
    with pytest.raises(Exception):
        s.text = "y"  # type: ignore[misc]
