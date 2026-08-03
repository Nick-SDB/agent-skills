---
name: project-code-map
description: Create a concise agent instruction file plus docs/code_map.md for rapid repository orientation. Use when a project lacks agent-readable entry guidance or its source and script layout is costly to rediscover.
---

# Create a Project Code Map

Create two coordinated files:

1. The project's native root agent instruction file: a short, always-loaded tripwire.
2. `docs/code_map.md`: a detailed on-demand index of source modules, entry points, workflows, terminology, and hard rules.

Use `AGENTS.md` for a cross-agent project unless the repository or user selects another supported instruction filename. Do not create duplicate instruction systems.

Read [reference/agent-instructions.md](reference/agent-instructions.md) and [reference/code_map.md](reference/code_map.md) as structural examples. Adapt all content to the target project.

## Inspect safely

1. Confirm the project root using repository and build markers.
2. Detect existing instruction files and `docs/code_map.md`.
3. Preserve existing content. If replacement or a material merge is needed, present the conflict and obtain a decision before writing.
4. Infer project facts from existing documentation and code; ask only for missing hard rules or choices that change the result.

## Gather the model

Determine:

- Project name, purpose, and audience.
- Three to eight safety-critical rules.
- Optional phases or subsystems and their status.
- A consistent tag vocabulary.
- Source and entry-point directories to index.
- Repeatable build, test, deployment, or data-pipeline commands.

Scan every non-temporary file in the selected directories. Read enough of each file to state its purpose, not merely its symbols.

## Write the code map

Include:

1. Purpose and audience.
2. Tag legend.
3. Current state or project summary.
4. Complete tagged source tree with one-line purposes.
5. Complete tagged entry-point tree.
6. Reproducible pipelines.
7. Key terminology.
8. Hard rules.
9. Documentation cross-references.
10. Explicit triggers for updating the map.

Maintain the invariant that every indexed file appears exactly once. Keep descriptions intent-focused and concise.

## Write the instruction file

Keep it under 100 lines. Include:

- A short project introduction.
- A prominent pointer to `docs/code_map.md`.
- The same hard rules as the map.
- A mandatory rule to update the map in the same change whenever indexed files are created, renamed, or deleted.
- Current phase state when applicable.

Require temporary artifacts to remain outside indexed source directories. When an unindexed persistent file is found, add it to the map or remove it with authorization.

## Verify

1. Check both files' line counts and readability.
2. Confirm hard rules match exactly across both files.
3. Confirm every indexed on-disk file appears once and every mapped file exists.
4. Confirm pipeline commands are exact and instruction-file references are valid.
5. Report files created, indexed-file count, hard-rule count, assumptions, and requested review items.
