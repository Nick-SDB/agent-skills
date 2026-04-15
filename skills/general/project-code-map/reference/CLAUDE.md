# flashed-vaed — Agent Entry Point

Flash-VAED reproduction on the Wan 2.1 video VAE. Three phases archived; Phase 3 (distillation training) not started.

---

## READ THIS FIRST

Before touching any code, open **`docs/code_map.md`**. It is the canonical index of every library module and runnable script in this project, plus pipelines, key concepts, and "how to update the map when you add a file". Do not guess the layout — the map is exact and kept in sync with source.

`CLAUDE.md` (this file) is intentionally short. It is loaded into every new
Claude Code session automatically, so its only job is to:
1. Point you at `docs/code_map.md` for the full picture.
2. List the hard rules that, if violated, will silently break things.
3. Give you the current Phase state in one glance.

Everything else lives in `code_map.md` and the referenced documents.

---

## Hard rules (will silently break things if violated)

- **DO NOT** modify anything under `submodules/Wan2.1/`. All three phases have worked around this rule with hooks and monkey-patches. See `scripts/phase2/generate_with_latent.py` for the monkey-patch pattern.
- **DO NOT** run `pixi install -e wan`. It would wipe the pip-installed torch, flash-attn, diffusers, lpips, piq, and scikit-image. Use `pixi run -e wan pip install <pkg>` for new deps. The existing `pixi.toml` has a comment explaining this.
- **DO NOT** delete or rename anything under `results/phase*/` or `openspec/changes/archive/`. They are the reproducible evidence of prior phases and are referenced by the spec archive.
- **DO NOT** modify files under `openspec/specs/*` directly. That directory is the synced output of archived OpenSpec changes. To change a spec, create a new OpenSpec change via `/opsx:propose <name>`.
- **DO NOT** use `pid=$(func_that_backgrounds)` in bash. The `&` runs in a subshell and the parent's `wait` will error with "not a child of this shell". Always background directly in the parent shell. See `scripts/phase2/parallel_generate_with_latent.sh` for the working pattern.
- **DO NOT** forget `.eval() + .requires_grad_(False)` on any decoder wrapped in a streaming shim. Without it, the 21-chunk streaming loop accumulates autograd buffers and OOMs a 96 GB H20. Both `WanVAEFlash` and `WanVAEFlashPruned` enforce this in their `__init__`; follow the pattern for any future shim.

---

## Maintaining the map (mandatory for every agent)

The code index at `docs/code_map.md` is the ground truth of "what lives where and does what". It only works if it stays in sync with the source tree. **Every agent that creates, renames, or deletes a non-temporary file under `src/` or `scripts/` is responsible for updating `docs/code_map.md` in the same session.** This is non-negotiable — a drifted map is worse than no map.

- **When you create a non-temporary file under `src/` or `scripts/`**: add a one-line row in the corresponding section of `docs/code_map.md`, with the right `[Px]` Phase tag and one of `[LIB]` / `[RUN]` / `[SHIM]` classification tags. The one-line description must say *what the file is for*, not *what functions it contains*. Keep it under ~100 chars so the tree stays readable.
- **When you rename a file**: update the path in `docs/code_map.md`. A `git grep` for the old path before committing is a cheap safety net.
- **When you delete a file**: remove its row from `docs/code_map.md` AND note the deletion in the most relevant Phase summary under `docs/phase*_implementation_summary.md` if the file was part of an archived phase.
- **When you start a new Phase**: add a section to `docs/code_map.md`'s "Pipelines" and "Quick state" blocks, and update the `Current state` table in this file (`CLAUDE.md`).
- **When you change a hard rule above**: update both `CLAUDE.md` and `docs/code_map.md`'s "Hard rules" section to keep them consistent.

### What counts as "non-temporary"

A file is **non-temporary** if it is committed to the repo and reused after its creation session. Almost every `.py` / `.sh` you add to `src/` or `scripts/` falls in this category.

A file is **temporary** only if it is a debug smoke test, a one-shot investigation script, or scratch work that will be deleted before the session ends. **Temporary files must not be written to `src/` or `scripts/`.** Put them in `/tmp/`, run them inline via `python -c "..."`, or write to a throwaway path like `/tmp/debug_xxx.py`. The invariant is: **if a file lives under `src/` or `scripts/`, it must appear in `docs/code_map.md`**.

If you find a file under `src/` or `scripts/` that is NOT in the map, either
(a) add it to the map (if it should have been there), or
(b) move it out / delete it (if it was temporary and leaked into the tree by mistake).
Do not leave orphaned files — it silently erodes the map's trustworthiness.

---

## Current state (2026-04-11)

| Phase | Change | Status | Headline |
|---|---|---|---|
| 0 | `decoder-profiling`  | ✅ archived | H20 streaming FPS = 14.56 |
| 1 | `decoder-surgery`    | ✅ archived | `Decoder3dFlash`, 9.06 M params (~7.7× compression) |
| 2 | `decoder-pruning`    | ✅ archived | `Decoder3dFlashPruned`, 6.45 M params (~10.8× compression) |
| 3 | distillation training | ⏳ not started | student = `Decoder3dFlashPruned`, PSNR target 30+ dB (currently 4.94 dB) |

4 capabilities synced to `openspec/specs/`:
`vae-decoder-profiling`, `vae-reconstruction-quality`, `flash-vaed-decoder-surgery`, `decoder-channel-pruning`.

---

## Go to the map

**→ `docs/code_map.md`** is the next file to read. It has the tagged file tree, pipelines, key concepts, and the "when to update this map" section that keeps it in sync with code.
