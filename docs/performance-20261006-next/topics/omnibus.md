# Prior1347-stage combined branch measurement

Combined source `80f062238e88d941a6b16e175477dff42e2ace4c`, binary SHA256 `4422ead1df414794d40e4a4aee1e5af3696d2fcec6d118bf965fe36f465f41b7`, combines P1 and H1. Its control is `d5f03691582bc6e425d122c5592d0b33448ff7eb`, binary `11b05349574ccca4347d85b24540d5e0b7f11066b9768d971994088f3c14d0da`. Both are rebased onto upstream `1347ca95c906db060ecfbf838a792c5739970294`. These comparisons do not use the older frozen topic baseline.

Both final campaigns completed 50 interleaved pairs across all eight cases. Every final output hash matched its same-file control. Reused and fresh output modes are separate; fresh unlinks only the harness output before the link stopwatch and does not flush input caches. Raw: `../results/omnibus.json` and `../results/omnibus-fresh.json`; paired summary: `../results/summary-omnibus.json`. Positive deltas mean more cost.

C hello improves in both modes, and Rust hello improves more modestly. Every large-case wall and total-CPU interval includes zero in this final state. In particular the fresh stripped-rust-analyzer wall interval is -1.82% to +2.51%, so the earlier standalone H1 fresh-screen hint of regression did not become a reliable combined-branch regression. This is not a proof of equivalence or of absence of all small regressions.

The later reused-output control was much cheaper on LLVM workloads than controls in the earlier H1 screens, and the large H1 gain largely disappeared. Earlier kernel profiles still show a real cleanup-contention mechanism in their recorded state. Reused-output mode alone does not cause or guarantee that state; the intervening fresh-output campaign is not a controlled explanation of the change.

Validation logs copied locally under `../validation/omnibus/` confirm linker unit 34+runner2, full native 550 passed/14 skipped/0 failed, and all-target workspace check. The first broader architecture attempt in full-20261006T180238.log hit the container PID limit2048 because PID1 did not reap children. The coordinator stopped only that container and is rerunning with --init, retaining the CPU/memory/PID limits. This failed infrastructure attempt is preserved, not counted as a passing suite. The rerun includes test-only omnibus revision007ca03c, which adds build-id-large-mmap.sh; measured production source and binary remain80f0622/4422ead1. The new test exercises >12 MiB plus partial hash-tail mapped/buffered byte equality at1/8 threads for fast/sha1/sha256. The rerun completed:18 targets,8028 pass/1026 skip/0 fail, including18 passes for the new large-output test; unit 34+2 also passed. The final format-only follow-up is review head839f4e4b; its additional formatting and armv7/i686/powerpc host-source checks passed.

## Reused output

| Case | Control → combined wall ms | Wall delta % [95% CI] | Control → combined CPU ms | CPU delta % [95% CI] |
|---|---:|---:|---:|---:|
| hello | 4.143 → 3.698 | -10.73 [-15.67, -5.10] | 4.026 → 3.563 | -11.49 [-16.30, -6.21] |
| rhello | 12.145 → 11.621 | -4.32 [-7.04, -1.75] | 18.587 → 17.604 | -5.29 [-7.53, -2.57] |
| tblgen | 17.983 → 18.104 | +0.68 [-2.24, +2.92] | 115.482 → 116.415 | +0.81 [-4.09, +4.18] |
| lld | 84.514 → 81.815 | -3.19 [-6.44, +1.63] | 1772.800 → 1770.546 | -0.13 [-2.14, +1.91] |
| clang | 138.919 → 139.438 | +0.37 [-0.83, +2.13] | 2773.125 → 2755.908 | -0.62 [-1.67, +0.57] |
| clang-s | 56.916 → 56.075 | -1.48 [-4.70, +0.98] | 1130.031 → 1126.601 | -0.30 [-2.23, +1.01] |
| ra | 131.841 → 133.247 | +1.07 [-1.61, +3.78] | 2377.745 → 2373.472 | -0.18 [-1.97, +1.43] |
| ra-s | 113.557 → 113.571 | +0.01 [-3.06, +3.25] | 1915.278 → 1909.103 | -0.32 [-2.68, +1.90] |

## Fresh output

| Case | Control → combined wall ms | Wall delta % [95% CI] | Control → combined CPU ms | CPU delta % [95% CI] |
|---|---:|---:|---:|---:|
| hello | 4.378 → 3.899 | -10.94 [-15.10, -7.56] | 4.128 → 3.669 | -11.11 [-15.41, -7.55] |
| rhello | 12.910 → 12.678 | -1.80 [-3.39, -0.04] | 20.118 → 19.502 | -3.06 [-3.79, -0.95] |
| tblgen | 21.608 → 21.196 | -1.91 [-3.02, +0.48] | 150.841 → 148.431 | -1.60 [-3.85, +0.23] |
| lld | 105.597 → 106.167 | +0.54 [-1.98, +9.45] | 1892.945 → 1885.750 | -0.38 [-2.35, +1.61] |
| clang | 152.270 → 155.474 | +2.10 [-0.61, +5.35] | 3197.530 → 3195.081 | -0.08 [-1.46, +1.63] |
| clang-s | 63.575 → 63.832 | +0.40 [-1.13, +1.92] | 1277.292 → 1253.998 | -1.82 [-4.97, +0.85] |
| ra | 153.129 → 155.920 | +1.82 [-0.70, +3.90] | 2543.919 → 2548.961 | +0.20 [-1.30, +1.59] |
| ra-s | 127.932 → 128.861 | +0.73 [-1.82, +2.51] | 2106.876 → 2078.641 | -1.34 [-3.54, +0.70] |

Source reproduction: `../patches/README.md` and `../patches/manifest.json` preserve every measured revision and final source head with exact base/source trees. The final review source 839f4e4b differs from frozen 80f0622 only by the new regression test and formatting of the existing hash expression; measured binary 4422ead1 is unchanged.
