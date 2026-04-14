# flashed-vaed — Code Map

> **This is the canonical index of every library module, runnable script, and
> document in the project.** It is the first thing a new agent should read
> after `CLAUDE.md`. Every file under `src/` and `scripts/` appears here with
> a one-line purpose statement and a Phase tag. If you add / rename / delete a
> file, update this map in the same commit — the CLAUDE.md points here, and
> this file is the ground truth of "what does X do".

---

## Tag legend

| Tag | Meaning |
|---|---|
| `[P0]` | Originated in Phase 0 — decoder-profiling (baseline latency + quality benchmark) |
| `[P1]` | Originated in Phase 1 — decoder-surgery (operator replacement → Decoder3dFlash) |
| `[P2]` | Originated in Phase 2 — decoder-pruning (channel pruning → Decoder3dFlashPruned) |
| `[LIB]` | Library module, imported by other modules or scripts |
| `[RUN]` | Runnable entrypoint (`python ...` or `bash ...`) |
| `[SHIM]` | Thin wrapper / adapter (e.g., streaming-mode decode loop) |

---

## Quick state (2026-04-11)

| Phase | Change (OpenSpec) | Status | Headline artifact |
|---|---|---|---|
| 0 | `decoder-profiling` | ✅ archived | `results/phase0/baseline_h20.json` (H20 streaming FPS = 14.56) |
| 1 | `decoder-surgery` | ✅ archived | `Decoder3dFlash` — 9.06 M params (~7.7× vs original Wan VAE) |
| 2 | `decoder-pruning` | ✅ archived | `Decoder3dFlashPruned` — 6.45 M params (~10.8× vs original Wan VAE) |
| 3 | distillation training | ⏳ not started | student = `Decoder3dFlashPruned`, target PSNR 30+ dB |

All three archived changes live under `openspec/changes/archive/`. Their specs
are synced to `openspec/specs/` (4 capabilities, 28 requirements total).

---

## Library code — `src/flashed_vaed/`

All library modules. Import from these; do not run directly.

```
src/flashed_vaed/
├── __init__.py                              [LIB]        package init; exports WAN_2_1_SUBMODULE_SHA constant
├── loader.py                                [P0][LIB]    load_wan_vae(path, dtype, device) — standalone VAE loader (no DiT/T5)
│
├── profiling/
│   ├── __init__.py                          [LIB]        subpackage marker
│   ├── block_map.py                         [P0][LIB]    BlockBoundary + get_block_boundaries + assert_block_map for ORIGINAL Wan decoder
│   └── hooks.py                             [P0][LIB]    BlockTimer: cuda.Event-based per-block + per-CC3D profiler (context manager)
│
├── quality/
│   ├── __init__.py                          [LIB]        subpackage marker
│   └── metrics.py                           [P0][LIB]    psnr_video / ssim_video / lpips_video for 5D [B,C,T,H,W] tensors
│
└── decoder_flash/
    ├── __init__.py                          [LIB]        subpackage with lazy re-exports (operators, architecture, remap, streaming, pruned*)
    ├── operators.py                         [P1][LIB]    CausalDWConv3d (subclasses CausalConv3d) + FrameConv2d + make_main_conv factory
    ├── architecture.py                      [P1][LIB]    Decoder3dFlash + ResidualBlockFlash + _UpBlock + WAN_2_1_OP_CONFIG constant
    ├── streaming.py                         [P1][SHIM]   WanVAEFlash — chunked streaming decode shim (eval+no_grad enforced)
    ├── remap.py                             [P1][LIB]    wan_state_dict_to_flash — translate Wan keys → Decoder3dFlash keys
    ├── prune_config.py                      [P2][LIB]    LayerPrune/ResBlkPrune/UpBlockPrune/PruneConfig frozen dataclasses + slice helpers
    ├── calibration.py                       [P2][LIB]    PRUNE_HOOK_ORDER (14 dump points) + dump_hooks context manager
    ├── greedy_selection.py                  [P2][LIB]    greedy_select_channels (forward greedy R²) + 3 compute_W_* variants
    ├── pruned.py                            [P2][LIB]    Decoder3dFlashPruned + PrunedResidualBlock + PrunedUpBlock (the Phase 3 student)
    ├── pruned_streaming.py                  [P2][SHIM]   WanVAEFlashPruned — streaming shim for the pruned decoder
    └── pruned_remap.py                      [P2][LIB]    wan_state_dict_to_pruned_flash — translate + per-channel slice Wan → Pruned Flash
```

---

## Entry points — `scripts/phase*/`

Runnable scripts. Each takes CLI args; see `--help` for details.

```
scripts/phase0/
├── profile_decoder.py                       [P0][RUN]    Streaming-mode decoder latency profiling (5 warmup + 20 iters); writes results/phase0/baseline_h20.json
├── measure_quality.py                       [P0][RUN]    encode→decode roundtrip PSNR/SSIM/LPIPS on reference clips; writes results/phase0/quality.json
└── generate_reference_clips.sh              [P0][RUN]    Sequential Wan T2V-14B generation of 3 reference clips (~1.5 hrs wall-clock)

scripts/phase1/
└── validate_surgery.py                      [P1][RUN]    7+1 validation of Decoder3dFlash (construction, weight loading, CC3D count, per-block shape match, sanity gate, cache-in-use); writes results/phase1/surgery_validation.json

scripts/phase2/
├── generate_with_latent.py                  [P2][RUN]    Standalone Wan T2V generator with monkey-patched DiT-output latent capture (saves both mp4 AND latent.pt)
├── parallel_generate_with_latent.sh         [P2][RUN]    7-GPU parallel launcher for 13 clips (2 batches). CONTAINS bash subshell fix — see IMPORTANT comment in script.
├── dump_calibration.py                      [P2][RUN]    14-hook feature dumping on 16 calibration clips (13 DiT-latent + 3 encoder-roundtrip); writes results/phase2/calibration_features/dump_NN_*.pt
├── select_channels.py                       [P2][RUN]    Greedy R² selection on 14 dumps + 8 W matrix computation; writes results/phase2/prune_config.pt + r2_stats.json
└── validate_pruning.py                      [P2][RUN]    7-check validation of Decoder3dFlashPruned (construction, load, cc3d count, forward, sanity, R² range, PSNR); writes results/phase2/pruning_validation.json
```

---

## Pipelines (how to re-run each phase from scratch)

### Phase 0 — baseline profiling + quality (~5 min after clips exist)

```bash
# Latency profiling (streaming only, per-block breakdown)
PYTHONPATH=src pixi run -e wan python scripts/phase0/profile_decoder.py

# Reconstruction quality on 3 reference clips (already in output/)
PYTHONPATH=src pixi run -e wan python scripts/phase0/measure_quality.py \
    --pattern 'ref_clip_0[1-3]_*.mp4' --clip-source generated
```

### Phase 1 — surgery validation (~1 min, structural-only)

```bash
CUDA_VISIBLE_DEVICES=6 PYTHONPATH=src pixi run -e wan python scripts/phase1/validate_surgery.py
```

### Phase 2 — full pipeline (~1.5-2 hours end-to-end)

```bash
# Step 1: parallel generation (~60 min wall-clock, GPUs 0-6)
bash scripts/phase2/parallel_generate_with_latent.sh

# Step 2: feature dumping on all 16 clips (~5 min, single GPU)
CUDA_VISIBLE_DEVICES=6 PYTHONPATH=src pixi run -e wan python scripts/phase2/dump_calibration.py

# Step 3: greedy channel selection + W computation (~45 min, single GPU)
CUDA_VISIBLE_DEVICES=6 PYTHONPATH=src pixi run -e wan python scripts/phase2/select_channels.py

# Step 4: validation (~30 sec, single GPU)
CUDA_VISIBLE_DEVICES=6 PYTHONPATH=src pixi run -e wan python scripts/phase2/validate_pruning.py
```

---

## Key concepts / terminology

Memorize these before reading any Phase code.

| Term | Meaning |
|---|---|
| `Decoder3d` | Wan 2.1's original VAE decoder (in `submodules/Wan2.1/wan/modules/vae.py`). Flat `nn.Sequential` of 15 layers in `upsamples`. |
| `Decoder3dFlash` | **Phase 1 output**. Operator-surgical version: 28 main-path 3×3×3 CausalConv3d replaced (16 DW3D in mid/up_0/up_1 + 12 FrameConv2d in up_2/up_3). Same channel widths as Wan. Params: 9.06 M. |
| `Decoder3dFlashPruned` | **Phase 2 output**. Further channel-pruned: 1/8 in up_2 (192→24) and up_3 (96→12). Independent class, NOT a subclass of Decoder3dFlash. Params: 6.45 M. |
| `CausalDWConv3d` | **Phase 1 operator**. Inherits from `CausalConv3d` (depthwise body, groups=in_ch) + owns a `self.pw = nn.Conv3d(1×1×1)` pointwise mixer. Inheritance is load-bearing for Wan's `isinstance(layer, CausalConv3d)` cache dispatch. |
| `FrameConv2d` | **Phase 1 operator**. Does `rearrange('b c t h w -> (b t) c h w').contiguous()` → `nn.Conv2d` → reshape back. NOT a CausalConv3d subclass (intentional — falls through to Wan's no-cache path). |
| `PruneConfig` | **Phase 2 data carrier**. Frozen dataclass holding 14 retained-index tuples + 8 W matrices + r2_stats. Serialized to `results/phase2/prune_config.pt`. |
| `PRUNE_HOOK_ORDER` | Canonical 14-entry tuple defining the hook points for Phase 2 calibration. Lives in `decoder_flash/calibration.py`. Order is load-bearing. |
| `WAN_2_1_OP_CONFIG` | `{"mid": "dw3d", "up_0": "dw3d", "up_1": "dw3d", "up_2": "frame2d", "up_3": "frame2d"}`. Lives in `decoder_flash/architecture.py`. |
| `feat_cache` | Wan's streaming-mode per-CausalConv3d cache (one slot per CC3D-isinstance layer). Decoder3dFlash has 21 slots; Decoder3dFlashPruned has 21 too (new 1×1 shortcuts are `nn.Conv3d`, not counted). |
| `14 dump points` | The 14 feature-dumping locations in Phase 2. 1 at up_1.Resample output, 2×3 inside up_2 ResBlks + 1 at up_2.Resample, 2×3 inside up_3 ResBlks. See `docs/flash_decoder_pruning_map.md`. |
| `8 W matrices` | The 8 1×1 W-init shortcuts/projections of Phase 2: 1 sparse entry (192→24) + 6 between-subsets (ResBlk shortcuts) + 1 full reconstruction exit (12→96). |

---

## Hard rules (duplicated in CLAUDE.md)

- **DO NOT** modify `submodules/Wan2.1/`. Use hooks / monkey-patches instead. All three phases have respected this rule.
- **DO NOT** run `pixi install -e wan`. It would clobber the pip-installed torch / flash-attn / diffusers / lpips / piq / scikit-image. Use `pixi run -e wan pip install <pkg>` for new deps.
- **DO NOT** delete `results/phase*/` or `openspec/changes/archive/`. They are the reproducible evidence of prior phases.
- **DO NOT** modify `openspec/specs/*` directly. Create a new OpenSpec change via `/opsx:propose <name>` instead.
- **DO NOT** forget the bash subshell trap: never use `pid=$(func_that_backgrounds)` — the `&` will run in a subshell and orphan the child. Always background directly in the parent shell. See `scripts/phase2/parallel_generate_with_latent.sh` for the working pattern.
- **DO NOT** forget production-aligned `.eval() + .requires_grad_(False)` when wrapping a decoder in a streaming shim — without it, the 21-chunk streaming loop accumulates autograd buffers and OOMs even on a 96 GB H20. This is enforced in `WanVAEFlash` and `WanVAEFlashPruned` but must be respected in any future shim.

---

## Documentation cross-references

Documents in `docs/` that complement this map:

| File | Phase | What's in it |
|---|---|---|
| `phase1_plan.md` | P1 | The pre-implementation plan for Phase 1 |
| `phase1_operator_brief.md` | P1 | Compact operator-focused brief (quantitative estimates) |
| `phase1_implementation_summary.md` | P1 | Post-impl summary with actual numbers + risks (DW3D + FrameConv2d) |
| `phase2_implementation_summary.md` | P2 | Post-impl summary with actual R²/PSNR + risks (pruning) |
| `wan_decoder_block_map.md` | P0 | Paper block ↔ Wan source index mapping (for ORIGINAL Wan decoder) |
| `flash_decoder_block_map.md` | P1 | Decoder3dFlash module hierarchy + inheritance trick explanation |
| `flash_decoder_pruning_map.md` | P2 | The 14 dump points + 8 W matrices + PrunedResBlock structure |
| `paper/flash-vaed-2602.19161v1-latex/paper.tex` | — | The source paper (arXiv 2602.19161v1) |
| `paper/flash-vaed-2602.19161v1-repro-notes.md` | — | User's original reproduction plan (may be slightly stale post-archive) |

OpenSpec archive locations (full change artifacts):

- `openspec/changes/archive/2026-04-10-decoder-profiling/` — Phase 0
- `openspec/changes/archive/2026-04-10-decoder-surgery/` — Phase 1
- `openspec/changes/archive/2026-04-11-decoder-pruning/` — Phase 2

Each archive contains `proposal.md`, `design.md`, `specs/`, `tasks.md`, `.openspec.yaml`.

---

## When to update this map

| Trigger | What to do |
|---|---|
| Add a new `.py` or `.sh` file under `src/` or `scripts/` | Add a row with Phase tag + one-line purpose |
| Rename a file | Update the row's path |
| Delete a file | Remove the row AND note in that Phase's summary doc |
| Start a new Phase | Add a section under "Quick state" + pipelines section |
| Change a hard rule | Update both this file AND `CLAUDE.md` |
| Change `WAN_2_1_OP_CONFIG` or `PRUNE_HOOK_ORDER` | Update the Key concepts table + the authoritative docs (`flash_decoder_block_map.md` / `flash_decoder_pruning_map.md`) |

> The CLAUDE.md file is an always-loaded tripwire for agents. This file
> (`code_map.md`) is the detailed reference agents consult once they've seen
> the CLAUDE.md pointer. Keep both in sync.
