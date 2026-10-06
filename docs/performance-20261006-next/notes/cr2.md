All topics start independently at `f8638be95ae14954ec3b1029e6008128d7a27f1b`. Builds and validation run only on `ssh wx-workstation`, CPUs 16–23, under the shared workstation gate; parent runs timing and profiles under the exclusive gate. These are experiments, not accepted changes. Floating point and random seeds are unchanged/N/A.

# CR2: Repeated-fragment range hint

Instrumented source `b6c6c09f`, binary `a9101dcbe9eb6e336f06c6fbb3e2439a0ef345c82889186559e9aa98962f521f` preserved at `bin/instrumented/cr2`. Clean source `7f9e54cee5c55fb729107a7827d80aa84158868a`, binary `78ed4a2db7d8b0fe21c00dbab63a5db24ef8869a908ccd1641de3a334e07cdf8` at `bin/cr2`.

The existing next-fragment interval check is followed by a previous-fragment interval check before binary search. `next` remains one past the last result. This is a per-stream location hint, not the failed C1 per-symbol operand cache. It is shared by nonallocated relocation resolution across architectures. Addends, resolved symbols, overflow checks, tombstones, order, and existing fragment+8 prefetch are unchanged.

Behavior proof: each fast path uses the same half-open interval selected by partition_point; the last interval extends without an upper boundary just as baseline. Before-first and empty inputs retain failure. Misses use exactly the original binary search. Unit coverage compares all tested offset/hint pairs against the original lookup, including repeated, backward, end, and invalid hints. Full native before counter removal: 550 passed/14 skipped/0 failed; clean rebuild and unit helper passed afterward. The parent-exclusive golden/timing screen subsequently completed; rejection results appear below.

Untimed counters use the instrumented binary and are not performance measurements. Production counters were removed before timing, avoiding their per-lookup atomic-enabled-flag check. Raw logs: `../results/cr2-stats/`. Denominator is next + previous + fallback calls. Next includes the initial hint at fragment zero, not solely a transition from another fragment. Fallback includes failed before-first/empty lookups. Zero rows had no recorded fragment-hint call.

| Case | Next | Previous | Fallback | Total | Previous % | Fallback % |
|---|---:|---:|---:|---:|---:|---:|
| hello | 0 | 0 | 0 | 0 | 0.0000 | 0.0000 |
| rhello | 13,575 | 38 | 18,961 | 32,574 | 0.1167 | 58.2090 |
| tblgen | 238,075 | 131 | 122 | 238,328 | 0.0550 | 0.0512 |
| lld | 9,359,984 | 2,429 | 3,612 | 9,366,025 | 0.0259 | 0.0386 |
| clang | 16,312,607 | 3,443 | 5,022 | 16,321,072 | 0.0211 | 0.0308 |
| clang-s | 0 | 0 | 0 | 0 | 0.0000 | 0.0000 |
| ra | 772,610 | 734 | 850,563 | 1,623,907 | 0.0452 | 52.3776 |
| ra-s | 0 | 0 | 0 | 0 | 0.0000 | 0.0000 |

Interpretation: C++ references are already overwhelmingly consecutive; fewer than 0.06% can benefit from the new repeated hint. Rust analyzer falls back to binary search on about half of its fragment lookups, while repeats remain rare. This suggests scattered/interleaved references rather than an immediately repeated-fragment problem. The clean candidate still merits the requested direct measurement, but the mechanism has a low upside ceiling and adds a range check on misses.

Measured result: rejected. Clean candidate, 24 interleaved runs per case, all eight output hashes match. No reliable wall or CPU improvement. The low repeated-hit fraction predicted this result. Positive deltas mean more cost; 95% intervals shown.

| Case | Wall delta % [CI] | CPU delta % [CI] | RSS delta % |
|---|---:|---:|---:|
| hello | -0.67 [-4.45, +5.68] | -0.57 [-3.35, +5.17] | +0.15 |
| rhello | -2.07 [-5.97, +2.48] | -0.09 [-5.38, +2.02] | -0.01 |
| tblgen | -1.35 [-3.33, +0.68] | -2.42 [-4.45, +0.53] | +0.62 |
| lld | +0.50 [-1.54, +2.43] | +2.70 [-13.96, +13.13] | -0.30 |
| clang | +0.88 [-1.76, +3.98] | +5.72 [-4.14, +21.31] | +0.01 |
| clang-s | +1.27 [-3.72, +4.63] | -0.72 [-3.27, +0.97] | -0.27 |
| ra | -2.27 [-4.73, +1.74] | +1.28 [-0.56, +2.49] | +0.09 |
| ra-s | +0.34 [-2.38, +4.02] | -0.66 [-2.96, +1.88] | -0.08 |

Validation count from remote helper logs: 33 mold library tests and 2 mold-tests harness tests passed (0 failed).
