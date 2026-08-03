from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TARGETS = ("claude-code", "codex", "kimi")
COMMAND_TIMEOUT_SECONDS = 30


def run_copy(repository: Path, isolated_home: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["HOME"] = str(isolated_home)
    return subprocess.run(
        [sys.executable, str(repository / "tools" / "skillctl.py"), *arguments],
        cwd=repository,
        env=environment,
        check=False,
        text=True,
        capture_output=True,
        timeout=COMMAND_TIMEOUT_SECONDS,
    )


class ThreeTargetEndToEndTests(unittest.TestCase):
    def test_install_update_and_conflict_for_every_target(self) -> None:
        with tempfile.TemporaryDirectory() as temp_text:
            root = Path(temp_text)
            repository = root / "repository"
            shutil.copytree(
                ROOT,
                repository,
                ignore=shutil.ignore_patterns(".git", "dist", "release", "__pycache__", "*.pyc"),
            )
            homes = {target: root / "homes" / target for target in TARGETS}
            destinations: dict[str, Path] = {}

            for target in TARGETS:
                adapter = json.loads((repository / "targets" / f"{target}.json").read_text())
                destinations[target] = homes[target] / adapter["user_path"]
                installed = run_copy(
                    repository, homes[target], "install", "--target", target, "--home", str(homes[target])
                )
                self.assertEqual(installed.returncode, 0, installed.stderr)
                checked = run_copy(
                    repository,
                    homes[target],
                    "sync",
                    "--target",
                    target,
                    "--home",
                    str(homes[target]),
                    "--check",
                )
                self.assertEqual(checked.returncode, 0, checked.stderr)

            source_skill = repository / "skills" / "general" / "better-shit" / "SKILL.md"
            source_skill.write_text(source_skill.read_text() + "\nVerify the first E2E update.\n")
            registry_path = repository / "registry.json"
            registry = json.loads(registry_path.read_text())
            next(entry for entry in registry["skills"] if entry["name"] == "better-shit")["version"] = "1.0.1"
            registry_path.write_text(json.dumps(registry, indent=2) + "\n")

            for target in TARGETS:
                updated = run_copy(
                    repository, homes[target], "sync", "--target", target, "--home", str(homes[target])
                )
                self.assertEqual(updated.returncode, 0, updated.stderr)
                installed_text = (destinations[target] / "better-shit" / "SKILL.md").read_text()
                self.assertIn("Verify the first E2E update.", installed_text)

            for target in TARGETS:
                installed_skill = destinations[target] / "better-shit" / "SKILL.md"
                installed_skill.write_text(installed_skill.read_text() + f"local {target} edit\n")
            source_skill.write_text(source_skill.read_text() + "Verify the second E2E update.\n")
            registry = json.loads(registry_path.read_text())
            next(entry for entry in registry["skills"] if entry["name"] == "better-shit")["version"] = "1.0.2"
            registry_path.write_text(json.dumps(registry, indent=2) + "\n")

            for target in TARGETS:
                blocked = run_copy(
                    repository, homes[target], "sync", "--target", target, "--home", str(homes[target])
                )
                self.assertEqual(blocked.returncode, 1)
                self.assertIn("locally modified managed skill blocks update", blocked.stderr)
                installed_text = (destinations[target] / "better-shit" / "SKILL.md").read_text()
                self.assertTrue(installed_text.endswith(f"local {target} edit\n"))
                self.assertNotIn("Verify the second E2E update.", installed_text)


if __name__ == "__main__":
    unittest.main()
