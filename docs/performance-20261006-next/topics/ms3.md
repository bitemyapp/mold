# MS3: density-guided fragment storage reservation

Status: rejected after the paired screen and explanatory allocation counts.

- Branch: `codex/mold-ms3-fragment-reservations`
- Worktree: `/Users/callen/.codex/worktrees/mold-ms3-fragment-reservations/mold`
- Base: `f8638be95ae14954ec3b1029e6008128d7a27f1b`

- Commit: `8db6b72248d04d4feefc0d788fea9f9c0cfbab0f`
- Binary SHA256: `c906164968f14eb8db38c6c713f5d94f4a25d2974074a3555cab52baf5a20871`
- Remote binary: `/home/callen/work/mold-next-20261006/bin/ms3`

## Hypothesis and implementation

After the 64th naturally scanned string, use observed bytes per fragment plus 12.5% headroom to reserve offset/hash arrays. Cap the prediction at 65536 entries per array. Fixed-record exact reservations remain unchanged. No extra string scan or global counter is added to production.

## Behavior and safety argument

All null detection, hashes, offsets and HLL insertions happen in the same order on the same bytes. Reservation affects capacity only. If prediction underestimates, standard Vec growth remains available. If the first strings misrepresent later density, the reservation is bounded. Floating point and RNG are not involved.

## Risks and limits

A misleading dense prefix may overreserve up to 768 KiB combined per section; sparse prefixes may underpredict. Many medium sections could amplify overhead. Separate measurement-only builds will quantify real capacity changes, pointer-moving reallocations and bytes of live elements moved; those are allocator observations, not timings.

## Validation and results

Release build and library unit suites passed on wx-workstation. Full native integration: **551 passed, 14 skipped, 0 failed**. New test covers opposite density changes after a 64-string prefix, 32-bit-wide strings, references to every string, and byte-identical output with 1 and 8 threads. Existing malformed mergeable-section diagnostics remain covered. The parent-exclusive screen and golden comparison are described below.

Measurement-only allocation sources are exported from the exact baseline/candidate commits using `measurement/ms3/prepare_counts.py`. No counters are present in the production branch or binary. The script observes capacity changes and pointer changes at each offset/hash push and reservation; only changed pointers with live elements contribute moved bytes. This records live element payload relocated, not hardware memory traffic or elapsed time.

## Screen and allocation attribution

All eight output hashes matched in the parent-exclusive 24-run-per-variant screen (`results/screen-third.json`, exact filename recorded in summary-third.json). TableGen wall +5.6% (95% CI +0.7% to +8.9%), CPU +7.1% (+0.2% to +12.3%), and median per-link peak RSS +33.7%. lld wall +0.3% and CPU -2.0% were inconclusive, with RSS +13.2%; Clang wall -0.4% and CPU +2.3% were inconclusive, with RSS +7.4%. Rust Analyzer remained neutral with RSS +2.9%. The candidate is rejected.

Separate instrumented baseline/candidate sources and binaries ran three untimed repetitions on all eight cases with eight threads on CPUs 0–7. All 48 outputs matched goldens. Clang offset/hash capacity changes fell from 93,188 to 69,828 and moved live payload from 266.17 to 13.95 MiB, but the sum of per-input capacities at split completion rose from 266.69 to 493.80 MiB. lld moved payload fell from 152.21 to 10.09 MiB while capacity rose 152.59 to 294.13 MiB. TableGen capacity more than doubled (4.10 to 9.35 MiB). The first 64 strings overpredicted later density on these corpora; allocation avoidance was real but bought excessive retained capacity. The production screen, not instrumented timing, establishes the rejection.

Raw counters, commands, binary/output hashes, min/median/max summaries and CSV are under `measurement/ms3/results/`. Instrumentation-only source patches and preparation scripts are in `measurement/ms3/`; production bin/ms3 remained untouched. Instrumented baseline SHA `2bd1efd6402296690cac4631bf31cc161a4074c037155339cd7ecd051c7a268e`; instrumented candidate SHA `5f13c29d187133b6215adc643dbf5a0fc82b0697d391a2d0b9b62c5f891cdae8`. Pointer-moving counts depend on allocator configuration; here all three repetitions agreed exactly.

The capacity counter sums each input section at split completion; it is not a sampled process working set or peak RSS. Hash arrays are subsequently freed during resolution. Production RSS figures come only from the separate unprofiled benchmark samples.

Validation logs are mirrored under `validation/ms3/`: linker library unit tests 33 passed, runner library 2 passed.
