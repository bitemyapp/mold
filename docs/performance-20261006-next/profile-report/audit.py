#!/usr/bin/env python3
"""Validate final trace completeness, provenance, and interval accounting."""
import json
import math
import argparse
from pathlib import Path

root = Path(__file__).resolve().parent.parent
p = argparse.ArgumentParser()
p.add_argument('--latest', action='store_true', help='Audit the later upstream catchup profiles')
a = p.parse_args()
suffix = '-latest' if a.latest else ''
raw = json.loads((root / f'results/final-phases{suffix}.json').read_text())
summary = json.loads((root / f'profile-report/phase-summary{suffix}.json').read_text())
manifest = json.loads((root / f'profile-report/manifest{suffix}.json').read_text())
labels = ('latest-control', 'latest-omnibus') if a.latest else ('current', 'omnibus')
golden = json.loads((root.parent / 'radical-20261006/golden-hashes.json').read_text())['sha256']
workers = {'hello':1, 'rhello':2, 'tblgen':12, 'lld':32,
           'clang':32, 'clang-s':32, 'ra':32, 'ra-s':32}
assert set(raw['cases']) == set(summary['cases']) == set(workers)
assert raw['args']['runs'] == 12
assert raw['args']['perf']
assert raw['args']['cpus'] == manifest['cpu_affinity'] == '32-63'
assert summary['provenance'] == manifest
count = 0
for case in workers:
    assert set(raw['cases'][case]) == set(summary['cases'][case]) == set(labels)
    for label in labels:
        row = raw['cases'][case][label]
        item = summary['cases'][case][label]
        assert len(row['samples']) == len(row['profiles']) == item['n'] == 12
        assert row['binary_sha256'] == item['profile_binary_sha256'] == manifest['labels'][label]['profile_binary_sha256']
        assert row['sha256'] == item['output_sha256'] == golden[case]
        assert {s['round'] for s in row['samples']} == set(range(12))
        assert item['workers'] == workers[case]
        assert all(s['trace_format'] == 2 and s['workers'] == workers[case] for s in item['samples'])
        assert math.isclose(sum(v['mean_ms'] for v in item['phases'].values()), item['window_ms']['mean'], abs_tol=1e-7)
        assert math.isclose(sum(v['mean_pct'] for v in item['phases'].values()), 100, abs_tol=1e-7)
        assert math.isclose(sum(v['mean_ms'] for v in item['other_breakdown'].values()), item['phases']['other']['mean_ms'], abs_tol=1e-7)
        assert math.isclose(sum(v['mean_pct_of_other'] for v in item['other_breakdown'].values()), 100, abs_tol=1e-7)
        for sample in item['samples']:
            assert math.isclose(sum(sample['phase_ms'].values()), sample['window_ms'], abs_tol=1e-7)
            assert math.isclose(sum(sample['other_breakdown_ms'].values()), sample['phase_ms']['other'], abs_tol=1e-7)
            assert sample['external_residual_ms'] >= 0
            records = sample['records']
            window = next(r for r in records if r['name'] == 'profile_window')
            assert math.isclose(window['user_s'] * 1000, sample['window_process_user_ms'])
            assert math.isclose(window['system_s'] * 1000, sample['window_process_system_ms'])
            assert sample['background_gdb_union_ms'] == 0
            count += 1
assert 'process-wide' in summary['cpu_warning']
print(f'PASS: {count} precise samples across 16 groups; all eight golden hashes; '
      '16 final-output digests checked, not every output; frozen binary provenance; adaptive workers; primary and secondary partitions; '
      'mean-ms/share sums; nonnegative residuals; process-wide CPU labeling.')
