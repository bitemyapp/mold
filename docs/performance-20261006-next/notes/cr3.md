All topics start independently at `f8638be95ae14954ec3b1029e6008128d7a27f1b`. Builds and validation run only on `ssh wx-workstation`, CPUs 16–23, under the shared workstation gate; parent runs timing and profiles under the exclusive gate. These are experiments, not accepted changes. Floating point and random seeds are unchanged/N/A.

# CR3: Actual future fragment prefetch

Source `f760835736645b1ba7e3d24a1e48b301376ef7a6`; binary `65922b71ffec0cc17fbb22438433176ea3403a1f84cb00203bb13ebb80edc591` at remote `bin/cr3`.

x86_64 nonallocated RELA streams of >=32 relocations decode windows of 16 relocation records. A lookahead pass uses source symbol metadata and fragment range search to prefetch actual future rich records. Resolution, diagnostics, overflow checks, tombstones, and writes then execute in original order. No resolved values or errors are produced by the prefetch pass. The existing useful guessed fragment+8 prefetch remains. Small streams and CREL use a window of one; special/extended section indices fall back to normal resolution without speculative lookup.

Behavior proof: the prefetch pass performs checked, side-effect-free metadata reads and wrapping address arithmetic matching the resolver. It does not write output or mutate lookup state. The original relocation loop runs over the same sequence, preserving overlaps and addend semantics. CREL is excluded to retain decode-error ordering. ELF RELA records are already validated fixed-width data. Ordering and tie-breaking of all merge/layout decisions are untouched.

Costs/limits: x86_64 only; actual fragment prefetch repeats the range search that ordinary resolution later needs. Windows add stack traffic and a second pass. Sparse/no-merge streams can lose despite guarded lookups. No claim is made that annotated prefetch stall samples prove a benefit: prior C1 real A/B showed the original guessed prefetch is useful.

Validation: unit helper passed; full native 551 passed, 14 skipped, 0 failed. Added test checks overlapping 32/64-bit writes, later-window overwrite, and all relevant small absolute overflow diagnostics. The parent-exclusive all-eight golden/timing screen subsequently completed; rejection results appear below.

Measured result: rejected. Twenty-four interleaved runs per case; all eight golden hashes matched. Actual-target decoding and prefetch did not produce a reliable large-link gain, and TableGen regressed in both wall and CPU time. CR2 counters show that the baseline consecutive-fragment hint already covers almost all large C++ references; its guessed +8 prefetch therefore often follows the future stream. The extra range search/window traffic did not repay its work. No additional iteration is justified by these results.

| Case | Wall delta % [95% CI] | CPU delta % [95% CI] | RSS delta % |
|---|---:|---:|---:|
| hello | +0.77 [-3.74, +4.50] | +0.58 [-4.01, +4.45] | +0.06 |
| rhello | -1.66 [-3.33, +4.41] | -0.85 [-3.01, +2.87] | -0.07 |
| tblgen | +4.46 [+0.63, +6.91] | +7.62 [+2.67, +11.01] | -0.10 |
| lld | +0.06 [-1.55, +3.07] | +2.13 [-9.09, +12.55] | +0.07 |
| clang | -1.20 [-2.62, +0.36] | +0.55 [-7.97, +9.54] | +0.01 |
| clang-s | +3.10 [-0.60, +4.58] | -0.53 [-2.92, +1.69] | +0.13 |
| ra | -0.22 [-4.58, +5.37] | -0.54 [-2.50, +0.79] | -0.03 |
| ra-s | +1.27 [-3.62, +4.81] | -0.22 [-1.89, +2.47] | -0.15 |

Validation count from remote helper logs: 33 mold library tests and 2 mold-tests harness tests passed (0 failed).
