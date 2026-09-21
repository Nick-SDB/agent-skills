# agent-skills

A portable collection of Agent Skills with deterministic distributions for Codex, Claude Code, and Kimi Code CLI.

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

The three `cc-*` skills are Claude Code-specific, and `codex-check-quota` is Codex-specific. Other registered skills declare their supported targets in `registry.json`.

## Upstream attribution: planning-with-files

The [planning-with-files skill](skills/general/planning-with-files/SKILL.md) is a portable adaptation of the upstream project listed below. Its [generated attribution](skills/general/planning-with-files/references/upstream.md) records licensing, pinned revision, and local adaptations.

It maintains `task_plan.md`, `findings.md`, and `progress.md` in a named `.planning/<plan-id>/` task directory. Templates are copied unchanged from upstream; the portable instructions and Python helper are maintained here. Task records complement the project's existing milestone or handoff document, which remains managed through its own conventions and `record-progress`.

After installing through `skillctl`, invoke `$planning-with-files` in Codex, `/planning-with-files` in Claude Code, or `/skill:planning-with-files` in Kimi. For example: "Use planning-with-files for this optimization task; record acceptance criteria, experiment results, and the next action in a separate task directory."

The helper requires Python 3.8+ and supports `init`, `list`, `resolve`, and `check`. From the project root, use the installed skill directory:

```bash
PWF_SKILL_DIR="$HOME/.agents/skills/planning-with-files"
python3 "$PWF_SKILL_DIR/scripts/planning.py" init "Optimization experiment"
python3 "$PWF_SKILL_DIR/scripts/planning.py" list
python3 "$PWF_SKILL_DIR/scripts/planning.py" resolve --plan-id <printed-plan-id>
python3 "$PWF_SKILL_DIR/scripts/planning.py" check --plan-id <printed-plan-id>
```

Use the printed ID for subsequent calls; multiple named plans require explicit selection. Initialization creates a new directory without overwriting previous plans. Resume by resolving and reading the three existing files. `check` verifies recorded phase status, not implementation correctness.

**No hooks are installed.** This integration does not alter host configuration, inject context automatically, read session histories, or enable autonomous continuation. Upstream lifecycle hooks and plugin commands require a separate integration and are not included in this distribution.

## External skill imports and attribution

Use the importer for third-party skills; it records the source before the skill enters the normal validation and distribution pipeline:

```bash
python3 tools/skillctl.py import \
  --repo https://github.com/github/awesome-copilot \
  --path skills/git-commit --ref <tag-or-commit> --license-path LICENSE
python3 tools/skillctl.py provenance --check
```

The importer currently supports GitHub HTTPS repositories and single-line `name` and `description` frontmatter. Review the skill and applicable license first. Supply `--license-id` when the skill does not declare one. It downloads the skill subtree and selected license at a fixed full commit SHA, checks downloaded Git blob hashes, preserves upstream SHA-256 hashes, and registers `origin: external`. It retains only portable frontmatter and adds attribution links; it does not execute downloaded code, install hooks, commit, push, or install locally. Incompatible imports fail validation and roll back the new skill, registry, and README changes. Existing skills are never overwritten.

Each external skill contains `references/upstream.json`, generated `references/upstream.md`, and a retained license. Upstream versions and local registry versions are independent; absent upstream versions are recorded as **Not declared**. The metadata stores both original upstream hashes and reviewed local file hashes. After adapting a skill, bump its local version and run:

```bash
python3 tools/skillctl.py provenance --refresh <skill-name> --note "Describe the reviewed adaptation"
python3 tools/skillctl.py validate
```

`provenance` without flags regenerates attribution documents and the table below; `--check` is read-only. Normal `validate` also rejects missing external metadata, invalid commit IDs, changed licenses, unrecorded local changes, and stale generated citations. Validation is offline and cannot identify unmarked third-party code: always declare new external skills with `origin: external`. Existing manually maintained skills are not automatically assigned an inferred origin. To update upstream itself, review the new revision and original hashes explicitly; this first importer supports new skills, not automatic upstream replacement.

<!-- skillctl:external-sources:start -->
| Skill | Upstream | Upstream version | Commit | Local version | License |
|---|---|---|---|---|---|
| [git-commit](skills/general/git-commit/SKILL.md) | [github/awesome-copilot](https://github.com/github/awesome-copilot) | Not declared | [4f4796f0bf30](https://github.com/github/awesome-copilot/tree/4f4796f0bf30e105700f97ed8408c12b6aa95e06) | 1.0.0 | MIT |
| [planning-with-files](skills/general/planning-with-files/SKILL.md) | [OthmanAdi/planning-with-files](https://github.com/OthmanAdi/planning-with-files) | 3.20.0 | [2fbbd77ba9a7](https://github.com/OthmanAdi/planning-with-files/tree/2fbbd77ba9a74cddb9504285935ef9ae0837cdec) | 1.1.0 | MIT |
<!-- skillctl:external-sources:end -->

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
