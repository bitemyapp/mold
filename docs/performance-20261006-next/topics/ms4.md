# MS4: dense unique rich records with compact bucket indices

Status: rejected after the paired eight-corpus screen.

- Branch: `codex/mold-ms4-dense-fragments`
- Worktree: `/Users/callen/.codex/worktrees/mold-ms4-dense-fragments/mold`
- Base: `f8638be95ae14954ec3b1029e6008128d7a27f1b`

- Commit: `d33ea5505f71adb604f660174bed64a3cb68c682`
- Remote binary: `/home/callen/work/mold-next-20261006/bin/ms4`
- Binary SHA256: `01563d19f361d3bdedd870da6f32226a11d47e7392dddfe8908c6a6c9a47c5b1`

## Hypothesis and implementation

Replace each rich sparse bucket with a 4-byte atomic state/index. Unique strings allocate rich records in a dense prefix per shard. Duplicate insertions allocate nothing. Records live at fixed addresses for the map lifetime, and external EntryId remains the bucket index.

## Behavior and safety argument

The hash, table capacity, probe sequence, key equality and canonical collision-run ordering remain unchanged. A winner initializes its callback before reserving a unique record index, writes that record, then release-publishes the dense index. Readers acquire the index before reading immutable key data or the initialized value. Each shard counter names an initialized prefix after insertion joins; drop destroys that prefix exactly once. Floating point and RNG are not involved.

## Risks and limits

Dense rich backing still reserves worst-case virtual address space per shard; only initialized prefixes touch physical pages on anonymous-mapping platforms. Windows allocator behavior may differ. Each unique insertion adds a sharded atomic increment; each occupied probe and final value lookup adds index indirection. Both effects can erase memory savings. The u32 external identity limit is checked before allocation.

## Validation and results

Remote release and library unit suites passed. Full native integration: **550 passed, 14 skipped, 0 failed**. Added forced collision wrap ordering, parallel duplicate publication/destruction, and failed-initializer destruction coverage. Independent source review by the relocation agent found no publication/drop/equality/order defect; it highlighted the dependent bucket-index load before rich-value prefetch. No sanitizer or Windows runtime claim is made.

The prototype removes a redundant bucket reload when returning the value of an already acquired record. It does not incorporate MS1 or MS2: rich keys and values remain colocated in dense records, and layout still uses the baseline occupancy-count pass. Measured tradeoffs and rejection are recorded below.

## Results and decision

Parent-exclusive 24 measured links per variant and case; all eight outputs matched goldens. Raw results: `results/screen-fourth.json`, summary-fourth.json. lld wall +6.0% (95% CI +5.2% to +7.1%), CPU +8.2% (+4.7% to +18.4%), median per-link peak RSS -3.1%. Clang wall +8.7% (+7.2% to +9.3%), CPU +4.0% with an inconclusive interval, RSS -1.3%. Rust Analyzer wall +6.1% (+3.0% to +13.2%), CPU +5.2% (+2.6% to +8.5%), RSS -2.2%. TableGen wall +4.7%, CPU +6.4%, RSS -1.7%. Absolute metrics and all-case results are in the raw file and report-data exports.

Dense rich records reduce whole-link memory modestly, but repeated dependent index loads and unique-record counter updates introduce costs absent from the original direct bucket/value path. Those are source-level candidate explanations, not separate hardware-counter attribution. The measured latency/CPU regressions outweigh the memory reduction for this goal. No further revision is proposed without a new mechanism; the independent branch and frozen binary remain preserved as a rejected experiment.

Validation logs are mirrored under `validation/ms4/`: linker library unit tests 36 passed, runner library 2 passed.
