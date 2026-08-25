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
5. **Route the timestamp out.** Shared memory needs no global-memory descriptor and works at a fixed offset: `STS [RZ+off], Rdead` at the probe point, `LDS` it back at an epilogue, then `STG` to global using an offset the kernel already computes. On sm_100, never treat a `desc[UR]` as a raw base pointer (it is a window descriptor; small immediate offsets fault).
6. **Verify.** Run accepted vs instrumented and require the runtime perturbation ratio ≤1.1 (CUDA-event A/B) and bit-exact output (`torch.equal` / `max_abs_diff == 0`).

## Gotchas (all observed in practice)

- **CS2R target must be an even register.** An odd register assembles to an instruction that `nvdisasm` shows as valid but faults at runtime with `CUDA_ERROR_ILLEGAL_INSTRUCTION`.
- **Do not recompile.** Rebuilding a register-bound kernel with a different toolchain can silently change register allocation (e.g. 64 B stack → 560 B stack + hundreds of spill stores). Patch the prebuilt cubin.
- **Tensor-core (IMMA/HMMA) operands have delayed reads.** A register that liveness marks dead can still be read by an in-flight tensor-core operation; reusing it right after an IMMA can trigger `misaligned address`. Prefer a register not recently touched by tensor-core instructions.
- **Register-file upper bound.** R254 (and often R253) sit outside the launch descriptor's declared register count; writing them faults. Reuse only registers the compiler actually allocated.
- **sm_100 `desc[UR]` is a window descriptor**, not a base pointer: a store at a small immediate offset faults for every parameter, while the kernel's own large register-computed offsets are valid. Route trace data through shared memory instead of writing to a separately allocated trace tensor.
- **Insert+fixup.** Inserting a 16-byte instruction shifts every later offset: grow `.text`, shift the tail sections/program headers, and relocate branch targets. Branch encoding is `target = branch_pc + 0x10 + 4*signed_imm`.
- **Per-warp drift needs warp-indexed slots.** Every warp in a CTA executes the same SASS, so a single shared slot is overwritten by every warp (last-warp-wins). Use `STS [RZ + base + warp_id*4]` (warp_id from `SR_TID.X >> 5`) to capture per-warp timestamps in the same SM clock domain.

## Encoding reference (sm_100)

- `CS2R Rx, SR_CLOCKLO`: word0 `0x0000000000{R:02x}7805`, word1 `0x002fe20000015000`.
- Copy `STS.U32 [RZ+imm], R` and `LDS.U32 R, [RZ+imm]` byte encodings from the kernel's own SASS; the immediate is a plain unsigned shared-memory byte offset.

## Generalization notes

- The principle (patch prebuilt SASS, reuse dead registers) is architecture-independent; the concrete `CS2R` encoding, the even-register rule, and the `desc[UR]` window-descriptor behaviour are sm_100-specific and must be re-verified per target architecture (sm_90 differs).
- On kernels with spare registers, source-level instrumentation may already be acceptable — always measure the perturbation ratio first and only fall back to this method when it exceeds ~10%.
