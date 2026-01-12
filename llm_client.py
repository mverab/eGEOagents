import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


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


def get_client() -> OpenAICompatibleClient:
    return OpenAICompatibleClient.from_env()
