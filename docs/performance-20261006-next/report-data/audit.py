#!/usr/bin/env python3
"""Independent scalar recomputation of CSV exports and renderer metric inputs."""
import csv
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import statistics as st

ROOT = Path(__file__).resolve().parent.parent
DEST = ROOT / 'report-data'
raw = {}
for p in (ROOT/'results').glob('*.json'):
    try:
        d = json.loads(p.read_text())
    except json.JSONDecodeError:
        continue
    if isinstance(d, dict) and isinstance(d.get('cases'), dict):
        raw[p.name] = d


def close(a, b):
    assert math.isclose(float(a), float(b), rel_tol=1e-12, abs_tol=1e-10), (a,b)


def quantile(values, q):
    return sorted(values)[math.ceil(q*len(values))-1]


summaries = list(csv.DictReader((DEST/'all-case-summary.csv').open()))
samples = list(csv.DictReader((DEST/'all-samples.csv').open()))
for rows, suffix in [(summaries, []), (samples, ['round'])]:
    keys = [tuple(r[k] for k in ['campaign','result_file','case','label']+suffix) for r in rows]
    assert len(keys)==len(set(keys)), 'Duplicate exported identity'

for row in summaries:
    doc = raw[row['result_file']]
    group = doc['cases'][row['case']][row['label']]
    values = group['samples']
    assert len(values)==int(row['sample_count'])
    assert len({s['round'] for s in values})==len(values)
    assert group['binary_sha256']==row['binary_sha256']
    assert group['sha256']==row['output_sha256']
    assert row['output_mode']==('fresh' if doc['args'].get('fresh_output') else 'reused')
    for key, values2 in [('wall',[s['wall']*1000 for s in values]),
                         ('user_cpu',[s['user']*1000 for s in values]),
                         ('sys_cpu',[s['sys']*1000 for s in values]),
                         ('total_cpu',[(s['user']+s['sys'])*1000 for s in values])]:
        close(row[key+'_p50_ms' if key=='wall' else key+'_median_ms'], st.median(values2))
        if key=='wall':
            close(row['wall_p95_ms'],quantile(values2,.95))
            close(row['wall_p99_ms'],quantile(values2,.99))
            close(row['wall_max_ms'],max(values2))
    rss = [s['rss_kib']/1024 for s in values]
    close(row['peak_rss_median_mib'],st.median(rss))
    close(row['peak_rss_max_mib'],max(rss))

for row in samples:
    group = raw[row['result_file']]['cases'][row['case']][row['label']]
    value = group['samples'][int(row['sample_index'])]
    assert int(row['round'])==value['round']
    close(row['wall_ms'],value['wall']*1000)
    close(row['total_cpu_ms'],(value['user']+value['sys'])*1000)
    close(row['peak_rss_kib'],value['rss_kib'])

render_path = ROOT/'report/rendered-comparisons.json'
rendered = json.loads(render_path.read_text())
ci_checked = 0
for row in rendered:
    doc = raw[row['file']]
    variants = doc['cases'][row['case']]
    base, candidate = variants[row['baseline_label']], variants[row['label']]
    assert len(base['samples'])==len(candidate['samples'])==row['n']
    assert row['base_binary']==base['binary_sha256'] and row['binary']==candidate['binary_sha256']
    assert row['output_hash']==candidate['sha256'] and row['base_output_hash']==base['sha256']
    assert row['output_mode']==('fresh' if doc['args'].get('fresh_output') else 'reused')
    assert row['env']==candidate.get('env',{})
    for metric, field in [('wall',lambda s:s['wall']),('cpu',lambda s:s['user']+s['sys']),('rss',lambda s:s['rss_kib'])]:
        b,c = [st.median(field(s) for s in variant['samples']) for variant in [base,candidate]]
        close(row[metric]['baseline'],b)
        close(row[metric]['candidate'],c)
        close(row[metric]['delta_pct'],(c/b-1)*100)
    if row['ci_source'].endswith('.json'):
        saved = json.loads((ROOT/'results'/row['ci_source']).read_text())
        matches = [r for r in saved if (r['file'],r['case'],r['topic'],r['baseline']) ==
                   (row['file'],row['case'],row['label'],row['baseline_label'])]
        assert len(matches)==1
        for metric in ['wall','cpu','rss']:
            assert row[metric]['ci95']==matches[0][metric]['ci95']
        ci_checked += 1

audit = dict(utc=datetime.now(timezone.utc).isoformat(), result='pass',
    summary_groups_checked=len(summaries), exported_samples_checked=len(samples),
    renderer_comparisons_checked=len(rendered), saved_confidence_intervals_matched=ci_checked,
    rendered_comparisons_sha256=hashlib.sha256(render_path.read_bytes()).hexdigest(),
    checks=['unique case/label/file identities and sample rounds', 'absolute medians and nearest-rank tails',
            'CPU sum before median', 'per-link peak RSS unit conversion and max',
            'sample metrics against raw links', 'renderer median ratios recomputed from raw samples',
            'binary/output hashes, environment and output-mode identity',
            'saved confidence intervals exactly match declared source'],
    limits='This audit recomputes numerical inputs and matches declared interval evidence; it does not independently validate hardware counters or infer causality from host-state changes.')
(DEST/'numerical-audit.json').write_text(json.dumps(audit,indent=2)+'\n')
print(json.dumps(audit,indent=2))
