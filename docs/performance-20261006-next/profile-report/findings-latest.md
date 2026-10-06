# Latest-upstream phase findings

All 192 precise traces (eight workloads × two binaries × 12 runs) pass `audit.py --latest`: complete paired rounds, frozen binary provenance, expected adaptive workers, primary and secondary interval partitions, and nonnegative external residuals. The harness hashes the final output per case/label group: all 16 final-output digests match the eight case goldens; it does not hash every repetition.

Production sources are control `f1dec0f067198959a1339e761f27f27ccc4179d1` and combined P1 + H1 `8e522e5217adea17329e8e2eeb753fc482de4b16`, both on upstream `75200f107ee958227e87a96e67ad491567a4854a`. `manifest-latest.json` records their distinct instrumentation commits and binary hashes. Instrumentation has the same patch-id as the earlier phase stage. These measurements explain attribution; they do not replace the uninstrumented production comparisons.

## Observed operating state

There is no uniform high- or low-contention label for this eight-case collection. Clang's control profile has a 291.87 ms mean foreground window and 6156.1 ms process system CPU, whereas lld remains at 74.62 ms and 331.7 ms. The earlier, different-source control profiles measured 165.88 ms / 1504.0 ms for Clang and 78.36 ms / 338.3 ms for lld. These are descriptions of distinct measured sessions, not optimization comparisons across source revisions or proof of one common kernel cause.

The current uninstrumented Clang 80-round repeat also recaptured a higher-cost state; retain it alongside the earlier latest-source 50-round reused-output result in which combined Clang regressed 1.75% (95% interval +0.30 to +3.13). H1 remains a conditional tradeoff. The later favorable state does not erase that regression.

Whole-window user/system values below are process-wide CPU totals summed across workers. They are not per-phase CPU allocations. Elapsed windows exclude argument/target setup before the existing `all` timer, trace rendering, and final exit; they include post-`all` input-mapping release.

| Case | Workers | Control window ms | Control user CPU ms | Control system CPU ms | Combined window ms | Combined user CPU ms | Combined system CPU ms |
|---|---:|---:|---:|---:|---:|---:|---:|
| hello | 1 | 2.20 | 1.45 | 0.75 | 1.83 | 1.08 | 0.75 |
| rhello | 2 | 9.34 | 10.55 | 5.17 | 9.44 | 10.35 | 5.63 |
| tblgen | 12 | 15.94 | 70.98 | 42.98 | 15.61 | 66.87 | 43.62 |
| lld | 32 | 74.62 | 1473.12 | 331.68 | 74.17 | 1456.58 | 324.80 |
| clang | 32 | 291.87 | 2144.05 | 6156.14 | 266.89 | 2174.90 | 4449.75 |
| clang-s | 32 | 51.11 | 895.64 | 244.70 | 52.23 | 903.29 | 248.43 |
| ra | 32 | 120.49 | 2092.91 | 401.20 | 118.58 | 2113.53 | 364.95 |
| ra-s | 32 | 113.01 | 1574.12 | 305.87 | 114.83 | 1549.29 | 304.46 |

## Where foreground elapsed time goes

This table uses the latest-control mean window. Copy / relocate excludes nested Build ID / advice; all categories partition the window without overlap. Primary charts should use means, since separately computed medians need not add.

| Case | Merge ms / share | Copy ms / share | Build ID ms / share | GC ms / share |
|---|---:|---:|---:|---:|
| hello | 0.04 / 2.0% | 0.05 / 2.3% | 0.01 / 0.4% | 0.00 / 0.0% |
| rhello | 2.24 / 23.9% | 1.66 / 17.7% | 0.44 / 4.7% | 0.28 / 2.9% |
| tblgen | 3.41 / 21.3% | 2.22 / 13.9% | 0.52 / 3.3% | 1.06 / 6.7% |
| lld | 21.18 / 28.4% | 14.53 / 19.5% | 3.88 / 5.2% | 0.00 / 0.0% |
| clang | 33.91 / 11.6% | 145.54 / 49.9% | 64.20 / 22.0% | 0.00 / 0.0% |
| clang-s | 6.37 / 12.5% | 6.49 / 12.7% | 1.21 / 2.4% | 0.00 / 0.0% |
| ra | 11.73 / 9.7% | 33.55 / 27.8% | 3.44 / 2.9% | 13.77 / 11.4% |
| ra-s | 7.20 / 6.4% | 28.63 / 25.3% | 2.62 / 2.3% | 14.86 / 13.2% |

Clang now spends 49.9% of the selected foreground window in Copy / relocate and another 22.0% in Build ID / advice. Across the paired profile copies, Copy is almost unchanged (145.54 → 144.01 ms), whereas Build ID / advice shrinks from 64.20 to 39.38 ms. Merge is 33.91 → 34.74 ms. This localizes the observed elapsed-time change to the build-ID/advice interval in this session; overlapping process CPU snapshots do not prove an exclusive CPU allocation to that phase.

The other workloads retain distinct limits. In lld, string merging is 28.4% and copying 19.5%. Rust-analyzer spends 27.8% in copying, 11.4% in GC, and 9.7% in merging. Stripped Clang has much smaller absolute merge/copy costs, leaving input, symbols, layout, and scanning as a larger portion of the link.

## What Other contains

This is an additive subdivision restricted to Other. Input / symbol resolution subtracts nested Gather symbols. Output assembly / layout subtracts primary Merge strings and includes output-section creation/sorting, sizes/headers/offsets, dynamic-symbol sorting, and output symbol-table sizing. Later merged-section layout remains here. The residual includes checks, smaller passes, thread-pool setup, and uninstrumented gaps.

| Control case | Input / resolve ms | Output assembly / layout ms | Relocation scan ms | Checks / setup / remaining ms | Total Other ms |
|---|---:|---:|---:|---:|---:|
| hello | 1.34 | 0.15 | 0.02 | 0.09 | 1.60 |
| rhello | 2.39 | 0.71 | 0.19 | 0.67 | 3.97 |
| tblgen | 4.07 | 1.26 | 0.44 | 1.48 | 7.25 |
| lld | 9.30 | 9.87 | 4.98 | 4.68 | 28.83 |
| clang | 12.08 | 14.24 | 7.48 | 5.54 | 39.34 |
| clang-s | 12.09 | 7.42 | 7.50 | 5.55 | 32.57 |
| ra | 18.88 | 13.75 | 8.05 | 7.00 | 47.68 |
| ra-s | 19.96 | 13.21 | 9.14 | 7.99 | 50.30 |

No GDB-index background timers occur in these eight workload commands; their GDB overlay is zero. Explicit-parent handling remains present for traces that contain background GDB work. Per-chunk copy intervals can overlap and are not summed.

Native timer CPU deltas include all process threads active in their intervals and overlap across nested timers. Use whole-link production CPU data for efficiency comparisons and the separate kernel-inclusive sampled call stacks for CPU-location attribution. Do not infer a phase-specific CPU stack from these elapsed-time shares or transplant an earlier kernel sample percentage into this profile session.
