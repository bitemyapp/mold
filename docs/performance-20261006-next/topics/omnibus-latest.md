# Latest 75200f10 experimental combined branch

Latest public upstream anchor: `75200f107ee958227e87a96e67ad491567a4854a`. Control source `f1dec0f067198959a1339e761f27f27ccc4179d1`, binary SHA256 `7bbec3c1526448e4e5426c2dada974e9c2017bfb531ca91de7b70dd6769b06ef`. Combined P1+H1 source `8e522e5217adea17329e8e2eeb753fc482de4b16`, binary `0257d93ddd1a92d5990d92294b8ae6d252bacff30dcb492f8755a8905d90d60b`.

Both release builds passed and are frozen. The rebase brings upstream crate/dependency/compression changes, so these binary identities and their same-stage measurements remain separate from prior 1347 results. Both Cargo.lock files have SHA256 `e11293521c6cf5adbb4abf011f2f1fc03686687e44563fff60fd3ce295d12763`. Build logs are under `../validation/latest-control/` and `../validation/latest-omnibus/`.

The 50-pair/eight-case campaigns in reused and fresh modes are complete: `../results/omnibus-latest.json` and `../results/omnibus-latest-fresh.json`. Every final case/variant output matched its same-file control. Latest combined source `8e522e52` passed 36 unit tests and 8,028 integration tests across 18 target configurations (1,026 skips, 0 failures), including the large mapped/buffered build-ID test on all 18. Native x86 passed 551/14/0. Formatting and armv7/i686/PowerPC host source checks passed. Logs: `../validation/latest-omnibus/full-20261006T182934.log` and `../validation/latest-omnibus/hosts-20261006T183708.log`. No completed prior-stage test or measurement is relabeled as a latest-source result.

Publication heads are PR1696/P1 `e41a4bd5ecfd23d318d4ce4a0a089f2e35a60e95` and independent H1 `626776e2087adff62d442c4e5fff1a824fe39446`. P1 source `e41a4bd5` was separately built and unit-tested, with frozen isolation binary `8179754f…` used in the completed selective comparison. The H1 publication head is not a separately measured standalone binary. The broad integration results above belong to combined source `8e522e52`. Source patches are in `../patches/`: latest-upstream-bridge, latest-control, latest-omnibus and both publication-latest patches. Each patch reconstructs its exact recorded source tree.


The latest combined candidate improves C hello wall by 9.89% in reused mode and 11.67% in fresh mode. Reused Clang wall rises 1.75% (95% interval [+0.30,+3.13]); its CPU interval includes zero. Fresh Clang wall+2.70% has an interval [-1.64,+5.17]. This is a comparison of the full P1+H1 composition and does not isolate either change. The selective comparison below completed. H1 is retained only in the experimental combined branch and draft PR as a conditional tradeoff, not as a universal default improvement.

## Reused output

| Case | Control → candidate wall ms | Wall delta % [95% CI] | Control → candidate CPU ms | CPU delta % [95% CI] |
|---|---:|---:|---:|---:|
| hello | 3.860 → 3.478 | -9.89 [-12.13, -6.75] | 3.762 → 3.381 | -10.10 [-12.73, -6.96] |
| rhello | 11.670 → 11.526 | -1.23 [-2.73, +0.45] | 18.094 → 17.787 | -1.69 [-3.72, -0.30] |
| tblgen | 18.011 → 18.104 | +0.51 [-0.46, +2.92] | 117.976 → 117.462 | -0.44 [-4.39, +3.66] |
| lld | 79.027 → 80.476 | +1.83 [-2.00, +3.01] | 1786.945 → 1790.658 | +0.21 [-1.22, +1.71] |
| clang | 118.930 → 121.010 | +1.75 [+0.30, +3.13] | 2896.465 → 2883.782 | -0.44 [-1.31, +0.65] |
| clang-s | 55.020 → 54.960 | -0.11 [-1.00, +1.23] | 1142.384 → 1141.228 | -0.10 [-1.06, +0.83] |
| ra | 129.045 → 131.747 | +2.09 [-0.61, +7.10] | 2434.871 → 2433.847 | -0.04 [-1.41, +1.44] |
| ra-s | 116.559 → 116.737 | +0.15 [-1.56, +1.44] | 1883.975 → 1865.884 | -0.96 [-2.01, +1.08] |

## Fresh output

| Case | Control → candidate wall ms | Wall delta % [95% CI] | Control → candidate CPU ms | CPU delta % [95% CI] |
|---|---:|---:|---:|---:|
| hello | 3.923 → 3.465 | -11.67 [-13.90, -9.87] | 3.800 → 3.338 | -12.15 [-14.02, -10.09] |
| rhello | 12.187 → 12.190 | +0.03 [-1.31, +1.15] | 19.139 → 19.077 | -0.33 [-1.73, +0.66] |
| tblgen | 21.103 → 21.377 | +1.30 [-0.75, +2.40] | 151.232 → 151.436 | +0.13 [-2.71, +4.07] |
| lld | 103.146 → 101.752 | -1.35 [-3.70, +2.27] | 1897.445 → 1886.848 | -0.56 [-2.76, +2.06] |
| clang | 152.937 → 157.064 | +2.70 [-1.64, +5.17] | 3062.389 → 3051.211 | -0.37 [-1.67, +0.53] |
| clang-s | 63.052 → 62.886 | -0.26 [-2.32, +1.40] | 1208.354 → 1218.706 | +0.86 [-1.44, +4.34] |
| ra | 149.912 → 152.200 | +1.53 [-0.99, +3.67] | 2493.849 → 2486.491 | -0.30 [-2.08, +0.92] |
| ra-s | 126.071 → 124.608 | -1.16 [-2.97, +1.66] | 2036.104 → 2079.564 | +2.13 [-1.76, +5.27] |


<!-- selective-confirmation -->

## Selective Clang confirmation and decision

A new 80-pair, three-binary interleaved comparison captured a higher-cost Clang control with the same frozen latest binaries. P1-only wall was neutral, while P1+H1 improved both wall and total CPU. The coordinator retains H1 in the **experimental combined branch and draft PR as a conditional tradeoff**. The primary 50-pair reused-output Clang regression remains valid evidence and is not dismissed as noise by this later result. Neither a universal large-link win nor reuse alone as the cause is established.

Raw: `../results/confirm-clang-latest.json`; paired summary: `../results/summary-confirm-clang-latest.json`. All three final output hashes match.

| Candidate | Control → candidate wall ms | Wall delta % [95% CI] | Control → candidate CPU ms | CPU delta % [95% CI] |
|---|---:|---:|---:|---:|
| latest-p1 | 293.891 → 294.175 | +0.10 [-0.73, +0.64] | 7268.799 → 7628.578 | +4.95 [-9.12, +14.36] |
| latest-omnibus | 293.891 → 271.991 | -7.45 [-8.36, -6.90] | 7268.799 → 6091.375 | -16.20 [-27.66, -9.20] |

The latest instrumented profiles follow this confirmation. Their state must be described from their own observed traces; the prior 1347 profile session’s lower-contention label must not be transferred to them.

The direct H1 isolation compares combined `8e522e52` with P1-only `e41a4bd5`, both including PR1696. Wall time was 294.175 → 271.991 ms, **-7.54% [95% interval -8.10, -6.98]**; total CPU was 7.629 → 6.091 s, **-20.15% [-29.05, -9.23]**. See `../results/summary-confirm-clang-h1-isolation.json`. These differ from the combined-versus-control rows above because the reference binary differs.

The latest profiles indeed captured mixed states: Clang control foreground time averaged 291.87 ms, with 145.54 ms in Copy/relocate and 64.20 ms in Build ID/advice; the latter fell to 39.38 ms with the combined candidate. lld control averaged 74.62 ms, with 21.18 ms merging and 14.53 ms copying. These nonoverlapping instrumented elapsed intervals are attribution evidence, separate from production speedup measurements and phase-specific CPU accounting. See `../profile-report/findings-latest.md`.
