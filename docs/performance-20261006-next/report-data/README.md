# Campaign evidence exports

Run `python3 export.py` from any directory to regenerate `all-case-summary.csv`, `all-samples.csv` and `export-metadata.json` as results arrive. `provenance.json` is an explicit frozen binary SHA256 → source commit/tree map; unknown binaries stay UNKNOWN. Do not substitute current topic heads. `export-ms.py` and its focused MS export remain separate.

The unique summary key is **(campaign, result_file, case, label)**. The unique sample key adds **round**. Campaign/case/label alone is not unique because screen and confirmation files intentionally repeat labels. Environment overrides are preserved per row: the S1 phase/thread experiments use the same binary with distinct labels and settings.

Wall quantiles use median and nearest-rank p95/p99. Total CPU is user+system for each link before taking its median. Separate user and system medians need not add to the median total. RSS is each link process’s peak; both the median of those peaks and maximum observed peak are exported. Small-N tail quantiles are descriptive.

Output hashes were verified on the **last measured output per case/label** by the benchmark harness. Their presence on every sample row expresses group provenance, not a claim that every timed output was hashed. The raw result’s SHA256 is included for traceability.

Profiled runs are flagged separately. Untimed allocation counters and kernel perf-record samples do not enter link timing totals; empty/failed profile runs cannot add samples. Partially completed case/label groups remain explicitly incomplete until the expected count and final digests exist. Only label environment overrides are recorded; inherited host environment is not reconstructed.

Separate driver instrumentation observed default worker counts1/2/12 for hello/rhello/TableGen and32 for the five large cases on CPUs32–63. S1 effective caps are explicitly labeled as inferred from those observations and wrapper semantics; TableGen cap16 is a no-op control. This metadata is omitted for rebased control/candidate lineages, other CPU masks or explicit thread overrides. It does not claim whole-process concurrency is capped.

The prior1347-stage control (`d5f03691`, binary `11b05349…`) and measured combined candidate (`80f06223`, binary `4422ead1…`) were rebased onto upstream `1347ca95`. They are explicitly labeled with separate source lineage and base anchor. They must not be treated as the original frozen topic baseline (`f8638be9`, binary `529467bd…`) when choosing comparison pairs. Compare each result with its declared baseline from the same file.

`output_mode` separates `fresh` from `reused` output runs. Fresh mode unlinks only the harness-owned output before each link, outside the link stopwatch; reused mode retains that pathname. Neither mode flushes input caches. Keep result files and modes distinct when selecting comparisons.

Run `python3 audit.py` after exports and report rendering to independently recompute medians, quantiles, CPU sums, RSS units and plotted median ratios from raw samples. `numerical-audit.json` records the exact renderer snapshot checked. Run `python3 refresh-manifest.py` to refresh checkout states while preserving explicit frozen-binary source identities; decision/validation prose in that script must be updated when new evidence arrives.

The export includes diagnostic links from separate instrumented sources at both upstream stages. They are flagged `profiled=True` and `binary_instrumented=True`, with production-source parent recorded in provenance. They are excluded from production timing totals; current separate counts are in export-metadata.json. The compact source reproduction bundle and tree-verification manifest are under `../patches/`.

The latest upstream stage uses anchor75200f107ee958227e87a96e67ad491567a4854a, controlf1dec0f0/binary7bbec3c1 and omnibus8e522e52/binary0257d93d. It has distinct latest_upstream_75200 control/candidate lineages. Prior1347 results and instrumented profiles retain their original source identities; never transfer their measurements to the new builds.
