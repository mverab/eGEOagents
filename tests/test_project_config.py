"""Tests for the portable project contract and legacy fallback."""
from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

from egeo import workspace


ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples" / "project.yaml"


class ProjectConfigTests(unittest.TestCase):
    def _workspace(self) -> Path:
        home = Path(tempfile.mkdtemp(prefix="egeo-project-test-"))
        shutil.copy(EXAMPLE, home / workspace.PROJECT_CONFIG_NAME)
        return home

    def test_example_contract_loads_and_summarizes(self) -> None:
        home = self._workspace()
        try:
            project = workspace.load_project_config(home)
            self.assertIsNotNone(project)
            summary = workspace.project_summary(project, home)
            self.assertEqual(summary["id"], "egeoagents")
            self.assertEqual(summary["active_queries"], 3)
            self.assertEqual(summary["active_pages"], 3)
            self.assertTrue(summary["validated"])
        finally:
            shutil.rmtree(home)

    def test_same_code_accepts_a_second_project_fixture(self) -> None:
        home = self._workspace()
        try:
            text = (home / workspace.PROJECT_CONFIG_NAME).read_text(encoding="utf-8")
            text = text.replace("egeoagents", "second-project").replace("E-GEO", "Second Project")
            text = text.replace("github.com/mverab/eGEOagents", "github.com/example/second-project")
            text = text.replace("second-project.com", "second.example.com")
            (home / workspace.PROJECT_CONFIG_NAME).write_text(text, encoding="utf-8")
            project = workspace.load_project_config(home)
            inputs = workspace.project_inputs(project, {"collectors": {"serp": {"queries": ["stale"]}}})
            self.assertEqual(inputs["source"], "project.yaml")
            self.assertEqual(inputs["target_domain"], "second.example.com")
            self.assertNotIn("stale", inputs["queries"])
        finally:
            shutil.rmtree(home)

    def test_legacy_config_fallback_is_explicit(self) -> None:
        home = Path(tempfile.mkdtemp(prefix="egeo-legacy-test-"))
        try:
            config = {"collectors": {"serp": {"queries": ["legacy query"], "target_domain": "legacy.example"}, "page": {"urls": ["https://legacy.example/"]}}}
            inputs = workspace.project_inputs(None, config)
            self.assertEqual(inputs["source"], "config.yaml (legacy fallback)")
            self.assertEqual(inputs["queries"], ["legacy query"])
            self.assertEqual(inputs["target_domain"], "legacy.example")
        finally:
            shutil.rmtree(home)

    def test_secret_key_is_rejected_without_echoing_value(self) -> None:
        project = {"schema_version": 1, "project": {"id": "safe", "name": "Safe", "repository": "https://github.com/example/safe", "canonical_domain": "safe.example", "canonical_url": "https://safe.example/", "language": "en"}, "api_key": "DO_NOT_PRINT", "pages": [], "queries": [], "measurement": {"engines": ["test"], "cadence": "weekly"}, "guardrails": {"no_duplicate_query_owners": True, "no_auto_publish_visible_copy": True, "no_fabricated_proof": True, "require_fresh_crawl_before_verdict": True}}
        errors = workspace.validate_project_config(project)
        rendered = " ".join(errors)
        self.assertIn("api_key", rendered)
        self.assertNotIn("DO_NOT_PRINT", rendered)

    def test_same_intent_cannot_have_two_canonical_owners(self) -> None:
        project = {"schema_version": 1, "project": {"id": "safe", "name": "Safe", "repository": "https://github.com/example/safe", "canonical_domain": "safe.example", "canonical_url": "https://safe.example/", "language": "en"}, "pages": [{"id": "page", "url": "https://safe.example/page", "active": True}], "queries": [{"id": "one", "text": "same", "class": "generic", "intent": "same", "target_pages": ["page"], "active": True}, {"id": "two", "text": "another", "class": "generic", "intent": "same", "target_pages": ["page"], "active": True}], "measurement": {"engines": ["test"], "cadence": "weekly"}, "guardrails": {"no_duplicate_query_owners": True, "no_auto_publish_visible_copy": True, "no_fabricated_proof": True, "require_fresh_crawl_before_verdict": True}}
        errors = workspace.validate_project_config(project)
        self.assertTrue(any("canonical ownership collision" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
