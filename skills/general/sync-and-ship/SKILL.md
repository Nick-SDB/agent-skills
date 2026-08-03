---
name: sync-and-ship
description: Synchronize a repository code map with the actual file tree, then prepare an approved commit and optional push. Use after indexed files or project phase state change, or when documentation drift is suspected.
---

# Synchronize and Ship a Code Map

Treat `docs/code_map.md` as the index of the repository's configured source and entry-point directories. Detect the repository's native root agent instruction file rather than assuming a vendor-specific filename.

## Check prerequisites

1. Confirm the instruction file and `docs/code_map.md` exist.
2. Read both files to identify indexed directories, tag vocabulary, hard rules, and current state.
3. Stop if the map format is ambiguous or existing user changes would be overwritten.

## Detect drift

1. Enumerate persistent files under every indexed directory.
2. Extract mapped paths from the documented trees.
3. Classify files as missing from the map, stale in the map, or unchanged.
4. Verify a stale entry is truly deleted rather than renamed before removing it.
5. Inspect new documentation and archived specifications for cross-reference updates.

## Update documentation

- Read enough of each missing file to state its intent.
- Insert entries in the appropriate section and preserve established ordering.
- Remove verified stale entries.
- Update current-state tables only when repository evidence supports the change.
- Keep existing descriptions unchanged unless their purpose changed.
- Keep hard rules identical in the instruction file and code map.
- Keep the instruction file under 100 lines.

## Verify

1. Confirm every indexed file appears exactly once and every mapped path exists.
2. Confirm hard rules and phase state agree across both files.
3. Review the complete diff and run documentation checks supplied by the repository.

## Ship with authorization

1. Inspect recent commit style and propose a focused message.
2. Obtain user approval before committing.
3. Stage only the intended documentation changes.
4. Commit without adding vendor-specific attribution unless repository policy requires it.
5. Push only when the user explicitly requests it, a remote exists, and the branch target is confirmed.

Never force-push or overwrite unrelated instruction-file content. Report drift found, files updated, verification results, commit hash, and push status.
