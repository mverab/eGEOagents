"""The E-GEO loop workspace: `$EGEO_HOME` resolution and idempotent bootstrap.

Loop *code* ships in this repository; loop *state* lives in a per-user workspace
outside it, so ``git pull`` can never clobber accumulated memory and private
data (SERP history, client domains) can never leak into a public fork. The
workspace layout is the substrate contract vendored at ``SUBSTRATE.md``::

    $EGEO_HOME/
    ├── LOG.md                        # append-only activity feed, one line per event
    ├── config.yaml                   # loop machinery: cadence, models, budgets
    ├── SUBSTRATE.md                  # the contract, copied at bootstrap
    ├── signals/<slug>.md             # kind: signal   (evidence, deduped)
    ├── docs/<slug>.md                # kind: doc      (durable knowledge)
    ├── data/<collector>/*.jsonl      # collector output (not artifacts)
    ├── domains/<loop>/README.md      # charter + Timeline
    └── prompts/*.txt                 # optimized prompt overrides

Everything that touches loop state — collectors, ``egeo loop``, and the
workspace-first prompt resolution in :mod:`geo_eval` — resolves paths through
this module, so there is exactly one definition of "where state lives".

Nothing here is required for one-shot mode: with no workspace on disk, ``/geo``
and ``egeo optimize`` behave exactly as before loop mode existed.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from . import repo_root

#: Environment variable that overrides the default workspace location.
HOME_ENV = "EGEO_HOME"

#: Workspace location used when :data:`HOME_ENV` is unset.
DEFAULT_HOME = "~/.egeo"

#: Directories created by :func:`bootstrap` (substrate layout + prompt overrides).
LAYOUT_DIRS = ("signals", "docs", "data", "domains", "prompts")

#: Domain that owns workspace machinery events (bootstrap, collector passes), so
#: every LOG.md line names an existing directory under ``domains/`` per SUBSTRATE.md 7.
MACHINERY_DOMAIN = "egeo-core"

CONFIG_NAME = "config.yaml"
LOG_NAME = "LOG.md"
SUBSTRATE_NAME = "SUBSTRATE.md"

_LOG_HEADER = """# LOG

<!--
Append-only activity feed for this E-GEO workspace: one line per event, oldest
first, so concurrent writers merge cleanly. Grammar (SUBSTRATE.md 7):

  <YYYY-MM-DDTHH:MMZ> [<domain>] <event>: <summary>

Summaries for completed units of work end in
outcome=<success|partial|failure|no-op>. Only lines matching that grammar are
valid; headings and comment blocks like this one are ignored by the parser.
-->
"""

_CORE_CHARTER = """# egeo-core

## Charter

Housekeeping loop for this E-GEO workspace itself. It owns workspace machinery
events (bootstrap, collector passes, doctor findings) so every `LOG.md` line has
a real domain, and it is where you record work about the loop rather than about
a site. Create one domain directory per site or client you optimize; keep this
one for the plumbing.

## Cadence

On demand — this domain has no scheduled agent run of its own.

## Current focus

Keep the workspace substrate valid (`egeo loop doctor` clean).

## Backlog

1. Add a domain for the first site to optimize (`domains/<site-slug>/README.md`).
2. Fill `collectors.serp.queries` and `collectors.page.urls` in `config.yaml`.
3. Schedule the collector and loop-run jobs.

## Timeline
"""

_CONFIG_TEMPLATE = """# E-GEO loop configuration. This file is yours: the repo never overwrites it.
# Paths are relative to this workspace ($EGEO_HOME).

# How often each trigger class is expected to run. Informational: the scheduler
# (Hermes cron, system cron, manual) is the source of truth; `egeo loop doctor`
# only checks these are sane.
cadence:
  collect_serp: daily
  collect_page: daily
  loop_run: weekly
  digest: weekly

# Models each component expects, so doctor can flag scheduler/env mismatches.
models:
  ranker: gpt-4o
  rewriter: gpt-4o
  meta: gpt-4o

# Hard caps. Collectors fail loudly rather than silently truncating.
budgets:
  queries_per_day: 50
  pages_per_day: 100

# Self-improvement autonomy. `never` means proposals are only ever applied by a
# human. Widening this is a deliberate one-line change.
reflect:
  auto_apply: never

# Weights used when the loop scores which unit of work to do next.
scaling:
  weights:
    freshness: 0.4
    frequency: 0.3
    impact: 0.3

# Collector inputs. Add your own queries and URLs.
collectors:
  serp:
    target_domain: example.com
    queries: []
  page:
    urls: []
"""


def resolve_home() -> Path:
    """Return the workspace path from ``$EGEO_HOME``, defaulting to ``~/.egeo``.

    The path is expanded and absolutised but not created; use :func:`bootstrap`
    for that. This is the single resolution point for the whole system.
    """
    raw = os.environ.get(HOME_ENV) or DEFAULT_HOME
    return Path(raw).expanduser().resolve()


def exists(home: Optional[Path] = None) -> bool:
    """True when a bootstrapped workspace is present (loop mode is enabled)."""
    home = home or resolve_home()
    return (home / LOG_NAME).is_file()


def prompts_dir(home: Optional[Path] = None) -> Path:
    """Path of the workspace prompt overrides (may not exist)."""
    return (home or resolve_home()) / "prompts"


def data_dir(collector: str, home: Optional[Path] = None) -> Path:
    """Path of a collector's JSONL stream directory (may not exist)."""
    return (home or resolve_home()) / "data" / collector


def domains_dir(home: Optional[Path] = None) -> Path:
    """Path of the domain charters directory (may not exist)."""
    return (home or resolve_home()) / "domains"


def domain_readme(domain: str, home: Optional[Path] = None) -> Path:
    """Path of a domain's charter README (may not exist)."""
    return domains_dir(home) / domain / "README.md"


def utc_stamp() -> str:
    """Now, as the minute-precision UTC timestamp required by SUBSTRATE.md 7."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")


def bootstrap(home: Optional[Path] = None) -> Dict[str, Any]:
    """Create the workspace layout if missing. Idempotent and non-destructive.

    Existing files are never rewritten, so a re-run over a populated workspace
    leaves every byte in place. Returns a summary with the resolved ``home``,
    whether this call created the workspace, and the relative paths created.
    """
    home = home or resolve_home()
    created: List[str] = []
    fresh = not (home / LOG_NAME).is_file()

    if not home.is_dir():
        home.mkdir(parents=True, exist_ok=True)
        created.append(".")
    for name in LAYOUT_DIRS:
        directory = home / name
        if not directory.is_dir():
            directory.mkdir(parents=True, exist_ok=True)
            created.append(f"{name}/")

    config = home / CONFIG_NAME
    if not config.is_file():
        config.write_text(_CONFIG_TEMPLATE, encoding="utf-8")
        created.append(CONFIG_NAME)

    substrate_src = repo_root() / SUBSTRATE_NAME
    substrate_dst = home / SUBSTRATE_NAME
    if not substrate_dst.is_file() and substrate_src.is_file():
        substrate_dst.write_text(substrate_src.read_text(encoding="utf-8"), encoding="utf-8")
        created.append(SUBSTRATE_NAME)

    charter = home / "domains" / MACHINERY_DOMAIN / "README.md"
    if not charter.is_file():
        charter.parent.mkdir(parents=True, exist_ok=True)
        charter.write_text(_CORE_CHARTER, encoding="utf-8")
        created.append(f"domains/{MACHINERY_DOMAIN}/README.md")

    log = home / LOG_NAME
    if not log.is_file():
        log.write_text(_LOG_HEADER, encoding="utf-8")
        created.append(LOG_NAME)

    if fresh:
        append_log(
            MACHINERY_DOMAIN,
            "bootstrap",
            f"created substrate layout at {home}, outcome=success",
            home=home,
        )

    return {"home": str(home), "bootstrapped": fresh, "created": created}


def append_log(domain: str, event: str, summary: str, home: Optional[Path] = None) -> str:
    """Append exactly one line to the workspace ``LOG.md`` and return it.

    ``domain`` must be a directory name under ``domains/`` (SUBSTRATE.md 7);
    machinery events that belong to no single loop use
    :data:`MACHINERY_DOMAIN`, whose charter is created at bootstrap.
    """
    home = home or resolve_home()
    log = home / LOG_NAME
    if not log.is_file():
        log.parent.mkdir(parents=True, exist_ok=True)
        log.write_text(_LOG_HEADER, encoding="utf-8")
    line = f"{utc_stamp()} [{domain}] {event}: {summary}"
    with log.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")
    return line


def load_config(home: Optional[Path] = None) -> Dict[str, Any]:
    """Parse the workspace ``config.yaml``.

    Uses PyYAML when importable (it is already a declared project dependency)
    and falls back to a small parser covering the documented config subset —
    nested mappings, scalars and inline/dash lists — so collectors keep working
    in a bare-stdlib environment. Raises ``FileNotFoundError`` when there is no
    config, and ``ValueError`` when it does not parse to a mapping.
    """
    home = home or resolve_home()
    path = home / CONFIG_NAME
    text = path.read_text(encoding="utf-8")  # FileNotFoundError is the honest error
    try:
        import yaml  # type: ignore
    except ImportError:
        data: Any = _parse_simple_yaml(text)
    else:
        data = yaml.safe_load(text)
    if data is None:
        data = {}
    if not isinstance(data, dict):
        raise ValueError(f"{path}: config must parse to a mapping, got {type(data).__name__}")
    return data


def config_get(config: Dict[str, Any], dotted: str, default: Any = None) -> Any:
    """Read ``a.b.c`` out of a parsed config, returning ``default`` if absent."""
    node: Any = config
    for part in dotted.split("."):
        if not isinstance(node, dict) or part not in node:
            return default
        node = node[part]
    return default if node is None else node


def _coerce(value: str) -> Any:
    value = value.strip()
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        return [_coerce(v) for v in inner.split(",") if v.strip()] if inner else []
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
        return value[1:-1]
    lowered = value.lower()
    if lowered in ("true", "false"):
        return lowered == "true"
    if lowered in ("null", "~", ""):
        return None
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        return value


def _parse_simple_yaml(text: str) -> Dict[str, Any]:
    """Parse the config subset documented in the template (no PyYAML needed).

    Supports nested mappings by indentation, scalars, inline lists and
    dash-prefixed list items. Anything richer requires PyYAML.
    """
    root: Dict[str, Any] = {}
    # Each frame is [indent, container, parent, key]: parent/key let an empty
    # mapping be replaced by a list the first time a dash item shows up under it.
    stack: List[List[Any]] = [[-1, root, None, None]]
    for raw in text.splitlines():
        line = raw.rstrip()
        if not line.strip() or line.strip().startswith("#"):
            continue
        line = line.split(" #", 1)[0].rstrip()
        indent = len(line) - len(line.lstrip())
        stripped = line.strip()
        while len(stack) > 1 and indent <= stack[-1][0]:
            stack.pop()
        frame = stack[-1]
        container = frame[1]

        if stripped.startswith("- "):
            if isinstance(container, dict) and not container and frame[2] is not None:
                container = []
                frame[1] = container
                frame[2][frame[3]] = container
            if isinstance(container, list):
                container.append(_coerce(stripped[2:]))
            continue

        if ":" not in stripped or not isinstance(container, dict):
            continue
        key, _, value = stripped.partition(":")
        key = key.strip()
        value = value.strip()
        if value == "":
            child: Dict[str, Any] = {}
            container[key] = child
            stack.append([indent, child, container, key])
        else:
            container[key] = _coerce(value)
    return root
