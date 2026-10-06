#!/usr/bin/env python3
"""Export measured links without combining campaigns, variants or profiler modes."""
import csv
import hashlib
import json
import math
from pathlib import Path
import statistics as st

ROOT = Path(__file__).resolve().parent.parent
DEST = ROOT / 'report-data'
PROVENANCE = json.loads((DEST / 'provenance.json').read_text())
summary_rows, sample_rows, warnings = [], [], []
worker_evidence = ROOT / 'topics/s2-assignment-counts/counts.json'
worker_cases = json.loads(worker_evidence.read_text()).get('cases', {}) if worker_evidence.exists() else {}



def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'))


def q(values, fraction):
    values = sorted(values)
    return values[max(0, math.ceil(fraction * len(values)) - 1)]


for path in sorted((ROOT / 'results').glob('*.json')):
    try:
        raw = path.read_bytes()
        data = json.loads(raw)
    except json.JSONDecodeError:
        warnings.append(f'{path.name}: partial or invalid JSON skipped; rerun after completion')
        continue
    if not isinstance(data, dict) or not isinstance(data.get('cases'), dict):
        continue
    args = data.get('args', {})
    raw_sha = hashlib.sha256(raw).hexdigest()
    for case, variants in data['cases'].items():
        for label, row in variants.items():
            samples = row.get('samples', [])
            if not samples:
                continue
            binary_sha = row.get('binary_sha256', '')
            provenance = PROVENANCE.get(binary_sha, {})
            env_known = 'env' in row or not args.get('label_env')
            env = row.get('env', {}) if env_known else 'UNKNOWN'
            command = row.get('command', [])
            thread_options = [v.split('=', 1)[1] for v in command if v.startswith('--threads=')]
            observed_workers = worker_cases.get(case, {}).get('workers', [])
            measured_default = (observed_workers[0] if len(observed_workers) == 1
                                and args.get('cpus') == '32-63' and not thread_options
                                and provenance.get('lineage') == 'original_topic_baseline' else '')
            phase, requested_cap, effective_cap, cap_active = '', '', '', ''
            phase_value = env.get('MOLD_PHASE_BUDGET') if isinstance(env, dict) else None
            if phase_value and ':' in phase_value:
                phase, requested_cap = phase_value.split(':', 1)
                if measured_default and requested_cap.isdigit():
                    effective_cap = min(measured_default, int(requested_cap))
                    cap_active = int(requested_cap) < measured_default
            profiled = bool(args.get('perf') or row.get('profiles'))
            complete = (len(samples) == args.get('runs', len(samples))
                        and bool(binary_sha) and bool(row.get('sha256')))
            common = dict(campaign=ROOT.name, result_file=path.name,
                case=case, label=label, environment_overrides_json=encoded(env),
                environment_recorded=env_known, threads=thread_options[-1] if thread_options else 'default',
                cpus=args.get('cpus', ''), profiled=profiled,
                output_mode='fresh' if args.get('fresh_output') else 'reused',
                measured_default_workers=measured_default, phase_budget=phase,
                requested_phase_cap=requested_cap, inferred_effective_phase_workers=effective_cap,
                inferred_phase_cap_active=cap_active,
                worker_evidence='topics/s2-assignment-counts/counts.json' if measured_default else '',
                binary_instrumented=provenance.get('instrumented', 'UNKNOWN'),
                complete_case_variant=complete, binary_sha256=binary_sha,
                source_commit=provenance.get('source_commit', 'UNKNOWN'),
                source_lineage=provenance.get('lineage', 'UNKNOWN'),
                source_base_anchor=provenance.get('base_anchor', 'UNKNOWN'),
                source_tree_sha1=provenance.get('source_tree_sha1', 'UNKNOWN'),
                provenance_evidence=provenance.get('evidence', 'UNKNOWN'),
                output_sha256=row.get('sha256', ''),
                output_hash_scope='last measured link for case/label',
                raw_result_sha256=raw_sha, command_json=encoded(command), cwd=row.get('cwd', ''))
            wall = [s['wall'] * 1000 for s in samples]
            user = [s['user'] * 1000 for s in samples]
            system = [s['sys'] * 1000 for s in samples]
            cpu = [(s['user'] + s['sys']) * 1000 for s in samples]
            rss = [s['rss_kib'] / 1024 for s in samples]
            summary_rows.append(common | dict(sample_count=len(samples), wall_p50_ms=st.median(wall),
                wall_p95_ms=q(wall, .95), wall_p99_ms=q(wall, .99), wall_max_ms=max(wall),
                user_cpu_median_ms=st.median(user), sys_cpu_median_ms=st.median(system),
                total_cpu_median_ms=st.median(cpu), peak_rss_median_mib=st.median(rss),
                peak_rss_max_mib=max(rss)))
            for i, sample in enumerate(samples):
                sample_rows.append(common | dict(sample_index=i, round=sample.get('round', ''),
                    position=sample.get('position', ''), wall_ms=sample['wall'] * 1000,
                    user_cpu_ms=sample['user'] * 1000, sys_cpu_ms=sample['sys'] * 1000,
                    total_cpu_ms=(sample['user'] + sample['sys']) * 1000,
                    peak_rss_kib=sample['rss_kib'], peak_rss_mib=sample['rss_kib'] / 1024,
                    voluntary_context_switches=sample.get('voluntary_cs', ''),
                    involuntary_context_switches=sample.get('involuntary_cs', ''),
                    minor_faults=sample.get('minor_faults', ''), major_faults=sample.get('major_faults', '')))

for filename, rows in [('all-case-summary.csv', summary_rows), ('all-samples.csv', sample_rows)]:
    if rows:
        with (DEST / filename).open('w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)

metadata = dict(campaign=ROOT.name, summary_rows=len(summary_rows), sample_rows=len(sample_rows),
    completed_unprofiled_samples=sum(r['sample_count'] for r in summary_rows if r['complete_case_variant'] and not r['profiled']),
    completed_profiled_samples=sum(r['sample_count'] for r in summary_rows if r['complete_case_variant'] and r['profiled']),
    unknown_binary_provenance=sorted({r['binary_sha256'] for r in summary_rows if r['source_commit']=='UNKNOWN'}),
    warnings=warnings,
    definitions={'summary_identity':'(campaign, result_file, case, label); result_file distinguishes screens and confirmations',
      'sample_identity':'(campaign, result_file, case, label, round); sample_index is also preserved',
      'wall_p50':'sample median; even N averages the two middle observations',
      'p95_p99':'nearest rank; sparse upper tails are descriptive, not stable production guarantees',
      'total_cpu':'user+system per sample before median',
      'rss':'per-link process peak RSS, not an average resident working set; MiB=KiB/1024',
      'environment':'label-specific overrides only; inherited host environment is not captured',
      'phase_workers':'for original-baseline descendants with default threads on CPUs32-63, observed per-case worker count comes from separate instrumentation; effective phase cap is inferred from S1 wrapper semantics, not counted during timings. TableGen default12 means cap16 is inactive',
      'output_mode':'fresh means only the harness output was unlinked before each link outside link timing; reused means the harness output pathname was retained. Neither mode flushes input caches',
      'output_hash':'harness verifies last measured output per case/label; copied to sample rows as group provenance',
      'profiled':'timed --perf phase runs kept separate by flag; untimed counters and perf-record kernel samples are not link timing rows',
      'source':'explicit frozen binary hash mapping; never inferred from current branch heads. Original f8638be9 topic baseline, prior1347ca95 rebased stage, and latest75200f10 stage have distinct source lineage and anchors',
      'complete':'requested sample count and final binary/output digests are all present'})
(DEST / 'export-metadata.json').write_text(json.dumps(metadata, indent=2)+'\n')
print(json.dumps(metadata, indent=2))
