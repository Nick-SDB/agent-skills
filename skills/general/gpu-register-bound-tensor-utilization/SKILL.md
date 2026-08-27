---
name: gpu-register-bound-tensor-utilization
description: Diagnose and optimize a CUDA/GPU kernel bottleneck via MFU/roofline analysis — classify throughput-bound vs latency/occupancy-bound, detect register-bound kernels, evaluate register-reduction / TMA / tcgen05+TMEM / warp-specialization levers, enforce a numerical-correctness gate (bit-exact vs bounded error), and verify speedups at production scale. Use when optimizing a GPU kernel (especially Blackwell/B200), when a kernel is register-bound or tensor-underutilized, or when a measured small-case speedup needs validation.
---

# GPU Register-Bound Tensor Utilization

A reusable methodology for diagnosing and optimizing GPU kernels, distilled from a full B200 attention-kernel optimization campaign (register reduction → tcgen05/TMEM → FA4-style CuTeDSL rewrite).

## When to use

- A kernel's tensor utilization / MFU is low and you need to find why.
- The kernel is register-bound (`registers/thread` at the ceiling, low occupancy, high `wait`/`selected` stall) — the classic "everything half-empty except registers" signature.
- You are considering a new hardware feature (tcgen05.mma / TMEM / TMA / warp specialization) and need to know whether to retrofit or rewrite.
- A measured speedup on a small benchmark needs to be checked at production scale before claiming a win.

## Core idea

**Classify first, then try levers in risk order, gate every step numerically, and verify at production scale.** Most "optimizations" fail because they were aimed at a throughput resource while the kernel was actually latency/occupancy-bound.

## Step 1 — Diagnose and classify (do this before any change)

1. **MFU/roofline**: `useful GEMM FLOPs ÷ peak ÷ measured time`, per-kernel and per-component.
2. **Classify the bottleneck** from the resource counters:
   - **throughput-bound**: tensor / XU / SMEM / HBM near saturation → roofline applies, attack the hot resource.
   - **latency/occupancy-bound**: tensor half-idle AND XU/SMEM/HBM all half-idle, but registers at the ceiling + low occupancy + high `wait` stall → do NOT attack throughput resources; raise occupancy / hide latency instead.
3. **Register-bound signature**: `registers/thread` at max → CTA/SM register-limited → low occupancy → dependency latency unhidden → `wait`/`selected` stall → tensor starved.

## Step 2 — Layered levers (risk order)

1. **L1 pure software**: `__launch_bounds__` / `-maxrregcount` / reduce unroll / re-tiling. Expect these to FAIL on a register-bound kernel: forcing registers down spills into the inner MMA loop (observed 1.97× slower), and unroll/chunk changes often leave the register count unchanged (`-O3` reuses freed registers for more aggressive scheduling).
2. **L2 memory**: TMA (`cp.async.bulk.tensor`) — worth it only if the load phase is a meaningful fraction.
3. **L3 new hardware (tcgen05/TMEM/warp-spec)**: see the retrofit-vs-from-scratch law below.

**Re-tiling invariance law**: the output accumulator's total register footprint is `CTA_Q × head_dim`, independent of how threads are split. WARP_Q halving halves per-thread registers but doubles threads — total registers unchanged, occupancy stays pinned. Re-tiling does NOT break register-bound.

## Step 3 — Retrofit vs from-scratch (the biggest lesson)

- **Retrofit** (bolt the new feature onto an existing kernel): the old kernel's SMEM layout was tuned for the old instruction (e.g. permuted/swizzled for `mma.sync`); the new feature needs a canonical (descriptor-compatible) layout, so a retrofit must add a **second staging copy**, blowing up SMEM (observed +99 KB → 1 CTA/SM → occupancy halved → 4× slower).
- **From-scratch** (canonical layout from the start): data enters SMEM already in the descriptor layout — **no staging tax**. This is the only valid way to adopt tcgen05/TMEM/TMA.
- **A failed retrofit does NOT disprove the feature.** It only disproves "swap the instruction without changing the layout/schedule".

## Step 4 — Numerical gate (enforce every step)

- **T0 (pure register/scheduling change, no math change)**: must be **bit-exact** (`max_abs == 0`). First measure **self-noise** (same kernel run twice → identical) to establish the bit-exact floor; tolerate ≤1e-3 relative for compiler FP reordering.
- **T1 (math changed, e.g. f16 accumulate / FP8)**: measure **E_base** (baseline vs dense reference = the operator's own approximation error) and **E_var** (variant vs baseline = added error). Gate: `E_var ≤ 1e-3 mean / ≤ 1e-2 max` AND `E_var ≪ E_base`.

## Step 5 — Verify at production scale

**Both small workloads and intermediate proxies mislead.** Small workloads give false positives (fixed overhead amortized specially); intermediate proxies can give false negatives. Observed: a 33.96% speedup at Q=1024, a tie at Q=4096/KV=16384 (false negative — too few blocks), then a 41% win at the true production scale L=75600. Every claimed win must be re-measured at the TRUE production scale.

## Hard constraints learned (apply these checks to any kernel)

1. **FP8 precision is scale-dependent.** Probability E4M3 and FP8 denominator are at the precision edge; restructuring the computation (tensor-core denominator, slack rescale) changes the FP8 rounding scale and blows up error. **Keep statistics (denominator) in FP32** (FA4 does); keep probability FP8 only if the scale is stable.
2. **Warp-specialization sync amortizes over total block-iteration count.** 16-warp specialization + multi-stage mbarrier sync has fixed overhead that amortizes over enough block iterations (density × sequence length × heads). An intermediate proxy with too few blocks gave a false negative; the true production scale (591×118 blocks × 40 heads) won 41%. Ask "is the workload large enough to amortize the sync?" before judging.
3. **The accumulator has to live somewhere** (registers / SMEM / TMEM), and each location has its own ceiling. TMEM is the only clean way to free the accumulator registers, but only with from-scratch canonical layout.

## Workflow checklist

- [ ] MFU/roofline: who takes the time, who is half-empty.
- [ ] Classify throughput-bound vs latency/occupancy-bound (regs full + occ low + wait high = latency-bound).
- [ ] Measure self-noise (bit-exact floor) + E_base (approximation error); set T0/T1 thresholds.
- [ ] L1 levers (expect spill / no-op on register-bound).
- [ ] L2 TMA (only if load is meaningful).
- [ ] L3 new hardware: **from-scratch only**, never retrofit.
- [ ] Every step: T0/T1 gate + bitwise-repeatable.
- [ ] **Re-measure at production scale before claiming a win.**

## Worked example (B200 block-sparse attention)

Full evidence: `turbodiffusion/docs/catalog_optimization/qattn-optimization/` — `L1-optimization-results.md` (register-reduction levers all rejected + why), `FA4-style-rewrite-assessment.md` (tcgen05 retrofit vs from-scratch, FP8 precision, warp-spec amortization, the CuTeDSL rewrite that reached 101 regs / 25% occupancy and won 41% at production scale), `methodology-generalization.md` (this document, fuller form).

Key numbers that anchor the lessons: 255 regs → 2 CTA/SM → 12.5% occupancy (register-bound); retrofit SMEM 32→132 KB (staging tax); from-scratch 255→101 regs, 12.5%→25% occupancy; small-case 33.96% faster, an intermediate proxy tie (false negative), and a 41% production-scale win.
