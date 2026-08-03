#!/usr/bin/env python3
"""Validate, render, and safely synchronize agent skills without third-party packages."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "registry.json"
TARGETS_DIR = ROOT / "targets"
MANIFEST_SCHEMA_PATH = ROOT / "schemas" / "rendered-manifest.schema.json"
LOCK_SCHEMA_PATH = ROOT / "schemas" / "install-lock.schema.json"
LOCK_SCHEMA_URL = (
    "https://raw.githubusercontent.com/Nick-SDB/agent-skills/master/schemas/install-lock.schema.json"
)
LOCK_FILENAME = "agent-skills.lock.json"

NAME_RE = re.compile(r"^[a-z0-9-]{1,64}$")
VERSION_RE = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")
LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)
PORTABLE_LEAKS = {
    "Claude instruction filename": re.compile(r"CLAUDE\.md"),
    "Claude argument placeholder": re.compile(r"\$ARGUMENTS|\$\{CLAUDE_(?:SKILL|PROJECT)_DIR\}"),
    "Claude dynamic context": re.compile(r"!`"),
    "host-specific tool name": re.compile(r"\*\*(?:Glob|Read|Write|Bash|Grep|Agent|AskUserQuestion)\*\*"),
}
MACHINE_PATH_RE = re.compile(
    r"(?<![A-Za-z0-9:.~/])(?:/(?!/)[A-Za-z0-9._~-]+(?:/[A-Za-z0-9._~-]+)+|"
    r"[A-Za-z]:\\|\\\\[A-Za-z0-9._-]+\\)"
)
PLACEHOLDER_RE = re.compile(
    r"\$ARGUMENTS|\$\{(?:CLAUDE|CODEX|KIMI)_[A-Z0-9_]+\}|"
    r"\{\{[^{}\n]+\}\}|__(?:TODO|PLACEHOLDER)__"
)
ALLOWED_SKILL_ENTRIES = {"SKILL.md", "adapters", "agents", "assets", "references", "scripts"}
RESOURCE_DIRECTORIES = {"assets", "references", "scripts"}


class SkillCtlError(RuntimeError):
    """A user-facing validation or rendering failure."""


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SkillCtlError(f"cannot read JSON {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise SkillCtlError(f"expected a JSON object in {path}")
    return value


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def relative(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def parse_frontmatter(path: Path) -> tuple[dict[str, str], str]:
    text = path.read_text(encoding="utf-8")
    match = FRONTMATTER_RE.match(text)
    if not match:
        raise SkillCtlError(f"{relative(path)}: missing YAML frontmatter")
    fields: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if not line.strip() or line.startswith((" ", "\t")) or ":" not in line:
            raise SkillCtlError(f"{relative(path)}: frontmatter must contain simple key/value lines")
        key, value = line.split(":", 1)
        if key in fields:
            raise SkillCtlError(f"{relative(path)}: duplicate frontmatter field {key}")
        fields[key] = value.strip()
    if list(fields) != ["name", "description"]:
        raise SkillCtlError(
            f"{relative(path)}: frontmatter fields must be exactly name, description in that order"
        )
    return fields, text[match.end() :]


def load_registry() -> dict[str, Any]:
    registry = read_json(REGISTRY_PATH)
    expected = {"$schema", "format_version", "skills", "targets"}
    if set(registry) != expected:
        raise SkillCtlError(f"registry.json fields must be {sorted(expected)}")
    if registry["$schema"] != "schemas/registry.schema.json":
        raise SkillCtlError("registry.json has an unexpected $schema path")
    if registry["format_version"] != 1:
        raise SkillCtlError("registry.json format_version must be 1")
    if not isinstance(registry["targets"], list) or not registry["targets"]:
        raise SkillCtlError("registry.json targets must be a non-empty list")
    if len(set(registry["targets"])) != len(registry["targets"]):
        raise SkillCtlError("registry.json contains duplicate targets")
    if not isinstance(registry["skills"], list) or not registry["skills"]:
        raise SkillCtlError("registry.json skills must be a non-empty list")
    return registry


def load_adapter(target: str) -> dict[str, Any]:
    path = TARGETS_DIR / f"{target}.json"
    adapter = read_json(path)
    expected = {
        "$schema",
        "display_name",
        "format_version",
        "id",
        "instruction_file",
        "invocation_prefix",
        "project_path",
        "supports_symlink",
        "user_path",
    }
    if set(adapter) != expected:
        raise SkillCtlError(f"{relative(path)} fields must be {sorted(expected)}")
    if adapter["$schema"] != "../schemas/target-adapter.schema.json":
        raise SkillCtlError(f"{relative(path)} has an unexpected $schema path")
    if adapter["format_version"] != 1 or adapter["id"] != target:
        raise SkillCtlError(f"{relative(path)} identity does not match {target}")
    for key in ("display_name", "instruction_file", "project_path", "user_path"):
        if not isinstance(adapter[key], str) or not adapter[key]:
            raise SkillCtlError(f"{relative(path)} field {key} must be a non-empty string")
    if not isinstance(adapter["invocation_prefix"], str):
        raise SkillCtlError(f"{relative(path)} invocation_prefix must be a string")
    if not isinstance(adapter["supports_symlink"], bool):
        raise SkillCtlError(f"{relative(path)} supports_symlink must be boolean")
    for key in ("instruction_file", "project_path", "user_path"):
        value_path = Path(adapter[key])
        if value_path.is_absolute() or ".." in value_path.parts:
            raise SkillCtlError(f"{relative(path)} field {key} must be a safe relative path")
    return adapter


def check_markdown_links(skill_dir: Path, path: Path, errors: list[str]) -> None:
    text = path.read_text(encoding="utf-8")
    for raw_target in LINK_RE.findall(text):
        target = raw_target.split("#", 1)[0]
        if not target or "://" in target or target.startswith(("mailto:", "#")):
            continue
        resolved = (path.parent / target).resolve()
        try:
            resolved.relative_to(skill_dir.resolve())
        except ValueError:
            errors.append(f"{relative(path)}: link escapes skill directory: {raw_target}")
            continue
        if not resolved.exists():
            errors.append(f"{relative(path)}: missing linked resource: {raw_target}")


def check_skill_resources(source: Path, skill_text: str, errors: list[str]) -> None:
    for child in sorted(source.iterdir()):
        if child.name not in ALLOWED_SKILL_ENTRIES:
            errors.append(f"{relative(child)}: unexpected top-level skill entry")
    for directory_name in RESOURCE_DIRECTORIES:
        resource_root = source / directory_name
        if not resource_root.exists():
            continue
        if not resource_root.is_dir():
            errors.append(f"{relative(resource_root)}: bundled resource path must be a directory")
            continue
        for resource in sorted(path for path in resource_root.rglob("*") if path.is_file()):
            resource_name = resource.relative_to(source).as_posix()
            if resource_name not in skill_text:
                errors.append(
                    f"{relative(resource)}: bundled resource is not referenced directly from SKILL.md"
                )


def check_content_leaks(source: Path, errors: list[str]) -> None:
    for path in sorted(candidate for candidate in source.rglob("*") if candidate.is_file()):
        text = path.read_text(encoding="utf-8", errors="ignore")
        if MACHINE_PATH_RE.search(text):
            errors.append(f"{relative(path)}: contains a machine-specific absolute path")
        if PLACEHOLDER_RE.search(text):
            errors.append(f"{relative(path)}: contains an unresolved host placeholder")


def validate_repository() -> dict[str, Any]:
    registry = load_registry()
    errors: list[str] = []
    target_names = registry["targets"]
    if target_names != sorted(target_names):
        errors.append("registry.json targets must be sorted")
    adapters = {}
    for target in target_names:
        if not isinstance(target, str) or not NAME_RE.fullmatch(target):
            errors.append(f"invalid target name: {target!r}")
            continue
        try:
            adapters[target] = load_adapter(target)
        except SkillCtlError as exc:
            errors.append(str(exc))

    registered_sources: set[str] = set()
    registered_names: set[str] = set()
    previous_name = ""
    for entry in registry["skills"]:
        if not isinstance(entry, dict):
            errors.append("registry skill entries must be objects")
            continue
        expected = {"category", "name", "source", "targets", "version"}
        if set(entry) != expected:
            errors.append(f"registry skill entry fields must be {sorted(expected)}: {entry!r}")
            continue
        name = entry["name"]
        source_text = entry["source"]
        if not isinstance(name, str) or not NAME_RE.fullmatch(name):
            errors.append(f"invalid skill name: {name!r}")
            continue
        if name <= previous_name:
            errors.append("registry skills must be sorted by name")
        previous_name = name
        if name in registered_names:
            errors.append(f"duplicate registry skill name: {name}")
        registered_names.add(name)
        if source_text in registered_sources:
            errors.append(f"duplicate registry source: {source_text}")
        registered_sources.add(source_text)
        if entry["category"] not in {"general", "claude-code"}:
            errors.append(f"{name}: unsupported category {entry['category']!r}")
        if not isinstance(entry["version"], str) or not VERSION_RE.fullmatch(entry["version"]):
            errors.append(f"{name}: invalid version {entry['version']!r}")
        if not isinstance(entry["targets"], list) or not entry["targets"]:
            errors.append(f"{name}: targets must be a non-empty list")
            continue
        if entry["targets"] != sorted(set(entry["targets"])):
            errors.append(f"{name}: targets must be unique and sorted")
        unknown_targets = set(entry["targets"]) - set(target_names)
        if unknown_targets:
            errors.append(f"{name}: unknown targets {sorted(unknown_targets)}")

        source = ROOT / source_text
        skill_file = source / "SKILL.md"
        if not skill_file.is_file():
            errors.append(f"{source_text}: missing SKILL.md")
            continue
        if source.name != name:
            errors.append(f"{source_text}: directory does not match skill name {name}")
        if source.parent.name != entry["category"]:
            errors.append(f"{source_text}: directory does not match category {entry['category']}")
        try:
            fields, _ = parse_frontmatter(skill_file)
        except SkillCtlError as exc:
            errors.append(str(exc))
        else:
            if fields["name"] != name:
                errors.append(f"{source_text}: frontmatter name does not match registry")
            if not fields["description"] or len(fields["description"]) > 1024:
                errors.append(f"{source_text}: description must contain 1-1024 characters")
        skill_text = skill_file.read_text(encoding="utf-8")
        if len(skill_text.splitlines()) > 500:
            errors.append(f"{source_text}: SKILL.md exceeds 500 lines")
        check_skill_resources(source, skill_text, errors)
        check_content_leaks(source, errors)

        for path in sorted(source.rglob("*")):
            if path.is_symlink():
                errors.append(f"{relative(path)}: source symlinks are not reproducible")
            if path.is_file() and path.suffix == ".md":
                check_markdown_links(source, path, errors)

        adapter_dir = source / "adapters"
        if adapter_dir.exists():
            for overlay in sorted(adapter_dir.iterdir()):
                if not overlay.is_file() or overlay.suffix != ".md":
                    errors.append(f"{relative(overlay)}: overlays must be Markdown files")
                    continue
                if overlay.stem not in entry["targets"]:
                    errors.append(f"{relative(overlay)}: overlay target is not enabled for {name}")
                if FRONTMATTER_RE.match(overlay.read_text(encoding="utf-8")):
                    errors.append(f"{relative(overlay)}: overlays cannot define frontmatter")

        if len(entry["targets"]) > 1:
            for path in sorted(source.rglob("*")):
                if not path.is_file() or "adapters" in path.parts:
                    continue
                text = path.read_text(encoding="utf-8", errors="ignore")
                for label, pattern in PORTABLE_LEAKS.items():
                    if pattern.search(text):
                        errors.append(f"{relative(path)}: portable source contains {label}")

    discovered = {
        relative(path.parent)
        for path in ROOT.glob("skills/*/*/SKILL.md")
    }
    for source in sorted(discovered - registered_sources):
        errors.append(f"unregistered skill source: {source}")
    for source in sorted(registered_sources - discovered):
        errors.append(f"registry source is not a discovered skill: {source}")

    schema_paths = [
        ROOT / "schemas/registry.schema.json",
        ROOT / "schemas/target-adapter.schema.json",
        MANIFEST_SCHEMA_PATH,
        LOCK_SCHEMA_PATH,
    ]
    for path in schema_paths:
        try:
            schema = read_json(path)
        except SkillCtlError as exc:
            errors.append(str(exc))
            continue
        if schema.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
            errors.append(f"{relative(path)}: expected JSON Schema draft 2020-12")

    if errors:
        raise SkillCtlError("validation failed:\n- " + "\n- ".join(errors))
    return registry


def iter_source_files(source: Path) -> Iterable[Path]:
    for path in sorted(source.rglob("*")):
        if path.is_file() and "adapters" not in path.relative_to(source).parts:
            yield path


def render_target(target: str, output_root: Path, *, check: bool = False) -> None:
    registry = validate_repository()
    if target not in registry["targets"]:
        raise SkillCtlError(f"unknown target {target!r}")
    adapter_path = TARGETS_DIR / f"{target}.json"
    adapter = load_adapter(target)

    output_root = output_root.resolve()
    output_root.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=f"skillctl-{target}-", dir=output_root.parent) as temp_text:
        temp_target = Path(temp_text) / target
        skills_root = temp_target / "skills"
        skills_root.mkdir(parents=True)
        manifest_skills: list[dict[str, Any]] = []

        for entry in registry["skills"]:
            if target not in entry["targets"]:
                continue
            source = ROOT / entry["source"]
            destination = skills_root / entry["name"]
            destination.mkdir()
            for path in iter_source_files(source):
                relative_path = path.relative_to(source)
                output_path = destination / relative_path
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_bytes(path.read_bytes())
                output_path.chmod(path.stat().st_mode & 0o777)

            overlay = source / "adapters" / f"{target}.md"
            if overlay.is_file():
                skill_path = destination / "SKILL.md"
                base = skill_path.read_text(encoding="utf-8").rstrip()
                addition = overlay.read_text(encoding="utf-8").strip()
                skill_path.write_text(f"{base}\n\n{addition}\n", encoding="utf-8")

            files = {
                path.relative_to(destination).as_posix(): sha256_file(path)
                for path in sorted(destination.rglob("*"))
                if path.is_file()
            }
            manifest_skills.append(
                {
                    "files": files,
                    "name": entry["name"],
                    "source": entry["source"],
                    "version": entry["version"],
                }
            )

        manifest_adapter = {key: value for key, value in adapter.items() if key != "$schema"}
        manifest = {
            "$schema": "manifest.schema.json",
            "adapter": manifest_adapter,
            "adapter_sha256": sha256_file(adapter_path),
            "format_version": 1,
            "skills": manifest_skills,
            "target": target,
        }
        (temp_target / "manifest.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        shutil.copyfile(MANIFEST_SCHEMA_PATH, temp_target / "manifest.schema.json")

        destination = output_root / target
        if check:
            differences = compare_trees(temp_target, destination)
            if differences:
                raise SkillCtlError(
                    f"rendered {target} distribution is stale:\n- " + "\n- ".join(differences)
                )
            return
        if destination.exists():
            shutil.rmtree(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(temp_target, destination)


def compare_trees(expected: Path, actual: Path) -> list[str]:
    if not actual.is_dir():
        return [f"missing directory: {actual}"]
    if actual.is_symlink():
        return ["unexpected symlink: ."]
    actual_paths = list(actual.rglob("*"))
    actual_symlinks = {
        path.relative_to(actual).as_posix()
        for path in actual_paths
        if path.is_symlink()
    }
    expected_files = {
        path.relative_to(expected).as_posix(): sha256_file(path)
        for path in expected.rglob("*")
        if path.is_file()
    }
    actual_files = {
        path.relative_to(actual).as_posix(): sha256_file(path)
        for path in actual_paths
        if path.is_file() and not path.is_symlink()
    }
    differences = [f"unexpected symlink: {path}" for path in sorted(actual_symlinks)]
    for path in sorted(expected_files.keys() - actual_files.keys()):
        differences.append(f"missing file: {path}")
    for path in sorted(actual_files.keys() - expected_files.keys()):
        differences.append(f"unexpected file: {path}")
    for path in sorted(expected_files.keys() & actual_files.keys()):
        if expected_files[path] != actual_files[path]:
            differences.append(f"content differs: {path}")
    return differences


def render(selection: str, output_root: Path, *, check: bool) -> None:
    registry = validate_repository()
    targets = registry["targets"] if selection == "all" else [selection]
    for target in targets:
        render_target(target, output_root, check=check)
        action = "checked" if check else "rendered"
        print(f"{action} {target}: {output_root.resolve() / target}")


def directory_files(path: Path) -> dict[str, str] | None:
    """Return regular-file checksums, or None for missing/unsafe trees."""
    if not path.exists() or not path.is_dir():
        return None
    root = path.resolve()
    files: dict[str, str] = {}
    for candidate in sorted(root.rglob("*")):
        if candidate.is_symlink():
            return None
        if candidate.is_file():
            files[candidate.relative_to(root).as_posix()] = sha256_file(candidate)
    return files


def load_lock(path: Path, target: str) -> dict[str, Any] | None:
    if not path.exists():
        return None
    lock = read_json(path)
    expected = {
        "$schema",
        "adapter_sha256",
        "format_version",
        "mode",
        "registry_sha256",
        "rendered_files",
        "skills",
        "target",
    }
    if set(lock) != expected:
        raise SkillCtlError(f"{path}: lockfile fields must be {sorted(expected)}")
    if lock["$schema"] != LOCK_SCHEMA_URL or lock["format_version"] != 1:
        raise SkillCtlError(f"{path}: unsupported lockfile format")
    if lock["target"] != target:
        raise SkillCtlError(
            f"{path}: lockfile target {lock['target']!r} does not match {target!r}"
        )
    if lock["mode"] not in {"copy", "symlink"}:
        raise SkillCtlError(f"{path}: lockfile mode must be copy or symlink")
    if not isinstance(lock["skills"], dict):
        raise SkillCtlError(f"{path}: lockfile skills must be an object")
    for digest_key in ("adapter_sha256", "registry_sha256"):
        if not isinstance(lock[digest_key], str) or not re.fullmatch(r"[0-9a-f]{64}", lock[digest_key]):
            raise SkillCtlError(f"{path}: invalid {digest_key}")
    if not isinstance(lock["rendered_files"], dict):
        raise SkillCtlError(f"{path}: rendered_files must be an object")
    for relative_name, digest in lock["rendered_files"].items():
        relative_path = Path(relative_name)
        if (
            not relative_name
            or "\\" in relative_name
            or relative_path.is_absolute()
            or ".." in relative_path.parts
            or not isinstance(digest, str)
            or not re.fullmatch(r"[0-9a-f]{64}", digest)
        ):
            raise SkillCtlError(f"{path}: invalid rendered file {relative_name!r}")
    for name, entry in lock["skills"].items():
        if not NAME_RE.fullmatch(name) or not isinstance(entry, dict):
            raise SkillCtlError(f"{path}: invalid locked skill {name!r}")
        if set(entry) != {"files", "link_target", "source", "version"}:
            raise SkillCtlError(f"{path}: invalid fields for locked skill {name}")
        if not isinstance(entry["files"], dict):
            raise SkillCtlError(f"{path}: files for {name} must be an object")
        for relative_name, digest in entry["files"].items():
            relative_path = Path(relative_name)
            if (
                not relative_name
                or "\\" in relative_name
                or relative_path.is_absolute()
                or ".." in relative_path.parts
                or not isinstance(digest, str)
                or not re.fullmatch(r"[0-9a-f]{64}", digest)
            ):
                raise SkillCtlError(f"{path}: invalid locked file for {name}: {relative_name!r}")
        if entry["link_target"] is not None and not isinstance(entry["link_target"], str):
            raise SkillCtlError(f"{path}: invalid link target for {name}")
        if not isinstance(entry["source"], str) or not isinstance(entry["version"], str):
            raise SkillCtlError(f"{path}: invalid source metadata for {name}")
    return lock


def installed_matches(path: Path, entry: dict[str, Any], mode: str) -> bool:
    if mode == "symlink":
        if not path.is_symlink() or os.readlink(str(path)) != entry["link_target"]:
            return False
    elif path.is_symlink():
        return False
    return directory_files(path) == entry["files"]


def installed_link_identity_matches(path: Path, entry: dict[str, Any], mode: str) -> bool:
    return mode == "symlink" and path.is_symlink() and os.readlink(str(path)) == entry["link_target"]


def remove_managed_path(path: Path) -> None:
    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.is_dir():
        shutil.rmtree(path)


def replace_with_copy(source: Path, destination: Path) -> None:
    staging = Path(tempfile.mkdtemp(prefix=".skillctl-copy-", dir=destination.parent))
    try:
        shutil.rmtree(staging)
        shutil.copytree(source, staging)
        remove_managed_path(destination)
        staging.replace(destination)
    finally:
        if staging.exists():
            shutil.rmtree(staging)


def replace_with_symlink(link_target: str, destination: Path) -> None:
    staging = Path(tempfile.mkdtemp(prefix=".skillctl-link-", dir=destination.parent))
    shutil.rmtree(staging)
    staging.symlink_to(link_target, target_is_directory=True)
    remove_managed_path(destination)
    staging.replace(destination)


def write_json_atomic(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, prefix=".skillctl-lock-", delete=False
    ) as handle:
        temporary = Path(handle.name)
        json.dump(value, handle, indent=2, sort_keys=True)
        handle.write("\n")
    temporary.replace(path)


def resolve_destination(args: argparse.Namespace, adapter: dict[str, Any]) -> Path:
    if args.destination is not None:
        destination = args.destination.expanduser()
        if destination.is_symlink():
            raise SkillCtlError(f"destination must be a real directory path: {destination}")
        return destination.resolve()
    if args.scope == "user":
        base = args.home.expanduser().resolve() if args.home is not None else Path.home().resolve()
        return base / adapter["user_path"]
    base = (
        args.project_root.expanduser().resolve()
        if args.project_root is not None
        else Path.cwd().resolve()
    )
    return base / adapter["project_path"]


def ensure_separate_paths(destination: Path, render_root: Path) -> None:
    destination = destination.resolve()
    render_root = render_root.resolve()
    for first, second in ((destination, render_root), (render_root, destination)):
        try:
            first.relative_to(second)
        except ValueError:
            continue
        raise SkillCtlError("destination and symlink render root must not contain one another")


def sync_install(args: argparse.Namespace) -> None:
    registry = validate_repository()
    if args.target not in registry["targets"]:
        raise SkillCtlError(f"unknown target {args.target!r}")
    adapter = load_adapter(args.target)
    destination = resolve_destination(args, adapter)
    if destination == Path(destination.anchor):
        raise SkillCtlError("refusing to use a filesystem root as the destination")
    if destination.is_symlink() or (destination.exists() and not destination.is_dir()):
        raise SkillCtlError(f"destination must be a real directory path: {destination}")
    lock_path = destination / LOCK_FILENAME
    old_lock = load_lock(lock_path, args.target)
    mode = args.mode or (old_lock["mode"] if old_lock is not None else "copy")
    if mode == "symlink" and not adapter["supports_symlink"]:
        raise SkillCtlError(f"target {args.target!r} does not support symlink installs")
    render_root = args.render_root.expanduser().resolve()
    if mode == "symlink":
        ensure_separate_paths(destination, render_root)

    with tempfile.TemporaryDirectory(prefix=f"skillctl-install-{args.target}-") as temp_text:
        temporary_root = Path(temp_text)
        render_target(args.target, temporary_root)
        rendered_target = temporary_root / args.target
        manifest = read_json(rendered_target / "manifest.json")
        rendered_files = directory_files(rendered_target)
        if rendered_files is None:
            raise SkillCtlError("internal error: rendered distribution is not a regular file tree")
        desired_entries: dict[str, dict[str, Any]] = {}
        for entry in manifest["skills"]:
            name = entry["name"]
            link_target = None
            if mode == "symlink":
                permanent_source = render_root / args.target / "skills" / name
                link_target = os.path.relpath(str(permanent_source), str(destination))
            desired_entries[name] = {
                "files": entry["files"],
                "link_target": link_target,
                "source": entry["source"],
                "version": entry["version"],
            }

        old_entries = old_lock["skills"] if old_lock is not None else {}
        old_mode = old_lock["mode"] if old_lock is not None else "copy"
        actions: list[tuple[str, str]] = []
        conflicts: list[str] = []
        for name in sorted(set(old_entries) | set(desired_entries)):
            installed_path = destination / name
            old_entry = old_entries.get(name)
            desired_entry = desired_entries.get(name)
            matches_old = (
                old_entry is not None and installed_matches(installed_path, old_entry, old_mode)
            )
            matches_desired = (
                desired_entry is not None and installed_matches(installed_path, desired_entry, mode)
            )

            if old_entry is None:
                if not installed_path.exists() and not installed_path.is_symlink():
                    actions.append(("add", name))
                elif matches_desired:
                    actions.append(("adopt", name))
                elif args.force:
                    actions.append(("replace", name))
                else:
                    conflicts.append(f"{name}: existing path is not managed")
            elif desired_entry is None:
                if not installed_path.exists() and not installed_path.is_symlink():
                    actions.append(("forget", name))
                elif matches_old or installed_link_identity_matches(installed_path, old_entry, old_mode) or args.force:
                    actions.append(("remove", name))
                else:
                    conflicts.append(f"{name}: locally modified managed skill blocks removal")
            elif matches_desired:
                if old_entry != desired_entry or old_mode != mode:
                    actions.append(("record", name))
            elif matches_old or args.force:
                actions.append(("update", name))
            else:
                conflicts.append(f"{name}: locally modified managed skill blocks update")

        new_lock = {
            "$schema": LOCK_SCHEMA_URL,
            "adapter_sha256": manifest["adapter_sha256"],
            "format_version": 1,
            "mode": mode,
            "registry_sha256": sha256_file(REGISTRY_PATH),
            "rendered_files": rendered_files,
            "skills": desired_entries,
            "target": args.target,
        }
        lock_changed = old_lock != new_lock
        render_needs_write = False
        if mode == "symlink":
            permanent_target = render_root / args.target
            current_rendered_files = directory_files(permanent_target)
            if current_rendered_files != rendered_files:
                if current_rendered_files is None:
                    if not permanent_target.exists() and not permanent_target.is_symlink():
                        render_needs_write = True
                    elif args.force:
                        render_needs_write = True
                    else:
                        conflicts.append("symlink render path is not a managed directory")
                elif old_lock is not None and old_lock["mode"] == "symlink":
                    if current_rendered_files == old_lock["rendered_files"] or args.force:
                        render_needs_write = True
                    else:
                        conflicts.append("symlink render tree has local modifications")
                elif args.force:
                    render_needs_write = True
                else:
                    conflicts.append("symlink render tree exists but is not managed by this lockfile")
        for action, name in actions:
            print(f"{action} {name}")
        if lock_changed:
            print(f"write {LOCK_FILENAME}")
        if render_needs_write:
            print(f"render {render_root / args.target}")
        if conflicts:
            raise SkillCtlError("installation conflicts:\n- " + "\n- ".join(conflicts))
        if args.check:
            if actions or lock_changed or render_needs_write:
                raise SkillCtlError(f"installation is stale: {destination}")
            print(f"checked {args.target}: {destination}")
            return
        if args.dry_run:
            print(f"dry-run {args.target}: {destination}")
            return
        if not actions and not lock_changed and not render_needs_write:
            print(f"unchanged {args.target}: {destination}")
            return

        if mode == "symlink" and render_needs_write:
            render_target_path = render_root / args.target
            render_target_path.parent.mkdir(parents=True, exist_ok=True)
            remove_managed_path(render_target_path)
            shutil.copytree(rendered_target, render_target_path)

        destination.mkdir(parents=True, exist_ok=True)
        for action, name in actions:
            installed_path = destination / name
            if action == "remove":
                remove_managed_path(installed_path)
            elif action in {"add", "replace", "update"}:
                if mode == "copy":
                    replace_with_copy(rendered_target / "skills" / name, installed_path)
                else:
                    replace_with_symlink(desired_entries[name]["link_target"], installed_path)
        write_json_atomic(lock_path, new_lock)
        print(f"synced {args.target}: {destination}")


def add_install_parser(subparsers: Any, name: str) -> None:
    install_parser = subparsers.add_parser(
        name, help="install or synchronize a managed target skill set"
    )
    install_parser.add_argument("--target", required=True, help="target id")
    install_parser.add_argument("--scope", choices=("user", "project"), default="user")
    install_parser.add_argument("--destination", type=Path, help="override the skills directory")
    install_parser.add_argument("--home", type=Path, help="override the home used for user scope")
    install_parser.add_argument(
        "--project-root", type=Path, help="override the root used for project scope"
    )
    install_parser.add_argument("--mode", choices=("copy", "symlink"))
    install_parser.add_argument(
        "--render-root", type=Path, default=ROOT / "dist", help="persistent symlink source root"
    )
    install_parser.add_argument("--dry-run", action="store_true", help="print without writing")
    install_parser.add_argument("--check", action="store_true", help="fail if synchronization is needed")
    install_parser.add_argument("--force", action="store_true", help="replace conflicting managed paths")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="skillctl")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("validate", help="validate registry, adapters, skills, and resources")

    render_parser = subparsers.add_parser("render", help="render target-specific distributions")
    render_parser.add_argument("--target", default="all", help="target id or 'all'")
    render_parser.add_argument("--output", type=Path, default=ROOT / "dist")
    render_parser.add_argument("--check", action="store_true", help="fail when output differs")
    add_install_parser(subparsers, "install")
    add_install_parser(subparsers, "sync")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "validate":
            registry = validate_repository()
            print(f"validated {len(registry['skills'])} skills and {len(registry['targets'])} targets")
        elif args.command == "render":
            render(args.target, args.output, check=args.check)
        elif args.command in {"install", "sync"}:
            if args.dry_run and args.check:
                raise SkillCtlError("--dry-run and --check cannot be used together")
            sync_install(args)
        else:
            raise SkillCtlError(f"unsupported command: {args.command}")
    except SkillCtlError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
