# Final phase attribution

Two separate profile stages are retained. The first uses control `d5f03691582bc6e425d122c5592d0b33448ff7eb` and omnibus `80f062238e88d941a6b16e175477dff42e2ace4c` (P1 + H1), with provenance in `manifest.json`. The latest-upstream stage uses control `f1dec0f067198959a1339e761f27f27ccc4179d1` and omnibus `8e522e5217adea17329e8e2eeb753fc482de4b16` on upstream `75200f107ee958227e87a96e67ad491567a4854a`, with provenance in `manifest-latest.json`. Each manifest records production source, instrumentation commit, and frozen profile-binary SHA-256. The latest stage includes the upstream package rename and registry allocator dependency; the first stage is retained as historical evidence. Production benchmark binaries are unchanged by instrumentation.

Collection runs on `wx-workstation`, affinity CPUs 32–63, with the existing adaptive worker policy. The first phase stage ran during a lower-contention session. The latest stage follows a selective Clang repeat whose elapsed time and system CPU had returned to a higher-cost state; its actual window and user/system totals must be inspected per case rather than inheriting the earlier low-state label. Compare each session internally: the earlier kernel call stacks establish the observed mechanism in that sampled session, while each phase trace describes its own observed elapsed-time distribution. The traces do not prove that a particular kernel contention mechanism remained dominant throughout either stage.

The coordinator alone invokes the following under the exclusive workstation gate, after shared build/test jobs drain:

```sh
bash /home/callen/work/mold-next-20261006/queue-run.sh final-phases \
  bash /home/callen/work/mold-next-20261006/profile-report/collect-phases.sh
```

For the latest stage use queue name `final-phases-latest` and `profile-report/collect-phases-latest.sh`. The collectors make 12 paired runs per case: the first writes `results/final-phases.json` and `profile-report/phase-summary.json`; the latest writes `results/final-phases-latest.json` and `profile-report/phase-summary-latest.json`. Run `audit.py` for the first stage and `audit.py --latest` for the latest. The raw file retains the run order, process resource measurements, output hashes, and all precise timer records. The derived file retains every decoded sample and its provenance as well as summaries. The harness hashes the final output per case/label group (16 outputs), and those hashes must agree with the eight corpus oracles; it does not hash every repetition.

`build.sh current` and `build.sh omnibus` build the measurement copies under a shared global gate and a per-target exclusive lock, on CPUs 8–15 with eight jobs. Each refuses to replace an existing profile binary. The build uses a separate target directory, frame pointers, and line-table debug information. The first stage uses offline dependencies. `build-latest.sh latest-control` and `build-latest.sh latest-omnibus` use the renamed `libmold`/`mold` packages and allow registry downloads for the new allocator dependency; Docker `--init` reaps subprocesses. Both stages retain the same CPU and memory limits. Neither command belongs in a performance measurement window.

## What the chart measures

`profile_window` starts immediately before the existing `all` timer and stops after `drop_mappings()` releases input mappings. Argument/target setup before `all`, trace rendering, and final process exit are outside the window. The difference from externally observed elapsed time is retained as a diagnostic residual; it includes instrumentation/reporting costs and is not a production phase.

The foreground chart is a partition of that window. For every interval between timer boundaries, the smallest enclosing selected timer receives that elapsed interval; everything else goes to Other. Thus nested merge timers are not added twice and build-ID/advice time is subtracted from Copy / relocate. Separate Open output and Release input mappings categories expose mapping preparation and post-link cleanup. The original `all` timer is retained for comparison.

Merge strings includes preparation, splitting, table sizing, and insertion. Later merged layout and uninstrumented member gathering stay in Other. Copy / relocate includes the copy wrapper except Build ID / advice; it can include finalization and GDB wait/write. H1 output-page advice already occurs inside the existing build-ID timer. Input-mapping release is separate and is not the main H1 operation.

Background GDB input/table work is shown as an overlay, never stacked with foreground time. Explicit parent relationships, rather than inferred temporal containment, distinguish this asynchronous work. The overlay reports its interval union and its overlap with explicitly named foreground phases, excluding Other.

Other is also subdivided from existing intervals into Input / symbol resolution, Output assembly / layout, Relocation scan, and Checks / setup / remaining. This secondary partition applies only inside Other and subtracts all primary categories, so it is not additional elapsed time. Exact timer mappings are saved in the JSON.

Mean milliseconds and mean per-sample shares add. Individual phase medians do not necessarily add to the median window. The summary provides median, p10, and p90 for inspection, but the stacked chart must use means.

## CPU and precision limits

Each native timer already snapshots process-wide `getrusage`. Its user/system delta includes all threads active during that interval and can overlap other timers. These fields are retained for diagnosis, not presented as exclusive additive CPU time by phase. Whole-window process user/system totals are meaningful; kernel-inclusive sampled self cycles are a separate measurement with a different denominator.

Wall boundaries are serialized at nanosecond precision from `Instant`; the clock's effective precision is platform dependent. CPU snapshots have microsecond resolution. Instrumentation preserves native timer start/stop paths and existing snapshots, adding only two coarse timers (four extra resource snapshots per link) and rendering after the window. These traces explain attribution; all speedup claims must use the immutable production binaries and paired production benchmark results.
