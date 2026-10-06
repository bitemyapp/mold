#!/usr/bin/env python3
"""Partition measured foreground elapsed intervals without summing nested work."""
import argparse
import collections
import json
import math
from pathlib import Path
import statistics as st

CATEGORIES = [
    ('merge', 'Merge strings'), ('copy', 'Copy / relocate'),
    ('build_id', 'Build ID / advice'), ('gather', 'Gather symbols'),
    ('gc', 'Section GC'), ('open_output', 'Open output'),
    ('input_cleanup', 'Release input mappings'), ('other', 'Other'),
]
NAMES = {
    'create_merged_sections':'merge', 'split_contents':'merge',
    'resize':'merge', 'resolve_contents':'merge', 'copy':'copy',
    'write_build_id':'build_id', 'gather_symbols':'gather', 'gc':'gc',
    'open_file':'open_output', 'release_input_mappings':'input_cleanup',
}
BACKGROUND_ROOTS = {'read_gdb_index_inputs', 'build_gdb_index_tables'}
OTHER_CATEGORIES = [
    ('read_resolve', 'Input / symbol resolution'),
    ('layout', 'Output assembly / layout'),
    ('scan', 'Relocation scan'),
    ('remaining', 'Checks / setup / remaining'),
]
OTHER_NAMES = {
    'read_input_files':'read_resolve', 'resolve_symbols':'read_resolve',
    'scan_relocations':'scan',
    'create_output_sections':'layout', 'sort_output_sections':'layout',
    'compute_section_sizes':'layout', 'compute_section_headers':'layout',
    'set_osec_offsets':'layout', 'sort_dynsyms':'layout',
    'compute_symtab_size':'layout',
}

def stats(values):
    values = sorted(values)
    def q(p):
        x=(len(values)-1)*p;lo=math.floor(x);hi=math.ceil(x)
        return values[lo]+(values[hi]-values[lo])*(x-lo)
    return dict(mean=st.mean(values), median=st.median(values), p10=q(.1), p90=q(.9))

def union(intervals):
    result=[]
    for start,end in sorted(intervals):
        if result and start<=result[-1][1]: result[-1][1]=max(end,result[-1][1])
        else: result.append([start,end])
    return result

def duration(intervals):
    return sum(b-a for a,b in union(intervals))*1000

def overlap(a,b):
    return duration([(max(x,u),min(y,v)) for x,y in union(a) for u,v in union(b)
                     if max(x,u)<min(y,v)])

def parse(text):
    records=[];threads=None;version=1
    for line in text.splitlines():
        f=line.split('\t')
        if f[0]=='PROFILE_FORMAT':version=int(f[1])
        elif f[0]=='PROFILE_THREADS':threads=int(f[1])
        elif f[0]=='PROFILE':
            if version==2:
                _,idx,parent,explicit,start,end,user,system,name=f
                start,end=int(start)/1e9,int(end)/1e9
                name=bytes.fromhex(name).decode('utf8')
            else:
                _,idx,parent,start,end,user,system,name=f
                start,end=float(start),float(end);explicit=-1
            records.append(dict(id=int(idx),parent=int(parent),explicit_parent=int(explicit),
                                start=start,end=end,user_s=float(user),system_s=float(system),name=name))
    assert records and threads is not None, 'Missing precise trace output'
    assert [r['id'] for r in records]==list(range(len(records)))
    return records,threads,version

def profile(text, external):
    records,threads,version=parse(text)
    window=next((r for r in records if r['name']=='profile_window'),
                next(r for r in records if r['name']=='all'))
    original=next(r for r in records if r['name']=='all')
    lo,hi=window['start'],window['end']
    background={r['id'] for r in records if r['name'] in BACKGROUND_ROOTS}
    # Inferred temporal containment is NOT parentage for asynchronous work.
    for r in records:
        if r['explicit_parent'] in background:background.add(r['id'])
    selected=[r|{'category':NAMES[r['name']]} for r in records
              if r['name'] in NAMES and r['id'] not in background]
    secondary=[r|{'category':OTHER_NAMES[r['name']]} for r in records
               if r['name'] in OTHER_NAMES and r['id'] not in background]
    for a in selected+secondary:
        assert lo<=a['start']<=a['end']<=hi, ('outside window',a)
        for b in selected+secondary:
            assert not (a['start']<b['start']<a['end']<b['end']), ('crossing foreground',a,b)
    points=sorted({lo,hi}|{r[k] for r in selected+secondary for k in ('start','end')})
    phases=dict.fromkeys(dict(CATEGORIES),0.)
    other=dict.fromkeys(dict(OTHER_CATEGORIES),0.)
    for start,end in zip(points,points[1:]):
        active=[r for r in selected if r['start']<=start and end<=r['end']]
        category=min(active,key=lambda r:(r['end']-r['start'],-r['id']))['category'] if active else 'other'
        phases[category]+=(end-start)*1000
        if category=='other':
            active=[r for r in secondary if r['start']<=start and end<=r['end']]
            detail=min(active,key=lambda r:(r['end']-r['start'],-r['id']))['category'] if active else 'remaining'
            other[detail]+=(end-start)*1000
    total=(hi-lo)*1000
    assert math.isclose(sum(phases.values()),total,abs_tol=1e-7)
    assert math.isclose(sum(other.values()),phases['other'],abs_tol=1e-7)
    bg=[(max(lo,r['start']),min(hi,r['end'])) for r in records
        if r['name'] in BACKGROUND_ROOTS and r['end']>lo and r['start']<hi]
    named=[(r['start'],r['end']) for r in selected]
    raw=collections.defaultdict(float)
    cpu=collections.defaultdict(lambda:dict(user_s=0.,system_s=0.,intervals=0))
    for r in records:
        raw[r['name']]+=(r['end']-r['start'])*1000
        cpu[r['name']]['user_s']+=r['user_s'];cpu[r['name']]['system_s']+=r['system_s'];cpu[r['name']]['intervals']+=1
    residual=external['wall']*1000-total
    assert residual>=-.05, ('negative external residual',residual)
    return dict(workers=threads,trace_format=version,window_ms=total,
                original_all_ms=(original['end']-original['start'])*1000,
                external_residual_ms=residual,phase_ms=phases,
                phase_pct={k:v/total*100 for k,v in phases.items()},
                other_breakdown_ms=other,
                other_pct_of_window={k:v/total*100 for k,v in other.items()},
                other_pct_of_other={k:v/phases['other']*100 if phases['other'] else 0. for k,v in other.items()},
                background_gdb_union_ms=duration(bg),
                background_gdb_overlap_with_foreground_ms=overlap(bg,named),
                window_process_user_ms=window['user_s']*1000,
                window_process_system_ms=window['system_s']*1000,
                timer_aggregate_wall_ms=dict(raw),
                timer_process_cpu_intervals=dict(cpu),records=records)

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--input',type=Path,required=True)
    p.add_argument('--manifest',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();raw=json.loads(a.input.read_text());manifest=json.loads(a.manifest.read_text())
    result=dict(schema_version=1,type='instrumented_phase_attribution',
        categories=[dict(id=k,label=v) for k,v in CATEGORIES],
        other_categories=[dict(id=k,label=v) for k,v in OTHER_CATEGORIES],
        other_accounting='Secondary partition restricted to the primary Other intervals. Input / symbol resolution is the union of read_input_files and resolve_symbols after subtracting primary categories such as Gather symbols. Output assembly / layout includes output-section creation/sorting, section size/header/offset calculation, dynamic-symbol sorting, and output symbol-table sizing after subtracting primary Merge strings. Relocation scan is scan_relocations. Checks / setup / remaining is the residual, including other instrumented passes and uninstrumented gaps. No component is added on top of the main window.',
        other_timer_mapping=OTHER_NAMES,
        window_definition='profile_window starts immediately before the existing all timer and ends after input mapping release, before trace rendering. It excludes argument/target setup before all, trace rendering, and final process exit.',
        accounting='Foreground elapsed intervals are partitioned by the smallest enclosing selected interval. Nested split/resolve is not added to create_merged_sections; nested build-ID/advice is removed from copy. GDB overlays follow explicit parentage only and are not stacked. Mean milliseconds and mean shares add; separate medians need not.',
        merge_scope='Preparation, splitting, table sizing, insertion. Later merged layout and uninstrumented member gathering stay in Other.',
        copy_scope='The copy wrapper excluding build-ID: copying, relocation, finalization, GDB wait/write if requested. Output mapping/preparation is separate.',
        cpu_warning='Per-timer user/system deltas are process-wide snapshots, include concurrent work, and overlap across timers. They are diagnostic intervals, not exclusive CPU attribution. Kernel-inclusive perf self-cycle samples belong in a separate chart.',
        precision='Wall boundaries are serialized in nanoseconds from Instant; underlying precision is platform-dependent. CPU snapshots use getrusage microsecond resolution.',
        performance_warning='Instrumented durations are attribution only and must not be used for production speedup claims. Four extra coarse rusage snapshots plus trace rendering are measurement overhead.',
        raw_input=str(a.input),provenance=manifest,cases={})
    for case,labels in raw['cases'].items():
        result['cases'][case]={}
        for label,row in labels.items():
            samples=[profile(t,s) for t,s in zip(row['profiles'],row['samples'],strict=True)]
            assert len({s['workers'] for s in samples})==1
            spec=manifest['labels'][label]
            if spec.get('profile_binary_sha256'):assert row['binary_sha256']==spec['profile_binary_sha256']
            phases={}
            for key,_ in CATEGORIES:
                ms=stats([s['phase_ms'][key] for s in samples]);pct=stats([s['phase_pct'][key] for s in samples])
                phases[key]={f'{k}_ms':v for k,v in ms.items()}|dict(mean_pct=pct['mean'],median_pct=pct['median'])
            other={}
            for key,_ in OTHER_CATEGORIES:
                ms=stats([s['other_breakdown_ms'][key] for s in samples])
                other[key]={f'{k}_ms':v for k,v in ms.items()}|dict(
                    mean_pct_of_window=st.mean(s['other_pct_of_window'][key] for s in samples),
                    mean_pct_of_other=st.mean(s['other_pct_of_other'][key] for s in samples))
            names=set().union(*(s['timer_aggregate_wall_ms'] for s in samples))
            out=spec|dict(n=len(samples),workers=samples[0]['workers'],
                profile_binary_sha256=row['binary_sha256'],output_sha256=row['sha256'],
                phases=phases,other_breakdown=other,background_gdb=dict(
                    union_ms=stats([s['background_gdb_union_ms'] for s in samples]),
                    overlap_with_foreground_ms=stats([s['background_gdb_overlap_with_foreground_ms'] for s in samples]),
                    overlap_definition='Intersection with the union of explicitly named foreground categories, excluding Other.'),
                timer_aggregate_wall_ms={name:stats([s['timer_aggregate_wall_ms'].get(name,0.) for s in samples]) for name in sorted(names)},
                samples=samples)
            for k in ['window_ms','original_all_ms','external_residual_ms','window_process_user_ms','window_process_system_ms']:
                out[k]=stats([s[k] for s in samples])
            assert math.isclose(sum(v['mean_ms'] for v in phases.values()),out['window_ms']['mean'],abs_tol=1e-7)
            assert math.isclose(sum(v['mean_ms'] for v in other.values()),phases['other']['mean_ms'],abs_tol=1e-7)
            result['cases'][case][label]=out
            print(case,label,'workers',out['workers'],'window_ms',round(out['window_ms']['median'],3))
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(result,indent=2)+'\n')

if __name__=='__main__':main()
