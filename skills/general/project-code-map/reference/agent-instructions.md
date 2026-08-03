# Project Name

Briefly state what the project does, who uses it, and what an agent must preserve.

## Read this first

Read `docs/code_map.md` before changing source or runnable scripts. It is the canonical index of project structure, workflows, terminology, and current phase state.

## Hard rules

- **DO NOT** replace this example with generic rules; derive three to eight concrete constraints from the target project.
- **DO NOT** modify generated or vendored paths identified by the project.
- **DO NOT** run destructive operations without explicit authorization.

## Maintain the map

Every agent that creates, renames, or deletes a persistent file in an indexed directory must update `docs/code_map.md` in the same change.

- Add new files with the correct tags and a one-line intent description.
- Update paths when files move.
- Remove entries only after confirming the file is gone.
- Update phase state when a project phase changes.
- Keep hard rules synchronized between this file and the code map.

Temporary artifacts belong in an operating-system temporary directory or another ignored scratch location, never beside persistent source. If a persistent indexed file is missing from the map, add it or remove it with authorization.

## Current state

Include a concise phase or subsystem table only when the project uses one.

Return to `docs/code_map.md` for file locations and exact project commands.
