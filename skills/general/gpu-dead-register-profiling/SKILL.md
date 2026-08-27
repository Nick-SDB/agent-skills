---
name: gpu-dead-register-profiling
description: Instrument a prebuilt CUDA kernel at the SASS level for low-perturbation cycle timing by inserting CS2R clock reads into registers that liveness analysis proves are dead at each probe point, avoiding the register spills that make source-level clock64() instrumentation unusable on register-bound kernels. Use when per-phase or per-warp GPU kernel timing is needed and source-level instrumentation perturbs the kernel beyond ~10%.
---

# GPU Dead-Register Low-Perturbation Profiling

Measure per-phase / per-warp cycle timing of an already-compiled CUDA kernel without the register-pressure perturbation that source-level `clock64()` instrumentation causes on register-bound kernels.

## When to use

- The kernel is register-bound (e.g. `registers/thread` at or near the 255 ceiling) and source-level `clock64()` instrumentation caused register spill, blowing up runtime (an 11.87× perturbation was observed in one case, versus ~1.001× for this method).
- You need per-phase or per-warp timestamps, not just whole-kernel NCU aggregates.
- You have the shipped cubin / fatbin and can patch it. Recompiling is the wrong move (see Gotchas).

## Core idea

The compiled kernel already knows which registers are live at every program point. At a phase boundary, several registers hold values whose last read has already happened — they are **dead**. Reuse a dead register as the target of `CS2R Rx, SR_CLOCKLO` (read the SM clock counter): register pressure does not change, so no spill is introduced.

Do **not** add the read at the source level and recompile; the compiler does not know your intent and will allocate a fresh register, spilling once the kernel is already at the register ceiling.

## Workflow

1. **Locate phase boundaries.** Disassemble the cubin (`nvdisasm -c` / `cuobjdump -sass`) and map source markers or SASS offsets to the boundaries you care about. A CFG `.dot` and a PC→basic-block map help.
2. **Extract the prebuilt cubin.** Pull the exact cubin from the shipped `.so` fatbin and confirm its SHA against provenance. Do not rebuild from source.
3. **Run liveness.** Parse SASS def/use per instruction — expand tensor-core operand tile widths, wide loads/stores, and `.reuse` — then solve backward dataflow liveness over the CFG including loop back-edges. Record the set of dead registers at each probe point.
4. **Pick the probe register.** Choose a dead register that is (a) even, (b) actually allocated by the compiler (not past the launch descriptor's register count), and (c) not a recent tensor-core operand (see Gotchas). Insert `CS2R Rdead, SR_CLOCKLO` at the probe point. With no free 16-byte slot, use insert+fixup: grow `.text`, shift the tail, and relocate branches (`target = branch_pc + 0x10 + 4*signed_imm`).
5. **Route the timestamp out.** Two options, in order of preference on sm_100a: (a) a **32-bit `STG.E desc[UR][R.64+off], R_clock`** into a buffer the kernel already owns (e.g. the V-tile pointer live at loop exit) — simplest, and if the pointer is per-warp-strided it gives per-warp slots for free; (b) shared memory `STS [RZ+off]` at the probe point, `LDS` at an epilogue, then `STG` to global. On sm_100 never treat `desc[UR]` as a raw base (window descriptor + absolute-address semantics).
6. **Verify.** Run accepted vs instrumented and require the runtime perturbation ratio ≤1.1 (CUDA-event A/B) and bit-exact output (`torch.equal` / `max_abs_diff == 0`).

## Gotchas (all observed in practice)

- **Hand-encoded ALU instructions are unreliable on sm_100a (most important).** `IADD3` / `IMAD.WIDE.U32` / `IMAD.IADD` / `LEA` — even with opcode and register fields copied from the compiler's own SASS — all fault at runtime (`misaligned address` / `illegal memory access` / `operation not supported on global/shared address space`), while `nvdisasm` renders them byte-for-byte identically to working kernel instructions. The safe hand-encodable subset is **MOV / S2R / CS2R / STG (and LDS/LDG)** — move/load/store only. If you genuinely need arithmetic (e.g. `base + warp_id*4`), do NOT hand-encode it: emit the exact instruction with nvcc in a throwaway micro-kernel and copy the full 16 bytes verbatim (do not edit the register fields — changing them re-breaks the hidden control bits). Prefer redesigning the probe to avoid arithmetic entirely (see per-warp note).
- **nvdisasm rendering ≠ hardware decoding.** Several hand-encoded instructions render with the correct operands yet fail on the device (the ALU set above, and some STG field layouts). Verify every encoding two ways: (1) nvdisasm shows the intended operands, and (2) the instrumented kernel runs fault-free AND the trace bytes read back as expected. The reliable method is to copy a proven-working instruction's bytes and change exactly one field byte at a time, re-checking both.
- **CS2R target must be an even register.** An odd register assembles to an instruction that `nvdisasm` shows as valid but faults at runtime with `CUDA_ERROR_ILLEGAL_INSTRUCTION`.
- **Do not recompile.** Rebuilding a register-bound kernel with a different toolchain can silently change register allocation (e.g. 64 B stack → 560 B stack + hundreds of spill stores). Patch the prebuilt cubin.
- **Tensor-core (IMMA/HMMA) operands have delayed reads.** A register that liveness marks dead can still be read by an in-flight tensor-core operation; reusing it right after an IMMA can trigger `misaligned address`. Prefer a register not recently touched by tensor-core instructions.
- **Register-file upper bound.** R254 (and often R253) sit outside the launch descriptor's declared register count; writing them faults. Reuse only registers the compiler actually allocated.
- **sm_100 `desc[UR]` is a window descriptor, and `STG.E desc[UR][R.64+imm]` treats `R.64` as an ABSOLUTE address**, not an offset into the descriptor: a store with `R.64 = 0` targets address 0 and faults. Reuse a pointer register the kernel already computed (e.g. the V-tile pointer at loop exit) as the address. Prefer **32-bit `STG.E`** (word1 `0x000fe8000c101916` for `UR22`); **`STG.E.64` with `desc[UR]` faults** (`misaligned`/`illegal`), so a 32-bit store is the only reliable desc-form on sm_100a.
- **Multiple insertions at the same SASS offset to keep a sequence contiguous.** `insert+fixup` chunk-copies the original text *between* distinct offsets, so inserting instructions at consecutive offsets (0x6fb0, 0x6fc0, …) interleaves them with the original epilogue and can clobber your carried register. Give every instruction of one logical block the *same* offset.
- **Insert+fixup.** Inserting a 16-byte instruction shifts every later offset: grow `.text`, shift the tail sections/program headers, and relocate branch targets. Branch encoding is `target = branch_pc + 0x10 + 4*signed_imm`.
- **Per-warp drift needs warp-indexed slots.** Every warp in a CTA executes the same SASS, so a single slot is overwritten by every warp (last-warp-wins). On sm_100a, however, the warps of a lockstep SIMD kernel may already differ in their pointer registers by a small fixed stride (observed: 16 bytes at the loop-exit V pointer) — so a single `STG [R4.64+off], R_clock` executed by all four warps lands at four *distinct* addresses, one per warp, giving per-warp timestamps with zero arithmetic. Check for this before reaching for `warp_id*4` addressing (which needs the forbidden ALU). A spread of 0 across those four slots is the direct evidence the warps are lockstep at that boundary — which is exactly what decides "draw 1 warp lane vs 4".
- **fp8/bf16 tensors must be read back as raw bytes** (`.view(torch.uint8)`): clock bytes interpreted as float8 are often NaN, which poisons the diff/compare.

## Encoding reference (sm_100)

- `CS2R Rx, SR_CLOCKLO`: word0 `0x0000000000{R:02x}7805`, word1 `0x002fe20000015000`.
- Copy `STS.U32 [RZ+imm], R` and `LDS.U32 R, [RZ+imm]` byte encodings from the kernel's own SASS; the immediate is a plain unsigned shared-memory byte offset.

## Generalization notes

- The principle (patch prebuilt SASS, reuse dead registers) is architecture-independent; the concrete `CS2R` encoding, the even-register rule, the hand-encoded-ALU failure, and the `desc[UR]` window-descriptor behaviour are sm_100-specific and must be re-verified per target architecture (sm_90 differs).
- On kernels with spare registers, source-level instrumentation may already be acceptable — always measure the perturbation ratio first and only fall back to this method when it exceeds ~10%.
- **Worked example (sm_100a, B200):** see `turbodiffusion/docs/catalog_optimization/qattn_sass_cs2r/` — `README.md` (rounds 1–7) and `round8_perwarp.md` (round 8) document a complete per-warp phase-boundary measurement of a register-bound block-sparse attention kernel, including the CS2R→STG 32-bit writeback, the ALU-encoding failures, and the finding that the four warps are lockstep (spread 0) at the loop-end boundary — the direct justification for drawing one representative warp lane instead of four.
