from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("skill_sources", ROOT / "tools/skill_sources.py")
SOURCES = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SOURCES)
COMMIT = "a" * 40


class ExternalSourceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "repo"
        shutil.copytree(ROOT, self.root, ignore=shutil.ignore_patterns(
            ".git", "dist", "release", "__pycache__", "*.pyc"))
        self.args = argparse.Namespace(
            repo="https://github.com/example/skills", path="skills/demo", ref="v2",
            license_path="LICENSE", license_id=None, category="general",
            targets=["codex", "claude-code", "kimi"],
        )
        self.upstream = {
            "skills/demo/SKILL.md": b"---\nname: demo\ndescription: A portable example.\nlicense: MIT\nallowed-tools: Bash\n---\n\n# Demo\n\nInspect changes.\n",
            "LICENSE": b"MIT License\n\nCopyright Example Authors\n",
        }
        self.requests = []
        self.blob_mode = "100644"
        self.truncated = False

    def registry(self):
        return json.loads((self.root / "registry.json").read_text())

    def fetch(self, url):
        self.requests.append(url)
        if "/commits/" in url:
            return json.dumps({"sha": COMMIT}).encode()
        if "/git/trees/" in url:
            tree = []
            for name, data in self.upstream.items():
                blob = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
                tree.append({"path": name, "type": "blob", "mode": self.blob_mode, "sha": blob})
            return json.dumps({"tree": tree, "truncated": self.truncated}).encode()
        prefix = "https://raw.githubusercontent.com/example/skills/" + COMMIT + "/"
        self.assertTrue(url.startswith(prefix), url)
        return self.upstream[url[len(prefix):]]

    def validate(self):
        result = subprocess.run(
            [sys.executable, str(self.root / "tools/skillctl.py"), "validate"],
            cwd=self.root, text=True, capture_output=True, timeout=20,
        )
        if result.returncode:
            raise SOURCES.SourceError(result.stderr)

    def import_demo(self):
        with patch.object(SOURCES, "fetch", side_effect=self.fetch):
            SOURCES.import_skill(self.root, self.registry(), self.args, self.validate)
        return self.root / "skills/general/demo"

    def test_import_pins_ref_records_hashes_normalizes_and_generates_citations(self):
        source = self.import_demo()
        data = SOURCES.metadata(source)
        self.assertEqual(data["commit"], COMMIT)
        self.assertEqual(data["requested_ref"], "v2")
        self.assertIsNone(data["upstream_version"])
        original = next(x for x in data["files"] if x["local_path"] == "SKILL.md")
        self.assertEqual(original["sha256"], SOURCES.digest(self.upstream["skills/demo/SKILL.md"]))
        self.assertNotEqual(original["sha256"], data["local_files"]["SKILL.md"])
        skill = (source / "SKILL.md").read_text()
        self.assertNotIn("allowed-tools:", skill)
        self.assertIn("Inspect changes.", skill)
        self.assertEqual((source / "references/LICENSE").read_bytes(), self.upstream["LICENSE"])
        self.assertIn("Not declared", (source / "references/upstream.md").read_text())
        self.assertIn("[demo]", (self.root / "README.md").read_text())
        self.assertEqual(SOURCES.validate(self.root, self.registry()), [])

    def test_invalid_import_rolls_back_and_preserves_existing_changes(self):
        readme = self.root / "README.md"
        readme.write_text(readme.read_text() + "\nUncommitted user note.\n")
        before = {p: (self.root / p).read_bytes() for p in ["README.md", "registry.json"]}
        self.upstream["skills/demo/SKILL.md"] += b"\n[Missing](missing.md)\n"
        with self.assertRaisesRegex(SOURCES.SourceError, "missing linked resource"):
            self.import_demo()
        self.assertFalse((self.root / "skills/general/demo").exists())
        for path, content in before.items():
            self.assertEqual((self.root / path).read_bytes(), content)

    def test_existing_skill_is_not_overwritten(self):
        source = self.import_demo()
        marker = source / "private.txt"
        marker.write_text("preserve")
        with self.assertRaisesRegex(SOURCES.SourceError, "already exists"):
            self.import_demo()
        self.assertEqual(marker.read_text(), "preserve")

    def test_incomplete_tree_symlinks_and_unsafe_paths_fail_without_import(self):
        self.truncated = True
        with self.assertRaisesRegex(SOURCES.SourceError, "truncated"):
            self.import_demo()
        self.truncated = False
        self.blob_mode = "120000"
        with self.assertRaisesRegex(SOURCES.SourceError, "symlinks"):
            self.import_demo()
        self.blob_mode = "100644"
        self.args.path = "../outside"
        with self.assertRaisesRegex(SOURCES.SourceError, "unsafe source path"):
            self.import_demo()
        self.assertFalse((self.root / "skills/general/demo").exists())

    def test_missing_license_declaration_is_not_guessed(self):
        self.upstream["skills/demo/SKILL.md"] = self.upstream["skills/demo/SKILL.md"].replace(b"license: MIT\n", b"")
        with self.assertRaisesRegex(SOURCES.SourceError, "license is not declared"):
            self.import_demo()
        self.args.license_id = "MIT"
        self.import_demo()

    def test_local_adaptation_requires_refresh_and_original_hashes_survive(self):
        source = self.import_demo()
        original = SOURCES.metadata(source)["files"]
        path = source / "SKILL.md"
        path.write_text(path.read_text() + "\nA reviewed local rule.\n")
        errors = SOURCES.validate(self.root, self.registry())
        self.assertTrue(any("local checksums differ" in e for e in errors))
        registry = self.registry()
        next(e for e in registry["skills"] if e["name"] == "demo")["version"] = "1.0.1"
        SOURCES.write_json(self.root / "registry.json", registry)
        SOURCES.provenance(self.root, registry, argparse.Namespace(
            check=False, refresh="demo", note="Added a reviewed local rule."))
        self.assertEqual(SOURCES.metadata(source)["files"], original)
        self.assertEqual(SOURCES.validate(self.root, registry), [])

    def test_license_tampering_cannot_be_accepted_by_refresh(self):
        source = self.import_demo()
        path = source / "references/LICENSE"
        path.write_text("changed copyright")
        with self.assertRaisesRegex(SOURCES.SourceError, "changed or missing upstream license"):
            SOURCES.provenance(self.root, self.registry(), argparse.Namespace(
                check=False, refresh="demo", note="Changed license."))

    def test_validation_detects_missing_origin_metadata_and_stale_citations(self):
        source = self.import_demo()
        readme = self.root / "README.md"
        readme.write_text(readme.read_text().replace("[demo]", "[wrong-name]"))
        self.assertTrue(any("table is stale" in e for e in SOURCES.validate(self.root, self.registry())))
        SOURCES.generate(self.root, self.registry())
        registry = self.registry()
        next(e for e in registry["skills"] if e["name"] == "demo").pop("origin")
        self.assertTrue(any("requires origin" in e for e in SOURCES.validate(self.root, registry)))
        (source / "references/upstream.json").unlink()
        self.assertTrue(any("missing or invalid" in e for e in SOURCES.validate(self.root, self.registry())))

    def test_full_sha_and_readonly_check_are_enforced(self):
        source = self.import_demo()
        before = {p: p.read_bytes() for p in source.rglob("*") if p.is_file()}
        SOURCES.provenance(self.root, self.registry(), argparse.Namespace(check=True, refresh=None, note=None))
        self.assertEqual(before, {p: p.read_bytes() for p in before})
        path = source / "references/upstream.json"
        data = SOURCES.metadata(source)
        data["commit"] = "main"
        SOURCES.write_json(path, data)
        self.assertTrue(any("full 40-character" in e for e in SOURCES.validate(self.root, self.registry())))


if __name__ == "__main__":
    unittest.main()
