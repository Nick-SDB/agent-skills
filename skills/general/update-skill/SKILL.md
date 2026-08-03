---
name: update-skill
description: Update a skill in its canonical repository and synchronize an explicitly configured development copy. Use when revising an existing skill while preserving validation and version-control safety.
---

# Update a Skill

Treat the checked-out repository as the source of truth. Obtain the skill name, repository root, and optional development-copy directory from the request or repository configuration; never assume machine-specific paths.

## Locate and inspect

1. Confirm the repository root and cleanly identify the skill directory.
2. Read the canonical `SKILL.md` and every referenced resource.
3. Inspect an optional development copy without overwriting it.
4. Compare both copies and surface local divergence before editing.

## Update

1. Change the canonical skill first.
2. Keep frontmatter limited to `name` and `description`.
3. Preserve required scripts, references, and assets.
4. Keep the body concise, imperative, and free of host-specific tool names or local absolute paths.
5. Run the repository's skill validator and relevant tests.

## Synchronize and commit

1. Show the diff and validation results.
2. Synchronize an explicitly configured development copy only after confirming that it has no uncommitted divergence; otherwise stop with a conflict report.
3. Propose a focused commit message and commit only with user authorization.
4. Push only when the user explicitly requests it and the target branch is confirmed.

Report canonical files changed, synchronized destinations, validation results, and any remaining divergence.
