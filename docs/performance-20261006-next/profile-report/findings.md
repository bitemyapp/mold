# Final phase findings

All 192 precise traces (eight workloads × two binaries × 12 runs) pass `audit.py`: complete paired rounds, frozen binary provenance, expected adaptive workers, primary and secondary interval partitions, and nonnegative external residuals. The harness hashes the final output in each case/label group: all 16 final-output digests match their eight case goldens; it does not hash all 192 outputs. Native timer boundaries were retained. Instrumented timings describe attribution and do not establish production speedups.

These profiles were collected in the later, lower-contention session. Earlier H1 kernel-inclusive profiles captured a higher-contention state. The sessions have different absolute costs; the later phase breakdown neither replaces the earlier call-stack evidence nor proves that the same bottleneck dominated throughout the campaign.

The table uses the current-control mean foreground window. Merge and Copy are disjoint here; Build ID / advice has been removed from its enclosing Copy timer. The window excludes startup before the existing `all` timer, trace rendering, and final exit, and includes input-mapping release after `all`.

| Case | Workers | Window ms | Merge ms / share | Copy ms / share | Build ID ms / share | GC ms / share |
|---|---:|---:|---:|---:|---:|---:|
| hello | 1 | 2.25 | 0.04 / 1.9% | 0.05 / 2.2% | 0.01 / 0.3% | 0.00 / 0.0% |
| rhello | 2 | 9.30 | 2.35 / 25.3% | 1.57 / 16.9% | 0.42 / 4.6% | 0.29 / 3.1% |
| tblgen | 12 | 15.62 | 3.10 / 19.7% | 2.28 / 14.6% | 0.54 / 3.4% | 1.04 / 6.6% |
| lld | 32 | 78.36 | 22.44 / 28.6% | 15.60 / 19.9% | 4.20 / 5.4% | 0.00 / 0.0% |
| clang | 32 | 165.88 | 40.45 / 24.3% | 52.62 / 31.8% | 21.95 / 13.3% | 0.00 / 0.0% |
| clang-s | 32 | 58.43 | 7.11 / 12.2% | 8.64 / 14.7% | 1.57 / 2.7% | 0.00 / 0.0% |
| ra | 32 | 128.03 | 12.74 / 9.9% | 35.10 / 27.3% | 3.94 / 3.1% | 14.40 / 11.3% |
| ra-s | 32 | 108.45 | 6.73 / 6.2% | 28.58 / 26.4% | 2.28 / 2.1% | 14.21 / 13.1% |

The large unstripped C++ links still put substantial elapsed time into string merging: lld 28.6% and Clang 24.3%. Copy / relocate contributes another 19.9% and 31.8%, respectively. Clang also spends 13.3% in Build ID / advice. On Rust-analyzer, copying is the larger selected center (27.3%), while GC is 11.3% and merging 9.9%. Stripping Clang reduces the absolute merge/copy work strongly; input, symbols, layout, and scanning then account for more of the remaining link.

Hello's main difference is localized to the existing COMDAT-signature timer: its mean falls from 0.429 ms in current to 0.0037 ms in omnibus. This is nested within symbol resolution, so it must not be added again. It supports the P1 mechanism; the independent uninstrumented production comparison remains the performance result.

## What Other contains

This is an additive subdivision of Other, not extra time. Input / symbol resolution subtracts nested Gather symbols. Output assembly / layout subtracts Merge strings and includes output-section creation and sorting, size/header/offset computation, dynamic-symbol sorting, and output symbol-table sizing. Later merged-section layout therefore remains here. The residual includes checks, other smaller passes, thread-pool setup, and uninstrumented gaps.

| Current case | Input / resolve ms | Output assembly / layout ms | Relocation scan ms | Checks / setup / remaining ms | Total Other ms |
|---|---:|---:|---:|---:|---:|
| hello | 1.40 | 0.15 | 0.02 | 0.09 | 1.65 |
| rhello | 2.33 | 0.75 | 0.19 | 0.64 | 3.90 |
| tblgen | 4.05 | 1.24 | 0.44 | 1.46 | 7.19 |
| lld | 9.47 | 10.49 | 5.21 | 4.56 | 29.73 |
| clang | 13.30 | 14.40 | 8.14 | 5.92 | 41.75 |
| clang-s | 13.07 | 8.64 | 8.14 | 5.99 | 35.84 |
| ra | 20.17 | 14.89 | 8.39 | 7.58 | 51.02 |
| ra-s | 19.57 | 11.88 | 8.40 | 7.58 | 47.43 |

The residual after this subdivision is only about 4.56 ms for lld and 5.92 ms for Clang. The large Other wedge is thus mostly explained by input/symbol resolution, output assembly/layout, and relocation scanning rather than an unidentified parallel phase.

## CPU and overlays

No GDB-index background timers occur in these eight workload commands, so the GDB union and overlap are zero. The decoder still preserves explicit parentage and supports the overlay when present. Per-chunk copy timers can overlap and are not summed.

User/system timer deltas are process-wide, across all workers. Nested or overlapping intervals cannot be assigned exclusively to individual phases. Whole-window process user/system totals are preserved in the JSON for diagnosis; use the uninstrumented production measurements for total CPU comparisons and the separate kernel-inclusive sampling data for CPU-call-stack attribution. No phase-specific CPU stack is inferred from the elapsed-time shares.
