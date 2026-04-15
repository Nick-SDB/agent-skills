---
name: project-code-map
description: Install the CLAUDE.md + docs/code_map.md "agent-entry documentation" pattern in a project. Creates a short always-loaded CLAUDE.md tripwire at the project root and a detailed docs/code_map.md index of all library modules and runnable scripts, with phase/kind tags and mandatory "maintaining the map" responsibility rules. Use when starting a new project, when joining an existing project without an agent-readable layout index, or when a project has enough src/ + scripts/ files that new agents waste time orienting. Triggers on phrases like "set up CLAUDE.md for this project", "add a code map / file index", "make this project agent-friendly", "apply the code_map pattern", or when the user explicitly names this skill.
---

# project-code-map

A two-file documentation pattern that lets a new Claude Code agent orient in a project in under 2 minutes:

1. **`CLAUDE.md`** at the project root (50-80 lines) — auto-loaded by Claude Code on every session start. Minimal tripwire. Contains project intro, "READ THIS FIRST" pointer, hard rules, "maintaining the map" responsibility section, current state table.

2. **`docs/code_map.md`** (150-300 lines) — on-demand detailed index. Contains tag legend, quick state, library tree (`src/`) with per-file one-liners, entry-point tree (`scripts/`) with per-file one-liners, pipelines, key concepts, hard rules (redundant safety), documentation cross-refs, "when to update this map" triggers.

**Why split into two files:** CLAUDE.md is always loaded into context on session start — keeping it short keeps the cost low. code_map.md is only loaded when the agent follows the pointer, so it can be much more detailed without paying per-session context cost.

---

## When to use this skill

- Starting a new project (generate both files from scratch).
- Joining an existing project that has no CLAUDE.md or equivalent (retrofit).
- A project has ≥10 files under `src/` / `scripts/` / `lib/` and agents waste time orienting.
- The user wants strong enforcement rules around file creation ("don't leave orphan scripts in the tree").
- The user explicitly asks for this pattern by name.

## When NOT to use this skill

- Projects that already have a maintained CLAUDE.md you must preserve — ask before overwriting.
- Single-file or very small projects (the map overhead outweighs the benefit).
- Projects where the layout is purely data / configs / docs and there are no scripts/modules to index.
- Projects with a different agent-index convention already in place (e.g., `AGENTS.md`, extensive `README.md` trees). Don't duplicate.

---

## Step-by-step instructions

Follow these steps in order. Use the two files in `reference/` inside this skill directory as style and structure examples — but **adapt them to the target project**, do not blindly copy their content.

### Step 1: Confirm the target directory

Run `pwd` to see where you are. Verify you're at the project root by checking for common markers: `pyproject.toml`, `package.json`, `Cargo.toml`, `pixi.toml`, `go.mod`, `.git/`, `CMakeLists.txt`, etc. If none of these are present, ask the user to confirm that this is indeed the project root. Do not proceed from a subdirectory.

### Step 2: Check for existing files — never silently overwrite

Check whether `CLAUDE.md` or `docs/code_map.md` already exist. If either does, **stop and ask the user**:

- **Overwrite** — replace the existing file(s) entirely with the new generated version. Destructive; only do this if the user explicitly confirms.
- **Merge** — keep the existing content but add any sections from this skill that are missing. Safer; use this by default when existing content exists.
- **Abort** — don't touch the files; just report what was found and stop.

Use the **AskUserQuestion** tool for this prompt. Never guess.

### Step 3: Gather project info

Ask the user (use **AskUserQuestion** for structured answers where possible):

1. **Project name.** Suggest a default based on the repo directory name; let the user confirm or edit.
2. **One-paragraph project description.** What is this project, what's its goal, and who's it for? If the user already described it earlier in the conversation, use that; otherwise ask.
3. **Hard rules (3-8).** What are things a new agent should NEVER do? Examples:
   - "Don't modify `vendor/` — it's auto-generated"
   - "Don't push to main directly"
   - "Don't run destructive DB migrations in dev"
   - "Don't delete anything under `results/` — that's the reproducible evidence"
   - "Don't modify `openspec/specs/` directly — use a new change"
   - "Don't use `pip install` — we use `poetry` / `uv` / `pixi`"
   Prompt the user to list them. Infer rules from the conversation history when possible (e.g., if the user mentioned a bug earlier that came from touching a forbidden directory).
4. **Phase / subsystem tracking** (optional). Does this project have discrete phases like "Phase 0: baseline, Phase 1: surgery, Phase 2: pruning"? If yes, what are they and their current status (not started / in progress / archived)? If no, skip this section in CLAUDE.md.
5. **Tag vocabulary.** Default is `[LIB]` / `[RUN]` / `[SHIM]` for file kind and `[P0]` / `[P1]` / etc. for phase. Let the user override if they have different categories in mind (e.g., `[CORE]` / `[UTIL]` / `[TEST]` / `[DEPRECATED]`).
6. **Target directories to index.** Default is `src/` and `scripts/`. Ask if they want to include `lib/`, `bin/`, `tools/`, `cmd/`, `internal/`, etc.

### Step 4: Scan the codebase

Use the **Glob** tool to find all files under the directories from Step 3 (e.g., `src/**/*.py`, `scripts/**/*.sh`, `scripts/**/*.py`). For each file, use **Read** to load the first 30 lines (or the module docstring if one exists at the top) — that's usually enough to write a one-line purpose statement.

Keep a running list: `(path, phase_tag, kind_tag, one_line_purpose)`.

If the project has a large tree (> 50 files), offer to use the **Agent** tool with the Explore subagent to do the scan in parallel and report back.

### Step 5: Write `docs/code_map.md`

Create the file using the **Write** tool. Follow the section skeleton from `reference/code_map.md`:

1. **Header** — title, one-paragraph statement of what this file is and who reads it.
2. **Tag legend** — table explaining each tag used in the tree.
3. **Quick state** — if phase tracking is enabled, a status table (one row per phase). Otherwise skip or replace with a one-paragraph project summary.
4. **Library code tree** — `src/` (or equivalent) with every file, indented, tagged, one-line purpose. Use a code block with proper indentation so the tree renders cleanly.
5. **Entry points tree** — `scripts/` (or `bin/`, `tools/`) with the same format.
6. **Pipelines** — if the project has repeatable workflows (build, test, deploy, data pipelines), document them with the exact commands. Skip if not applicable.
7. **Key concepts / terminology** — a table of 5-15 terms a new agent must know before reading code. Derive from the project's README, prior conversation, or ask the user.
8. **Hard rules** — copy the hard rules from Step 3 verbatim (safety redundancy with CLAUDE.md).
9. **Documentation cross-references** — list other docs in the project (`docs/*.md`, `README.md`, etc.) with one-line descriptions of what each covers.
10. **When to update this map** — copy the trigger table from `reference/code_map.md`, adapting directory names.

### Step 6: Write `CLAUDE.md`

Create the file at the project root using the **Write** tool. Keep it **strictly under 100 lines**. Follow the section skeleton from `reference/CLAUDE.md`:

1. **Title + one-paragraph intro.**
2. **"READ THIS FIRST" section** — point at `docs/code_map.md` with a clear instruction to read it before any code action.
3. **Hard rules** — the same 3-8 rules from Step 3, phrased as **DO NOT** statements with brief rationale.
4. **"Maintaining the map (mandatory for every agent)" section** — this is the critical responsibility-enforcement block. Copy the structure from `reference/CLAUDE.md`:
   - Preamble: "Every agent that creates, renames, or deletes a non-temporary file under `<dirs>` is responsible for updating `docs/code_map.md` **in the same session**. This is non-negotiable."
   - 5 triggers: create, rename, delete, new phase, change hard rule.
   - "What counts as non-temporary" definition — temporary files must go to `/tmp/` or inline, not `src/` / `scripts/`.
   - Orphan cleanup rule — if you find an unindexed file, either add it to the map or delete it. Never leave orphans.
5. **Current state** — same table as `docs/code_map.md`'s Quick state, if phase tracking is enabled.
6. **"Go to the map" final pointer** — one sentence sending the reader to `docs/code_map.md`.

### Step 7: Verify

Use **Bash** to run:

```bash
wc -l CLAUDE.md docs/code_map.md
```

Assert:
- `CLAUDE.md` is under 100 lines (warn the user if it's longer and suggest trimming).
- `docs/code_map.md` exists and has a reasonable line count (100-400).

Use **Grep** to verify cross-consistency:

- Every hard rule in `CLAUDE.md` appears in `docs/code_map.md`'s Hard rules section (and vice versa).
- Every file from your Step 4 scan appears in `docs/code_map.md`'s tree.

If any assertion fails, fix it before reporting success.

### Step 8: Summary report to the user

Print a concise summary:
- Files created (with line counts)
- Files indexed (count)
- Phase count (if applicable)
- Hard rule count
- A reminder that the user should review the hard rules and customize where the skill guessed
- Next step: "Review the two files, commit them, and from this point forward follow the Maintaining the Map rules when adding new files."

---

## Design principles (preserve when adapting)

These principles make the pattern work. Do not break them when customizing for a specific project:

1. **CLAUDE.md is a tripwire, not a handbook.** Keep it minimal (under 100 lines). Its only jobs are to inject safety-critical facts into every session automatically and point at the detailed map. Long CLAUDE.md files waste session context budget.

2. **`docs/code_map.md` is the ground truth of the file tree.** Every file under tracked directories appears exactly once with a one-line purpose. If a file isn't in the map, it either needs to be added or deleted — no orphans are allowed. This invariant is what keeps the map useful over time.

3. **"Maintaining the map" is a mandatory agent responsibility**, not a suggestion. The invariant is: *if a file lives under the indexed directories, it must appear in the map*. Temporary debug files go to `/tmp/` or inline `python -c "..."`. This enforcement must be explicit in CLAUDE.md, not hidden in a README.

4. **Hard rules are deliberately duplicated in both files** as safety redundancy. CLAUDE.md is the auto-loaded tripwire; code_map.md has the full context. When rules change, update both.

5. **Tags must be consistent across the tree.** Pick a vocabulary (e.g., `[LIB]`/`[RUN]`/`[SHIM]` + `[P0]`/`[P1]`/etc.) and use it uniformly. A new agent should be able to `grep '\[P2\]'` to find all Phase 2 files. Don't mix conventions.

6. **Phase / subsystem tracking is optional.** For multi-phase projects (reproductions, rolled-out features), use a Quick state table. For flat projects, omit the phase tags and just use file-kind tags. Don't force phase structure where it doesn't belong.

7. **The one-line purpose must say *what the file is for*, not *what functions it contains*.** "PSNR / SSIM / LPIPS for 5D video tensors" is good; "Defines `psnr_video`, `ssim_video`, `lpips_video` functions" is bad. Agents benefit from intent descriptions more than API listings.

8. **Cross-references go to other docs, not into the map.** `code_map.md` points at `docs/*_summary.md`, `README.md`, `openspec/`, etc. Don't inline deep content — the map should stay scannable.

9. **The map includes a "when to update this map" section at the bottom.** This is the self-propagating rule that keeps the map from drifting. Every trigger (add / rename / delete / new phase / change rule) must be listed with a concrete action.

---

## Reference files

This skill ships two reference files in `reference/`:

- `reference/CLAUDE.md` — 71-line example from the `flashed-vaed` project (a video VAE reproduction). Shows the complete CLAUDE.md structure with hard rules, "Maintaining the map" section, and phase state table.
- `reference/code_map.md` — 203-line example from the same project. Shows the complete code_map.md structure with tag legend, quick state, library tree, entry-point tree, pipelines, key concepts, hard rules, documentation cross-refs, and the "when to update" triggers.

**Important:** These are concrete examples from a specific project (a video VAE reproduction with Phase 0/1/2). Their *structure* is reusable; their *content* is project-specific. Do not copy references to `Decoder3dFlash`, `Wan 2.1`, `CausalDWConv3d`, etc. into an unrelated project — those are placeholders that show where project-specific content goes.

Read the reference files once before generating the target project's files. Then build the target files by following the section skeleton but writing fresh content.

---

## Common mistakes to avoid

- **Treating the reference files as a copy-paste template.** They are style guides, not templates. Every sentence must be re-derived for the target project.
- **Writing a 300-line CLAUDE.md.** Keep it under 100 lines. If you need more, move it to `docs/code_map.md`.
- **Omitting the "Maintaining the map" section from CLAUDE.md.** This section is the whole reason the map stays useful over time. Without it, the map drifts within a few sessions.
- **Listing files but skipping the one-line purpose.** A path without intent is only slightly better than `ls` output. The purpose is the value-add.
- **Forgetting hard rules.** Every project has at least 2-3 things that silently break if touched wrongly. Ask the user until you get concrete ones; don't accept "there are no hard rules" as an answer.
- **Indexing files outside `src/` and `scripts/`.** Unless the user explicitly asked, don't index `tests/`, `docs/`, `.github/`, `.venv/`, etc. Focus on code the agent will need to modify.
- **Creating `docs/code_map.md` when `docs/` doesn't exist.** Create the directory if needed (`mkdir -p docs/`). Don't dump the map at the project root.
- **Leaving the verification step out.** Step 7 is there to catch inconsistencies between the two files. Don't skip it.
