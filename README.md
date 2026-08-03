# agent-skills

A portable collection of 11 Agent Skills with deterministic distributions for Codex, Claude Code, and Kimi Code CLI.

## Repository layout

```text
registry.json                    canonical skill and target manifest
schemas/                         JSON Schemas for source and rendered manifests
skills/<category>/<name>/        portable skill sources
targets/                         target discovery and invocation metadata
tools/skillctl.py                validation and deterministic renderer
tests/                           isolated standard-library tests
```

Portable sources use the common `SKILL.md` format with only `name` and `description` in YAML frontmatter. Target-specific wording is kept in minimal `adapters/<target>.md` overlays and appended only while rendering. Bundled links must remain inside their skill directory, and source symlinks, host-specific absolute paths, and vendor placeholders are rejected.

## Targets

| Target | Project skills | User skills | Invocation |
|---|---|---|---|
| Claude Code | `.claude/skills` | `~/.claude/skills` | `/<skill-name>` |
| Codex | `.agents/skills` | `~/.agents/skills` | `$<skill-name>` |
| Kimi Code CLI | `.kimi/skills` | `~/.kimi/skills` | `/skill:<skill-name>` |

The three `cc-*` skills are Claude Code-specific. The eight general skills render for all three targets.

## Validate and render

The tooling requires Python 3.8 or newer and has no runtime package dependencies.

```bash
python3 tools/skillctl.py validate
python3 tools/skillctl.py render --target all --output dist
python3 tools/skillctl.py render --target all --output dist --check
python3 -m unittest discover -s tests -v
```

`render` builds each selected target in a temporary directory before replacing `dist/<target>`. Every distribution contains `skills/`, `manifest.json`, and the matching `manifest.schema.json`. Manifests include SHA-256 checksums for every rendered skill file. Rendering the same revision twice produces byte-identical files; `--check` exits nonzero when an existing distribution is missing, modified, or contains unexpected files.

## Add or update a skill

1. Keep the folder name and frontmatter `name` identical and lowercase-hyphenated.
2. Put purpose and trigger conditions in `description`; write the body as concise imperative instructions.
3. Put reusable documentation in `references/`, deterministic helpers in `scripts/`, and output material in `assets/` only when needed.
4. Add a target overlay only for wording that cannot remain portable.
5. Update `registry.json`, run validation and tests, then inspect each rendered target.

The repository validator enforces the same naming, frontmatter, resource-link, and 500-line limits used by the Agent Skills skill-creator workflow.
