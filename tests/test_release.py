from __future__ import annotations

import hashlib
import subprocess
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "tools" / "build_release.py"
COMMAND_TIMEOUT_SECONDS = 30


def build(output: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(BUILDER), "--output", str(output)],
        cwd=ROOT,
        check=False,
        text=True,
        capture_output=True,
        timeout=COMMAND_TIMEOUT_SECONDS,
    )


class ReproducibleReleaseTests(unittest.TestCase):
    def test_release_archives_and_checksums_are_reproducible(self) -> None:
        with tempfile.TemporaryDirectory() as temp_text:
            root = Path(temp_text)
            first = root / "first"
            second = root / "second"
            first_result = build(first)
            second_result = build(second)
            self.assertEqual(first_result.returncode, 0, first_result.stderr)
            self.assertEqual(second_result.returncode, 0, second_result.stderr)

            expected_names = {
                "SHA256SUMS",
                "agent-skills-claude-code.tar.gz",
                "agent-skills-codex.tar.gz",
                "agent-skills-kimi.tar.gz",
            }
            self.assertEqual({path.name for path in first.iterdir()}, expected_names)
            self.assertEqual({path.name for path in second.iterdir()}, expected_names)
            for name in expected_names:
                self.assertEqual((first / name).read_bytes(), (second / name).read_bytes())

            checksum_lines = (first / "SHA256SUMS").read_text().splitlines()
            self.assertEqual(len(checksum_lines), 3)
            for line in checksum_lines:
                digest, name = line.split("  ", 1)
                self.assertEqual(digest, hashlib.sha256((first / name).read_bytes()).hexdigest())

            for archive_path in sorted(first.glob("*.tar.gz")):
                target = archive_path.name[len("agent-skills-") : -len(".tar.gz")]
                with tarfile.open(archive_path, "r:gz") as archive:
                    members = archive.getmembers()
                    self.assertEqual([member.name for member in members], sorted(member.name for member in members))
                    self.assertTrue(all(member.mtime == 0 for member in members))
                    self.assertTrue(all(member.uid == 0 and member.gid == 0 for member in members))
                    self.assertIn(f"{target}/manifest.json", {member.name for member in members})


if __name__ == "__main__":
    unittest.main()
