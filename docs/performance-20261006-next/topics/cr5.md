# CR5: flat copy jobs across output sections

Baseline f8638be9. Worktree: /Users/callen/.codex/worktrees/mold-cr5-cross-section-batches/mold. Branch: codex/mold-cr5-cross-section-batches.

First evidence: existing same-baseline high-resolution traces, collected on wx-workstation with CPUs 32–63 and 20 instrumented links per case. Copy-chunk children overlap and are not additive exclusive costs. The table records whole copy_chunks interval and number of top-level output-copy timers, not claimed CPU overhead.

| Case | Median copy_chunks ms | Median top-level chunk timers |
|---|---:|---:|
| tblgen | 1.363 | 49 |
| lld | 14.489 | 55 |
| clang | 28.434 | 54 |
| ra | 31.243 | 51 |

The existing path schedules chunks, then recursively schedules members within each output section. Prior C4 weighted only within sections and failed. This new experiment flattens normal, thunk-free output members into one shared batch queue across output-section boundaries, while preserving special chunks and the later relocation-output barrier. Batches should combine tiny adjacent members, with no extra copy or relocation metadata graph. Original disjoint output slices remain the ownership proof. Impact 4, confidence 3, effort 3: score 4.

Untimed coverage counts, targeted validation and parent-exclusive performance measurements subsequently completed; the rejection is recorded below.

Prototype committed as 6789e6c53fa9a82e27bc8295d88f212575a030e0; frozen binary SHA-256 1624bcf787c69f7f18892497037b23b7f29b0738e28fd37c346edc0f45fc99b2. For >=4096 ordinary members, jobs hold at most 64 adjacent members and aim at <= 256KiB, with oversized individual members remaining indivisible. Eight jobs form one outer Rayon batch, including jobs across output-section boundaries. Special chunks, thunk finishing, NOBITS behavior, target relocation mutation, and first/last output barriers retain their established paths. Three coarse counters report actual flattened sections, groups, and bytes. Group timers overlap; their summed durations are not exclusive CPU time.

Independent relocation_kernels review found no blocker: group intervals telescope through the next member/end, so padding remains with its preceding member; zero-sized members remain valid. The extracted writer preserves own-size bounds, absolute relocation runs, and trap/zero filling. Thunk/NOBITS/synthesized extra buffers retain the original path. The first/last run_tasks join still precedes emitted-relocation target patching.

Targeted native integration completed on wx-workstation: 13 passed, 0 skipped, 0 failed, including the 5000-output-section byte-comparison regression case, many-input/output sections, emitted relocations, and section alignment. Candidate is frozen for the parent's eight-corpus screen.

Untimed path coverage (one link each, all eight golden hashes matched):

| Case | Flattened output sections | Member groups | Flattened bytes |
|---|---:|---:|---:|
| hello | 0 | 0 | 0 |
| rhello | 0 | 0 | 0 |
| tblgen | 0 | 0 | 0 |
| lld | 19 | 3328 | 499407638 |
| clang | 18 | 5930 | 905590018 |
| clang-s | 10 | 2940 | 85240286 |
| ra | 18 | 7818 | 140930233 |
| ra-s | 13 | 7177 | 67261726 |

The tiny and tblgen cases use the original scheduling path; every large case exercises cross-section batching.

Performance decision: reject the initial prototype. All eight golden outputs matched in the 24-pair screen. Negative deltas are improvements.

| Case | Wall change (95% interval) | CPU change (95% interval) | RSS change |
|---|---:|---:|---:|
| hello | -0.8% [-3.4, +2.4] | +0.4% [-2.5, +3.3] | +0.0% |
| rhello | +1.0% [-1.8, +4.3] | +0.9% [-1.5, +4.0] | -0.2% |
| tblgen | -3.1% [-6.2, +1.6] | -3.2% [-7.0, +1.8] | -0.7% |
| lld | +1.2% [+0.5, +2.5] | +1.7% [-3.6, +11.2] | +0.1% |
| clang | +1.0% [-0.7, +2.6] | -1.8% [-17.9, +5.1] | +0.1% |
| clang-s | +6.6% [+4.8, +9.1] | +0.1% [-1.6, +2.5] | +0.3% |
| ra | +7.6% [+4.6, +12.7] | -1.1% [-3.5, +2.3] | -0.1% |
| ra-s | +5.5% [+2.2, +8.6] | +1.1% [-0.1, +2.9] | +0.1% |

Cross-section batching increases latency for stripped Clang and both rust-analyzer variants without a material CPU reduction. Preserve the branch for review; do not include it in the omnibus.
