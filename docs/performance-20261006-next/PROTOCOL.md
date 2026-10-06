# Second optimization campaign

Baseline f8638be95ae14954ec3b1029e6008128d7a27f1b. All 15 topics are independent unless a genuine dependency is documented.

Remote root: /home/callen/work/mold-next-20261006. Global gate: /home/callen/work/mold-radical-20261006/workstation.lock. Root exclusively runs benchmarks and performance profiles. Shared lock for all sync, build, test, and untimed counters. Each topic owns src/ID, targets/ID, bin/ID, logs/ID. Frozen binary+SHA+source commit must be sent to parent before measurements; do not overwrite queued candidates.

Run /home/callen/work/mold-next-20261006/run-work.sh ID build|unit|native|check|full|shell. Resource groups MS*:0-7; CR1–4:16-23; CR5/S1/S2/G1:8-15; P1/H1/H2/omnibus:24-31. Cargo -j8 and 24GiB/container ceiling. Avoid simultaneous builds within a track.

Sync with rsync -az --delete --exclude=.git --exclude=.codex --exclude=target --exclude=out --rsync-path='flock -s /home/callen/work/mold-radical-20261006/workstation.lock rsync' LOCAL_WORKTREE/ wx-workstation:/home/callen/work/mold-next-20261006/src/ID/

Unrelated GPU inference optimization workload must be left alone. No host tuning, cache flushing, affinity edits to others, or process killing. Record CPU/memory/IO activity around performance runs. Delayed/invalid timings must be labeled, not silently discarded. Repeat selective candidates if host activity may affect acceptance.

Acceptance: byte-identical eight-corpus output, targeted correctness and native integration, interleaved baseline/candidate wall+CPU+RSS. Follow promising candidates with fresh paired samples and phase profiles, then measure combined improvements and broad-architecture validation. Reject neutral/regressive changes, preserve reviewable worktrees and evidence.

Publication refreshes use separate frozen controls and binaries. The first combined comparison rebased the original PR onto upstream1347ca95 (control d5f03691); the final publication refresh uses upstream75200f10 (control f1dec0f0, combined8e522e52). Original topic screens remain based on f8638be9. Never pool these baselines. run-latest.sh uses the renamed libmold/mold packages and permits fetching the newly published allocator dependencies; run-work.sh preserves the earlier package commands.

Each case uses one harness-owned output path shared by the interleaved variants. Reused mode retains that path; --fresh-output removes it before each invocation outside link timing. Neither mode flushes input caches. Output mode alone does not explain the observed high/low contention states. Final-output hashing covers the last measured invocation of each case/label group, not every invocation.

All test containers use --init to reap orphaned children while keeping the same resource caps. One earlier broad-suite attempt without an init reached the2048-process cap and was stopped; its logs are retained as an infrastructure failure. The complete rerun passed. Missing32-bit Rust standard libraries were installed only inside disposable test containers before the corresponding host checks.
