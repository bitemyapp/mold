All topics start independently at `f8638be95ae14954ec3b1029e6008128d7a27f1b`. Builds and validation run only on `ssh wx-workstation`, CPUs 16–23, under the shared workstation gate; parent runs timing and profiles under the exclusive gate. These are experiments, not accepted changes. Floating point and random seeds are unchanged/N/A.

# CR1: Compact final fragment offsets

Initial source: `62fa0761f75dc7a1f273749b640b6f48cfb28ca6`; binary `bdfa8b02e0ee324575cbf8ef5c2ea4aee63fa4f2791eddc7dc592b2b7e01fd6b` at remote `bin/cr1`.

A side array stores one u64 per map bucket for nonallocated `.debug_*` string pools with estimated cardinality >=4096. EntryIds remain bucket identities. `Context::fragment_addr` reads this array, and the existing fragment+8 prefetch targets it. Other pools retain the original rich-record path. The initial implementation builds the array through an extra bucket scan after every layout.

Behavior proof: relative offsets are copied after rich offsets settle. Layout ordering, equality, collisions, alignment, liveness, and 32-bit grouping are unchanged. Relayout rebuilds the array. Absolute addresses still use the current parent section address. Empty buckets are never addressed by valid EntryIds. Allocated sections/tombstones retain the original path.

Validation: unit helper passed including explicit equality across DWARF32 relayout, duplicate alignment, and allocated fallback. Full native integration: 550 passed, 14 skipped, 0 failed. Parent all-eight corpus outputs are byte identical.

Initial result: rejected. Twenty-four interleaved runs per case. Positive deltas mean more cost; CI is 95%. The array preparation and allocation did not repay their costs, especially lld CPU and RSS.

| Case | Wall delta % [CI] | CPU delta % [CI] | RSS delta % | Golden |
|---|---:|---:|---:|---|
| hello | -1.15 [-4.55, +1.74] | -0.59 [-4.74, +1.77] | +0.00 | matched |
| rhello | -0.49 [-2.66, +2.76] | +0.40 [-2.38, +2.63] | +0.70 | matched |
| tblgen | +1.62 [-1.62, +4.02] | +2.43 [-2.42, +8.29] | +0.55 | matched |
| lld | +1.25 [+0.67, +1.82] | +3.11 [+1.20, +4.15] | +1.23 | matched |
| clang | +3.08 [-1.29, +8.19] | +1.98 [+1.04, +3.20] | +0.57 | matched |
| clang-s | +1.82 [-2.02, +5.23] | -1.73 [-3.58, +0.59] | -0.15 | matched |
| ra | +0.16 [-5.70, +5.84] | +0.26 [-2.72, +3.64] | +0.92 | matched |
| ra-s | +0.35 [-2.90, +3.65] | -0.88 [-4.23, +2.90] | -0.10 | matched |

Revision source: `24be8a795e466c363d05b6d86bd3537371be3efb`. The revised candidate populates disjoint shard slices of the side array inside the existing final-offset loop. This eliminates the extra map scan. It still pays zeroed allocation, 8 bytes per bucket, extra stores, and lookup dispatch; a win is not assumed. Built at remote `bin/cr1-v2`, SHA256 `261750bd3f2be8a590150bac3c5426a502d927405e1765e9c202ea0852f910de`. Unit 34+2 passed; full native passed 550/14/0. The subsequent screen measured and rejected v2, as recorded below. The original binary remains frozen.

Validation count from remote helper logs: 34 mold library tests and 2 mold-tests harness tests passed (0 failed).


<!-- final-screen-summary -->

Final revision: rejected. Reusing the existing offset loop removed the redundant scan, but the compact side array did not establish a useful whole-link improvement. The remaining allocation, stores and lookup dispatch still have to repay their costs.

All eight output hashes matched. Positive deltas mean more cost. These runs reuse the harness output pathname and compare with the original frozen f8638be9 baseline in the same result file. Neither input caches nor host VM state were flushed. Raw links: `../results/screen-fourth.json`; derived paired summary: `../results/summary-fourth.json`.

| Case | Pairs | Wall delta % [95% CI] | CPU delta % [95% CI] | Peak RSS delta % |
|---|---:|---:|---:|---:|
| hello | 24 | -0.03 [-2.90, +3.69] | +1.83 [-1.63, +3.79] | +0.00 |
| rhello | 24 | -0.14 [-1.77, +1.74] | -0.15 [-1.74, +1.73] | -0.52 |
| tblgen | 24 | -2.98 [-5.43, +0.94] | -1.02 [-7.81, +1.97] | +0.89 |
| lld | 24 | +0.62 [-0.14, +1.89] | +1.05 [-4.73, +12.25] | +1.22 |
| clang | 24 | +1.30 [-0.00, +2.06] | +1.36 [-10.99, +5.57] | +0.71 |
| clang-s | 24 | -0.85 [-3.81, +2.66] | -1.11 [-2.97, +0.85] | +0.00 |
| ra | 24 | +2.44 [-1.09, +7.71] | -0.02 [-2.57, +3.25] | +0.98 |
| ra-s | 24 | -1.04 [-3.99, +0.94] | +0.70 [-0.60, +2.74] | +0.17 |
