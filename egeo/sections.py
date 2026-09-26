"""Byte-exact Markdown section splitting for section-mode ``fix-gaps``.

Spec: openspec/specs/citation-gap-fixing. Plan: docs/plans/2026-09-25-fix-gaps-sections-plan.md.

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


def _fence(line: str):
    st = line.strip()
    m = re.match(r"^(`{3,}|~{3,})", st)
    return m.group(1) if m else None


def split_sections(body: str) -> List[Section]:
    lines = body.splitlines(keepends=True)
    starts = []  # (index, level, heading)
    fence = None
    for i, ln in enumerate(lines):
        content = ln.rstrip("\r\n")
        f = _fence(content)
        if fence:
            if f and f[0] == fence[0] and len(f) >= len(fence) and content.strip() == f:
                fence = None
            continue
        if f:
            fence = f
            continue
        m = HEADING_RE.match(content)
        if m:
            starts.append((i, len(m.group(1)), m.group(2).strip()))
    chunks = []
    first = starts[0][0] if starts else len(lines)
    pre = "".join(lines[:first])
    if pre:
        chunks.append((0, "", pre))
    for n, (i, level, heading) in enumerate(starts):
        end = starts[n + 1][0] if n + 1 < len(starts) else len(lines)
        chunks.append((level, heading, "".join(lines[i:end])))
    return [Section(id=f"s{k:02d}", heading=h, level=lv, text=t, word_count=count_words(t))
            for k, (lv, h, t) in enumerate(chunks)]


def join_sections(sections: Sequence[Section]) -> str:
    return "".join(s.text for s in sections)


def replace_section(sections: Sequence[Section], section_id: str, new_text: str) -> List[Section]:
    if not any(s.id == section_id for s in sections):
        raise KeyError(section_id)
    return [Section(s.id, s.heading, s.level, new_text, count_words(new_text)) if s.id == section_id else s
            for s in sections]
