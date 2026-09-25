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


def extract_invariants(text: str) -> Invariants:
    """Extract the fact-bearing invariants of a Markdown section."""
    raise NotImplementedError


def check_fidelity(
    original: str,
    rewritten: str,
    *,
    min_ratio: float = MIN_RATIO,
    max_ratio: float = MAX_RATIO,
) -> FidelityResult:
    """Compare invariants; ``passed`` is True only when there are no violations."""
    raise NotImplementedError
