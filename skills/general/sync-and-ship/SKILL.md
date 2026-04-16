# sync-and-ship

Sync the project's documentation index with the actual file tree, then commit and push.

This skill performs three things in sequence:
1. Update `docs/code_map.md` to reflect the current `src/` and `scripts/` file tree
2. Update `CLAUDE.md` current-state table if needed
3. Suggest a commit message, get user approval, commit (with co-author tag) and push

---

## What is the code map?

`docs/code_map.md` is the canonical index of every library module and runnable script in the project. It contains:

- **Tag legend** — phase tags (`[P0]`..`[P3]`) and kind tags (`[LIB]`/`[RUN]`/`[SHIM]`/`[DOC]`/`[DATA]`)
- **Quick state** — one-row-per-phase status table with headline artifacts
- **Library code tree** — every file under `src/` with a one-line purpose
- **Entry points tree** — every file under `scripts/` with a one-line purpose
- **Pipelines** — how to re-run each phase from scratch
- **Key concepts** — domain terms an agent must know
- **Hard rules** — duplicated from `CLAUDE.md` for safety
- **Documentation cross-references** — pointers to other docs
- **When to update this map** — self-propagating triggers

The invariant is: **if a file lives under `src/` or `scripts/`, it must appear in the map**. No orphans allowed.

`CLAUDE.md` is the always-loaded tripwire (<100 lines). It contains hard rules, a "READ THIS FIRST" pointer to `code_map.md`, a "Maintaining the map" responsibility section, and a current-state table.

---

## When to use

- After adding, renaming, or deleting files under `src/` or `scripts/`
- After a significant feature lands (new phase, new subsystem, restructured directories)
- Periodically to catch drift between code and docs
- When the user says "sync the map", "update code_map", "ship it", or invokes `/sync-and-ship`

## When NOT to use

- If `docs/code_map.md` doesn't exist — use the `project-code-map` skill to create it first
- If the only changes are to non-indexed files (docs, configs, tests)
- If the user explicitly says "don't update docs"

---

## Steps

### Step 1: Verify files exist

Check that both `CLAUDE.md` and `docs/code_map.md` exist. If either is missing, tell the user and stop.

### Step 2: Scan the file tree

Use **Glob** to find all files under the indexed directories (typically `src/` and `scripts/`):
- `src/**/*.py`
- `scripts/**/*.py`
- `scripts/**/*.sh`
- `scripts/**/*.md` (README files in script dirs)

For each file, check if it appears in `docs/code_map.md`. Build two lists:
- **Missing from map**: files on disk but not in code_map.md
- **Stale in map**: files in code_map.md but not on disk

### Step 3: Update `docs/code_map.md`

For each missing file:
1. **Read** the first 30 lines to get the module docstring / purpose
2. Determine the appropriate phase tag (`[P0]`..`[P3]`) and kind tag (`[LIB]`/`[RUN]`/`[SHIM]`/`[DOC]`/`[DATA]`)
3. Write a one-line purpose statement (say *what the file is for*, not *what functions it contains*)
4. Insert the entry in the correct tree section, maintaining alphabetical/logical order within its directory

For each stale entry:
- Remove the line from the map

Also check:
- **Quick state table** — update if phase status has changed (read recent git log for clues)
- **Documentation cross-references** — add any new `docs/*.md` files
- **OpenSpec archive list** — add any new archives under `openspec/changes/archive/`

Keep descriptions of **existing, unchanged** entries as-is. Only touch what actually changed.

### Step 4: Update `CLAUDE.md`

Check the current-state table in `CLAUDE.md`. If the phase status or headline has changed (based on what you learned in Step 3), update it. Keep `CLAUDE.md` under 100 lines.

### Step 5: Suggest commit message

1. Run `git log --oneline -5` to see the recent commit message style
2. Run `git diff --stat` to see what changed
3. Draft a commit message following the project's convention (typically `feat:`, `fix:`, `chore:`, `docs:`)
4. Present the message to the user using **AskUserQuestion** with options:
   - "Use this message" (recommended)
   - "Edit message" (let user provide their own)

### Step 6: Commit and push

1. Stage the changed files: `git add CLAUDE.md docs/code_map.md` (and any other modified tracked files)
2. Commit with the approved message, appending:
   ```
   Co-Authored-By: Claude <noreply@anthropic.com>
   ```
3. Check if a remote exists: `git remote -v`
4. If remote exists, push: `git push origin <current-branch>`
5. Report the commit hash and push status

---

## Guardrails

- **Never overwrite user content in CLAUDE.md** beyond the current-state table. Hard rules, "Maintaining the map" section, and other content are user-authored.
- **Never remove a file entry without verifying** the file is truly gone from disk (not just renamed).
- **Never add files from outside the indexed directories** (`src/`, `scripts/`) unless the user asks.
- **Always show the commit message for approval** before committing. Never auto-commit.
- **Never force-push.** Use `git push`, not `git push --force`.
- The one-line purpose must say *what the file is for*, not *what functions it contains*.
- Keep `CLAUDE.md` under 100 lines. If it's over, warn the user.
