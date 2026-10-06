#!/usr/bin/env python3
"""Refresh checkout state without substituting it for frozen-binary provenance."""
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parent.parent
WORKTREES = Path('/Users/callen/.codex/worktrees')
BASE = 'f8638be95ae14954ec3b1029e6008128d7a27f1b'
UPSTREAM = '1347ca95c906db060ecfbf838a792c5739970294'
LATEST_UPSTREAM = '75200f107ee958227e87a96e67ad491567a4854a'
PROVENANCE = json.loads((ROOT / 'report-data/provenance.json').read_text())

# Decisions are explicit coordinator decisions, not classifications inferred from CIs.
# Keep validation scoped to the revision/suite actually reported in the linked notes.
SPECS = {
 'ms1': ('compact-probes', ['f8bb8d52'], 'rejected', ['topics/ms1.md'], 'Release; unit 35+2; full native 550/14/0; eight goldens.'),
 'ms2': ('single-pass-layout', ['10fcda6c', '3ef1d72d'], 'rejected', ['topics/ms2.md'], 'v1: release, unit34+2, full native550/14/0. v2: release, unit35+2, full native551/14/0. Both eight goldens.'),
 'ms3': ('fragment-reservations', ['8db6b722'], 'rejected', ['topics/ms3.md'], 'Release; unit33+2; full native551/14/0; eight goldens; separate48 untimed counter links all matched.'),
 'ms4': ('dense-fragments', ['d33ea550'], 'rejected', ['topics/ms4.md'], 'Release; unit36+2; full native550/14/0; eight goldens; independent source review.'),
 'cr1': ('compact-offsets', ['62fa0761', '24be8a79'], 'rejected', ['notes/cr1.md'], 'Both versions release/unit/full native550/14/0 and eight goldens; v2 unit34+2.'),
 'cr2': ('fragment-hints', ['b6c6c09f', '7f9e54ce'], 'rejected', ['notes/cr2.md'], 'Instrumented version full native550/14/0; clean rebuild and unit33+2 passed; clean eight goldens; separate untimed hint counts.'),
 'cr3': ('reloc-prefetch', ['f7608357'], 'rejected', ['notes/cr3.md'], 'Release; unit33+2; full native551/14/0; eight goldens.'),
 'cr4': ('input-offsets', ['168ca9f5'], 'rejected', ['notes/cr4.md'], 'Release; unit33+2; full native551/14/0; eight goldens. Current a14c236e corrects only a test; measured binary remains code commit168ca9f5.'),
 'cr5': ('cross-section-batches', ['6789e6c5'], 'rejected', ['topics/cr5.md'], 'Release; targeted native13/0/0; eight goldens and separate eligibility counts; no full-suite claim.'),
 's1': ('phase-concurrency', ['70291748'], 'tradeoff_not_general_default', ['topics/s1.md', 'topics/s1-env.json'], 'Release; targeted native15/0/0; same binary across phase caps. Twenty-pair four-case sweep plus32-pair eight-case copy-cap confirmation; goldens matched.'),
 's2': ('cache-locality', ['412974f6'], 'rejected', ['topics/s2.md'], 'Release; targeted native9/0/0; eight goldens and separate untimed handoff/assignment counts.'),
 'g1': ('compact-gc-targets', ['25c7f28f'], 'rejected_after_confirmation', ['topics/g1.md', 'topics/g1-measurements.md'], 'Release; targeted native23; full native550/14/0; eight screen goldens; four-case50-pair confirmation.'),
 'p1': ('symbol-blocks', ['871cfa70', 'e0f2d3e9'], 'included_in_combined_final_timings_complete', ['topics/p1.md', 'notes/production-review-h1-p1.md'], 'v1 release/unit/full native550/14/0. v2 release/unit/targeted native14 passed. Current45934a7b adds semantic test only; unit helper passed. Both eight goldens.'),
 'h1': ('batched-advice', ['e3347c30', 'c35c2fbb'], 'retained_experimental_conditional_tradeoff', ['topics/h1.md', 'notes/h1-kernel-attribution.md', 'notes/production-review-h1-p1.md'], 'v1 release/unit/full native550/14/0; cleaned release and targeted build-ID test passed; eight goldens; separate kernel profiles.'),
 'h2': ('pipelined-hash', ['2790a988'], 'rejected', ['topics/h2.md'], 'Release/unit/full native550/14/0; eleven-mode12MiB oracle fixture matched; eight corpus goldens.'),
 'k1': ('prefault-output', ['6d24b45a'], 'rejected_as_default_both_output_modes', ['topics/k1.md', 'topics/k1-review.md'], 'Release; local logs confirm unit33+2 and full native550/14/0 (validation/k1/). Eight reused-output and eight fresh-output goldens.'),
}


def git(path, *args):
    return subprocess.check_output(['git', '-C', str(path), *args], text=True).strip()


def checkout(name):
    path = WORKTREES / name / 'mold'
    branch = git(path, 'branch', '--show-current')
    return dict(worktree=str(path), branch=branch or None,
                commit=git(path, 'rev-parse', 'HEAD'),
                dirty=bool(git(path, 'status', '--porcelain')))


def frozen(prefixes):
    values = []
    for prefix in prefixes:
        matches = [(sha, p) for sha, p in PROVENANCE.items() if p['source_commit'].startswith(prefix)]
        assert len(matches) == 1, (prefix, matches)
        sha, p = matches[0]
        row = dict(binary_sha256=sha, **p)
        row['measurement_groups'] = []
        for path in sorted((ROOT / 'results').glob('*.json')):
            try:
                data = json.loads(path.read_text())
            except json.JSONDecodeError:
                continue
            if not isinstance(data, dict) or not isinstance(data.get('cases'), dict):
                continue
            for case, labels in data['cases'].items():
                for label, measured in labels.items():
                    if measured.get('binary_sha256') == sha:
                        row['measurement_groups'].append(dict(result_file=path.name, case=case,
                            label=label, sample_count=len(measured.get('samples', [])),
                            output_mode='fresh' if data.get('args', {}).get('fresh_output') else 'reused'))
        values.append(row)
    return values


manifest = dict(schema_version=2, refreshed_utc=datetime.now(timezone.utc).isoformat(),
    baseline=BASE,
    scope='Second campaign: 15 requested ideas plus K1 profile-driven follow-up. Historical first-campaign M/C topics remain in radical-20261006.',
    authority='Raw result files and validation logs are primary. This is a coordinator-approved evidence index; pending outcomes are not inferred.',
    baseline_lineage={
        'original_topic_baseline': dict(commit=BASE, frozen_binaries=frozen([BASE])),
        'prior_1347_upstream_main': dict(commit=UPSTREAM),
        'updated_upstream_main': dict(commit=LATEST_UPSTREAM, fork_main_fast_forward='pushed, reported by coordinator'),
        'rebased_control': dict(**checkout('mold-next-baseline'), frozen_binaries=frozen(['d5f03691']),
            upstream_anchor=UPSTREAM, purpose='Prior 1347-stage control retaining the earlier PR1696 thread/GOT work, excluding the new P1/H1 additions; compare only with its same-file candidate.'),
        'latest_rebased_control': dict(**checkout('mold-next-latest-control'), frozen_binaries=frozen(['f1dec0f0']),
            upstream_anchor=LATEST_UPSTREAM, purpose='Latest 75200f10 control retaining the earlier PR1696 thread/GOT work, excluding the new P1/H1 additions; separate from both older baselines.')},
    protocol=dict(host='wx-workstation', remote_root='/home/callen/work/mold-next-20261006',
        gate='/home/callen/work/mold-radical-20261006/workstation.lock',
        validation='shared gate; bounded CPU/memory; unrelated GPU workload left alone',
        timing='coordinator-exclusive gate; compare same result file/output mode/environment'),
    topics={})

for topic, (suffix, prefixes, decision, evidence, validation) in SPECS.items():
    manifest['topics'][topic] = dict(**checkout(f'mold-{topic}-{suffix}'),
        base_commit=BASE, independent=True, decision=decision, notes=evidence,
        validation=validation, frozen_revisions=frozen(prefixes))

manifest['prior_1347_omnibus'] = dict(
    branch='codex/mold-next-omnibus-1347', commit='839f4e4bea0c9b6f1a2df6814859fd3714137d52',
    source_composition=['rebased control d5f03691', 'P1 file-major demand-sized symbol blocks', 'H1 batched output advice'],
    upstream_anchor=UPSTREAM, frozen_revisions=frozen(['80f06223']),
    decision='Prior 1347 stage complete: 50 pairs/eight cases in both modes, full validation passed; do not attribute to latest rebased binaries',
    timing_results=['results/omnibus.json', 'results/omnibus-fresh.json'],
    timing_summary='results/summary-omnibus.json',
    result_note='topics/omnibus.md',
    validation='Full --init rerun:18 targets,8028 pass/1026 skip/0 fail; new build-id-large-mmap test18 passes; native551/14/0; unit34+2. First attempt stopped at container PID limit due unreaped children, preserved as infrastructure failure. Review839f4e4b adds only the regression test and formatting over frozen80f0622. Formatting and armv7/i686/powerpc 32-bit host source checks passed; missing i686/ppc Rust std components were installed only in a disposable test container for the successful retry.')
manifest['omnibus'] = dict(**checkout('mold-next-omnibus'),
    source_composition=['latest rebased control f1dec0f0', 'P1 symbol allocation', 'H1 batched advice', 'regression tests and formatting'],
    upstream_anchor=LATEST_UPSTREAM, frozen_revisions=frozen(['8e522e52']),
    decision='Retained experimental P1+H1 composition as conditional tradeoff. Primary50 reused Clang wall+1.75% CI[+0.30,+3.13] remains. Separate80-pair Clang confirmation in renewed contention: P1-only wallneutral; combined wall-7.45% CI[-8.36,-6.90], CPU-16.20% CI[-27.66,-9.20]. No universal large-link speedup claim.',
    timing_results=['results/omnibus-latest.json','results/omnibus-latest-fresh.json','results/confirm-clang-latest.json'],
    result_note='topics/omnibus-latest.md',
    timing_summary='results/summary-omnibus-latest.json',
    h1_isolation=dict(summary='results/summary-confirm-clang-h1-isolation.json', reference='e41a4bd5', candidate='8e522e52', pairs=80, wall_pct=-7.5411778, wall_ci95=[-8.101452,-6.980189], cpu_pct=-20.150589, cpu_ci95=[-29.054745,-9.234921], scope='Same latest binaries in a separately observed higher-cost Clang state; does not erase primary50 regression.'),
    validation='Latest combined 8e522e52: release, unit34+2, full18-target architecture suite8028 pass/1026 skip/0 fail; large build-id test18 passes; native551/14/0; fmt and armv7/i686/PowerPC foreign-host source checks passed. Logs validation/latest-omnibus/full-20261006T182934.log and hosts-20261006T183708.log. Prior1347 validation is separate.')
manifest['publication_worktrees'] = {
    'pr1696_p1': dict(**checkout('mold-pr1696-refined'),
        lineage='latest 75200f10 rebased control f1dec0f0 plus P1', frozen_revisions=frozen(['e41a4bd5']),
        purpose='Existing PR1696 refinement; latest P1-only separately built and unit-tested. Its frozen binary completed the80-pair Clang comparison. Broad integration counts belong to combined8e522e52. PR edit/comment publication is handled separately by coordinator.'),
    'h1_upstream': dict(**checkout('mold-h1-upstream'),
        lineage='latest upstream75200f10 plus H1 only', measured_binary_at_this_head=None,
        purpose='Separate experimental H1 draft planned by coordinator. Includes large-output regression test and formatting. The test passed on18 targets in both prior and latest combined full suites. This standalone publication head was not separately benchmarked; H1 isolation is combined8e522e52 versus P1-onlye41a4bd5, both including PR1696.')}
manifest['prior_publication_refs'] = {
    'h1': dict(branch='codex/mold-h1-upstream-1347',commit='b29d960523eff28b41d30c4feb0969ac93ea061b'),
    'pr1696_p1': dict(branch='codex/mold-pr1696-refined-1347',commit='3b5caf8a2db31dd4278268eaa9218e96f391d21e')}
manifest['profile_worktrees'] = {
    'control': dict(**checkout('mold-current-profile'), frozen_revisions=frozen(['d048c042'])),
    'omnibus': dict(**checkout('mold-omnibus-profile'), frozen_revisions=frozen(['88b76de5']))}
manifest['latest_profile_worktrees'] = {
    'control': dict(**checkout('mold-latest-control-profile'), frozen_revisions=frozen(['9acc8702'])),
    'omnibus': dict(**checkout('mold-latest-omnibus-profile'), frozen_revisions=frozen(['5edabcfa']))}
manifest['attribution_artifacts'] = {
    'ms3': dict(manifest='measurement/ms3/manifest.json',
        details=json.loads((ROOT/'measurement/ms3/manifest.json').read_text())),
    'cr2': dict(source='notes/cr2.md', frozen_binary=frozen(['b6c6c09f'])[0]),
}
for path in sorted((ROOT/'topics').glob('*counts/counts.json')):
    data = json.loads(path.read_text())
    manifest['attribution_artifacts'][path.parent.name] = dict(
        file=str(path.relative_to(ROOT)), **{k:v for k,v in data.items() if k!='cases'})
manifest['limitations'] = [
    'Validation is native x86_64 unless separately stated; no sanitizer, Windows runtime or cross-target runtime claim.',
    'Current checkout commit may include test-only changes; only frozen_revisions.source_commit identifies each measured production binary.',
    'Output hashes apply to last measured link per case/label, not every individual timed sample.',
    'Fresh output means harness output unlink outside timing; input caches are not flushed.',
    'Untimed attribution counters and sequential kernel profiles are not interleaved timing evidence.',
    'H1 gains depended on the observed contention state; later reused-output controls also became much cheaper. Output-mode labels alone do not establish the cause or guarantee the earlier speedup.',
    'Original-baseline topic measurements do not directly measure newly rebased publication heads.'
]
(ROOT/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
print(f"Refreshed {len(manifest['topics'])} topics and separate control/omnibus/publication lineage")
