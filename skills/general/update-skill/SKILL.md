---
name: update-skill
description: Update, create, or sync a skill across its canonical repository, the cloud remote, and local installs. Use when revising or creating a skill, syncing a skill repo with its remote (同步/云端同步), pushing skill changes up, pulling updates down and installing them, or shipping a skill after content changes.
---

# Update a Skill

One skill covers the full skill lifecycle: edit the canonical source, sync it to the cloud, and install it locally. The canonical repository is the single source of truth; the installed copy is a read-only artifact updated only through `skillctl install`.

## Pre-flight check

Establish the current state before editing anything:

1. `git status --short` — confirm the repository is clean and identify uncommitted changes.
2. `python3 tools/skillctl.py install --target <target> --scope user --home <home> --check` — compare the local install lock against the registry to surface divergence, including manual edits to installed skills.
3. Confirm the remote and branch: `git remote -v` and the current branch.

Never edit an installed skill directly; it is read-only. All changes go through the canonical source and `skillctl install`.

## Edit the canonical skill

1. Change the canonical `SKILL.md` first, under `skills/<category>/<name>/`.
2. Keep frontmatter limited to `name` and `description`.
3. Preserve required scripts, references, and assets.
4. Keep the body concise and imperative, free of host-specific tool names or local absolute paths.

## Version the change

Bump the version in `registry.json` deterministically; do not deliberate:

- Content-only change to the `SKILL.md` body → patch +1 (1.0.0 → 1.0.1).
- Structural change (added/removed resources, scripts, targets, or merging skills) → minor +1 (1.0.0 → 1.1.0).
- Removing a skill → delete its registry entry and source directory.

## Validate and render

1. `python3 tools/skillctl.py validate` — must pass.
2. `python3 tools/skillctl.py render --target all --output dist`, then `... --check` — rebuild and verify the distribution.
3. Run repository tests if present.

## Commit and push

1. Show the diff summary (`git diff --stat`).
2. Commit with a focused message. When the user's instruction already includes the action (for example "云端同步" or "push"), treat that as authorization and do not re-ask.
3. Push to the confirmed branch. Never force-push.

## Install locally

1. `python3 tools/skillctl.py install --target <target> [--scope user] --home <home>` — sync the installed copy from the rendered distribution.
2. Use `--dry-run` first to preview, and `--check` to verify consistency.

## Pull cloud updates

Reverse direction, for pulling remote updates and installing them:

1. `git fetch origin`; inspect with `git status` and `git log HEAD..origin/<branch> --oneline`.
2. Pull fast-forward only (`git pull --ff-only origin <branch>`); on conflict, stop and report instead of rewriting.
3. Re-run `validate` and `render --check`, then install locally (confirm the install target first).

## Fast path

For a content-only `SKILL.md` edit, run the steps in order in one pass without deliberation: pre-flight check → edit → patch bump → validate → render `--check` → commit → push → install.

## Report

Report: canonical files changed, version changes, validation and render results, commit hash, push status, install target, and any remaining divergence.

## Anti-patterns

- Editing an installed skill directly.
- Skipping the pre-flight check and discovering divergence mid-process.
- Committing or pushing without the user's instruction, or without confirming the branch.
- Force-pushing or rewriting remote history.
- Skipping validation or render and installing an inconsistent skill.
- Silently overwriting local edits or unmanaged files.
