#!/usr/bin/env python3
"""Validate and render the agent-skills registry without third-party packages."""

from __future__ import annotations

import argparse
import hashlib
import json
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

NAME_RE = re.compile(r"^[a-z0-9-]{1,64}$")
VERSION_RE = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")
LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)
PORTABLE_LEAKS = {
    "Claude instruction filename": re.compile(r"CLAUDE\.md"),
    "Claude argument placeholder": re.compile(r"\$ARGUMENTS|\$\{CLAUDE_(?:SKILL|PROJECT)_DIR\}"),
    "Claude dynamic context": re.compile(r"!`"),
    "host-specific tool name": re.compile(r"\*\*(?:Glob|Read|Write|Bash|Grep|Agent|AskUserQuestion)\*\*"),
    "local NFS path": re.compile(r"/nfs/"),
}


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
        if len(skill_file.read_text(encoding="utf-8").splitlines()) > 500:
            errors.append(f"{source_text}: SKILL.md exceeds 500 lines")

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
    expected_files = {
        path.relative_to(expected).as_posix(): sha256_file(path)
        for path in expected.rglob("*")
        if path.is_file()
    }
    actual_files = {
        path.relative_to(actual).as_posix(): sha256_file(path)
        for path in actual.rglob("*")
        if path.is_file()
    }
    differences = []
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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="skillctl")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("validate", help="validate registry, adapters, skills, and resources")

    render_parser = subparsers.add_parser("render", help="render target-specific distributions")
    render_parser.add_argument("--target", default="all", help="target id or 'all'")
    render_parser.add_argument("--output", type=Path, default=ROOT / "dist")
    render_parser.add_argument("--check", action="store_true", help="fail when output differs")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "validate":
            registry = validate_repository()
            print(f"validated {len(registry['skills'])} skills and {len(registry['targets'])} targets")
        elif args.command == "render":
            render(args.target, args.output, check=args.check)
        else:
            raise SkillCtlError(f"unsupported command: {args.command}")
    except SkillCtlError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
