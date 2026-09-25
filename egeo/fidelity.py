"""Deterministic fidelity rules for a rewritten section (section-mode ``fix-gaps``).

SCAFFOLD — implement until ``tests/test_fidelity.py`` passes.

A rewrite may change wording, order and emphasis. It may NOT change facts. The rules:

- ``heading_changed``        : the first line is a heading in the original and differs in the rewrite
                               (compare the stripped first lines; if the original has no heading, skip).
- ``link_removed:<url>``     : a URL in the original is missing from the rewrite.
- ``link_added:<url>``       : a URL in the rewrite is not in the original.
- ``number_removed:<n>``     : a normalized number in the original is missing from the rewrite.
- ``number_added:<n>``       : a normalized number in the rewrite is not in the original.
- ``table_rows_decreased``   : fewer table rows (lines whose stripped form starts with ``|``).
- ``code_block_changed``     : the tuple of fenced code blocks (exact text, in order) differs.
- ``too_short`` / ``too_long``: rewrite/original word ratio < min_ratio or > max_ratio. Only
                               checked when the original has >= 20 words.

Extraction details (tests depend on them):
- URLs: targets of Markdown links/images ``[text](URL)`` / ``![alt](URL)`` (URL = text up to the
  first whitespace or ``)``), autolinks ``<http...>``, and bare ``http://`` / ``https://`` URLs
  (stop at whitespace, ``)``, ``>``, ``]``, ``"`` or ``'``; strip trailing ``.,;:``).
- Numbers: regex ``(?<![\\w.])[$€£]?\\d[\\d,]*(?:\\.\\d+)?%?`` applied to the text AFTER removing all
  URLs and all fenced code blocks. Normalize by removing ``$``, ``€``, ``£`` and ``,``
  (``"$1,185"`` -> ``"1185"``, ``"40%"`` stays ``"40%"``).
- Fenced code blocks: from an opening fence line (``` or ~~~) through its closing fence line, lines
  joined with ``\n`` and no trailing newline (e.g. ``"```bash\npip install x\n```"``).
- Heading line: the first line of the text if it matches ``^#{1,6}[ \t]``, else ``""``.
- Word count: ``len(re.findall(r"\\w+", text))``.

Violations are reported in this order: heading, links removed, links added, numbers removed,
numbers added, table rows, code blocks, length. Within a group, sort values alphabetically.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import FrozenSet, Tuple

MIN_RATIO = 0.8
MAX_RATIO = 1.6
MIN_WORDS_FOR_RATIO = 20


@dataclass(frozen=True)
class Invariants:
    heading_line: str
    links: FrozenSet[str]
    numbers: FrozenSet[str]
    table_rows: int
    code_blocks: Tuple[str, ...]
    word_count: int


@dataclass(frozen=True)
class FidelityResult:
    passed: bool
    violations: Tuple[str, ...]


import re as _re

_MD_LINK = _re.compile(r"!?\[[^\]]*\]\(([^\s)]+)")
_AUTOLINK = _re.compile(r"<(https?://[^>\s]+)>")
_BARE = _re.compile(r"https?://[^\s)>\]\"']+")
_NUM = _re.compile(r"(?<![\w.])[$€£]?\d[\d,]*(?:\.\d+)?%?")
_WORD = _re.compile(r"\w+")


def _code_blocks(text):
    blocks, cur, fence = [], [], None
    for line in text.split("\n"):
        st = line.strip()
        m = _re.match(r"^(`{3,}|~{3,})", st)
        if fence is None:
            if m:
                fence = m.group(1); cur = [line]
        else:
            cur.append(line)
            if m and m.group(1)[0] == fence[0] and len(m.group(1)) >= len(fence) and st == m.group(1):
                blocks.append("\n".join(cur)); cur, fence = [], None
    return tuple(blocks)


def _links(text):
    found = set(_MD_LINK.findall(text)) | set(_AUTOLINK.findall(text))
    for u in _BARE.findall(text):
        found.add(u.rstrip(".,;:"))
    return frozenset(found)


def extract_invariants(text: str) -> Invariants:
    first = text.split("\n", 1)[0]
    heading = first.strip() if _re.match(r"^#{1,6}[ \t]", first) else ""
    blocks = _code_blocks(text)
    prose = text
    for b in blocks:
        prose = prose.replace(b, " ")
    links = _links(prose)
    for u in sorted(links, key=len, reverse=True):
        prose = prose.replace(u, " ")
    numbers = frozenset(_re.sub(r"[$€£,]", "", n) for n in _NUM.findall(prose))
    rows = sum(1 for ln in text.split("\n") if ln.strip().startswith("|"))
    return Invariants(heading, links, numbers, rows, blocks, len(_WORD.findall(text)))


def check_fidelity(original: str, rewritten: str, *, min_ratio: float = MIN_RATIO, max_ratio: float = MAX_RATIO) -> FidelityResult:
    a, b = extract_invariants(original), extract_invariants(rewritten)
    v = []
    if a.heading_line and a.heading_line != b.heading_line:
        v.append("heading_changed")
    v += [f"link_removed:{u}" for u in sorted(a.links - b.links)]
    v += [f"link_added:{u}" for u in sorted(b.links - a.links)]
    v += [f"number_removed:{n}" for n in sorted(a.numbers - b.numbers)]
    v += [f"number_added:{n}" for n in sorted(b.numbers - a.numbers)]
    if b.table_rows < a.table_rows:
        v.append("table_rows_decreased")
    if a.code_blocks != b.code_blocks:
        v.append("code_block_changed")
    if a.word_count >= MIN_WORDS_FOR_RATIO:
        r = b.word_count / a.word_count
        if r < min_ratio:
            v.append("too_short")
        elif r > max_ratio:
            v.append("too_long")
    return FidelityResult(passed=not v, violations=tuple(v))
