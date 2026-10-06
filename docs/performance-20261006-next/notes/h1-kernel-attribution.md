# H1 kernel attribution: lld

H1's large-link win is consistent with eliminating contended parallel page-table cleanup after build-ID hashing. The dominant kernel samples are in ext4 dirty-folio locking. They are not evidence that mold's own mutexes account for the same percentage.

Evidence: `results/lld-{baseline,h1}-cycles.txt`, `lld-*-lock-callers.txt`, and `lld-*-lock-callees.txt`. Root recorded 30 sequential lld links per binary on CPUs32–63 with kernel-inclusive `cycles` sampling at 999 Hz and frame-pointer call graphs. The callee reports were generated afterward, without another recording or timing run, under the shared gate on CPUs16–23. Both reports show zero lost samples; the baseline recording/report warned of one out-of-order event.

## Kernel paths

The table gives percent of **all sampled cycle period**, not percent within the spinlock symbol. These are stack attributions to samples whose instruction was in `native_queued_spin_lock_slowpath`, not separate inclusive CPU costs to add to the spinlock row.

| Spinlock sample attribution | Baseline | H1 |
|---|---:|---:|
| All native_queued_spin_lock_slowpath self samples | 58.27% | 49.51% |
| Through block_dirty_folio → _raw_spin_lock | 57.90% | 48.92% |
| MADV_DONTNEED cleanup: zap_present_ptes | 20.35% | No branch >=0.5% displayed |
| Shared-write fault: fault_dirty_shared_page | 18.84% | 24.48% |
| Filesystem write preparation: block_page_mkwrite | 18.72% | 24.44% |

The baseline cleanup chain is `write_build_id` Rayon shard jobs → `__madvise` → `__x64_sys_madvise` → `do_madvise` → `madvise_walk_vmas` → `zap_page_range_single_batched` → `unmap_page_range` → `zap_pte_range` → `zap_present_ptes` → `folio_mark_dirty` → `ext4_dirty_folio` → `block_dirty_folio` → `_raw_spin_lock` → `native_queued_spin_lock_slowpath`. The aggregation ties the cleanup contention to the advice inside the hash workers.

The two remaining dominant H1 chains start with output copying (`__memmove_avx512_unaligned_erms` beneath section-copy jobs), then `asm_exc_page_fault` → `do_user_addr_fault` → `handle_mm_fault` → `do_shared_fault`. One enters `fault_dirty_shared_page`; the other enters `do_page_mkwrite` → `ext4_page_mkwrite` → `block_page_mkwrite`. Both converge through dirty-folio handling into the spinlock. H1 addresses the advice phase; it does not remove the cost of initially dirtying output pages. This report identifies the observed caller chain, not the exact kernel lock field or a new optimization proposal.

The graph displays branches >=0.5% of all cycle period. The absent madvise branch therefore means it is below that display threshold, not that the syscall or all cleanup costs became literally zero. Some call chains unwind incompletely. Direct sampled instruction placement can also skid; caller attribution is stronger evidence here than attributing a stalled instruction to a single source line.

## Shares versus absolute work

The separate 30-link profile recordings report approximately 504.386 billion total cycles for baseline and 409.979 billion for H1. Multiplying by displayed shares gives the following indicative cycle-period totals (rounded shares, not exact counter measurements):

| Category | Baseline, billions | H1, billions |
|---|---:|---:|
| All cycles | 504.386 | 409.979 |
| Spinlock self | 293.906 | 202.981 |
| Spinlock from advice/zapping | 102.643 | Below display threshold |
| Spinlock from the two shared-write fault paths | 189.447 | 200.562 |
| MergedSection::insert self | 19.066 | 19.064 |

For example, merged insertion rises from 3.78% to4.65% of samples while its approximate cycle period stays virtually unchanged: the denominator shrank. Likewise the remaining fault paths become a larger fraction of a cheaper run. These recordings were sequential diagnostic captures, not interleaved confidence-tested measurements; their totals support the mechanism but should not be presented as the accepted wall/CPU speedup.

The accepted performance evidence comes from the independent 50-sample interleaved confirmation (`summary-confirm-g1-h1.json`):

| Case | Wall baseline → H1 | Total CPU baseline → H1 | Wall delta, 95% CI | CPU delta, 95% CI |
|---|---:|---:|---:|---:|
| lld | 199.822 →185.554 ms | 4.498 →3.936 s | -7.14% [-8.17,-6.37] | -12.49% [-23.09,-5.38] |
| clang | 299.490 →275.078 ms | 7.383 →5.296 s | -8.15% [-9.23,-7.17] | -28.26% [-33.71,-18.39] |

For lld, median system CPU falls 3.247→2.590 s while median user CPU rises 1.247→1.308 s. For clang, system CPU falls 5.407→3.175 s and user CPU rises 2.036→2.132 s. Each is a separately computed median; user and system medians need not sum to the median of their sum. These data support a kernel-efficiency gain, not faster merge or relocation arithmetic. Filesystem, kernel, output size, and host activity can change its magnitude; this evidence is from wx-workstation's measured environment.

<!-- contention-state-qualifier -->

## Final interpretation across source stages

The completed prior `1347ca95` combined comparisons used 50 pairs across eight cases in each output mode. All large-case wall and CPU intervals included zero in that later, cheaper state; the standalone fresh-output ra-s hint was not confirmed (combined wall +0.73%, interval [-1.82, +2.51]). See [prior-stage evidence](../topics/omnibus.md). Those results do not overwrite the earlier kernel samples above.

The latest `75200f10` stage also completed 50 pairs in both modes. Reused-output Clang wall regressed **+1.75% [95% interval +0.30, +3.13]**. A separate 80-pair Clang repeat then captured renewed contention with the same frozen binaries: comparing P1+H1 directly with P1-only isolated H1 at **-7.54% wall [-8.10, -6.98] and -20.15% CPU [-29.05, -9.23]**. The positive repeat does not erase the primary regression. H1 remains an experimental, conditional tradeoff; neither a universal large-link gain nor output reuse alone as the cause is established. See [latest comparisons, mixed-state profiles and completed validation](../topics/omnibus-latest.md).

Latest combined source `8e522e52` passed 36 unit tests and 8,028 integration tests across 18 target configurations, with 1,026 skips and 0 failures. Its large mapped/buffered build-ID regression test passed on all 18. Formatting and armv7/i686/PowerPC host source checks passed. These results belong to the combined source, not a separately benchmarked standalone H1 publication executable.
