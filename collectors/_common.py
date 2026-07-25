"""Shared plumbing for collectors: paths, slugs, JSONL appends, HTTP, LOG lines.

Standard library only, in the style of ``llm_client.py``. Everything that writes
goes through :mod:`egeo.workspace`, so ``$EGEO_HOME`` is resolved in exactly one
place. See ``collectors/README.md`` for the contract these helpers exist to make
easy to honor.
"""
from __future__ import annotations

import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

# Allow ``python collectors/serp.py`` from anywhere: the repo root ships the
# ``egeo`` package this module depends on.
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from egeo import workspace  # noqa: E402  (after the sys.path bootstrap above)

USER_AGENT = "egeo-collector/2.0 (+https://github.com/mverab/eGEOagents)"


class CollectorError(RuntimeError):
    """Hard failure: the pass must exit non-zero and write no partial record."""


def slugify(value: str, max_length: int = 60) -> str:
    """Kebab-case, filesystem-safe stream name for a query or URL."""
    value = re.sub(r"^https?://", "", value.strip().lower())
    value = re.sub(r"[^a-z0-9]+", "-", value).strip("-")
    return (value[:max_length].rstrip("-") or "untitled")


def stream_path(collector: str, stream: str, home: Optional[Path] = None) -> Path:
    """Path of ``data/<collector>/<stream>.jsonl``, creating the directory."""
    directory = workspace.data_dir(collector, home)
    directory.mkdir(parents=True, exist_ok=True)
    return directory / f"{stream}.jsonl"


def append_record(path: Path, record: Dict[str, Any]) -> None:
    """Append exactly one JSON object as one line. Never rewrites the file."""
    line = json.dumps(record, ensure_ascii=False, sort_keys=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")


def read_records(path: Path) -> List[Dict[str, Any]]:
    """Read a JSONL stream, skipping blank lines. Missing file → empty list."""
    if not path.is_file():
        return []
    records: List[Dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            records.append(json.loads(line))
    return records


def count_today(paths: Iterable[Path], today: str) -> int:
    """How many records in these streams carry a ``ts`` on ``today`` (UTC date)."""
    total = 0
    for path in paths:
        for record in read_records(path):
            if str(record.get("ts", "")).startswith(today):
                total += 1
    return total


def log_pass(collector: str, summary: str, home: Optional[Path] = None) -> str:
    """Append the collector's single LOG.md line for this pass."""
    return workspace.append_log(workspace.MACHINERY_DOMAIN, f"collect-{collector}", summary, home=home)


def http_get(url: str, headers: Optional[Dict[str, str]] = None, timeout: int = 30):
    """GET a URL with stdlib urllib. Returns ``(status, body_text)``.

    Raises :class:`CollectorError` on transport failure. HTTP error responses are
    returned with their status so the caller decides whether they are fatal.
    """
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, **(headers or {})})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            charset = response.headers.get_content_charset() or "utf-8"
            return response.status, response.read().decode(charset, errors="replace")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
        return exc.code, body
    except urllib.error.URLError as exc:
        raise CollectorError(f"network failure for {url}: {exc.reason}") from exc
    except OSError as exc:  # timeouts, DNS, TLS
        raise CollectorError(f"network failure for {url}: {exc}") from exc


def ensure_workspace(home: Optional[Path] = None) -> Path:
    """Resolve and bootstrap the workspace, returning its path."""
    resolved = home or workspace.resolve_home()
    workspace.bootstrap(resolved)
    return resolved


def fail(message: str) -> int:
    """Print an actionable error to stderr and return the exit status."""
    print(f"ERROR: {message}", file=sys.stderr)
    return 1
