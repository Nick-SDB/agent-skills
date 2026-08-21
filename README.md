# agent-skills

A portable collection of 16 Agent Skills with deterministic distributions for Codex, Claude Code, and Kimi Code CLI.

## Repository layout

```text
registry.json                    canonical skill and target manifest
schemas/                         JSON Schemas for source and rendered manifests
skills/<category>/<name>/        portable skill sources
targets/                         target discovery and invocation metadata
tools/skillctl.py                validation and deterministic renderer
tools/build_release.py           reproducible release archive builder
tests/                           isolated standard-library tests
```

Portable sources use the common `SKILL.md` format with only `name` and `description` in YAML frontmatter. Target-specific wording is kept in minimal `adapters/<target>.md` overlays and appended only while rendering. Bundled links must remain inside their skill directory, and source symlinks, host-specific absolute paths, and vendor placeholders are rejected.

## Targets

| Target | Project skills | User skills | Invocation |
|---|---|---|---|
| Claude Code | `.claude/skills` | `~/.claude/skills` | `/<skill-name>` |
| Codex | `.agents/skills` | `~/.agents/skills` | `$<skill-name>` |
| Kimi Code CLI | `.kimi/skills` | `~/.kimi/skills` | `/skill:<skill-name>` |

The three `cc-*` skills are Claude Code-specific. The thirteen general skills render for all three targets.

## Validate and render

The tooling requires Python 3.8 or newer and has no runtime package dependencies.

```bash
python3 tools/skillctl.py validate
python3 tools/skillctl.py render --target all --output dist
python3 tools/skillctl.py render --target all --output dist --check
python3 -m unittest discover -s tests -v
```

`render` builds each selected target in a temporary directory before replacing `dist/<target>`. Every distribution contains `skills/`, `manifest.json`, and the matching `manifest.schema.json`. Manifests include SHA-256 checksums for every rendered skill file. Rendering the same revision twice produces byte-identical files; `--check` exits nonzero when an existing distribution is missing, modified, or contains unexpected files.

## Install and synchronize

`install` and `sync` are idempotent aliases. Copy mode is the default; it leaves unrelated skill directories untouched and writes `agent-skills.lock.json` beside the managed skills.

```bash
# User scope using the target's standard path
python3 tools/skillctl.py install --target codex

# Project scope or an exact destination override
python3 tools/skillctl.py sync --target claude-code --scope project --project-root /path/to/project
python3 tools/skillctl.py sync --target kimi --destination /path/to/skills

# Preview or verify without writing
python3 tools/skillctl.py sync --target codex --dry-run
python3 tools/skillctl.py sync --target codex --check
```

The lockfile records the target, install mode, source metadata, and SHA-256 checksums for every managed file. Updates and removals proceed only when installed content still matches that state. A conflicting unmanaged path or local edit is preserved and reported; use `--force` only when replacing it is intentional.

Symlink mode is intended for development checkouts and points each installed skill at a persistent rendered distribution:

```bash
python3 tools/skillctl.py install --target codex --mode symlink --render-root /path/to/render-cache
```

Use a dedicated render root per independently managed checkout. `--home`, `--project-root`, `--destination`, and `--render-root` make every path explicit and support isolated automation. Omitting `--mode` during later syncs preserves the mode recorded in the lockfile.

## Add or update a skill

1. Keep the folder name and frontmatter `name` identical and lowercase-hyphenated.
2. Put purpose and trigger conditions in `description`; write the body as concise imperative instructions.
3. Put reusable documentation in `references/`, deterministic helpers in `scripts/`, and output material in `assets/` only when needed.
4. Add a target overlay only for wording that cannot remain portable.
5. Update `registry.json`, run validation and tests, then inspect each rendered target.

The repository validator enforces the same naming, frontmatter, resource-link, and 500-line limits used by the Agent Skills skill-creator workflow.

## CI and releases

Run the same core checks as CI from the repository root:

```bash
python3 -m py_compile tools/skillctl.py tools/build_release.py tests/*.py
python3 tools/skillctl.py validate
python3 tools/skillctl.py render --target all --output dist
python3 tools/skillctl.py render --target all --output dist --check
python3 -m unittest discover -s tests -v
```

The CI workflow runs on every pull request and push with a ten-minute job limit. Test subprocesses also have explicit deadlines, so a stalled renderer, installer, or archive build fails instead of waiting indefinitely.

Build the three target archives and their checksum manifest with:

```bash
python3 tools/build_release.py --output release
(cd release && sha256sum --check SHA256SUMS)       # Linux
(cd release && shasum -a 256 --check SHA256SUMS)  # macOS
```

Each archive has sorted members, normalized ownership, permissions, and timestamps, and a gzip header with a fixed timestamp. Building the same revision twice produces byte-identical archives and `SHA256SUMS`. Tags matching `v*` run `.github/workflows/tag-artifacts.yml`, verify the checksums, and upload the files as a workflow artifact. The workflow does not create or publish a GitHub release.
