#!/usr/bin/env python3
"""Summarize untimed instrumentation separately from production performance."""
import csv, json, statistics
from pathlib import Path
root = Path(__file__).resolve().parent
result = json.loads((root / 'results/counts.json').read_text())
rows = result['rows']
keys = sorted({key for row in rows for key in row['counters']})
with (root / 'results/counters.csv').open('w', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=['case', 'variant', 'run', 'binary_sha256', 'output_sha256'] + keys)
    writer.writeheader()
    for row in rows:
        writer.writerow({key: row[key] for key in ['case', 'variant', 'run', 'binary_sha256', 'output_sha256']} | row['counters'])
summary = {}
for case in dict.fromkeys(row['case'] for row in rows):
    summary[case] = {}
    for variant in ['baseline', 'candidate']:
        group = [row for row in rows if row['case'] == case and row['variant'] == variant]
        summary[case][variant] = {'n': len(group)}
        for key in keys:
            values = [row['counters'].get(key, 0) for row in group]
            summary[case][variant][key] = {'min': min(values), 'median': statistics.median(values), 'max': max(values)}
(root / 'results/counter-summary.json').write_text(json.dumps(summary, indent=2) + '\n')
lines = ['# MS3 allocation observations', '',
  'These are separate instrumented binaries, three untimed runs per variant and case, eight threads on CPUs 0–7. They are not production timing samples. Pointer changes count payload bytes preserved at a new address, not measured hardware traffic. Capacity is summed per input section at the end of splitting, not sampled simultaneous RSS; hash arrays are later freed during resolution. Allocator state and the instrumentation can affect whether reallocation moves.', '',
  '| Case | Capacity changes, baseline → candidate | Live bytes moved, MiB | Sum of capacities at split completion, MiB |',
  '|---|---:|---:|---:|']
for case, groups in summary.items():
    parts = [case]
    for key, scale in [('ms3_vec_allocations', 1), ('ms3_vec_live_bytes_moved', 2**20), ('ms3_vec_final_capacity_bytes', 2**20)]:
        a = groups['baseline'][key]['median'] / scale
        b = groups['candidate'][key]['median'] / scale
        parts.append(f'{a:,.2f} → {b:,.2f}' if scale != 1 else f'{a:,.0f} → {b:,.0f}')
    lines.append('| ' + ' | '.join(parts) + ' |')
lines += ['', 'All outputs were compared with the eight-corpus golden hashes. Per-run ranges, exact binaries, commands and raw counters are preserved in counts.json and counters.csv.']
(root / 'results/README.md').write_text('\n'.join(lines) + '\n')
