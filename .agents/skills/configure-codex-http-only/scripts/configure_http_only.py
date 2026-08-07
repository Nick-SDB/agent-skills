#!/usr/bin/env python3
"""Configure Codex to use HTTP/SSE instead of WebSocket."""

from __future__ import annotations

import argparse
import datetime as dt
import os
from pathlib import Path
import re
import shutil
import stat
import sys
import tempfile

try:
    import tomllib
except ModuleNotFoundError:  # Python < 3.11
    tomllib = None


PROVIDER_ID = "openai_http"
PROVIDER_HEADER = f"[model_providers.{PROVIDER_ID}]"
PROVIDER_VALUES = {
    "name": '"OpenAI HTTP Only"',
    "wire_api": '"responses"',
    "supports_websockets": "false",
    "requires_openai_auth": "true",
}
CONFLICTING_AUTH_KEYS = {"env_key", "experimental_bearer_token"}

TABLE_RE = re.compile(r"^\s*\[\[?.+?\]?\]\s*(?:#.*)?$")
ROOT_PROVIDER_RE = re.compile(r"^\s*model_provider\s*=")
ASSIGNMENT_RE = re.compile(r"^\s*([A-Za-z0-9_-]+)\s*=")
EXACT_PROVIDER_RE = re.compile(
    rf"^\s*\[model_providers\.{re.escape(PROVIDER_ID)}\]\s*(?:#.*)?$"
)
NESTED_AUTH_RE = re.compile(
    rf"^\s*\[model_providers\.{re.escape(PROVIDER_ID)}\.auth\]\s*(?:#.*)?$"
)


class ConfigError(RuntimeError):
    pass


def default_config_path() -> Path:
    codex_home = os.environ.get("CODEX_HOME")
    base = Path(codex_home).expanduser() if codex_home else Path.home() / ".codex"
    return base / "config.toml"


def parse_toml(text: str, label: str) -> dict | None:
    if tomllib is None:
        return None
    try:
        return tomllib.loads(text)
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"{label} is not valid TOML: {exc}") from exc


def effective_http_only_text(text: str) -> bool:
    lines = text.splitlines()
    first_table = next((i for i, line in enumerate(lines) if TABLE_RE.match(line)), len(lines))
    root_ok = any(
        re.match(r'^\s*model_provider\s*=\s*"openai_http"\s*(?:#.*)?$', line)
        for line in lines[:first_table]
    )
    block = locate_provider_block(lines)
    if not root_ok or block is None:
        return False

    start, end = block
    values = {}
    for line in lines[start + 1 : end]:
        match = re.match(r"^\s*([A-Za-z0-9_-]+)\s*=\s*(.*?)\s*(?:#.*)?$", line)
        if match:
            values[match.group(1)] = match.group(2)
    return all(values.get(key) == value for key, value in PROVIDER_VALUES.items())


def effective_http_only(data: dict | None, text: str) -> bool:
    if data is None:
        return effective_http_only_text(text)
    provider = data.get("model_providers", {}).get(PROVIDER_ID, {})
    return (
        data.get("model_provider") == PROVIDER_ID
        and provider.get("name") == "OpenAI HTTP Only"
        and provider.get("wire_api") == "responses"
        and provider.get("supports_websockets") is False
        and provider.get("requires_openai_auth") is True
    )


def newline_for(text: str) -> str:
    return "\r\n" if "\r\n" in text else "\n"


def locate_provider_block(lines: list[str]) -> tuple[int, int] | None:
    start = next((i for i, line in enumerate(lines) if EXACT_PROVIDER_RE.match(line)), None)
    if start is None:
        return None
    end = len(lines)
    for i in range(start + 1, len(lines)):
        if TABLE_RE.match(lines[i]):
            end = i
            break
    return start, end


def detect_conflicting_auth(lines: list[str], block: tuple[int, int] | None) -> None:
    if any(NESTED_AUTH_RE.match(line) for line in lines):
        raise ConfigError(
            f"{PROVIDER_ID} already has a nested auth table; refusing to replace its authentication."
        )
    if block is None:
        return
    start, end = block
    for line in lines[start + 1 : end]:
        match = ASSIGNMENT_RE.match(line)
        if match and match.group(1) in CONFLICTING_AUTH_KEYS:
            raise ConfigError(
                f"{PROVIDER_ID} already sets {match.group(1)}; refusing to replace its authentication."
            )


def set_root_provider(lines: list[str], nl: str) -> list[str]:
    first_table = next((i for i, line in enumerate(lines) if TABLE_RE.match(line)), len(lines))
    root_matches = [i for i in range(first_table) if ROOT_PROVIDER_RE.match(lines[i])]
    if root_matches:
        lines[root_matches[0]] = f'model_provider = "{PROVIDER_ID}"{nl}'
        return lines

    insertion = 0
    if lines and lines[0].startswith("\ufeff"):
        lines[0] = lines[0].lstrip("\ufeff")
        lines.insert(0, f'\ufeffmodel_provider = "{PROVIDER_ID}"{nl}')
        insertion = 1
    else:
        lines.insert(0, f'model_provider = "{PROVIDER_ID}"{nl}')
        insertion = 1

    if len(lines) > insertion and lines[insertion].strip():
        lines.insert(insertion, nl)
    return lines


def set_provider_table(lines: list[str], nl: str) -> list[str]:
    block = locate_provider_block(lines)
    detect_conflicting_auth(lines, block)
    desired = [f"{key} = {value}{nl}" for key, value in PROVIDER_VALUES.items()]

    if block is None:
        if lines and lines[-1].strip():
            lines.append(nl)
        lines.append(f"{PROVIDER_HEADER}{nl}")
        lines.extend(desired)
        return lines

    start, end = block
    preserved = []
    for line in lines[start + 1 : end]:
        match = ASSIGNMENT_RE.match(line)
        if match and match.group(1) in PROVIDER_VALUES:
            continue
        preserved.append(line)
    return lines[: start + 1] + desired + preserved + lines[end:]


def render_updated(text: str) -> str:
    nl = newline_for(text)
    lines = text.splitlines(keepends=True)
    if text and lines and not lines[-1].endswith(("\n", "\r")):
        lines[-1] += nl
    lines = set_root_provider(lines, nl)
    lines = set_provider_table(lines, nl)
    updated = "".join(lines)
    data = parse_toml(updated, "updated configuration")
    if not effective_http_only(data, updated):
        raise ConfigError("updated configuration did not produce the required HTTP-only provider")
    return updated


def backup_path(path: Path) -> Path:
    stamp = dt.datetime.now().astimezone().strftime("%Y%m%d-%H%M%S")
    candidate = path.with_name(f"{path.name}.bak-{stamp}")
    counter = 1
    while candidate.exists():
        candidate = path.with_name(f"{path.name}.bak-{stamp}-{counter}")
        counter += 1
    return candidate


def atomic_write(path: Path, text: str, original_mode: int | None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(tmp_path, original_mode if original_mode is not None else 0o600)
        os.replace(tmp_path, path)
    finally:
        if tmp_path.exists():
            tmp_path.unlink()


def run(path: Path, check: bool, dry_run: bool) -> int:
    exists = path.exists()
    original = path.read_text(encoding="utf-8") if exists else ""
    current = parse_toml(original, "existing configuration") if original else {}

    if check:
        if effective_http_only(current, original):
            print(f"HTTP-only Codex provider is configured: {path}")
            return 0
        print(f"HTTP-only Codex provider is not configured: {path}")
        return 1

    updated = render_updated(original)
    if updated == original:
        print(f"No change needed; HTTP-only Codex provider is already configured: {path}")
        return 0
    if dry_run:
        print(f"Would configure HTTP-only Codex provider in: {path}")
        return 0

    original_mode = stat.S_IMODE(path.stat().st_mode) if exists else None
    backup = None
    if exists:
        backup = backup_path(path)
        shutil.copy2(path, backup)
    atomic_write(path, updated, original_mode)

    written = path.read_text(encoding="utf-8")
    result = parse_toml(written, "written configuration")
    if not effective_http_only(result, written):
        raise ConfigError("post-write validation failed")

    print(f"Configured HTTP-only Codex provider: {path}")
    if backup:
        print(f"Backup: {backup}")
    print("Fully quit and reopen Codex Desktop, or restart the CLI session.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Configure Codex Responses transport to use HTTP/SSE instead of WebSocket."
    )
    parser.add_argument("--config", type=Path, default=default_config_path())
    parser.add_argument("--check", action="store_true", help="inspect without changing files")
    parser.add_argument("--dry-run", action="store_true", help="show whether a change is needed")
    args = parser.parse_args()
    try:
        return run(args.config.expanduser().resolve(), args.check, args.dry_run)
    except (ConfigError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
