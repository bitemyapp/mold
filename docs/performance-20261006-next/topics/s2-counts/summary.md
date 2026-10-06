
Baseline handoff instrumentation, one untimed link per case, all eight golden hashes matched. Values below are percentages of fragments, not percentages of runtime:

| Case | Fragments | Same worker | Same L3 | Cross L3 | Endpoint migrations |
|---|---:|---:|---:|---:|---:|
| hello | 7 | 100.0% | 100.0% | 0.0% | 0 |
| rhello | 18,811 | 100.0% | 100.0% | 0.0% | 0 |
| tblgen | 238,606 | 13.5% | 20.9% | 79.1% | 1 |
| lld | 9,374,968 | 4.7% | 26.4% | 73.6% | 1 |
| clang | 16,333,687 | 1.5% | 25.9% | 74.1% | 3 |
| clang-s | 182,232 | 0.9% | 28.9% | 71.1% | 0 |
| ra | 1,171,402 | 5.5% | 22.3% | 77.7% | 0 |
| ra-s | 32,571 | 2.5% | 24.0% | 76.0% | 0 |

This confirms frequent split-to-resolve handoff between workers/cache domains on large cases. Endpoint observations cannot see migrations that return to the starting CPU, and the counters do not prove a particular cache-miss penalty. The static worker prototype is source commit412974f6cb927e2a35c2827b28ac371f4d5c9b5b. Counter script and full source patch, logs, binary identity, commands, and output hashes are retained under topics/s2-counts. The instrumented binary is bin/s2-counts, separate from the production candidate.
