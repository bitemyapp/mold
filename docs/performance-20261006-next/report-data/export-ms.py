#!/usr/bin/env python3
"""Rerunnable MS1–MS4 raw-metric export; profiles remain separate."""
import csv, json, math, statistics
from pathlib import Path
root=Path(__file__).resolve().parent.parent
commits={sha: info['source_commit'] for sha,info in json.loads((root/'report-data/provenance.json').read_text()).items()}
rows=[]
for p in sorted((root/'results').glob('*.json')):
    data=json.loads(p.read_text())
    if not isinstance(data,dict) or 'cases' not in data or data.get('args',{}).get('perf'):
        continue
    for case, variants in data['cases'].items():
        if not any(k.split('-')[0] in ('ms1','ms2','ms3','ms4') for k in variants):
            continue
        for label, row in variants.items():
            if label.split('-')[0] not in ('baseline','ms1','ms2','ms3','ms4') or 'samples' not in row:
                continue
            samples=row['samples']; wall=sorted(s['wall']*1000 for s in samples)
            sha=row.get('binary_sha256','')
            rows.append(dict(result_file=p.name,case=case,variant=label,n=len(samples),
              output_mode='fresh' if data.get('args',{}).get('fresh_output') else 'reused',
              wall_p50_ms=statistics.median(wall),wall_p95_ms=wall[math.ceil(.95*len(wall))-1],
              wall_p99_ms=wall[math.ceil(.99*len(wall))-1],
              cpu_median_ms=statistics.median((s['user']+s['sys'])*1000 for s in samples),
              peak_rss_median_mib=statistics.median(s['rss_kib']/1024 for s in samples),
              peak_rss_max_mib=max(s['rss_kib']/1024 for s in samples),binary_sha256=sha,
              source_commit=commits.get(sha,'UNKNOWN'),output_sha256=row.get('sha256','')))
if rows:
    with (root/'report-data/ms-topic-metrics.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
print(f'{len(rows)} absolute-metric rows exported')
