All topics start independently at `f8638be95ae14954ec3b1029e6008128d7a27f1b`. Builds and validation run only on `ssh wx-workstation`, CPUs 16–23, under the shared workstation gate; parent runs timing and profiles under the exclusive gate. These are experiments, not accepted changes. Floating point and random seeds are unchanged/N/A.

# CR4: Translate input fragment offsets after layout

Code source `168ca9f5`; test-corrected source `a14c236e2bdc2d19eaf16f87361cde2282953ef0`. Binary `e7c08c342d0cfdd2174a302c7c6603c32345ff54563adcca68a2f18046f356bd` built from code commit at remote `bin/cr4`.

Each eligible input merge section gets a sidecar of final u64 offsets in input-fragment order after all merged-layout and DWARF32-ordering passes, before debug compression relocates data. Eligibility: nonallocated `.debug_*` SHF_STRINGS output pool with estimated cardinality >=4096, input with >=32 fragments. The existing range lookup yields the sidecar index; final address uses the current parent sh_addr and bypasses the rich fragment map. EntryIds remain for identity/tombstones and all original users. Prefetch targets the input sidecar when present; fallback keeps the original guessed map prefetch.

Behavior proof: the sidecar copies final rich offsets and is immutable thereafter. `final_offset` clears before every lookup, including early returns, and only a successful lookup fills it using next-1 (the chosen fragment index). Cached and uncached paths add the same current parent address. Symbol/addend semantics, relocation order, diagnostic order, arithmetic, and tombstone identity are unchanged. Compression occurs after preparation, so its relocation pass sees final offsets. Allocated, tiny, non-string, and non-debug pools retain baseline resolution. Merge equality, alignment, and layout order are untouched.

Costs/limits: this applies to the shared nonallocated resolver on all targets, but validation so far is native x86_64. Sidecars cost 8 bytes per eligible input fragment, 16 bytes of metadata per MergeInfo, an extra preparation traversal, and a cache-state field. Duplicate input fragments duplicate offsets even when their output record is shared; total size may exceed CR1. This is a deliberate trade to replace random global rich-record reads with compact input-local reads. The preparation timer is `prepare_fragment_offsets`, with `translated_debug_fragments` once per input for attribution (no per-relocation instrumentation).

Validation: build and unit helper passed. Added native case crosses the threshold with 8192 unique/4096 duplicate strings, checks named/section/negative addends against actual string bytes, confirms translation counter, and checks exact decompressed probe/string data. Full native passed: 551 passed, 14 skipped, 0 failed. Independent read-only review by merge_ownership found no blocking issue. The parent-exclusive golden/timing screen subsequently completed; rejection results appear below.

Validation count from remote helper logs: 33 mold library tests and 2 mold-tests harness tests passed (0 failed).


<!-- final-screen-summary -->

Measured result: rejected. Input-local offsets increased memory and large-link latency. Their preparation and duplicate-offset storage did not repay the avoided rich-map reads.

All eight output hashes matched. Positive deltas mean more cost. These runs reuse the harness output pathname and compare with the original frozen f8638be9 baseline in the same result file. Neither input caches nor host VM state were flushed. Raw links: `../results/screen-fourth.json`; derived paired summary: `../results/summary-fourth.json`.

| Case | Pairs | Wall delta % [95% CI] | CPU delta % [95% CI] | Peak RSS delta % |
|---|---:|---:|---:|---:|
| hello | 24 | -0.63 [-3.52, +4.86] | +0.95 [-2.81, +5.09] | +0.00 |
| rhello | 24 | +1.31 [-0.85, +3.26] | +1.11 [-0.99, +2.97] | +4.82 |
| tblgen | 24 | +0.16 [-4.11, +5.05] | -0.94 [-4.94, +3.04] | +8.49 |
| lld | 24 | +1.36 [+0.54, +2.61] | +6.02 [+2.12, +13.84] | +5.29 |
| clang | 24 | +3.79 [+2.23, +4.37] | +4.11 [-2.89, +8.31] | +4.24 |
| clang-s | 24 | +1.74 [-2.12, +5.94] | -0.03 [-2.58, +1.42] | -0.29 |
| ra | 24 | +3.57 [+0.69, +9.32] | -2.11 [-4.76, +1.19] | +0.37 |
| ra-s | 24 | +2.99 [-1.63, +6.36] | +0.28 [-1.02, +1.67] | +0.10 |
