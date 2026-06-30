"""Runtime adapter layer.

The four-agent contract (Analyzer, Ranker, Rewriter, Indexer) is defined once in
:mod:`egeo.agents`. This module lets multiple *runtimes* supply implementations
of that contract:

- :class:`PythonRuntime` (``python`` / ``cli``) runs the agents in-process using
  ``llm_client.get_client()`` and the ``prompts/`` templates. This is the
  runtime the standalone ``egeo`` CLI uses.
- :class:`ClaudeCodeRuntime` (``claude-code``) is a *descriptor*: it maps each
  agent to its ``.claude/agents/*.md`` definition and slash command. Claude Code
  itself executes those; attempting to run them in-process raises a clear error.

A tiny registry (:func:`get_runtime`, :func:`list_runtimes`) exposes the known
runtimes to the CLI (``egeo runtimes``).
"""
from __future__ import annotations

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from . import repo_root
from .agents import Analyzer, Indexer, Ranker, Rewriter

__all__ = [
    "RuntimeAdapter",
    "PythonRuntime",
    "ClaudeCodeRuntime",
    "RuntimeUnsupportedError",
    "RuntimeInfo",
    "get_runtime",
    "list_runtimes",
    "runtime_status",
]


class RuntimeUnsupportedError(RuntimeError):
    """Raised when an agent cannot be executed in-process by a given runtime."""


@dataclass
class RuntimeInfo:
    name: str
    aliases: List[str]
    description: str
    available: bool
    executes_in_process: bool


class RuntimeAdapter(ABC):
    """Contract every runtime adapter implements.

    A runtime is a factory for the four agents plus metadata used by
    ``egeo runtimes``. Concrete runtimes either execute the agents in-process
    (``executes_in_process = True``) or merely describe how a host runtime runs
    them (``executes_in_process = False``).
    """

    name: str = "base"
    aliases: List[str] = []
    description: str = ""
    executes_in_process: bool = False

    def __init__(self, *, root: Optional[Path] = None):
        self.root = root or repo_root()

    # --- discovery ---------------------------------------------------------- #

    @abstractmethod
    def available(self) -> bool:
        """Whether this runtime can be used in the current environment."""

    def info(self) -> RuntimeInfo:
        return RuntimeInfo(
            name=self.name,
            aliases=list(self.aliases),
            description=self.description,
            available=self.available(),
            executes_in_process=self.executes_in_process,
        )

    # --- agent factories ---------------------------------------------------- #

    @abstractmethod
    def make_analyzer(self) -> Analyzer: ...

    @abstractmethod
    def make_ranker(self) -> Ranker: ...

    @abstractmethod
    def make_rewriter(self) -> Rewriter: ...

    @abstractmethod
    def make_indexer(self) -> Indexer: ...


class PythonRuntime(RuntimeAdapter):
    """In-process runtime backed by ``llm_client`` and the ``prompts/`` templates.

    The Ranker and Rewriter use the client returned by ``llm_client.get_client()``
    — which honors ``GEO_EVAL_MOCK=1`` — so this runtime works fully offline in
    CI. The Analyzer and Indexer are deterministic and never touch the network.
    """

    name = "python"
    aliases = ["cli", "local"]
    description = "In-process Python runtime used by the `egeo` CLI (honors GEO_EVAL_MOCK)."
    executes_in_process = True

    def __init__(
        self,
        *,
        root: Optional[Path] = None,
        ranker_model: Optional[str] = None,
        rewriter_model: Optional[str] = None,
        temperature: float = 0.0,
    ):
        super().__init__(root=root)
        self.prompts_dir = self.root / "prompts"
        self.schema_dir = self.root / "geo-output" / "schema"
        self.ranker_model = ranker_model or os.environ.get("RANKER_MODEL", "gpt-4o")
        self.rewriter_model = rewriter_model or os.environ.get("REWRITER_MODEL", "gpt-4o")
        self.temperature = temperature

    def available(self) -> bool:
        return self.prompts_dir.is_dir()

    def _client(self) -> Any:
        # Imported lazily so the package can be imported without configuring a
        # client (e.g. for `egeo runtimes`).
        import llm_client

        return llm_client.get_client()

    def make_analyzer(self) -> Analyzer:
        return Analyzer()

    def make_ranker(self) -> Ranker:
        return Ranker(
            client=self._client(),
            model=self.ranker_model,
            prompts_dir=self.prompts_dir,
            temperature=self.temperature,
        )

    def make_rewriter(self) -> Rewriter:
        return Rewriter(
            client=self._client(),
            model=self.rewriter_model,
            prompts_dir=self.prompts_dir,
            temperature=self.temperature,
        )

    def make_indexer(self) -> Indexer:
        return Indexer(schema_dir=self.schema_dir)


class ClaudeCodeRuntime(RuntimeAdapter):
    """Descriptor adapter for the Claude Code host.

    Claude Code executes the agents from their ``.claude/agents/*.md``
    definitions via slash commands (``/geo``, ``/geo:audit`` ...). Python cannot
    drive Claude Code, so the agent factories raise a helpful error pointing the
    user at the slash-command entry point. This adapter exists to (a) make the
    runtime discoverable via ``egeo runtimes`` and (b) document the mapping
    between the contract and the Claude Code artifacts.
    """

    name = "claude-code"
    aliases = ["claude"]
    description = "Claude Code host runtime (executes .claude/ agents via /geo slash commands)."
    executes_in_process = False

    #: Maps each agent to its Claude Code definition + the slash command that runs it.
    AGENT_MAP: Dict[str, Dict[str, str]] = {
        "analyzer": {"definition": ".claude/agents/geo-analyzer.md", "command": "/geo:audit"},
        "ranker": {"definition": ".claude/agents/geo-ranker.md", "command": "/geo"},
        "rewriter": {"definition": ".claude/agents/geo-rewriter.md", "command": "/geo:optimize"},
        "indexer": {"definition": ".claude/agents/geo-indexer.md", "command": "/geo"},
    }

    def available(self) -> bool:
        return (self.root / ".claude").is_dir()

    def _unsupported(self, agent: str) -> "RuntimeUnsupportedError":
        meta = self.AGENT_MAP[agent]
        return RuntimeUnsupportedError(
            f"The '{self.name}' runtime does not execute the {agent} agent in-process. "
            f"Run it inside Claude Code using '{meta['command']}' "
            f"(definition: {meta['definition']}). For an in-process pipeline use the "
            f"'python' runtime, e.g. `egeo optimize <file>`."
        )

    def make_analyzer(self) -> Analyzer:
        raise self._unsupported("analyzer")

    def make_ranker(self) -> Ranker:
        raise self._unsupported("ranker")

    def make_rewriter(self) -> Rewriter:
        raise self._unsupported("rewriter")

    def make_indexer(self) -> Indexer:
        raise self._unsupported("indexer")


# --------------------------------------------------------------------------- #
# Registry
# --------------------------------------------------------------------------- #

_RUNTIME_CLASSES = [PythonRuntime, ClaudeCodeRuntime]


def _resolve_class(name: str):
    key = (name or "").strip().lower()
    for cls in _RUNTIME_CLASSES:
        if key == cls.name or key in cls.aliases:
            return cls
    raise ValueError(
        f"Unknown runtime '{name}'. Known: "
        + ", ".join(c.name for c in _RUNTIME_CLASSES)
    )


def get_runtime(name: str = "python", **kwargs: Any) -> RuntimeAdapter:
    """Return a runtime adapter by name or alias (default: ``python``)."""
    cls = _resolve_class(name)
    return cls(**kwargs)


def list_runtimes(**kwargs: Any) -> List[RuntimeAdapter]:
    """Instantiate every known runtime adapter."""
    return [cls(**kwargs) for cls in _RUNTIME_CLASSES]


def runtime_status(**kwargs: Any) -> List[RuntimeInfo]:
    """Return :class:`RuntimeInfo` for every known runtime (used by ``egeo runtimes``)."""
    return [rt.info() for rt in list_runtimes(**kwargs)]
