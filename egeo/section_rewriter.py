"""LLM rewrite of ONE section for section-mode ``fix-gaps``.

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


import os as _os
from pathlib import Path as _Path


def _prompt(name):
    import egeo
    return (_Path(egeo.resource_root()) / "prompts" / name).read_text(encoding="utf-8")


def render_prompts(query, section_text, page_title):
    return _prompt(SYSTEM_PROMPT_FILE), _prompt(USER_PROMPT_FILE).format(query=query, page_title=page_title, section=section_text)


def clean_output(raw, original):
    t = raw.strip()
    lines = t.split("\n")
    if len(lines) >= 2 and lines[0].strip().startswith("```") and lines[-1].strip() == "```":
        t = "\n".join(lines[1:-1])
    t = t.strip()
    return t + original[len(original.rstrip()):]


def rewrite_section(query, section_text, *, page_title, model, client=None):
    if (_os.environ.get("GEO_EVAL_MOCK") or "").strip().lower() in {"1", "true", "yes"}:
        return section_text
    if client is None:
        import llm_client
        client = llm_client.get_client()
    system, user = render_prompts(query, section_text, page_title)
    raw = client.chat_text(model=model, system=system, user=user, temperature=REWRITE_TEMPERATURE)
    return clean_output(raw, section_text)
