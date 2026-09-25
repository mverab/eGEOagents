"""LLM rewrite of ONE section for section-mode ``fix-gaps``.

SCAFFOLD — implement until ``tests/test_section_rewriter.py`` passes.

- Prompts live in ``prompts/section_rewriter_system.txt`` and ``prompts/section_rewriter_user.txt``
  (repo root, canonical) with byte-identical packaged copies under ``egeo/resources/prompts/``.
  Load them through ``egeo.resource_root() / "prompts" / <name>``.
- ``render_prompts(query, section_text, page_title)`` returns ``(system, user)``; ``user`` is the
  user template formatted with ``query``, ``page_title`` and ``section`` (``str.format``; the
  templates contain no other braces).
- ``clean_output(raw, original)``:
  1. strip leading/trailing whitespace;
  2. if the result starts with a fence line (``` or ```markdown / ```md) and ends with ```, remove
     the first and last lines;
  3. strip again, then append the original's trailing whitespace
     (``original[len(original.rstrip()):]``) so section joins stay byte-exact.
- ``rewrite_section(query, section_text, *, page_title, model, client=None)``:
  if ``GEO_EVAL_MOCK`` is truthy (1/true/yes, case-insensitive) return ``section_text`` unchanged
  WITHOUT touching any client. Otherwise use ``client`` or ``llm_client.get_client()`` and call
  ``chat_text(model=model, system=system, user=user, temperature=REWRITE_TEMPERATURE)``, then
  return ``clean_output(raw, section_text)``.
"""
from __future__ import annotations

from typing import Any, Optional, Tuple

REWRITE_TEMPERATURE = 0.2
SYSTEM_PROMPT_FILE = "section_rewriter_system.txt"
USER_PROMPT_FILE = "section_rewriter_user.txt"


def render_prompts(query: str, section_text: str, page_title: str) -> Tuple[str, str]:
    raise NotImplementedError


def clean_output(raw: str, original: str) -> str:
    raise NotImplementedError


def rewrite_section(
    query: str,
    section_text: str,
    *,
    page_title: str,
    model: str,
    client: Optional[Any] = None,
) -> str:
    raise NotImplementedError
