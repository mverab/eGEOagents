"""Byte-exact Markdown section splitting for section-mode ``fix-gaps``.

SCAFFOLD — implement the functions below until ``tests/test_sections.py`` passes.
Spec: openspec/changes/update-fix-gaps-section-rewrite. Plan: docs/plans/2026-09-25-fix-gaps-sections-plan.md.

Rules (all enforced by tests):
- Input is a Markdown *body* (frontmatter already removed with
  ``egeo.pipeline._extract_frontmatter``; ``raw + body == original``).
- A heading is an ATX line ``^(#{1,6})[ \\t]+(.+?)[ \\t#]*$`` that is NOT inside a
  fenced code block. Fences open with a line whose stripped form starts with ```
  or ``~~~`` and close with a line starting with the same character repeated at
  least as many times. Setext headings (``===`` / ``---`` underlines) are NOT headings.
- Every heading line starts a new section. Text before the first heading forms a
  preamble section (level 0, heading "") if that text is non-empty (even if only
  whitespace), so the split is lossless.
- Section ids are ``s00``, ``s01``, ... in document order (preamble included).
- ``Section.text`` is the exact source text from the heading line (or document
  start) up to, not including, the next heading line; it keeps its trailing newlines.
- ``join_sections(split_sections(body)) == body`` for every input, byte for byte.
- ``word_count`` is ``len(re.findall(r"\\w+", text))``.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Sequence

HEADING_RE = re.compile(r"^(#{1,6})[ \t]+(.+?)[ \t#]*$")
WORD_RE = re.compile(r"\w+")


@dataclass(frozen=True)
class Section:
    id: str
    heading: str
    level: int
    text: str
    word_count: int


def count_words(text: str) -> int:
    return len(WORD_RE.findall(text))


def split_sections(body: str) -> List[Section]:
    """Split a Markdown body into sections (see module docstring)."""
    raise NotImplementedError


def join_sections(sections: Sequence[Section]) -> str:
    """Concatenate section texts in order. Inverse of :func:`split_sections`."""
    raise NotImplementedError


def replace_section(sections: Sequence[Section], section_id: str, new_text: str) -> List[Section]:
    """Return a new list where ``section_id`` has ``new_text`` (and a recomputed
    ``word_count``); heading/level/id stay as they were. Raise ``KeyError`` if the
    id is not present. The input list is not mutated."""
    raise NotImplementedError
