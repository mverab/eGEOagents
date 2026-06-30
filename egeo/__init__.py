"""E-GEO runtime adapter layer and standalone ``egeo`` CLI.

This package decouples the four GEO agents (Analyzer, Ranker, Rewriter, Indexer)
from any single host runtime. The agent *contract* is defined once in
:mod:`egeo.agents`; concrete runtimes plug in implementations via
:mod:`egeo.runtimes`. The :mod:`egeo.cli` module exposes a runtime-agnostic
``egeo`` command (``optimize``, ``evaluate``, ``optimize-prompts``, ``runtimes``).

The Ranker and Rewriter agents intentionally *reuse* the existing
``geo_eval``/``llm_client`` modules at the repository root rather than
duplicating their logic. To make those root-level modules importable regardless
of the current working directory (e.g. ``python -m egeo`` from any folder), this
module bootstraps the repository root onto ``sys.path``.
"""
from __future__ import annotations

import sys
from pathlib import Path

__version__ = "2.0.0"

# Repository root = parent of this package directory. Adding it to sys.path lets
# ``import geo_eval`` / ``import llm_client`` succeed even when the CLI is run
# from outside the repo root or installed in editable mode.
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


def repo_root() -> Path:
    """Return the repository root that ships ``geo_eval``/``prompts``/``geo-output``."""
    return _REPO_ROOT


__all__ = ["__version__", "repo_root"]
