# Rebase validation, 6 October 2026

Both Rayon experiment branches were rebased onto upstream `main` at `b2e5a7084f7391fca5c13631d20d36f64f72fe3a`.

| Check on wx-workstation | Polling | Async startup |
| --- | --- | --- |
| x86_64 release build | pass | pass |
| mold library tests | 32 passed | 32 passed |
| harness library tests | 2 passed | 2 passed |
| native integration tests | 550 passed, 14 skipped, 0 failed | 550 passed, 14 skipped, 0 failed |
| upstream Rayon + added tests | pass | pass |
| workspace and Rayon formatting | pass | pass |
| output comparison against upstream | all 24 combinations byte-identical | all 24 combinations byte-identical |

The output check links C hello, Rust hello, LLVM TableGen, lld, Clang, stripped Clang, rust-analyzer and stripped rust-analyzer, each at 1, 8 and 32 workers. The 72 links compare upstream and both candidates. [Output hashes and binary hashes](output-comparison.json), [validation commands](run-work.sh), [comparison script](output-compare.py), and [logs](logs) are included.

The Rayon source and tests are byte-for-byte unchanged by the rebase. Upstream's dependency versions, lockfile, single-codegen-unit release setting and fatal startup-error diagnostic were retained. The only mold driver change relative to this base is the idle-timeout call in one branch and the async-build call in the other. [Polling range-diff](idle-range-diff.txt) and [startup range-diff](startup-range-diff.txt) record the replayed commits.

The [manifest](manifest.json) identifies the tested commits. Any subsequent source-branch commit changes only the experiment notes. Builds and tests used the existing mold-upstream-ci container, 16 build CPUs, fresh cleaned mold/Rayon packages and the same compiler settings for all three release binaries. Validation held the workstation lock in shared mode; no performance timings were collected during this rebase. The original performance results remain measurements of the pre-rebase code, not current main.
