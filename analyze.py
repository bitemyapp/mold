#!/usr/bin/env python3
"""Compare interleaved arms; preserve uncertainty and produce portable evidence."""
import base64, html, json, math, re, statistics as st
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parent
OUT=ROOT/'report';OUT.mkdir(exist_ok=True)
DATA=json.loads((ROOT/'results/latency.json').read_text())
CASES=['hello','rhello','tblgen','lld','clang','clang-s','ra','ra-s']
NAMES=['C hello','Rust hello','LLVM TableGen','lld','Clang','Clang stripped','rust-analyzer','rust-analyzer stripped']
PAIRS=[('idle','original-idle','rayon-idle'),('startup','original-startup','rayon-startup')]
LABELS=['base','original-idle','rayon-idle','original-startup','rayon-startup']
SUMMARY={'cases':{},'comparisons':{},'method':'Positive savings = lower resource use. Paired round bootstrap of ratio of medians; 10000 resamples; 95% percentile interval.'}
rng=np.random.default_rng(16941695)
def vals(row,metric):
    samples=sorted(row['samples'],key=lambda s:s['round'])
    return np.array([s['user']+s['sys'] if metric=='cpu' else s[metric] for s in samples])
def compare(a,b,metric):
    x,y=vals(a,metric),vals(b,metric)
    ix=rng.integers(0,len(x),size=(10000,len(x)))
    boot=100*(1-np.median(y[ix],axis=1)/np.median(x[ix],axis=1))
    low,high=np.percentile(boot,[2.5,97.5])
    return {'savings_pct':100*(1-float(np.median(y))/float(np.median(x))),'ci95':[float(low),float(high)]}
def q(xs,p):return sorted(xs)[max(0,math.ceil(len(xs)*p)-1)]
for case in CASES:
    rows=DATA['cases'][case]
    SUMMARY['cases'][case]={}
    for label in LABELS:
        row=rows[label];wall=vals(row,'wall');cpu=vals(row,'cpu');rss=vals(row,'rss_kib')
        SUMMARY['cases'][case][label]={'p10_ms':q(wall,.1)*1000,'p50_ms':float(np.median(wall))*1000,'p95_ms':q(wall,.95)*1000,'cpu_ms':float(np.median(cpu))*1000,'peak_rss_mib':float(np.median(rss))/1024,'sha256':row['sha256']}
    assert len({r['sha256'] for r in rows.values()})==1
    for name,old,new in PAIRS:
        SUMMARY['comparisons'].setdefault(name,{})[case]={metric:compare(rows[old],rows[new],metric) for metric in ['wall','cpu','rss_kib']}
        SUMMARY['comparisons'].setdefault(name+'_vs_base',{})[case]={metric:compare(rows['base'],rows[new],metric) for metric in ['wall','cpu','rss_kib']}
SUMMARY['geomean']={}
for name,old,new in PAIRS:
    SUMMARY['geomean'][name]={}
    for metric in ['p50_ms','cpu_ms','peak_rss_mib']:
        ratio=math.exp(st.mean(math.log(SUMMARY['cases'][c][new][metric]/SUMMARY['cases'][c][old][metric]) for c in CASES))
        SUMMARY['geomean'][name][metric]=100*(1-ratio)
(OUT/'summary.json').write_text(json.dumps(SUMMARY,indent=2))
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False,'axes.spines.left':False})
fig,axes=plt.subplots(1,2,figsize=(14,7),sharey=True)
for ax,(name,old,new) in zip(axes,PAIRS):
    for offset,metric,color,legend in [(-.17,'wall','#217a91','Elapsed time'),(.17,'cpu','#ca7941','CPU time')]:
        rows=[SUMMARY['comparisons'][name][c][metric] for c in CASES]
        estimates=np.array([r['savings_pct'] for r in rows]);lo=np.array([r['ci95'][0] for r in rows]);hi=np.array([r['ci95'][1] for r in rows])
        y=np.arange(len(CASES))+offset
        ax.barh(y,estimates,height=.28,color=color,label=legend,alpha=.85)
        # Draw CI endpoints directly; bootstrap percentile CI need not contain the point estimate.
        ax.hlines(y,lo,hi,color='#263d4b',lw=1.2)
        ax.plot(lo,y,'|',color='#263d4b');ax.plot(hi,y,'|',color='#263d4b')
    ax.set_title('Rayon polling vs original #1694' if name=='idle' else 'Rayon startup vs original #1695',fontsize=13)
    ax.axvline(0,color='#72828a',lw=.8);ax.grid(axis='x',alpha=.15);ax.set_axisbelow(True)
    ax.set_xlabel('Savings (%) · positive is better')
axes[0].set_yticks(np.arange(len(CASES)),NAMES);axes[0].invert_yaxis()
fig.suptitle('Move the runtime behavior into Rayon',fontsize=20,x=.05,ha='left')
fig.text(.05,.93,'40 interleaved samples per arm and case · 32 workers · error bars: paired 95% bootstrap intervals',fontsize=10,color='#596976')
fig.text(.05,.905,'Blue: elapsed time · Amber: aggregate CPU time. Positive savings mean lower cost.',fontsize=10,color='#596976')
fig.tight_layout(rect=[.01,.01,1,.89]);fig.savefig(OUT/'comparison.png',dpi=170);fig.savefig(OUT/'comparison.svg');plt.close(fig)
def table(headers,rows):
    return '<table><thead><tr>'+''.join('<th>'+html.escape(str(h))+'</th>' for h in headers)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+str(cell)+'</td>' for cell in r)+'</tr>' for r in rows)+'</tbody></table>'
def fmt(x):return f'{x:.2f}'
def change(r):return f'{r["savings_pct"]:+.1f}% <small>[{r["ci95"][0]:+.1f}, {r["ci95"][1]:+.1f}]</small>'
parts=['''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>mold: Rayon runtime experiments</title><style>body{font:16px/1.55 system-ui;max-width:1250px;margin:40px auto;padding:0 25px;color:#203747;background:#fbfcfd}h1{font-size:34px;line-height:1.15}h2{margin-top:34px}table{border-collapse:collapse;width:100%;font-size:14px}th,td{padding:10px;text-align:right;border-bottom:1px solid #dae3e9}th:first-child,td:first-child{text-align:left}small{font-size:12px;color:#5b6c78}img{max-width:100%}.note{border-left:4px solid #217a91;background:#edf4f7;padding:15px 20px}a{color:#216a8a}code{font-size:14px}</style><h1>mold: moving polling and startup into Rayon</h1><p>6 October 2026 · Builds, tests and measurements on <code>ssh wx-workstation</code>.</p>''']
notes=ROOT/'report-conclusion.html'
if notes.exists():parts.append(notes.read_text())
parts.append('<p class="note">These branches patch vendored <b>rayon-core 1.13.0</b>. The APIs are experimental and are not available in released Rayon. Each branch descends from its original PR; both comparisons share baseline <code>99d79c42</code>.</p>')
img=base64.b64encode((OUT/'comparison.png').read_bytes()).decode();parts.append(f'<img alt="Elapsed and CPU savings with uncertainty for both Rayon experiments" src="data:image/png;base64,{img}">')
for name,old,new in PAIRS:
    parts.append('<h2>'+('Idle polling — #1694' if name=='idle' else 'Asynchronous startup — #1695')+'</h2>')
    rows=[]
    for case,label in zip(CASES,NAMES):
        r=SUMMARY['cases'][case];comp=SUMMARY['comparisons'][name][case]
        rows.append([label,fmt(r['base']['p50_ms']),fmt(r[old]['p50_ms']),fmt(r[new]['p50_ms']),change(comp['wall']),change(comp['cpu'])])
    parts.append(table(['Workload','Base p50 ms','Original PR p50 ms','Rayon p50 ms','Elapsed savings vs PR','CPU savings vs PR'],rows))
    parts.append('<p><small>Positive savings means lower cost. Bracketed ranges are paired 95% bootstrap intervals. Intervals crossing zero do not establish a direction. CPU is aggregate user + system time across the process’s threads.</small></p>')
parts.append('<h2>Concurrent-link throughput</h2><p>Each process requests 32 workers on the same 32 physical cores. Ten measured batches per arm, one warmup, cyclic interleaving. RSS shown elsewhere is per process, not total concurrent memory.</p>')
through=json.loads((ROOT/'results/throughput.json').read_text())
SUMMARY['throughput']={}
for case, data in through['cases'].items():
    SUMMARY['throughput'][case]={}
    for name, old, new in PAIRS:
        a={'samples':[dict(s,round=i) for i,s in enumerate(data['variants'][old])]}
        b={'samples':[dict(s,round=i) for i,s in enumerate(data['variants'][new])]}
        SUMMARY['throughput'][case][name]={metric:compare(a,b,metric) for metric in ['wall','cpu']}
(OUT/'summary.json').write_text(json.dumps(SUMMARY,indent=2))
rows=[]
for case,data in through['cases'].items():
    for label in LABELS:
        ss=data['variants'][label];wall=st.median(x['wall'] for x in ss);cpu=st.median(x['user']+x['sys'] for x in ss)
        rows.append([f'{data["total"]} {case}, {data["jobs"]} at once',label,fmt(wall),f'{data["total"]/wall:.1f}',fmt(cpu)])
parts.append(table(['Batch','Variant','Median seconds','Links/second','CPU seconds'],rows))
parts.append('<h2>One- and eight-worker checks</h2><p>20 samples per arm and selected workload. These are sensitivity checks; the main comparison uses 32 workers.</p>')
rows=[]
for n in [1,8]:
    d=json.loads((ROOT/f'results/threads{n}.json').read_text())
    for case,values in d['cases'].items():
        assert len({r['sha256'] for r in values.values()})==1
        rows.append([n,case]+[fmt(st.median(s['wall'] for s in values[label]['samples'])*1000) for label in LABELS])
parts.append(table(['Workers','Case']+LABELS,rows))
parts.append('<h2>Tail latency and memory</h2>')
rows=[]
for case,label in zip(CASES,NAMES):
    for v in LABELS:
        r=SUMMARY['cases'][case][v];rows.append([label,v,fmt(r['p10_ms']),fmt(r['p95_ms']),fmt(r['cpu_ms']),fmt(r['peak_rss_mib'])])
parts.append(table(['Workload','Variant','p10 ms','p95 ms','CPU ms','Median peak RSS MiB'],rows))
parts.append('''<h2>Implementation and correctness</h2><p>Polling: <code>ThreadPoolBuilder::idle_timeout(Duration)</code> extends idle search between completed top-level jobs, leaving initial startup and nested join/scope waits on the normal policy. Zero retains the original policy. Mold removes its broadcast polling jobs and timer hooks, and opts into 2 ms.</p><p>Startup: <code>ThreadPoolBuilder::build_global_async()</code> moves the spawn helper into Rayon and preserves the global pool, thread names, stack sizes and callbacks. A single current worker needs no helper. Synchronous helper-creation errors are returned; later worker-creation failures abort rather than leave a worker queue permanently unserviced. This error policy requires upstream API review.</p><p>Baseline and both candidates pass the mold native suite: 503 passed, 14 skipped, zero failures each. Upstream Rayon tests and added lifecycle/startup/failure tests pass. Captured link outputs are byte-identical across all arms and tested worker counts. No claims are made about untested target architectures.</p><h2>Measurement limits</h2><p>AMD Threadripper PRO 9985WX; CPUs 32–63, one hardware thread per core; warm inputs; ext4 output; <code>--no-fork</code>; same compiler and release flags. Each build cleans the affected packages to prevent cross-checkout Cargo cache reuse. The original PRs and their exact parent are tested, without later upstream changes. Three warmups precede 40 single-link samples, with 50 ms between processes.</p><p>Unrelated workstation build/VM activity occurred. Interleaving reduces time-order bias but does not remove shared-memory, storage or scheduler interference. Bootstrap intervals describe this sample and do not account for every systematic effect. The p95 figures are descriptive with 40 samples; extreme-tail estimates are not reliable. Equal-weight geometric means, where quoted, describe these eight cases and are not a production-workload forecast.</p><p>Internal <code>--perf</code> pass profiles are retained separately from uninstrumented timings. Their millisecond resolution and overlapping nested/concurrent spans limit fine attribution; do not sum nested spans or treat those CPU counters as per-section CPU attribution.</p><h2>Evidence and reproducibility</h2><p>Raw samples, fingerprints, hashes, phase profiles, logs, scripts, the first polling revision’s results and the branch manifest accompany this report in the experiment directory. The repository branches include the vendored source and its licenses.</p></html>''')
(OUT/'report.html').write_text(''.join(parts))
print(json.dumps(SUMMARY['geomean'],indent=2))
