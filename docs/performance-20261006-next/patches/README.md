# Reproduce the investigated source revisions

These patches preserve every frozen production revision, the final topic heads, the original and rebased controls, final source compositions and final profiling instrumentation for the second campaign. They do not require publication of the sixteen experimental branches. The fixed plan is in `../report-data/patch-plan.json`; regenerate with `python3 ../report-data/export-patches.py` in the original repository containing those commits. Set `MOLD_PATCH_REPO` to that repository if the evidence directory is outside it.

`manifest.json` records full base/source commit IDs, tree IDs, patch SHA256 and frozen binary SHA256. **A source tree is reproducible from these patches; a byte-identical binary additionally requires the same compiler, dependencies, build flags and environment.** The recorded binary hashes identify what was actually measured and are not promises of a reproducible build on arbitrary machines.

Start in a clean clone at a declared public anchor. Keep this evidence directory outside the checkout while applying patches, since checking out an older source revision may remove the bundled report. Apply each patch with `git apply --index /absolute/path/to/patch.patch`; then `git write-tree` must equal its `source_tree_sha1`. No commit with the original source SHA needs to exist in the clone: the tree identity is the verification target.

For an original-baseline topic, start at public upstream `b2e5a7084f7391fca5c13631d20d36f64f72fe3a`, apply `original-topic-baseline.patch`, then exactly one selected topic revision patch. Do not stack independently based topic patches. A final-topic patch already includes its earlier topic changes; it is not an incremental patch over v1.

For the completed prior 1347-stage comparison, start at public upstream `1347ca95c906db060ecfbf838a792c5739970294` and apply `rebased-control.patch`. That is the measured control. Apply `omnibus-measured.patch` to obtain the measured P1+H1 candidate. `omnibus-final-tests.patch` adds only the later regression test. Alternatively, `omnibus-final-review.patch` applies both that test and the final formatting-only change directly over the measured composition; do not stack these two alternatives. That stage's frozen production binary remains tied to `omnibus-measured`.

The latest stage starts at public upstream `75200f107ee958227e87a96e67ad491567a4854a`. `latest-upstream-bridge.patch` reproduces that public tree from the prior1347 upstream anchor if needed. Apply `latest-control.patch`, then `latest-omnibus.patch` for the latest combined candidate. These sources and binaries are separate from the prior stage. `pr1696_p1-publication-latest.patch` applies to latest-control; `h1_upstream-publication-latest.patch` applies directly to latest upstream. The latest P1 source also has a separately built isolation binary; timing status comes from actual result groups, never from the moving publication ref alone.

For diagnostic profile sources, reconstruct the matching production control/candidate first, then apply `control-profile.patch` or `omnibus-profile.patch`. These add measurement instrumentation and must not replace the production speedup binaries. The separate latest stage uses latest-control-profile.patch or latest-omnibus-profile.patch after its matching latest production tree. Earlier standalone untimed allocation/locality probes retain their source patches and manifests in `../measurement/ms3/` and `../topics/*counts/`; their recorded counts are not performance timings.

Publication patches use their own declared base: H1 publication is directly on latest upstream, while the PR1696/P1 refinement is on the rebased control. Consult the frozen binary mappings and result groups for measurement status; a publication head alone does not establish timing evidence. The complete measured compositions are preserved separately.

All generated patches were verified by applying them in a private Git index and comparing the resulting tree hash with the declared source tree. This verification does not modify a checkout, branch or normal index. Later documentation-only report bundle commits do not change the frozen source plan.

| Patch | Base | Source | Role |
|---|---|---|---|
| [original-topic-baseline.patch](original-topic-baseline.patch) | `b2e5a708` | `f8638be9` | Bridge from public upstream ancestor to the frozen original topic baseline |
| [rebased-control.patch](rebased-control.patch) | `1347ca95` | `d5f03691` | Prior1347 stage: Bridge from latest public upstream to the rebased PR1696 control |
| [ms1-f8bb8d52.patch](ms1-f8bb8d52.patch) | `f8638be9` | `f8bb8d52` | Frozen production revision |
| [ms2-10fcda6c.patch](ms2-10fcda6c.patch) | `f8638be9` | `10fcda6c` | Frozen production revision |
| [ms2-3ef1d72d.patch](ms2-3ef1d72d.patch) | `f8638be9` | `3ef1d72d` | Frozen production revision |
| [ms3-8db6b722.patch](ms3-8db6b722.patch) | `f8638be9` | `8db6b722` | Frozen production revision |
| [ms4-d33ea550.patch](ms4-d33ea550.patch) | `f8638be9` | `d33ea550` | Frozen production revision |
| [cr1-62fa0761.patch](cr1-62fa0761.patch) | `f8638be9` | `62fa0761` | Frozen production revision |
| [cr1-24be8a79.patch](cr1-24be8a79.patch) | `f8638be9` | `24be8a79` | Frozen production revision |
| [cr2-b6c6c09f.patch](cr2-b6c6c09f.patch) | `f8638be9` | `b6c6c09f` | Frozen instrumentation revision |
| [cr2-7f9e54ce.patch](cr2-7f9e54ce.patch) | `f8638be9` | `7f9e54ce` | Frozen production revision |
| [cr3-f7608357.patch](cr3-f7608357.patch) | `f8638be9` | `f7608357` | Frozen production revision |
| [cr4-168ca9f5.patch](cr4-168ca9f5.patch) | `f8638be9` | `168ca9f5` | Frozen production revision |
| [cr4-final-a14c236e.patch](cr4-final-a14c236e.patch) | `f8638be9` | `a14c236e` | Final topic head; may include test-only changes beyond the frozen production revision |
| [cr5-6789e6c5.patch](cr5-6789e6c5.patch) | `f8638be9` | `6789e6c5` | Frozen production revision |
| [s1-70291748.patch](s1-70291748.patch) | `f8638be9` | `70291748` | Frozen production revision |
| [s2-412974f6.patch](s2-412974f6.patch) | `f8638be9` | `412974f6` | Frozen production revision |
| [g1-25c7f28f.patch](g1-25c7f28f.patch) | `f8638be9` | `25c7f28f` | Frozen production revision |
| [p1-871cfa70.patch](p1-871cfa70.patch) | `f8638be9` | `871cfa70` | Frozen production revision |
| [p1-e0f2d3e9.patch](p1-e0f2d3e9.patch) | `f8638be9` | `e0f2d3e9` | Frozen production revision |
| [p1-final-45934a7b.patch](p1-final-45934a7b.patch) | `f8638be9` | `45934a7b` | Final topic head; may include test-only changes beyond the frozen production revision |
| [h1-e3347c30.patch](h1-e3347c30.patch) | `f8638be9` | `e3347c30` | Frozen production revision |
| [h1-c35c2fbb.patch](h1-c35c2fbb.patch) | `f8638be9` | `c35c2fbb` | Frozen production revision |
| [h2-2790a988.patch](h2-2790a988.patch) | `f8638be9` | `2790a988` | Frozen production revision |
| [k1-6d24b45a.patch](k1-6d24b45a.patch) | `f8638be9` | `6d24b45a` | Frozen production revision |
| [omnibus-measured.patch](omnibus-measured.patch) | `d5f03691` | `80f06223` | Prior1347 stage: Measured P1+H1 composition on the rebased control |
| [omnibus-final-tests.patch](omnibus-final-tests.patch) | `80f06223` | `007ca03c` | Prior1347 stage: Test-only follow-up; production source and measured binary unchanged |
| [pr1696_p1-publication.patch](pr1696_p1-publication.patch) | `d5f03691` | `3b5caf8a` | Prior1347 stage: Publication source head, not directly measured at this new head |
| [h1_upstream-publication.patch](h1_upstream-publication.patch) | `1347ca95` | `b29d9605` | Prior1347 stage: Final H1 publication head including regression test and formatting-only follow-up; not directly measured as a new binary |
| [control-profile.patch](control-profile.patch) | `d5f03691` | `d048c042` | Measurement-only diagnostic intervals; never substitute for production timings |
| [omnibus-profile.patch](omnibus-profile.patch) | `80f06223` | `88b76de5` | Measurement-only diagnostic intervals; never substitute for production timings |
| [omnibus-final-review.patch](omnibus-final-review.patch) | `80f06223` | `839f4e4b` | Prior1347 stage: Final review head: regression test plus formatting-only follow-up over measured production source |
| [latest-upstream-bridge.patch](latest-upstream-bridge.patch) | `1347ca95` | `75200f10` | Public upstream bridge from prior1347 stage to latest752 stage |
| [latest-control.patch](latest-control.patch) | `75200f10` | `f1dec0f0` | Latest752 same-base control, separately frozen |
| [latest-omnibus.patch](latest-omnibus.patch) | `f1dec0f0` | `8e522e52` | Latest752 P1+H1 composition with tests and formatting, separately frozen |
| [pr1696_p1-publication-latest.patch](pr1696_p1-publication-latest.patch) | `f1dec0f0` | `e41a4bd5` | Latest752 P1 publication source and separately frozen P1-only isolation candidate |
| [h1_upstream-publication-latest.patch](h1_upstream-publication-latest.patch) | `75200f10` | `626776e2` | Latest752 independent H1 publication source, no standalone timing at this head |
| [latest-control-profile.patch](latest-control-profile.patch) | `f1dec0f0` | `9acc8702` | Latest752 diagnostic instrumentation only; not production speedup source |
| [latest-omnibus-profile.patch](latest-omnibus-profile.patch) | `8e522e52` | `5edabcfa` | Latest752 diagnostic instrumentation only; not production speedup source |
