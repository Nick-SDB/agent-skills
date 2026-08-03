from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILLCTL = ROOT / "tools" / "skillctl.py"


def run_skillctl(*arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SKILLCTL), *arguments],
        cwd=ROOT,
        check=False,
        text=True,
        capture_output=True,
    )


def tree_digest(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(candidate for candidate in root.rglob("*") if candidate.is_file()):
        digest.update(path.relative_to(root).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


class SkillCtlRenderTests(unittest.TestCase):
    def test_repository_validates(self) -> None:
        result = run_skillctl("validate")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("validated 11 skills and 3 targets", result.stdout)

    def test_render_is_repeatable_and_check_reports_no_diff(self) -> None:
        with tempfile.TemporaryDirectory() as temp_text:
            output = Path(temp_text) / "dist"
            first = run_skillctl("render", "--output", str(output))
            self.assertEqual(first.returncode, 0, first.stderr)
            first_digest = tree_digest(output)

            second = run_skillctl("render", "--output", str(output))
            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertEqual(tree_digest(output), first_digest)

            checked = run_skillctl("render", "--output", str(output), "--check")
            self.assertEqual(checked.returncode, 0, checked.stderr)
            self.assertEqual(tree_digest(output), first_digest)

    def test_target_selection_and_overlays(self) -> None:
        with tempfile.TemporaryDirectory() as temp_text:
            output = Path(temp_text) / "dist"
            result = run_skillctl("render", "--target", "codex", "--output", str(output))
            self.assertEqual(result.returncode, 0, result.stderr)

            manifest = json.loads((output / "codex" / "manifest.json").read_text())
            self.assertEqual(manifest["$schema"], "manifest.schema.json")
            self.assertEqual(manifest["target"], "codex")
            self.assertEqual(len(manifest["skills"]), 8)
            self.assertFalse((output / "codex" / "skills" / "cc-create-skill").exists())
            rendered = (output / "codex" / "skills" / "project-code-map" / "SKILL.md").read_text()
            self.assertIn("## Codex convention", rendered)
            self.assertNotIn("adapters/", "\n".join(manifest["skills"][0]["files"]))

    def test_check_detects_stale_output(self) -> None:
        with tempfile.TemporaryDirectory() as temp_text:
            output = Path(temp_text) / "dist"
            rendered = run_skillctl("render", "--target", "kimi", "--output", str(output))
            self.assertEqual(rendered.returncode, 0, rendered.stderr)
            skill_file = output / "kimi" / "skills" / "better-shit" / "SKILL.md"
            skill_file.write_text(skill_file.read_text() + "stale\n")

            checked = run_skillctl("render", "--target", "kimi", "--output", str(output), "--check")
            self.assertEqual(checked.returncode, 1)
            self.assertIn("content differs: skills/better-shit/SKILL.md", checked.stderr)


if __name__ == "__main__":
    unittest.main()
