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
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

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
PROJECT_CONFIG_NAME = "project.yaml"
LOG_NAME = "LOG.md"
SUBSTRATE_NAME = "SUBSTRATE.md"
PROJECT_SCHEMA_VERSION = 1
_PROJECT_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
_SECRET_KEY_RE = re.compile(r"(?:api[_-]?key|secret|token|password|credential|private[_-]?key|oauth)", re.I)
_QUERY_CLASSES = {"branded", "generic", "commercial", "informational", "navigational", "other"}

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


def project_config_path(home: Optional[Path] = None) -> Path:
    """Return the active project's declarative contract path."""
    return (home or resolve_home()) / PROJECT_CONFIG_NAME


class ProjectConfigError(ValueError):
    """Raised when the portable project contract is absent or invalid."""


def _secret_paths(value: Any, path: str = "") -> List[str]:
    """Find credential-like keys without returning their values."""
    found: List[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}" if path else str(key)
            if _SECRET_KEY_RE.search(str(key)):
                found.append(child_path)
            else:
                found.extend(_secret_paths(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found.extend(_secret_paths(child, f"{path}[{index}]"))
    return found


def _normalized_domain(value: str) -> str:
    return (value or "").strip().lower().removeprefix("www.").rstrip(".")


def _is_http_url(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc) and not parsed.username and not parsed.password


def validate_project_config(data: Any) -> List[str]:
    """Return deterministic, value-safe validation errors for project.yaml."""
    errors: List[str] = []
    if not isinstance(data, dict):
        return ["root must be a mapping"]
    if data.get("schema_version") != PROJECT_SCHEMA_VERSION:
        errors.append(f"schema_version must be {PROJECT_SCHEMA_VERSION}")
    secret_paths = _secret_paths(data)
    if secret_paths:
        errors.append("credential-like keys are forbidden: " + ", ".join(secret_paths))

    project = data.get("project")
    if not isinstance(project, dict):
        errors.append("project must be a mapping")
        project = {}
    for key in ("id", "name", "repository", "canonical_domain", "canonical_url", "language"):
        if not str(project.get(key) or "").strip():
            errors.append(f"project.{key} is required")
    project_id = str(project.get("id") or "")
    if project_id and not _PROJECT_ID_RE.fullmatch(project_id):
        errors.append("project.id must use lowercase letters, digits, and hyphens")
    for key in ("repository", "canonical_url"):
        if project.get(key) and not _is_http_url(project.get(key)):
            errors.append(f"project.{key} must be an http(s) URL")
    canonical_url = str(project.get("canonical_url") or "")
    canonical_domain = _normalized_domain(str(project.get("canonical_domain") or ""))
    if canonical_url and canonical_domain and _normalized_domain(urlparse(canonical_url).hostname or "") != canonical_domain:
        errors.append("project.canonical_domain does not match project.canonical_url")

    pages = data.get("pages", [])
    if not isinstance(pages, list):
        errors.append("pages must be a list")
        pages = []
    page_ids: set[str] = set()
    page_urls: Dict[str, str] = {}
    for index, page in enumerate(pages):
        prefix = f"pages[{index}]"
        if not isinstance(page, dict):
            errors.append(f"{prefix} must be a mapping")
            continue
        page_id = str(page.get("id") or "")
        if not page_id:
            errors.append(f"{prefix}.id is required")
        elif page_id in page_ids:
            errors.append(f"duplicate page id: {page_id}")
        else:
            page_ids.add(page_id)
        url = page.get("url")
        if not _is_http_url(url):
            errors.append(f"{prefix}.url must be an http(s) URL")
        elif bool(page.get("active", True)):
            normalized_url = str(url).split("#", 1)[0].rstrip("/") or "/"
            if normalized_url in page_urls:
                errors.append(f"duplicate active page URL: {page_urls[normalized_url]} and {page_id}")
            else:
                page_urls[normalized_url] = page_id

    queries = data.get("queries", [])
    if not isinstance(queries, list):
        errors.append("queries must be a list")
        queries = []
    query_ids: set[str] = set()
    ownership: Dict[tuple[str, str], List[tuple[str, str]]] = {}
    for index, query in enumerate(queries):
        prefix = f"queries[{index}]"
        if not isinstance(query, dict):
            errors.append(f"{prefix} must be a mapping")
            continue
        query_id = str(query.get("id") or "")
        if not query_id:
            errors.append(f"{prefix}.id is required")
        elif query_id in query_ids:
            errors.append(f"duplicate query id: {query_id}")
        else:
            query_ids.add(query_id)
        active = bool(query.get("active", True))
        text = str(query.get("text") or "").strip()
        if active and not text:
            errors.append(f"{prefix}.text is required for active queries")
        query_class = str(query.get("class") or "").strip().lower()
        if active and query_class not in _QUERY_CLASSES:
            errors.append(f"{prefix}.class must be one of {sorted(_QUERY_CLASSES)}")
        target_pages = query.get("target_pages", [])
        if not isinstance(target_pages, list) or any(not isinstance(item, str) for item in target_pages):
            errors.append(f"{prefix}.target_pages must be a list of page IDs")
            target_pages = []
        for page_id in target_pages:
            if page_id not in page_ids:
                errors.append(f"{prefix}.target_pages references unknown page: {page_id}")
            if active and query.get("intent"):
                ownership.setdefault((page_id, str(query.get("intent"))), []).append(
                    (query_id, str(query.get("experiment") or ""))
                )
    for (page_id, intent), owners in ownership.items():
        if len(owners) > 1 and not all(experiment for _, experiment in owners):
            errors.append(f"canonical ownership collision: page {page_id!r}, intent {intent!r}, queries {[query_id for query_id, _ in owners]}")

    measurement = data.get("measurement")
    if not isinstance(measurement, dict):
        errors.append("measurement must be a mapping")
    else:
        engines = measurement.get("engines")
        if not isinstance(engines, list) or not engines or any(not isinstance(engine, str) or not engine.strip() for engine in engines):
            errors.append("measurement.engines must be a non-empty list of names")
        if not str(measurement.get("cadence") or "").strip():
            errors.append("measurement.cadence is required")

    guardrails = data.get("guardrails")
    required_guardrails = ("no_duplicate_query_owners", "no_auto_publish_visible_copy", "no_fabricated_proof", "require_fresh_crawl_before_verdict")
    if not isinstance(guardrails, dict):
        errors.append("guardrails must be a mapping")
    else:
        for key in required_guardrails:
            if guardrails.get(key) is not True:
                errors.append(f"guardrails.{key} must be true")
    return errors


def load_project_config(home: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    """Load and strictly validate optional ``project.yaml``.

    ``None`` means the workspace is legacy and still uses config.yaml project
    fields. An invalid file raises ``ProjectConfigError`` and never falls back.
    """
    path = project_config_path(home)
    if not path.is_file():
        return None
    try:
        import yaml  # type: ignore
    except ImportError as exc:
        raise ProjectConfigError(f"{path}: PyYAML is required to parse project.yaml") from exc
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise ProjectConfigError(f"{path}: cannot parse YAML: {exc}") from exc
    errors = validate_project_config(data)
    if errors:
        raise ProjectConfigError(f"{path}: " + "; ".join(errors))
    return data


def project_summary(project: Optional[Dict[str, Any]], home: Optional[Path] = None) -> Dict[str, Any]:
    """Return safe, machine-readable project status for doctor and run plans."""
    if not project:
        return {
            "id": None,
            "canonical_domain": None,
            "config_source": "config.yaml (legacy fallback)",
            "active_queries": 0,
            "active_pages": 0,
            "validated": False,
        }
    return {
        "id": project["project"]["id"],
        "canonical_domain": project["project"]["canonical_domain"],
        "config_source": str(project_config_path(home)),
        "active_queries": sum(1 for query in project.get("queries", []) if query.get("active", True)),
        "active_pages": sum(1 for page in project.get("pages", []) if page.get("active", True)),
        "validated": True,
    }


def project_inputs(project: Optional[Dict[str, Any]], config: Dict[str, Any]) -> Dict[str, Any]:
    """Resolve project-specific collector inputs with explicit legacy fallback."""
    if project:
        active_queries = [query["text"] for query in project.get("queries", []) if query.get("active", True)]
        active_pages = [page["url"] for page in project.get("pages", []) if page.get("active", True)]
        return {
            "queries": active_queries,
            "urls": active_pages,
            "target_domain": project["project"]["canonical_domain"],
            "source": PROJECT_CONFIG_NAME,
        }
    return {
        "queries": list(config_get(config, "collectors.serp.queries", []) or []),
        "urls": list(config_get(config, "collectors.page.urls", []) or []),
        "target_domain": str(config_get(config, "collectors.serp.target_domain", "") or ""),
        "source": CONFIG_NAME + " (legacy fallback)",
    }


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
