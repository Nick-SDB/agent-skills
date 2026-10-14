"""Probe symlink privileges before tests that require actual symlinks."""

import tempfile
import unittest
from pathlib import Path


def require_symlink(*, target_is_directory: bool = True) -> None:
    with tempfile.TemporaryDirectory() as temp_text:
        root = Path(temp_text)
        target = root / "target"
        if target_is_directory:
            target.mkdir()
        else:
            target.write_text("probe\n", encoding="utf-8")
        try:
            (root / "link").symlink_to(target, target_is_directory=target_is_directory)
        except OSError as exc:
            if getattr(exc, "winerror", None) == 1314:
                raise unittest.SkipTest("Windows process lacks symlink creation privileges") from exc
            raise
