"""Contract tests for egeo.section_rewriter. Fake LLM client; never the network."""
from __future__ import annotations

from pathlib import Path

import pytest

import egeo
from egeo import section_rewriter as sr

SECTION = "## Tools\n\nE-GEO rewrites pages ([repo](https://github.com/mverab/eGEOagents)).\n\n"


class FakeLLM:
    def __init__(self, reply: str) -> None:
        self.reply, self.calls = reply, []

    def chat_text(self, **kwargs):
        self.calls.append(kwargs)
        return self.reply


def test_prompt_files_exist_in_repo_and_package() -> None:
    for name in (sr.SYSTEM_PROMPT_FILE, sr.USER_PROMPT_FILE):
        repo = Path(egeo.resource_root()) / "prompts" / name
        packaged = Path(egeo.__file__).parent / "resources" / "prompts" / name
        assert repo.read_bytes() == packaged.read_bytes()


def test_render_prompts() -> None:
    system, user = sr.render_prompts("best geo tools", SECTION, "GEO Tools 2026")
    assert "Keep the first line (the heading) exactly as it is" in system
    assert user.startswith("Query: best geo tools\nPage title: GEO Tools 2026\n")
    assert user.rstrip().endswith(SECTION.rstrip())


@pytest.mark.parametrize(
    "raw",
    [
        "## Tools\n\nBetter text.",
        "```markdown\n## Tools\n\nBetter text.\n```",
        "```md\n## Tools\n\nBetter text.\n```\n",
        "```\n## Tools\n\nBetter text.\n```",
        "\n\n  ## Tools\n\nBetter text.  \n\n",
    ],
)
def test_clean_output_strips_fences_and_keeps_original_trailing_whitespace(raw: str) -> None:
    assert sr.clean_output(raw, SECTION) == "## Tools\n\nBetter text.\n\n"


def test_rewrite_section_calls_llm(monkeypatch) -> None:
    monkeypatch.delenv("GEO_EVAL_MOCK", raising=False)
    fake = FakeLLM("```markdown\n## Tools\n\nE-GEO rewrites pages.\n```")
    out = sr.rewrite_section("q", SECTION, page_title="T", model="openai/gpt-4o", client=fake)
    assert out == "## Tools\n\nE-GEO rewrites pages.\n\n"
    call = fake.calls[0]
    assert call["model"] == "openai/gpt-4o" and call["temperature"] == sr.REWRITE_TEMPERATURE
    assert (call["system"], call["user"]) == sr.render_prompts("q", SECTION, "T")


@pytest.mark.parametrize("flag", ["1", "true", "YES"])
def test_mock_mode_returns_input_without_client(monkeypatch, flag: str) -> None:
    monkeypatch.setenv("GEO_EVAL_MOCK", flag)

    class Exploding:
        def chat_text(self, **kwargs):
            raise AssertionError("must not be called in mock mode")

    assert sr.rewrite_section("q", SECTION, page_title="T", model="m", client=Exploding()) == SECTION
