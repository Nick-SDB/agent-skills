from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "general" / "planning-with-files"
HELPER = SKILL / "scripts" / "planning.py"


class PlanningWithFilesTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.project = Path(self.temp.name)

    def run_helper(self, *args, env=None, code=0):
        environment = dict(os.environ)
        for name in ("PLAN_ID", "PWF_PLAN_ROOT"):
            environment.pop(name, None)
        environment.update(env or {})
        result = subprocess.run(
            [sys.executable, str(HELPER), *args],
            cwd=self.project, env=environment, capture_output=True, text=True, timeout=10,
        )
        self.assertEqual(result.returncode, code, result.stdout + result.stderr)
        return result

    def initialize(self, title="Experiment"):
        result = self.run_helper("init", title)
        return result.stdout.splitlines()[0].split("=", 1)[1]

    def test_initialization_preserves_existing_work_and_host_settings(self):
        host = self.project / ".codex"
        host.mkdir()
        hook = host / "hooks.json"
        hook.write_text('{"existing": true}\n')
        (self.project / ".mode").write_text("autonomous gate\n")
        first = self.initialize("双 Q128 优化")
        directory = self.project / ".planning" / first
        self.assertEqual(
            {p.name for p in directory.iterdir()},
            {"task_plan.md", "findings.md", "progress.md"},
        )
        progress = directory / "progress.md"
        progress.write_text("Measured baseline; preserve this result.\n")
        second = self.initialize("双 Q128 优化")
        self.assertNotEqual(first, second)
        self.assertEqual(progress.read_text(), "Measured baseline; preserve this result.\n")
        self.assertEqual(hook.read_text(), '{"existing": true}\n')
        self.assertFalse((self.project / ".planning" / ".active_plan").exists())

    def test_selection_rejects_ambiguity_and_never_falls_back_for_bad_pin(self):
        first = self.initialize("First")
        self.run_helper("resolve")
        second = self.initialize("Second")
        (self.project / "task_plan.md").write_text("Legacy plan\n")
        result = self.run_helper("resolve", code=2)
        self.assertIn("multiple named plans", result.stderr)
        self.run_helper("resolve", "--plan-id", "missing", code=2)
        self.run_helper("resolve", "--plan-id", "../outside", code=2)
        self.run_helper("resolve", "--plan-id", "", code=2)
        selected = self.run_helper("resolve", env={"PLAN_ID": second})
        self.assertEqual(Path(selected.stdout.strip()).name, second)
        selected = self.run_helper("resolve", "--plan-id", first, env={"PLAN_ID": second})
        self.assertEqual(Path(selected.stdout.strip()).name, first)
        legacy = self.run_helper("resolve", "--plan-id", "root")
        self.assertEqual(Path(legacy.stdout.strip()), self.project)
        self.assertEqual(set(self.run_helper("list").stdout.splitlines()), {first, second, "root"})

    def test_root_environment_and_invalid_root_do_not_fall_back(self):
        nested = self.project / "nested"
        nested.mkdir()
        self.run_helper("init", "Nested", env={"PWF_PLAN_ROOT": str(nested)})
        result = self.run_helper("resolve", env={"PWF_PLAN_ROOT": str(nested)})
        self.assertEqual(Path(result.stdout.strip()).parent, nested / ".planning")
        self.run_helper("resolve", env={"PWF_PLAN_ROOT": str(self.project / "missing")}, code=2)
        self.assertFalse((self.project / ".planning").exists())

    def test_check_requires_valid_completed_phases_and_checked_items(self):
        plan_id = self.initialize()
        path = self.project / ".planning" / plan_id / "task_plan.md"
        self.run_helper("check", code=1)
        text = path.read_text()
        text = text.replace("**Status:** in_progress", "**Status:** complete")
        text = text.replace("**Status:** pending", "**Status:** complete")
        path.write_text(text)
        self.run_helper("check", code=1)  # unchecked acceptance tasks remain
        text = text.replace("- [ ]", "- [x]")
        path.write_text(text)
        self.run_helper("check")
        path.write_text(text.replace("**Status:** complete", "**Status:** invalid", 1))
        self.run_helper("check", code=2)
        path.write_text("# No phases\n")
        self.run_helper("check", code=2)

    def test_check_ignores_fenced_examples_and_unrelated_status_lines(self):
        plan_id = self.initialize()
        path = self.project / ".planning" / plan_id / "task_plan.md"
        path.write_text(
            "# Task\n\n### Phase 1: Verify\n- **Status:** complete\n- [x] Evidence\n"
            "```markdown\n### Phase 2: Example\n- **Status:** pending\n```\n"
            "## Notes\n- **Status:** pending\n- [ ] unrelated\n"
        )
        self.run_helper("check")
        path.write_text(path.read_text().replace("- [x] Evidence", "- **Status:** complete"))
        self.run_helper("check", code=2)

    def test_initialization_refuses_symlinked_planning_root(self):
        with tempfile.TemporaryDirectory() as outside:
            (self.project / ".planning").symlink_to(outside, target_is_directory=True)
            self.run_helper("init", "Experiment", code=2)
            self.assertEqual(list(Path(outside).iterdir()), [])

    def test_imported_files_match_pinned_checksums(self):
        manifest = json.loads((SKILL / "references" / "upstream.json").read_text())
        self.assertEqual(len(manifest["commit"]), 40)
        for entry in manifest["files"]:
            content = (SKILL / entry["local_path"]).read_bytes()
            self.assertEqual(hashlib.sha256(content).hexdigest(), entry["sha256"])


if __name__ == "__main__":
    unittest.main()
