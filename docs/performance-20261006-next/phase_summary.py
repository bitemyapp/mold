#!/usr/bin/env python3
import json
from pathlib import Path
import re
import statistics as st
root = Path(__file__).resolve().parent
d = json.loads((root/'results/topic-phases.json').read_text())
out = {}
for case, topics in d['cases'].items():
    out[case] = {}
    for topic, row in topics.items():
        samples = []
        for profile in row['profiles']:
            totals = {'merge_ms':0., 'copy_ms':0., 'build_id_ms':0., 'all_ms':0.}
            stack = []
            for line in profile.splitlines():
                match = re.match(r'^\s*([\d.]+)\s+([\d.]+)\s+([\d.]+)  ( *)(\S.*)$', line)
                if not match:
                    continue
                _, _, wall, indent, name = match.groups()
                depth = len(indent)//2
                stack = stack[:depth]
                if name == 'create_merged_sections' or (name in ('split_contents','resize','resolve_contents') and 'create_merged_sections' not in stack):
                    totals['merge_ms'] += float(wall)*1000
                if name == 'copy':
                    totals['copy_ms'] += float(wall)*1000
                if name == 'write_build_id':
                    totals['build_id_ms'] += float(wall)*1000
                    if 'copy' in stack:
                        totals['copy_ms'] -= float(wall)*1000
                if name == 'all':
                    totals['all_ms'] = float(wall)*1000
                stack.append(name)
            assert totals['copy_ms'] >= 0
            samples.append(totals)
        out[case][topic] = {k:st.median(s[k] for s in samples) for k in samples[0]}
        out[case][topic]['samples'] = samples
        print(case,topic,{k:round(v,1) for k,v in out[case][topic].items() if k!='samples'})
(root/'phase-summary.json').write_text(json.dumps(out,indent=2)+'\n')
