"""Portable, hook-free helper for the adapted planning-with-files workflow."""

import argparse
from datetime import date
import os
from pathlib import Path
import re
import sys


FILES = ("task_plan.md", "findings.md", "progress.md")
TEMPLATES = Path(__file__).resolve().parents[1] / "assets" / "templates"
PLAN_ID = re.compile(r"[a-z0-9][a-z0-9-]{0,95}\Z")
STATUS = re.compile(r"- \*\*Status:\*\* (pending|in_progress|complete)\s*\Z")


def planning_root(root):
    path = root / ".planning"
    if path.is_symlink():
        raise ValueError(".planning must be a real directory, not a symlink")
    if path.exists() and not path.is_dir():
        raise ValueError(".planning is not a directory")
    return path


def named_plans(root):
    parent = planning_root(root)
    if not parent.exists():
        return []
    return sorted(
        p for p in parent.iterdir()
        if not p.is_symlink() and p.is_dir() and (p / FILES[0]).is_file()
    )


def resolve(root, selector):
    if selector is not None:
        if not PLAN_ID.fullmatch(selector):
            raise ValueError("invalid plan ID; use a directory name from list, or root")
        path = root if selector == "root" else planning_root(root) / selector
        if path.is_symlink() or not (path / FILES[0]).is_file():
            raise ValueError("selected plan does not exist; no other plan was substituted")
        return path
    plans = named_plans(root)
    if len(plans) > 1:
        raise ValueError("multiple named plans; pass --plan-id explicitly")
    if plans:
        return plans[0]
    if (root / FILES[0]).is_file():
        return root
    raise ValueError("no plan found; initialize a task or select an existing plan")


def initialize(root, title, slug):
    if not title.strip() or "\n" in title or "\r" in title:
        raise ValueError("task name must be a non-empty single line")
    if slug is None:
        slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:60].rstrip("-")
        slug = slug or "task"
    if not PLAN_ID.fullmatch(slug) or len(slug) > 60:
        raise ValueError("slug must contain 1-60 lowercase ASCII letters, digits, or hyphens")
    # Read all templates before creating the destination.
    contents = {name: (TEMPLATES / name).read_text(encoding="utf-8") for name in FILES}
    today = date.today().isoformat()
    contents[FILES[0]] = contents[FILES[0]].replace("[Brief Description]", title)
    contents[FILES[2]] = contents[FILES[2]].replace("[DATE]", today)
    parent = planning_root(root)
    parent.mkdir(exist_ok=True)
    base = today + "-" + slug
    suffix = 1
    while True:
        path = parent / (base if suffix == 1 else base + "-" + str(suffix))
        try:
            path.mkdir()
            break
        except FileExistsError:
            suffix += 1
    for name, content in contents.items():
        with (path / name).open("x", encoding="utf-8") as stream:
            stream.write(content)
    print("PLAN_ID=" + path.name)
    print(path)


def phase_states(text):
    phases = []
    current = None
    fence = None
    for line in text.splitlines():
        stripped = line.strip()
        marker = re.match(r"^(`{3,}|~{3,})", stripped)
        if fence:
            if re.fullmatch(re.escape(fence[0]) + "{" + str(len(fence)) + ",}", stripped):
                fence = None
            continue
        if marker:
            fence = marker.group(1)
            continue
        if re.match(r"^#{1,3}\s", line):
            current = None
            if re.match(r"^### Phase \d+:\s*\S", line):
                current = {"heading": line[4:], "statuses": [], "unchecked": False}
                phases.append(current)
        if current is not None:
            match = STATUS.fullmatch(stripped)
            if match:
                current["statuses"].append(match.group(1))
            if re.match(r"^[-*+] \[ \]", stripped):
                current["unchecked"] = True
    if not phases:
        raise ValueError("no phases found; use ### Phase N: Title headings")
    for phase in phases:
        if len(phase["statuses"]) != 1:
            raise ValueError(phase["heading"] + ": expected exactly one valid status line")
    return phases


def check(path):
    phases = phase_states((path / FILES[0]).read_text(encoding="utf-8"))
    completed = sum(p["statuses"] == ["complete"] and not p["unchecked"] for p in phases)
    print(str(completed) + "/" + str(len(phases)) + " phases complete: " + str(path))
    if completed == len(phases):
        print("All recorded phases complete; verify acceptance evidence before delivery.")
        return 0
    return 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("init", "list", "resolve", "check"):
        sub = subparsers.add_parser(command)
        sub.add_argument("--root", default=os.environ.get("PWF_PLAN_ROOT", "."))
        if command in ("resolve", "check"):
            sub.add_argument("--plan-id", default=os.environ.get("PLAN_ID"))
        if command == "init":
            sub.add_argument("title")
            sub.add_argument("--slug")
    args = parser.parse_args()
    try:
        root = Path(args.root).resolve(strict=True)
        if not root.is_dir():
            raise ValueError("project root must be an existing directory")
        if args.command == "init":
            initialize(root, args.title, args.slug)
        elif args.command == "list":
            for path in named_plans(root):
                print(path.name)
            if (root / FILES[0]).is_file():
                print("root")
        else:
            path = resolve(root, args.plan_id)
            if args.command == "check":
                return check(path)
            print(path)
        return 0
    except (OSError, ValueError) as exc:
        print("planning-with-files: " + str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
