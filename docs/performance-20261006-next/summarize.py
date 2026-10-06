#!/usr/bin/env python3
"""Summarize paired rounds, preserving the whole-link and CPU tradeoff."""
import argparse
import json
from pathlib import Path
import statistics as st
import numpy as np

p = argparse.ArgumentParser()
p.add_argument('files', nargs='+', type=Path)
p.add_argument('--json', type=Path)
p.add_argument('--baseline')
a = p.parse_args()
rng = np.random.default_rng(1696)
out = []
for path in a.files:
    data = json.loads(path.read_text())
    for case, rows in data['cases'].items():
        base_key = a.baseline or ('baseline' if 'baseline' in rows else next(iter(rows)))
        base = rows[base_key]
        for name, row in rows.items():
            if name == base_key:
                continue
            item = dict(file=path.name, case=case, topic=name, baseline=base_key,
                        samples=len(row['samples']), binary=row['binary_sha256'])
            for metric, field in [('wall', lambda s:s['wall']),
                                  ('cpu', lambda s:s['user']+s['sys']),
                                  ('rss', lambda s:s['rss_kib'])]:
                b = {s['round']:field(s) for s in base['samples']}
                c = {s['round']:field(s) for s in row['samples']}
                pairs = np.array([(b[i], c[i]) for i in sorted(b.keys() & c.keys())])
                # Paired bootstrap of the ratio of medians; keep each round together.
                ix = rng.integers(0, len(pairs), (10000, len(pairs)))
                samples = pairs[ix]
                delta = (np.median(samples[:,:,1], axis=1) /
                         np.median(samples[:,:,0], axis=1)-1)*100
                item[metric] = dict(baseline=float(np.median(pairs[:,0])),
                                    candidate=float(np.median(pairs[:,1])),
                                    delta_pct=float((np.median(pairs[:,1])/np.median(pairs[:,0])-1)*100),
                                    ci95=[float(v) for v in np.quantile(delta,[.025,.975])])
            item['baseline_p95_ms'] = base['summary']['p95_ms']
            item['candidate_p95_ms'] = row['summary']['p95_ms']
            item['hash_match'] = base['sha256'] == row['sha256']
            out.append(item)
            fmt = lambda k: f"{item[k]['delta_pct']:+6.1f} [{item[k]['ci95'][0]:+5.1f},{item[k]['ci95'][1]:+5.1f}]"
            print(f"{name:8} {case:9} wall {fmt('wall')} cpu {fmt('cpu')} rss {item['rss']['delta_pct']:+5.1f}")
if a.json:
    a.json.write_text(json.dumps(out,indent=2)+'\n')
