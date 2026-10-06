# Independent production review: H1 and P1

Reviewed H1 `e3347c30bc6d4827a62357599fb9ac5ae528d08f` and the complete P1 diff from baseline to `e0f2d3e942fc9985b202f8d2f9327d79acd90e78`. No blocking correctness or maintainability finding. Root's proposed removal of H1's unused enumerate is equivalent because indexed parallel chunk collection preserves hash order without it.

## H1: one mapping-advice call after hashing

The ordered 4 MiB hashes and final hash-of-hashes are unchanged. The parallel collection joins before advice, so no hashing worker is still accessing the advised range. `[SHARD, len)` is exactly the union of the ranges previously advised by workers for shards with index >0, including the partial final shard. The new pointer is derived directly from the output slice, and the len > SHARD guard keeps pointer arithmetic inside the allocation. Callers obtain both the slice and is_mmapped flag from the same OutputFile; map_mut is shared file-backed storage, not anonymous/private heap memory. The slice includes only actual file bytes, even when the mapping reserves a larger range.

Empty and <=4 MiB outputs skip advice just as before. In-memory output also skips it. Windows still compiles out the call; other Unix targets retain the existing advice type and the same page-aligned start and end coverage. Host kernels rejecting/ignoring the hint remain nonfatal as before. Data are still in the shared file/page cache; a later write outside the retained first shard may refault but remains valid. The comment about retaining the first shard for build-ID is the common layout rationale, not a correctness assumption about every script's build-ID position.

This change reduces parallel syscalls and delays page-table cleanup until after hashing. It may retain mapped pages longer and serializes cleanup, so performance/RSS effects are workload/filesystem dependent. The measured Linux/ext4 result does not establish a benefit on every Unix filesystem. There is no additional state or lifetime machinery, and the unsafe operation has a small, clear provenance argument.

## P1: reserve demand-sized symbol blocks

Let n be input records for a shard and b=min(n,256). At most k<=n records can create new symbols. For n>0, its claimed space is ceil(k/b)*b <= k+b-1 <= n+b-1. Summing n + saturating_sub(b,1) therefore safely bounds all claimed blocks. n=0 takes the explicit empty path and claims nothing; existing-only shards also claim no block. additional_capacity remains spare capacity beyond the upper bound.

Atomic fetch_add continues to give disjoint intervals. Each occupied slot is initialized before assignment, unused tails are initialized before set_len, and the parallel map joins before setting vector length. No pointer is retained across reserve. The array counts exactly the private fixed 64-shard Bins shape in input order. Skipping empty shards preserves existing shard entries and global ranges; it merely avoids empty sketch/reserve work. Repeated gathers retain existing IDs, and new global ranges are appended as before. Numeric IDs for newly interned names may shift relative to baseline, but per-shard key order, equality, and symbol resolution are unchanged; they were already allocated concurrently.

A focused semantic unit test was added at root's request in test-only commit `45934a7b546408ecebbdfa5a4ad8c5a6f96ebd3f` on the P1 worktree. It uses real hashes, sparse/empty shards, record counts 1/255/256/257, duplicate-heavy and existing-only shards, and a repeated gather with an intervening local symbol. It asserts lookup/name identity, duplicate agreement, distinct-name nonaliasing, retained local data, and exact named-global membership. It does not assert the private block size or allocation layout. The remote p1 unit helper passed; no production binary was replaced by this test-only change.

Both source changes are architecture-independent except H1's existing OS gate. Native/golden campaign results are necessary evidence, while broad target and combined-branch validation remain root's final integration checks. No additional experimental scope is proposed.
