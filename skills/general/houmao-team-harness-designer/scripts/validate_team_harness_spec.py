"""Validate the structural contract of a Houmao team-harness dossier."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


REQUIRED_SECTIONS = (
    "Objectives, Scope, and Acceptance Criteria",
    "Assumptions, Decisions, and Open Questions",
    "Domain Vocabulary",
    "Roles, Capabilities, and Ownership",
    "Team Topology",
    "Primary Work Flow",
    "Design Session State Machine",
    "Team Lifecycle State Machine",
    "Work Item Lifecycle State Machine",
    "Transition Contract",
    "Scheduling, Queueing, and Concurrency",
    "Message Contract",
    "Persistence, Identity, and Recovery",
    "Runtime Safety and Operations",
    "Validation Plan",
    "Authorization Boundary",
    "Revision Deltas",
)

MERMAID_SECTIONS = (
    "Team Topology",
    "Primary Work Flow",
    "Design Session State Machine",
    "Team Lifecycle State Machine",
    "Work Item Lifecycle State Machine",
)

REQUIRED_TABLE_HEADERS = (
    (
        "Current state",
        "Event",
        "Guard",
        "Next state",
        "Owner",
        "Persistence",
        "Side effect",
        "Failure path",
        "Recovery",
    ),
    (
        "Subject",
        "Sender",
        "Recipient policy",
        "Triggered transition",
        "Required payload",
        "Delivery",
        "Deduplication",
        "Timeout",
        "Failure result",
    ),
)

PLACEHOLDER_RE = re.compile(r"\[REPLACE:[^\]\n]+\]")
MATURITY_RE = re.compile(r"(?im)^Maturity:\s*(D[012])\s*$")
HEADING_RE = re.compile(r"(?m)^##\s+(.+?)\s*$")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check required sections, diagrams, tables, maturity, and placeholders."
    )
    parser.add_argument("dossier", help="Markdown dossier path, or - to read stdin")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable results")
    return parser.parse_args()


def read_text(source: str) -> str:
    if source == "-":
        return sys.stdin.read()
    return Path(source).read_text(encoding="utf-8")


def sections(text: str) -> dict[str, str]:
    matches = list(HEADING_RE.finditer(text))
    result: dict[str, str] = {}
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        result[match.group(1).strip()] = text[start:end]
    return result


def normalized_table_headers(text: str) -> set[tuple[str, ...]]:
    headers: set[tuple[str, ...]] = set()
    lines = text.splitlines()
    for index, line in enumerate(lines[:-1]):
        if not line.lstrip().startswith("|"):
            continue
        separator = lines[index + 1]
        if not re.fullmatch(r"\s*\|(?:\s*:?-+:?\s*\|)+\s*", separator):
            continue
        cells = tuple(cell.strip() for cell in line.strip().strip("|").split("|"))
        headers.add(cells)
    return headers


def validate(text: str) -> tuple[str | None, list[str]]:
    errors: list[str] = []
    maturity_match = MATURITY_RE.search(text)
    maturity = maturity_match.group(1) if maturity_match else None
    if maturity is None:
        errors.append("missing exact maturity line: Maturity: D0, D1, or D2")

    found_sections = sections(text)
    for name in REQUIRED_SECTIONS:
        if name not in found_sections:
            errors.append(f"missing section: {name}")

    for name in MERMAID_SECTIONS:
        content = found_sections.get(name, "")
        if not re.search(r"```mermaid\s+.+?```", content, flags=re.DOTALL):
            errors.append(f"section lacks a Mermaid block: {name}")

    state_blocks = len(re.findall(r"```mermaid\s+stateDiagram(?:-v2)?\b", text))
    if state_blocks < 3:
        errors.append("fewer than three Mermaid state-machine blocks")

    headers = normalized_table_headers(text)
    for required in REQUIRED_TABLE_HEADERS:
        if required not in headers:
            errors.append("missing table header: " + " | ".join(required))

    placeholders = sorted(set(PLACEHOLDER_RE.findall(text)))
    if placeholders:
        preview = ", ".join(placeholders[:5])
        suffix = " ..." if len(placeholders) > 5 else ""
        errors.append(f"unresolved template markers: {preview}{suffix}")

    return maturity, errors


def main() -> int:
    args = parse_args()
    try:
        text = read_text(args.dossier)
    except (OSError, UnicodeError) as exc:
        if args.json:
            print(json.dumps({"ok": False, "errors": [str(exc)]}, ensure_ascii=False))
        else:
            print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    maturity, errors = validate(text)
    if args.json:
        print(
            json.dumps(
                {"ok": not errors, "maturity": maturity, "errors": errors},
                ensure_ascii=False,
                indent=2,
            )
        )
    elif errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
    else:
        print(f"OK: structurally valid Houmao team-harness dossier ({maturity})")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
