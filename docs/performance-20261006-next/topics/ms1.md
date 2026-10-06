# MS1: compact probe keys, separate bucket-indexed values

Status: first production candidate rejected by the paired screen; no revision without a new mechanism.

- Branch: `codex/mold-ms1-compact-probes`
- Worktree: `/Users/callen/.codex/worktrees/mold-ms1-compact-probes/mold`
- Base: `f8638be95ae14954ec3b1029e6008128d7a27f1b`
- Commit: `f8bb8d521df7f478c453e8a4d79c41a7c8dd8832`
- Remote binary: `/home/callen/work/mold-next-20261006/bin/ms1`
- Binary SHA256: `930881d2798b67c8c87b3dcf9bd21b2a6033bf6105a35235144635e41bae7c42`

## Hypothesis and implementation

The previous profile showed random merge-table probes and fragment-value access dominating string merging. Split the old aligned rich entry into a 16-byte key bucket and a separate bucket-indexed value array. This doubles keys per cache line and reduces stride for later value lookup. It retains the existing sparse representation and introduces no descriptor redistribution or additional input pass. Hashing, table capacity, home buckets and collision probes are unchanged.

For SectionFragment the nominal combined storage remains 32 bytes per bucket (16 key + 16 value). Successful insertion now accesses two arrays; footprint locality is a hypothesis, not an automatic savings. The candidate also has two anonymous mappings. Value access and prefetch target the value array, while insertion prefetch targets compact keys.

## Behavior and safety argument

EntryId still names the identical bucket. CAS ownership, key length, key-byte equality and acquire/release publication are unchanged. Only a winning inserter writes the matching separate value slot, before publishing its key. Frozen lookup follows the same bucket index. Drop examines published keys and destroys each initialized value exactly once. Both allocations retain their exact allocation/deallocation size and alignment on each platform. Collision-run sorting, wraparound handling, tie-breaking and final output order are unchanged. Floating point and RNG are not involved.

## Validation

All compilation and tests ran on wx-workstation through the shared gate and bounded ms1 helper. Release build and library unit suites passed. Full native integration: **550 passed, 14 skipped, 0 failed**. Added forced wraparound collisions with opposite insertion orders plus parallel duplicate insertion/value-publication/exactly-once destruction coverage. Generic map users include merge fragments and GDB index names; native coverage includes both. Parent's paired screen verified byte-identical output on all eight benchmark corpora.

No Windows runtime or sanitizer claim is made; platform allocation was source-reviewed. Broader architecture testing is reserved for candidates retained for integration.

## Results and decision

Source: `results/screen-ms1.json`, `results/summary-ms1.json`; 24 unprofiled samples per case and variant after warmups, parent-exclusive queue. Parent reported Clang wall **+4.8%** (95% CI +2.5% to +9.2%), CPU **+5.7%** (+3.6% to +7.7%), RSS +0.1%; lld wall +3.5% and CPU +3.4% with intervals crossing zero; Rust Analyzer wall +2.1%, CPU -0.3%. Rust hello wall -3.6% does not offset the large-workload regression. Absolute samples, quantiles and resource metrics remain in the raw result.

The extra key/value memory accesses plausibly outweigh probe-stride savings; this is a source-level explanation, not an isolated hardware-counter attribution. No performance instrumentation is present in the production candidate. The branch is preserved as a rejected experiment and is not proposed for the omnibus.

Validation logs are mirrored under `validation/ms1/`: linker library unit tests 35 passed, runner library 2 passed.
