from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from collections.abc import Callable
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILLCTL = ROOT / "tools" / "skillctl.py"
COMMAND_TIMEOUT_SECONDS = 30


def run_skillctl(*arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SKILLCTL), *arguments],
        cwd=ROOT,
        check=False,
        text=True,
        capture_output=True,
        timeout=COMMAND_TIMEOUT_SECONDS,
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
        self.assertIn("validated 16 skills and 3 targets", result.stdout)

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
            self.assertEqual(len(manifest["skills"]), 13)
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

    def test_check_rejects_symlinked_output_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_text:
            root = Path(temp_text)
            output = root / "dist"
            rendered = run_skillctl("render", "--target", "codex", "--output", str(output))
            self.assertEqual(rendered.returncode, 0, rendered.stderr)
            skill_file = output / "codex" / "skills" / "better-shit" / "SKILL.md"
            external_file = root / "external-skill.md"
            external_file.write_bytes(skill_file.read_bytes())
            skill_file.unlink()
            skill_file.symlink_to(external_file)

            checked = run_skillctl(
                "render", "--target", "codex", "--output", str(output), "--check"
            )

            self.assertEqual(checked.returncode, 1)
            self.assertIn(
                "unexpected symlink: skills/better-shit/SKILL.md", checked.stderr
            )


class RepositoryLintTests(unittest.TestCase):
    def assert_lint_rejects(self, mutation: Callable[[Path], None], expected: str) -> None:
        with tempfile.TemporaryDirectory() as temp_text:
            repository = Path(temp_text) / "repository"
            shutil.copytree(
                ROOT,
                repository,
                ignore=shutil.ignore_patterns(".git", "dist", "release", "__pycache__", "*.pyc"),
            )
            mutation(repository)
            result = subprocess.run(
                [sys.executable, str(repository / "tools" / "skillctl.py"), "validate"],
                cwd=repository,
                check=False,
                text=True,
                capture_output=True,
                timeout=COMMAND_TIMEOUT_SECONDS,
            )
            self.assertEqual(result.returncode, 1, result.stdout)
            self.assertIn(expected, result.stderr)

    def test_schema_dialect_is_linted(self) -> None:
        def mutate(repository: Path) -> None:
            path = repository / "schemas" / "registry.schema.json"
            schema = json.loads(path.read_text())
            schema["$schema"] = "https://json-schema.org/draft/2019-09/schema"
            path.write_text(json.dumps(schema, indent=2) + "\n")

        self.assert_lint_rejects(mutate, "expected JSON Schema draft 2020-12")

    def test_frontmatter_is_linted(self) -> None:
        def mutate(repository: Path) -> None:
            path = repository / "skills" / "general" / "better-shit" / "SKILL.md"
            path.write_text(path.read_text().replace("name: better-shit", "title: better-shit", 1))

        self.assert_lint_rejects(mutate, "frontmatter fields must be exactly name, description")

    def test_unreferenced_resource_is_linted(self) -> None:
        def mutate(repository: Path) -> None:
            path = repository / "skills" / "general" / "better-shit" / "assets" / "orphan.txt"
            path.parent.mkdir()
            path.write_text("orphan\n")

        self.assert_lint_rejects(mutate, "bundled resource is not referenced directly from SKILL.md")

    def test_absolute_path_is_linted(self) -> None:
        def mutate(repository: Path) -> None:
            path = repository / "skills" / "general" / "better-shit" / "SKILL.md"
            path.write_text(path.read_text() + "\nRead /opt/company/private.conf before running.\n")

        self.assert_lint_rejects(mutate, "contains a machine-specific absolute path")

    def test_unresolved_placeholder_is_linted(self) -> None:
        def mutate(repository: Path) -> None:
            path = repository / "skills" / "general" / "better-shit" / "SKILL.md"
            path.write_text(path.read_text() + "\nUse {{UNRESOLVED_VALUE}} here.\n")

        self.assert_lint_rejects(mutate, "contains an unresolved host placeholder")


class SkillCtlInstallTests(unittest.TestCase):
    def test_copy_install_is_idempotent_and_uses_overridden_home(self) -> None:
        with tempfile.TemporaryDirectory() as temp_text:
            home = Path(temp_text) / "home"
            dry_run = run_skillctl("install", "--target", "codex", "--home", str(home), "--dry-run")
            self.assertEqual(dry_run.returncode, 0, dry_run.stderr)
            destination = home / ".agents" / "skills"
            self.assertFalse(destination.exists())

            checked_before = run_skillctl("install", "--target", "codex", "--home", str(home), "--check")
            self.assertEqual(checked_before.returncode, 1)
            self.assertFalse(destination.exists())

            installed = run_skillctl("install", "--target", "codex", "--home", str(home))
            self.assertEqual(installed.returncode, 0, installed.stderr)
            lock = json.loads((destination / "agent-skills.lock.json").read_text())
            self.assertEqual(lock["mode"], "copy")
            self.assertEqual(lock["target"], "codex")
            self.assertEqual(len(lock["skills"]), 13)
            self.assertTrue((destination / "better-shit" / "SKILL.md").is_file())

            checked_after = run_skillctl("sync", "--target", "codex", "--home", str(home), "--check")
            self.assertEqual(checked_after.returncode, 0, checked_after.stderr)
            repeated = run_skillctl("sync", "--target", "codex", "--home", str(home))
            self.assertEqual(repeated.returncode, 0, repeated.stderr)
            self.assertIn("unchanged codex", repeated.stdout)

    def test_unmanaged_and_modified_content_require_force(self) -> None:
        with tempfile.TemporaryDirectory() as temp_text:
            destination = Path(temp_text) / "skills"
            collision = destination / "better-shit"
            collision.mkdir(parents=True)
            local_file = collision / "local.txt"
            local_file.write_text("keep me\n")
            unrelated = destination / "my-own-skill"
            unrelated.mkdir()
            (unrelated / "SKILL.md").write_text("unmanaged\n")

            blocked = run_skillctl(
                "install", "--target", "kimi", "--destination", str(destination)
            )
            self.assertEqual(blocked.returncode, 1)
            self.assertEqual(local_file.read_text(), "keep me\n")
            self.assertFalse((destination / "agent-skills.lock.json").exists())

            forced = run_skillctl(
                "install", "--target", "kimi", "--destination", str(destination), "--force"
            )
            self.assertEqual(forced.returncode, 0, forced.stderr)
            self.assertFalse(local_file.exists())
            self.assertTrue((unrelated / "SKILL.md").is_file())

            managed = destination / "better-shit" / "SKILL.md"
            managed.write_text(managed.read_text() + "local edit\n")
            blocked_update = run_skillctl(
                "sync", "--target", "kimi", "--destination", str(destination)
            )
            self.assertEqual(blocked_update.returncode, 1)
            self.assertTrue(managed.read_text().endswith("local edit\n"))

            forced_update = run_skillctl(
                "sync", "--target", "kimi", "--destination", str(destination), "--force"
            )
            self.assertEqual(forced_update.returncode, 0, forced_update.stderr)
            self.assertFalse(managed.read_text().endswith("local edit\n"))

    def test_managed_removal_is_conflict_safe(self) -> None:
        with tempfile.TemporaryDirectory() as temp_text:
            destination = Path(temp_text) / "skills"
            installed = run_skillctl(
                "install", "--target", "codex", "--destination", str(destination)
            )
            self.assertEqual(installed.returncode, 0, installed.stderr)
            lock_path = destination / "agent-skills.lock.json"
            lock = json.loads(lock_path.read_text())
            retired = destination / "retired-skill"
            retired.mkdir()
            retired_file = retired / "SKILL.md"
            retired_file.write_text("retired\n")
            digest = hashlib.sha256(retired_file.read_bytes()).hexdigest()
            lock["skills"]["retired-skill"] = {
                "files": {"SKILL.md": digest},
                "link_target": None,
                "source": "skills/general/retired-skill",
                "version": "1.0.0",
            }
            lock_path.write_text(json.dumps(lock, indent=2, sort_keys=True) + "\n")

            clean_removal = run_skillctl(
                "sync", "--target", "codex", "--destination", str(destination)
            )
            self.assertEqual(clean_removal.returncode, 0, clean_removal.stderr)
            self.assertFalse(retired.exists())

            lock = json.loads(lock_path.read_text())
            retired.mkdir()
            retired_file.write_text("retired\n")
            lock["skills"]["retired-skill"] = {
                "files": {"SKILL.md": hashlib.sha256(retired_file.read_bytes()).hexdigest()},
                "link_target": None,
                "source": "skills/general/retired-skill",
                "version": "1.0.0",
            }
            lock_path.write_text(json.dumps(lock, indent=2, sort_keys=True) + "\n")

            retired_file.write_text("locally changed\n")
            blocked = run_skillctl(
                "sync", "--target", "codex", "--destination", str(destination)
            )
            self.assertEqual(blocked.returncode, 1)
            self.assertTrue(retired.exists())

            forced = run_skillctl(
                "sync", "--target", "codex", "--destination", str(destination), "--force"
            )
            self.assertEqual(forced.returncode, 0, forced.stderr)
            self.assertFalse(retired.exists())

    def test_symlink_install_uses_isolated_render_root(self) -> None:
        with tempfile.TemporaryDirectory() as temp_text:
            root = Path(temp_text)
            destination = root / "skills"
            render_root = root / "rendered"
            installed = run_skillctl(
                "install",
                "--target",
                "claude-code",
                "--destination",
                str(destination),
                "--mode",
                "symlink",
                "--render-root",
                str(render_root),
            )
            self.assertEqual(installed.returncode, 0, installed.stderr)
            lock = json.loads((destination / "agent-skills.lock.json").read_text())
            self.assertEqual(lock["mode"], "symlink")
            self.assertEqual(len(lock["skills"]), 16)
            for name, entry in lock["skills"].items():
                installed_skill = destination / name
                self.assertTrue(installed_skill.is_symlink())
                self.assertEqual(os.readlink(str(installed_skill)), entry["link_target"])
                self.assertTrue((installed_skill / "SKILL.md").is_file())

            checked = run_skillctl(
                "sync",
                "--target",
                "claude-code",
                "--destination",
                str(destination),
                "--render-root",
                str(render_root),
                "--check",
            )
            self.assertEqual(checked.returncode, 0, checked.stderr)

            rendered_skill = render_root / "claude-code" / "skills" / "better-shit" / "SKILL.md"
            rendered_skill.write_text(rendered_skill.read_text() + "local render edit\n")
            blocked = run_skillctl(
                "sync",
                "--target",
                "claude-code",
                "--destination",
                str(destination),
                "--render-root",
                str(render_root),
            )
            self.assertEqual(blocked.returncode, 1)
            self.assertTrue(rendered_skill.read_text().endswith("local render edit\n"))

            forced = run_skillctl(
                "sync",
                "--target",
                "claude-code",
                "--destination",
                str(destination),
                "--render-root",
                str(render_root),
                "--force",
            )
            self.assertEqual(forced.returncode, 0, forced.stderr)
            self.assertFalse(rendered_skill.read_text().endswith("local render edit\n"))

    def test_project_and_destination_path_overrides(self) -> None:
        with tempfile.TemporaryDirectory() as temp_text:
            root = Path(temp_text)
            project = root / "project"
            project.mkdir()
            project_install = run_skillctl(
                "install", "--target", "kimi", "--scope", "project", "--project-root", str(project)
            )
            self.assertEqual(project_install.returncode, 0, project_install.stderr)
            self.assertTrue((project / ".kimi" / "skills" / "agent-skills.lock.json").is_file())

            override = root / "custom" / "destination"
            override_install = run_skillctl(
                "install",
                "--target",
                "codex",
                "--scope",
                "project",
                "--project-root",
                str(project),
                "--destination",
                str(override),
            )
            self.assertEqual(override_install.returncode, 0, override_install.stderr)
            self.assertTrue((override / "agent-skills.lock.json").is_file())

    def test_explicit_symlink_destination_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_text:
            root = Path(temp_text)
            real_destination = root / "real-skills"
            real_destination.mkdir()
            linked_destination = root / "skills-link"
            linked_destination.symlink_to(real_destination, target_is_directory=True)

            result = run_skillctl(
                "install", "--target", "codex", "--destination", str(linked_destination)
            )

            self.assertEqual(result.returncode, 1)
            self.assertIn("destination must be a real directory path", result.stderr)
            self.assertTrue(linked_destination.is_symlink())
            self.assertEqual(list(real_destination.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
