#!/usr/bin/env python3
"""Build byte-reproducible target archives and their SHA-256 checksum file."""

from __future__ import annotations

import argparse
import gzip
import io
import os
import tarfile
import tempfile
from pathlib import Path

from skillctl import render_target, sha256_file, validate_repository


FIXED_MTIME = 0


def archive_tree(source: Path, archive_path: Path, archive_root: str) -> None:
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=archive_path.parent, prefix=".release-", delete=False) as raw:
        temporary = Path(raw.name)
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, compresslevel=9, mtime=FIXED_MTIME) as zipped:
            with tarfile.open(fileobj=zipped, mode="w", format=tarfile.PAX_FORMAT) as archive:
                paths = [source, *sorted(source.rglob("*"))]
                for path in paths:
                    relative_name = path.relative_to(source).as_posix()
                    archive_name = archive_root if not relative_name or relative_name == "." else f"{archive_root}/{relative_name}"
                    info = tarfile.TarInfo(archive_name)
                    info.uid = 0
                    info.gid = 0
                    info.uname = "root"
                    info.gname = "root"
                    info.mtime = FIXED_MTIME
                    if path.is_dir():
                        info.type = tarfile.DIRTYPE
                        info.mode = 0o755
                        archive.addfile(info)
                    elif path.is_file() and not path.is_symlink():
                        data = path.read_bytes()
                        info.size = len(data)
                        info.mode = 0o755 if os.access(path, os.X_OK) else 0o644
                        archive.addfile(info, io.BytesIO(data))
                    else:
                        raise RuntimeError(f"release input is not a regular file tree: {path}")
    temporary.replace(archive_path)


def write_checksums(output: Path, artifacts: list[Path]) -> Path:
    checksum_path = output / "SHA256SUMS"
    content = "".join(f"{sha256_file(path)}  {path.name}\n" for path in sorted(artifacts))
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=output, prefix=".checksums-", delete=False
    ) as handle:
        temporary = Path(handle.name)
        handle.write(content)
    temporary.replace(checksum_path)
    return checksum_path


def build_release(output: Path) -> list[Path]:
    registry = validate_repository()
    output = output.expanduser().resolve()
    output.mkdir(parents=True, exist_ok=True)
    artifacts: list[Path] = []
    with tempfile.TemporaryDirectory(prefix="agent-skills-release-") as temp_text:
        rendered = Path(temp_text)
        for target in registry["targets"]:
            render_target(target, rendered)
            artifact = output / f"agent-skills-{target}.tar.gz"
            archive_tree(rendered / target, artifact, target)
            artifacts.append(artifact)
    artifacts.append(write_checksums(output, artifacts))
    return artifacts


def main() -> int:
    parser = argparse.ArgumentParser(prog="build_release")
    parser.add_argument("--output", type=Path, default=Path("release"))
    args = parser.parse_args()
    for artifact in build_release(args.output):
        print(artifact)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
