# MS2: single-pass layout collection

Status: reservation-only v1 and exact-count-reuse v2 both validated, measured and rejected. The final v2 results appear below.

- Branch: `codex/mold-ms2-single-pass-layout`
- Worktree: `/Users/callen/.codex/worktrees/mold-ms2-single-pass-layout/mold`
- Base: `f8638be95ae14954ec3b1029e6008128d7a27f1b`

- Commit: `10fcda6c688f474571b79c63f6c23c16e7d89269`
- Binary SHA256: `9204becb1de90c9d8d5c0871cb350050282b10bc5aa4b9d3b459d18f24cc780e`
- Remote binary: `/home/callen/work/mold-next-20261006/bin/ms2`

## Hypothesis and implementation

Remove the full shard occupancy-count traversal used only to reserve the layout vector. Reserve the bounded shard size instead; actual occupancy is obtained by the existing collection length. This avoids new atomic insertion counters and does not change map capacity.

## Behavior and safety argument

The trailing wrap collection, forward collection, key-length/key-byte comparator and bucket IDs are identical. A larger Vec capacity changes storage only; all pushes and returned IDs preserve order. Forced wraparound opposite-insertion tests cover the ordering boundary. Floating point and RNG are not involved.

## Risks and limits

Scratch reservation is now the shard upper bound rather than exact occupancy. Sparse maps may reserve more address space and materialize more pages if later writes fill them; RSS must be measured.

## Validation and results

Release build and library unit suites passed on wx-workstation. Full native integration: **550 passed, 14 skipped, 0 failed**. Added forced wraparound collisions with opposite insertion orders; generic map users include both merge fragments and GDB index names. The later parent-exclusive screen and eight-corpus golden comparison completed; see the final results below.

## V1 measurement and bounded revision

All eight hashes matched in the 24-run-per-variant screen (summary-second.json). Clang wall +1.7% (95% CI -0.7% to +3.8%), CPU +15.3% (+3.9% to +21.7%), median per-link peak RSS +1.1%; lld wall +0.4% and CPU +4.8% were inconclusive with RSS +1.7%; Rust Analyzer wall +2.0%, CPU -0.9% were inconclusive with RSS +1.8%. The upper-bound reservation produced no payoff and is rejected; bin/ms2 remains the frozen v1 artifact.

V2 restores exact layout Vec capacity. A bounded 64-element array belongs to each Rayon fold of the existing member traversal. Only the thread that receives inserted=true increments its local shard count; folds reduce by elementwise addition. Both resolver paths and synthetic .comment insertions participate. Freeze attaches the final counts, which layout and length queries reuse. Generic maps without supplied counts retain the original scan. There is no per-unique shared atomic, no extra input scan and no fragment descriptor stream. Costs are one local scalar increment per unique insertion, fold-array reduction, and a 512-byte count box per counted map on this host.

The key/probe/ordering and output bytes are unchanged. A new concurrent duplicate-insertion test checks that fold reduction exactly matches every shard’s collected entries. The original wraparound and generic-map fallback tests remain. Remote validation passed. Independent source review was requested, but no completed review is recorded.

V2 source commit: `3ef1d72da621bebe186476692b5570b83c2a163b`. Frozen remote binary `bin/ms2-v2`, SHA256 `b563006f96559de44ba351ad51c80b46fa84f7e1709cfc7e78a072cbfa517db7`. Release and library unit suites passed; full native **551 passed, 14 skipped, 0 failed**, including duplicate/synthetic/MOLD_DEBUG comment count coverage. The original bin/ms2 is unchanged.

Validation logs are mirrored under `validation/ms2/`. V1: 34 linker + 2 runner unit tests. V2: 35 linker + 2 runner unit tests. Both suites passed without failures.


<!-- final-screen-summary -->

Exact-count revision: rejected by the coordinator. Every wall interval includes zero; stripped rust-analyzer CPU rose 1.32% (95% interval +0.27% to +2.79%). Eliminating the extra occupancy traversal with bounded local counters did not establish a useful whole-link improvement. This closes MS2; both independent revision binaries remain preserved.

All eight output hashes matched. Positive deltas mean more cost. These runs reuse the harness output pathname and compare with the original frozen f8638be9 baseline in the same result file. Neither input caches nor host VM state were flushed. Raw links: `../results/screen-fifth.json`; derived paired summary: `../results/summary-screen-fifth.json`.

| Case | Pairs | Wall delta % [95% CI] | CPU delta % [95% CI] | Peak RSS delta % |
|---|---:|---:|---:|---:|
| hello | 32 | -2.04 [-6.35, +1.59] | -1.95 [-6.52, +1.45] | +0.00 |
| rhello | 32 | -0.95 [-3.26, +1.32] | -1.57 [-3.33, +1.28] | -0.22 |
| tblgen | 32 | -0.75 [-1.85, +2.36] | -0.29 [-3.92, +3.50] | -0.35 |
| lld | 32 | -0.13 [-0.71, +0.50] | +1.31 [-3.15, +5.15] | +0.05 |
| clang | 32 | +0.31 [-1.74, +1.89] | -5.67 [-15.28, +7.85] | -0.02 |
| clang-s | 32 | +0.80 [-2.46, +4.13] | -0.59 [-2.25, +1.17] | +0.47 |
| ra | 32 | -1.52 [-3.94, +3.19] | -0.03 [-2.25, +2.49] | +0.01 |
| ra-s | 32 | +0.93 [-1.00, +2.13] | +1.32 [+0.27, +2.79] | +0.11 |
