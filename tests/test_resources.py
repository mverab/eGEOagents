"""Packaged runtime resources: resolution and drift guard.

The wheel must be self-contained: ``prompts/``, ``collectors/``, ``SUBSTRATE.md``
and ``examples/project.yaml`` ship under ``egeo/resources/`` so an installed
package works outside the repository tree. In a source checkout the repo-root
copies stay canonical; the packaged copies are byte-identical duplicates and
these tests fail if the two drift apart.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

import egeo

REPO_ROOT = Path(__file__).resolve().parent.parent
PACKAGED = REPO_ROOT / "egeo" / "resources"

RESOURCE_FILES = [
    "prompts/ranker_system.txt",
    "prompts/ranker_user.txt",
    "prompts/rewriter_system.txt",
    "prompts/rewriter_user.txt",
    "prompts/meta_optimizer_system.txt",
    "prompts/meta_optimizer_user.txt",
    "prompts/section_rewriter_system.txt",
    "prompts/section_rewriter_user.txt",
    "collectors/_common.py",
    "collectors/serp.py",
    "collectors/page.py",
    "collectors/README.md",
    "collectors/fixtures/serp_brave_response.json",
    "collectors/fixtures/serp_serpbase_response.json",
    "SUBSTRATE.md",
    "examples/project.yaml",
    "geo-output/schema/Article.json",
    "geo-output/schema/FAQPage.json",
    "geo-output/schema/Organization.json",
    "geo-output/schema/Product.json",
    "geo-output/schema/Service.json",
]


class ResourceRootTests(unittest.TestCase):
    def test_resource_root_prefers_repo_tree(self) -> None:
        root = egeo.resource_root()
        self.assertEqual(root, REPO_ROOT)
        self.assertTrue((root / "prompts" / "ranker_system.txt").is_file())

    def test_resource_root_falls_back_to_packaged_resources(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(egeo, "_REPO_ROOT", Path(tmp)):
                root = egeo.resource_root()
        self.assertEqual(root, PACKAGED)
        self.assertTrue((root / "prompts" / "ranker_system.txt").is_file())
        self.assertTrue((root / "SUBSTRATE.md").is_file())

    def test_load_collector_works_from_packaged_resources(self) -> None:
        from egeo import loop

        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(egeo, "_REPO_ROOT", Path(tmp)):
                module = loop.load_collector("serp")
        self.assertTrue(hasattr(module, "main") or hasattr(module, "run"))

    def test_cli_default_prompts_dir_resolves(self) -> None:
        from egeo import cli

        self.assertTrue((Path(cli._DEFAULT_PROMPTS) / "ranker_system.txt").is_file())

    def test_geo_eval_default_prompts_dir_resolves(self) -> None:
        import subprocess
        import sys

        out = subprocess.run(
            [sys.executable, "geo_eval.py", "evaluate", "--help"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(out.returncode, 0, out.stderr)


class RuntimeRootOverrideTests(unittest.TestCase):
    def test_explicit_root_controls_prompts_and_schema_dirs(self) -> None:
        from egeo import runtimes

        with tempfile.TemporaryDirectory() as tmp:
            custom = Path(tmp)
            (custom / "prompts").mkdir()
            (custom / "prompts" / "ranker_system.txt").write_text("custom", encoding="utf-8")
            runtime = runtimes.PythonRuntime(root=custom)
            self.assertEqual(runtime.prompts_dir, custom / "prompts")
            self.assertEqual(runtime.schema_dir, custom / "geo-output" / "schema")

    def test_default_root_uses_resource_root(self) -> None:
        from egeo import runtimes

        runtime = runtimes.PythonRuntime()
        self.assertEqual(runtime.prompts_dir, egeo.resource_root() / "prompts")


class DriftGuardTests(unittest.TestCase):
    def test_packaged_copies_match_repo_canonical_files(self) -> None:
        mismatches = []
        pairs = [(rel, rel) for rel in RESOURCE_FILES]
        for canonical_rel, packaged_rel in pairs:
            canonical = REPO_ROOT / canonical_rel
            packaged = PACKAGED / packaged_rel
            if not packaged.is_file():
                mismatches.append(f"missing packaged copy: {packaged_rel}")
            elif canonical.read_bytes() != packaged.read_bytes():
                mismatches.append(f"drifted: {canonical_rel} vs {packaged_rel}")
        self.assertEqual(mismatches, [])


if __name__ == "__main__":
    unittest.main()
