import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


class LLMError(RuntimeError):
    pass


def _extract_json_object(text: str) -> Dict[str, Any]:
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise LLMError("Model did not return a JSON object")
    snippet = text[start : end + 1]
    try:
        return json.loads(snippet)
    except json.JSONDecodeError as e:
        raise LLMError(f"Failed to parse JSON: {e}") from e


@dataclass
class OpenAICompatibleConfig:
    api_key: str
    base_url: str = "https://api.openai.com/v1"
    timeout_seconds: int = 120


class OpenAICompatibleClient:
    def __init__(self, config: OpenAICompatibleConfig):
        self._config = config

    @staticmethod
    def from_env() -> "OpenAICompatibleClient":
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise LLMError("Missing OPENAI_API_KEY")
        base_url = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
        timeout_seconds = int(os.environ.get("OPENAI_TIMEOUT_SECONDS", "120"))
        return OpenAICompatibleClient(
            OpenAICompatibleConfig(api_key=api_key, base_url=base_url, timeout_seconds=timeout_seconds)
        )

    def chat_text(
        self,
        *,
        model: str,
        system: str,
        user: str,
        temperature: float = 0.0,
        max_tokens: Optional[int] = None,
        max_retries: int = 3,
    ) -> str:
        url = f"{self._config.base_url.rstrip('/')}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self._config.api_key}",
            "Content-Type": "application/json",
        }
        payload: Dict[str, Any] = {
            "model": model,
            "temperature": temperature,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens

        body = json.dumps(payload).encode("utf-8")

        last_err: Optional[Exception] = None
        for attempt in range(max_retries):
            try:
                req = urllib.request.Request(url, data=body, headers=headers, method="POST")
                with urllib.request.urlopen(req, timeout=self._config.timeout_seconds) as resp:
                    raw = resp.read().decode("utf-8", errors="replace")
                data = json.loads(raw)
                return data["choices"][0]["message"]["content"]
            except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, KeyError, json.JSONDecodeError) as e:
                last_err = e
                if attempt < max_retries - 1:
                    time.sleep(1.5 * (attempt + 1))
                    continue
                break

        raise LLMError(f"Chat request failed: {last_err}")

    def chat_json(
        self,
        *,
        model: str,
        system: str,
        user: str,
        temperature: float = 0.0,
        max_tokens: Optional[int] = None,
        max_retries: int = 3,
    ) -> Dict[str, Any]:
        text = self.chat_text(
            model=model,
            system=system,
            user=user,
            temperature=temperature,
            max_tokens=max_tokens,
            max_retries=max_retries,
        )
        return _extract_json_object(text)


class MockClient:
    """Deterministic, offline LLM client for CI smoke tests and local development.

    Enabled via the ``GEO_EVAL_MOCK=1`` environment variable. It never performs
    network calls. Instead, it inspects the system prompt to decide which role it
    is playing (ranker, rewriter, or meta-optimizer) and returns a deterministic
    JSON object that matches the schema each prompt expects.

    The behaviour is intentionally simple but produces a *non-trivial, positive*
    signal so that smoke tests exercise the full evaluate/optimize code paths:
      - The ranker scores candidates by description length plus a bonus when the
        description contains the "Best for" intent marker.
      - The rewriter prepends a "Best for ..." line and appends a scannable
        closing line, so a rewritten candidate reliably ranks higher than its
        original, yielding a positive ``avg_rank_improvement``.
      - The meta-optimizer returns a lightly-augmented version of the current
        prompt so optimize() converges deterministically.
    """

    BEST_FOR_MARKER = "Best for"

    def chat_text(self, *, model: str, system: str, user: str, **_: Any) -> str:
        return json.dumps(self.chat_json(model=model, system=system, user=user))

    def chat_json(self, *, model: str, system: str, user: str, **_: Any) -> Dict[str, Any]:
        role = (system or "").lower()
        # Order matters: the meta-optimizer system prompt also mentions "rewriting",
        # so it must be checked before the rewriter branch.
        if "meta-optimizer" in role or "new_prompt" in role:
            return {"new_prompt": self._meta(user), "rationale": "mock-deterministic"}
        if "re-ranking" in role or "ordered_ids" in role:
            return {"ordered_ids": self._rank(user), "notes": "mock-deterministic"}
        if "rewrit" in role:
            return {"rewritten_description": self._rewrite(user)}
        # Fallback: fail loudly rather than hang or return an off-schema object.
        raise LLMError("MockClient could not infer role from system prompt")

    # --- role implementations -------------------------------------------------

    @staticmethod
    def _parse_candidates(user: str) -> List[Dict[str, str]]:
        """Parse the rendered candidate block produced by geo_eval._format_candidates."""
        candidates: List[Dict[str, str]] = []
        current: Optional[Dict[str, Any]] = None
        mode: Optional[str] = None
        for raw in user.splitlines():
            stripped = raw.strip()
            if stripped.startswith("- id:"):
                if current is not None:
                    current["description"] = "\n".join(current["description"]).strip()
                    candidates.append(current)  # type: ignore[arg-type]
                current = {"id": stripped[len("- id:"):].strip(), "title": "", "description": []}
                mode = None
            elif current is not None and stripped.startswith("title:"):
                current["title"] = stripped[len("title:"):].strip()
                mode = None
            elif current is not None and stripped.startswith("description:"):
                mode = "description"
            elif current is not None and mode == "description":
                current["description"].append(raw)
        if current is not None:
            current["description"] = "\n".join(current["description"]).strip()
            candidates.append(current)  # type: ignore[arg-type]
        return candidates

    def _rank(self, user: str) -> List[str]:
        candidates = self._parse_candidates(user)

        def score(c: Dict[str, str]) -> Tuple[int, int, str]:
            desc = c.get("description", "") or ""
            bonus = 1 if self.BEST_FOR_MARKER.lower() in desc.lower() else 0
            # Higher score ranks first: prefer intent marker, then richer content.
            return (bonus, len(desc), c["id"])

        ordered = sorted(candidates, key=score, reverse=True)
        return [c["id"] for c in ordered]

    def _rewrite(self, user: str) -> str:
        # Extract the original description following the "Description:" label.
        desc_lines: List[str] = []
        capture = False
        for line in user.splitlines():
            if line.strip().lower().startswith("description:"):
                capture = True
                continue
            if capture:
                if line.strip().lower().startswith("return only json"):
                    break
                desc_lines.append(line)
        original = "\n".join(desc_lines).strip() or "Product details."
        return (
            f"{self.BEST_FOR_MARKER} buyers who want a clear, reliable choice. "
            f"{original} "
            "Key specs are easy to scan, with differentiated value over typical alternatives."
        )

    @staticmethod
    def _meta(user: str) -> str:
        marker = "{{current_prompt}}"
        # The meta_optimizer_user template embeds the current prompt verbatim.
        current = ""
        if marker not in user:
            # Heuristic: take the largest block as the current prompt.
            current = user
        return (
            (current or "Rewrite the product description to maximize ranking in AI recommendations.")
            + "\n\nAlways lead with a concise 'Best for ...' intent line and keep specs scannable."
        )


def get_client() -> Any:
    """Return an LLM client.

    When ``GEO_EVAL_MOCK`` is truthy (``1``/``true``/``yes``), a fully offline,
    deterministic :class:`MockClient` is returned so evaluation can run in CI
    without API keys or network access. Otherwise the real OpenAI-compatible
    client is constructed from environment variables.
    """
    flag = os.environ.get("GEO_EVAL_MOCK", "").strip().lower()
    if flag in {"1", "true", "yes", "on"}:
        return MockClient()
    return OpenAICompatibleClient.from_env()
