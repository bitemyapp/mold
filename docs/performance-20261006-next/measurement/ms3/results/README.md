# MS3 allocation observations

These are separate instrumented binaries, three untimed runs per variant and case, eight threads on CPUs 0–7. They are not production timing samples. Pointer changes count payload bytes preserved at a new address, not measured hardware traffic. Capacity is summed per input section at the end of splitting, not sampled simultaneous RSS; hash arrays are later freed during resolution. Allocator state and the instrumentation can affect whether reallocation moves.

| Case | Capacity changes, baseline → candidate | Live bytes moved, MiB | Sum of capacities at split completion, MiB |
|---|---:|---:|---:|
| hello | 8 → 8 | 0.00 → 0.00 | 0.00 → 0.00 |
| rhello | 304 → 268 | 0.27 → 0.01 | 0.28 → 0.63 |
| tblgen | 3,472 → 2,820 | 4.08 → 0.34 | 4.10 → 9.35 |
| lld | 65,314 → 49,918 | 152.21 → 10.09 | 152.59 → 294.13 |
| clang | 93,188 → 69,828 | 266.17 → 13.95 | 266.69 → 493.80 |
| clang-s | 19,124 → 18,534 | 2.57 → 0.86 | 2.91 → 3.86 |
| ra | 85,920 → 79,938 | 18.63 → 5.52 | 19.48 → 30.57 |
| ra-s | 25,986 → 25,986 | 0.09 → 0.09 | 0.68 → 0.68 |

All outputs were compared with the eight-corpus golden hashes. Per-run ranges, exact binaries, commands and raw counters are preserved in counts.json and counters.csv.
