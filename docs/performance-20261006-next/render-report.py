#!/usr/bin/env python3
"""Render paired campaign evidence; selection is explicit in report-config.json.

Run with the existing profile-report/.venv/bin/python. Only this renderer,
config, and report/ outputs are owned here; evidence exporters remain separate.
"""
import argparse
import base64
import hashlib
import html
import json
import math
from pathlib import Path
import statistics as st
import textwrap
from datetime import datetime, timezone

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import TwoSlopeNorm
import numpy as np

ROOT = Path(__file__).resolve().parent
CASES = ['hello','rhello','tblgen','lld','clang','clang-s','ra','ra-s']
NAMES = {'hello':'C hello','rhello':'Rust hello','tblgen':'TableGen','lld':'lld',
         'clang':'Clang','clang-s':'Clang stripped','ra':'rust-analyzer','ra-s':'rust-analyzer stripped'}
SHORT = ['C hello','Rust hello','TableGen','lld','Clang','Clang\nstripped','rust-analyzer','rust-analyzer\nstripped']
INK, MUTED, TEAL, RUST, PAPER = '#173447','#687b86','#157f82','#be654a','#fbfcfc'
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'figure.facecolor':PAPER,
    'axes.facecolor':PAPER,'savefig.facecolor':PAPER,'text.color':INK,'axes.labelcolor':INK,
    'xtick.color':MUTED,'ytick.color':INK,'axes.spines.top':False,'axes.spines.right':False})


def read_json(path, default=None):
    try:
        return json.loads(path.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def esc(value):
    return html.escape(str(value))


def taglink(path, label):
    return f'<a href="{esc(path)}">{esc(label)}</a>'


class Report:
    def __init__(self, config, out):
        self.config, self.out = config, out
        out.mkdir(parents=True, exist_ok=True)
        self.provenance = read_json(ROOT/'report-data/provenance.json', {})
        self.worker_counts = read_json(ROOT/'topics/s2-assignment-counts/counts.json', {}).get('cases', {})
        self.raw = {}
        for p in sorted((ROOT/'results').glob('*.json')):
            value = read_json(p)
            if isinstance(value, dict) and isinstance(value.get('cases'), dict):
                self.raw[p.name] = value
        self.summaries = {}
        for p in sorted((ROOT/'results').glob('summary*.json')):
            rows = read_json(p, [])
            if isinstance(rows, list):
                for row in rows:
                    if all(k in row for k in ['file','case','topic','baseline']):
                        self.summaries[(row['file'],row['case'],row['topic'],row['baseline'])] = row | {'summary_file':p.name}
        sources = sorted({r['file'] for t in config['topics'] for r in self.references(t) if r} |
                         {config.get('omnibus',{}).get('file','omnibus.json'),config.get('s1',{}).get('file','s1-sweep.json')} |
                         {r['file'] for r in config.get('omnibus_confirmations',[])} |
                         {r['file'] for r in config.get('state_checks',[])})
        self.codes = {name:f'R{i+1}' for i,name in enumerate(sources)}
        self.cache, self.warnings = {}, []

    @staticmethod
    def references(topic):
        return [topic.get('primary')] + topic.get('confirmations',[]) + topic.get('revisions',[])

    def rows(self, ref):
        if not ref:
            return {}
        key = (ref['file'],ref['label'],ref.get('baseline','baseline'))
        if key in self.cache:
            return self.cache[key]
        data = self.raw.get(ref['file'], {})
        result = {}
        if data.get('args',{}).get('perf'):
            self.warnings.append(f'{ref["file"]}: profiled data excluded from comparisons')
            return {}
        for case, variants in data.get('cases',{}).items():
            baseline = ref.get('baseline','baseline')
            if baseline not in variants or ref['label'] not in variants:
                continue
            base, candidate = variants[baseline], variants[ref['label']]
            expected = data.get('args',{}).get('runs')
            complete = all(v.get('binary_sha256') and v.get('sha256') and
                           len(v.get('samples',[])) == expected for v in [base,candidate])
            if not complete:
                continue
            b = {s['round']:s for s in base['samples'] if 'round' in s}
            c = {s['round']:s for s in candidate['samples'] if 'round' in s}
            rounds = sorted(b.keys() & c.keys())
            if not rounds or len(rounds) != expected:
                continue
            saved = self.summaries.get((ref['file'],case,ref['label'],baseline))
            if saved and (saved.get('binary') != candidate['binary_sha256'] or saved.get('samples') != len(rounds)):
                saved = None
            row = dict(file=ref['file'],case=case,label=ref['label'],baseline_label=baseline,
                n=len(rounds),binary=candidate['binary_sha256'],base_binary=base['binary_sha256'],
                output_hash=candidate['sha256'],base_output_hash=base['sha256'],
                hash_match=candidate['sha256']==base['sha256'],env=candidate.get('env',{}),
                cpus=data.get('args',{}).get('cpus','unknown'),command=candidate.get('command',[]),
                output_mode='fresh' if data.get('args',{}).get('fresh_output',False) else 'reused')
            if ref.get('output_mode') and ref['output_mode']!=row['output_mode']:
                self.warnings.append(f'{ref["file"]}: output mode differs from declared comparison')
                continue
            for metric, field in [('wall',lambda x:x['wall']),('cpu',lambda x:x['user']+x['sys']),('rss',lambda x:x['rss_kib'])]:
                pairs = np.array([(field(b[i]),field(c[i])) for i in rounds])
                if saved:
                    row[metric] = saved[metric]
                else:
                    seed = int.from_bytes(hashlib.sha256(f'{key}:{case}:{metric}'.encode()).digest()[:8],'little')
                    rng = np.random.default_rng(seed)
                    ix = rng.integers(0,len(pairs),(10000,len(pairs)))
                    boot = pairs[ix]
                    ratios = (np.median(boot[:,:,1],axis=1)/np.median(boot[:,:,0],axis=1)-1)*100
                    mb,mc = np.median(pairs,axis=0)
                    row[metric] = dict(baseline=float(mb),candidate=float(mc),delta_pct=float((mc/mb-1)*100),ci95=np.quantile(ratios,[.025,.975]).tolist())
            row['ci_source'] = saved['summary_file'] if saved else 'renderer: paired bootstrap, 10000 resamples, deterministic per-cell seed'
            row['source'] = self.provenance.get(row['binary'],{}).get('source_commit','UNKNOWN')
            row['base_source'] = self.provenance.get(row['base_binary'],{}).get('source_commit','UNKNOWN')
            for prefix,digest in [('',row['binary']),('base_',row['base_binary'])]:
                entry=self.provenance.get(digest,{})
                row[prefix+'lineage']=entry.get('lineage','UNKNOWN')
                row[prefix+'anchor']=entry.get('base_anchor','UNKNOWN')
            observed=self.worker_counts.get(case,{}).get('workers',[])
            explicit_threads=any(v in ('--threads','-j') or v.startswith(('--threads=','-j')) for v in row['command'])
            row['observed_default_workers']=observed[0] if len(observed)==1 and row['cpus']=='32-63' and not explicit_threads and row['lineage']=='original_topic_baseline' else None
            budget=row['env'].get('MOLD_PHASE_BUDGET','')
            if ':' in budget and row['observed_default_workers']:
                phase,cap=budget.split(':',1)
                if cap.isdigit():
                    row['phase_cap']={'phase':phase,'requested':int(cap),'effective':min(int(cap),row['observed_default_workers']),
                                      'active':int(cap)<row['observed_default_workers']}
            if row['source']=='UNKNOWN' or row['base_source']=='UNKNOWN':
                self.warnings.append(f'{ref["file"]}/{ref["label"]}: frozen binary provenance missing')
            if not row['hash_match']:
                self.warnings.append(f'{ref["file"]}/{ref["label"]}/{case}: output hash mismatch; correctness not established')
            row['user'] = {k:st.median(v[i]['user'] for i in rounds) for k,v in [('baseline',b),('candidate',c)]}
            row['system'] = {k:st.median(v[i]['sys'] for i in rounds) for k,v in [('baseline',b),('candidate',c)]}
            row['cpu_mean']={k:{'user':st.mean(v[i]['user'] for i in rounds),'system':st.mean(v[i]['sys'] for i in rounds)} for k,v in [('baseline',b),('candidate',c)]}
            result[case] = row
        self.cache[key] = result
        return result

    def save(self, fig, name):
        fig.savefig(self.out/(name+'.png'),dpi=170)
        fig.savefig(self.out/(name+'.svg'))
        plt.close(fig)

    def embed(self, name, alt):
        encoded = base64.b64encode((self.out/(name+'.png')).read_bytes()).decode()
        return f'<figure><img alt="{esc(alt)}" src="data:image/png;base64,{encoded}"><figcaption>{taglink(name+".png","PNG")} · {taglink(name+".svg","SVG")}</figcaption></figure>'

    def matrix(self, metric):
        topics = self.config['topics']
        fig,ax = plt.subplots(figsize=(16,5.4+.48*len(topics)))
        fig.subplots_adjust(left=.275,right=.97,top=.88,bottom=.205)
        title = 'Elapsed time' if metric=='wall' else 'Total CPU time (user + system)'
        fig.text(.035,.957,title,fontsize=23,weight='bold')
        modes=sorted({r['output_mode'] for t in topics for r in self.rows(t.get('primary')).values()})
        fig.text(.035,.923,self.config['campaign']+' · one declared variant per topic · same-file pairs · output: '+', '.join(modes),fontsize=11,color=MUTED)
        colors = np.full((len(topics),8,4),[.94,.95,.96,1.])
        cmap = plt.get_cmap('RdBu_r'); norm = TwoSlopeNorm(vmin=-15,vcenter=0,vmax=15)
        for i,t in enumerate(topics):
            rows = self.rows(t.get('primary'))
            for j,case in enumerate(CASES):
                r = rows.get(case)
                if not r:
                    ax.text(j,i,'—',ha='center',va='center',color=MUTED,fontsize=13)
                    continue
                d = r[metric]; unclear = d['ci95'][0]<=0<=d['ci95'][1]
                if not unclear:colors[i,j]=cmap(norm(np.clip(d['delta_pct'],-15,15)))
                ink = 'white' if np.mean(colors[i,j,:3])<.5 else INK
                ax.text(j,i-.13,f'{d["delta_pct"]:+.1f}%'+(' ·' if unclear else ''),ha='center',va='center',fontsize=11,weight='bold',color=ink)
                code = self.codes[r['file']]
                ax.text(j,i+.22,f'{code}/{r["label"]}',ha='center',va='center',fontsize=6.5,color=ink)
        ax.imshow(colors,aspect='auto',zorder=-1)
        ax.set_yticks(range(len(topics)),[f'{t["id"].upper()}  {t["title"]}' for t in topics],fontsize=10)
        ax.set_xticks(range(8),SHORT,fontsize=9)
        ax.tick_params(length=0,pad=10)
        ax.set_xticks(np.arange(-.5,8),minor=True);ax.set_yticks(np.arange(-.5,len(topics)),minor=True)
        ax.grid(which='minor',color='white',linewidth=2);ax.tick_params(which='minor',length=0)
        for sp in ax.spines.values():sp.set_visible(False)
        fig.text(.035,.133,'Blue = lower cost; red = higher cost. Gray + dot = 95% CI crosses zero. “—” = no completed declared comparison.',fontsize=10,color=MUTED)
        used = sorted({t['primary']['file'] for t in topics if t.get('primary')})
        key = '  ·  '.join(self.codes[f]+' = '+f for f in used)
        fig.text(.035,.103,'Cell sources in '+self.config['campaign']+':\n'+textwrap.fill(key,145),fontsize=8.5,color=MUTED,va='top',linespacing=1.6)
        fig.text(.035,.026,'Colors saturate at ±15%; full effects are labeled. Exact hashes / CIs are in the report. No multiple-comparison correction.',fontsize=9,color=MUTED)
        self.save(fig,metric+'-heatmap')

    def omnibus(self, ref=None, name='omnibus-comparison'):
        ref = ref or self.config.get('omnibus',{})
        rows = self.rows(ref) if ref.get('file') and ref.get('label') else {}
        if not rows:
            return '<p class="pending">The final combined comparison is pending. Topic deltas are not added together to predict it.</p>'
        cases = [c for c in CASES if c in rows]
        fig,axes = plt.subplots(1,3,figsize=(15,6.8),sharey=True)
        fig.subplots_adjust(left=.16,right=.96,top=.81,bottom=.15,wspace=.32)
        fig.text(.035,.95,ref.get('chart_title','The combined branch, measured against its paired baseline'),fontsize=21,weight='bold')
        ns = sorted({rows[c]['n'] for c in cases})
        modes='/'.join(sorted({r['output_mode'] for r in rows.values()}))
        fig.text(.035,.901,f'{ref["file"]} · {ref["baseline"]} → {ref["label"]} · {"/".join(map(str,ns))} pairs per case · {modes} output · control = 100',fontsize=11,color=MUTED)
        for ax,metric,title in zip(axes,['wall','cpu','rss'],['Elapsed time','Total CPU time','Peak RSS per link']):
            vals = [100+rows[c][metric]['delta_pct'] for c in cases]
            ax.axvline(100,color='#9cadb5',lw=1)
            for i,(case,value) in enumerate(zip(cases,vals)):
                d=rows[case][metric]
                color=MUTED if d['ci95'][0]<=0<=d['ci95'][1] else (TEAL if value<100 else RUST)
                ax.plot([100,value],[i,i],color=color,lw=2.5)
                ax.scatter([100],[i],color='#9cadb5',s=30,zorder=3)
                ax.errorbar(value,i,xerr=[[max(0,d['delta_pct']-d['ci95'][0])],[max(0,d['ci95'][1]-d['delta_pct'])]],fmt='o',color=color,ms=6,capsize=2,zorder=4)
                ax.text(max(value,100+d['ci95'][1],100)+1,i,f'{d["delta_pct"]:+.1f}%',va='center',fontsize=9)
            ends=[100+end for c in cases for end in rows[c][metric]['ci95']]
            ax.set_xlim(min(95,min(vals+ends))-5,max(105,max(vals+ends))+12)
            ax.set_title(title,loc='left',fontsize=13,weight='bold');ax.grid(axis='x',alpha=.15)
            ax.set_xlabel('Cost index');ax.spines['left'].set_visible(False)
            ax.set_yticks(range(len(cases)),[NAMES[c] for c in cases]);ax.tick_params(axis='y',length=0)
        axes[0].invert_yaxis()
        fig.text(.035,.044,'Control = 100. Whiskers: paired 95% intervals. Candidate is gray when its interval crosses zero change.',fontsize=10,color=MUTED)
        self.save(fig,name)
        return self.embed(name,'Combined branch elapsed time, CPU time, and peak RSS compared with paired control')+self.details_table(rows)+self.cpu_table(rows)+self.source_details(ref,rows)

    def kernel(self):
        data=read_json(ROOT/'results/h1-kernel-attribution.json')
        if not data:return '<p>Kernel attribution is pending.</p>'
        labels=['baseline','h1']; periods=data['total_cycle_period']; shares=data['shares_pct']
        fig,axes=plt.subplots(1,2,figsize=(14.5,6.9))
        fig.subplots_adjust(left=.08,right=.96,top=.79,bottom=.23,wspace=.34)
        fig.text(.035,.947,'H1: kernel contention in the earlier observed state',fontsize=22,weight='bold')
        fig.text(.035,.904,f'{data["recorded_links_per_binary"]} lld links per diagnostic recording · sampled cycles include user and kernel execution',fontsize=11,color=MUTED)
        x=np.arange(3)
        for k,label in enumerate(labels):
            vals=[periods[label]/1e9,periods[label]*shares[label]['spinlock']/100/1e9,periods[label]*shares[label]['merge_insert']/100/1e9]
            axes[0].bar(x+(k-.5)*.33,vals,width=.31,label=label,color=['#8095a4',TEAL][k])
            for a,b in zip(x+(k-.5)*.33,vals):axes[0].text(a,b+7,f'{b:.1f}',ha='center',fontsize=9)
        axes[0].set_xticks(x,['All cycles','Spinlock self','Merge insertion']);axes[0].set_ylabel('Approx. sampled cycle period, billions')
        axes[0].legend(frameon=False);axes[0].set_ylim(0,max(periods.values())/1e9*1.16)
        categories=[('advice_zap','Advice / page-table cleanup'),('fault_dirty_shared_page','Shared-write dirty fault'),('block_page_mkwrite','Filesystem write preparation')]
        for k,label in enumerate(labels):
            for i,(key,title) in enumerate(categories):
                v=shares[label][key];y=i+(k-.5)*.28
                if v is None:
                    axes[1].text(.5,y,f'<{data["missing_advice_limit_pct"]:g}% displayed threshold',va='center',fontsize=9,color=TEAL)
                else:
                    axes[1].barh(y,v,height=.26,color=['#8095a4',TEAL][k]);axes[1].text(v+.4,y,f'{v:.2f}%',va='center',fontsize=9)
        axes[1].set_yticks(range(3),[v for _,v in categories],fontsize=9);axes[1].invert_yaxis();axes[1].set_xlim(0,31)
        axes[1].set_xlabel('Spinlock-path samples, % of all cycle period')
        for ax in axes:ax.grid(axis='x' if ax==axes[1] else 'y',alpha=.15);ax.set_axisbelow(True)
        fig.text(.035,.12,'These path shares are portions of spinlock self samples, not additional costs to sum with the spinlock total.',fontsize=10,color=MUTED)
        fig.text(.035,.085,'Merge insertion rises from 3.78% to 4.65% of a smaller denominator, while its estimated cycle period remains 19.1 billion.',fontsize=10,color=MUTED)
        fig.text(.035,.05,'Sequential profiles explain mechanisms; only interleaved link measurements establish wall/CPU improvements.',fontsize=10,color=MUTED)
        self.save(fig,'kernel-attribution')
        return self.embed('kernel-attribution','Kernel spinlock caller paths and absolute sampled cycle-period comparison')+'''<p>Baseline hash workers call <code>madvise</code> in parallel. The sampled chain continues through page-table zapping, <code>folio_mark_dirty</code>, <code>ext4_dirty_folio</code>, and <code>block_dirty_folio</code> to the kernel spinlock. H1 batches that advice after hashing. Its remaining dominant lock samples come from shared output write faults. The missing advice branch is below the graph threshold, not proof of zero cleanup cost.</p><p>These recordings describe the earlier high-system-CPU filesystem state, not a universal property of reused outputs. Later reused-output campaigns entered a cheaper state too. The profiles are diagnostic evidence, not a paired speedup estimate. '''+taglink('../notes/h1-kernel-attribution.md','Full attribution and limitations')+'</p>'

    def phases(self, spec=None, stem='phase'):
        spec=spec or self.config.get('profiles',{})
        path=ROOT/spec.get('summary_file','profile-report/phase-summary.json')
        data=read_json(path,{})
        labels=spec.get('labels',['current','omnibus'])
        expected=self.raw.get(spec.get('file'),{}).get('args',{}).get('runs')
        cases=[case for case in CASES if all(data.get('cases',{}).get(case,{}).get(label,{}).get('n',0)>0 and (expected is None or data['cases'][case][label]['n']==expected) for label in labels)]
        if not cases:
            return '<p class="pending">High-resolution phase recordings are pending. They will explain where the final control and combined branch spend time; unprofiled paired links determine performance acceptance.</p>'
        categories=data['categories']
        colors={'merge':'#d4a548','copy':TEAL,'build_id':'#735c9d','gather':'#5b91b4','gc':'#bf7163','open_output':'#6b9270','input_cleanup':'#997f61','other':'#ced8dd'}
        phase_rows=[]
        production_ref=spec.get('production_comparison',self.config.get('omnibus'))
        production=self.rows(production_ref)
        for case in cases:
            for label in labels:
                row=data['cases'][case][label]
                if case in production:
                    expected_hash=production[case]['base_output_hash'] if label==production_ref['baseline'] else production[case]['output_hash']
                    if row.get('output_sha256')!=expected_hash:self.warnings.append(f'Profile output differs from production: {case}/{label}')
                total=row['window_ms']['mean']
                if not math.isclose(sum(row['phases'][c['id']]['mean_ms'] for c in categories),total,rel_tol=1e-5,abs_tol=1e-5):
                    self.warnings.append(f'Phase partition does not sum to window: {case}/{label}')
                phase_rows.append((case,label,row))
        fig,ax=plt.subplots(figsize=(14.5,10.2))
        fig.subplots_adjust(left=.22,right=.84,top=.85,bottom=.20)
        fig.text(.035,.96,'Where elapsed time goes',fontsize=23,weight='bold')
        fig.text(.035,.92,spec.get('stage','Instrumented control / candidate')+' · nonoverlapping foreground intervals · mean time shares',fontsize=11,color=MUTED)
        for i,(case,label,row) in enumerate(phase_rows):
            left=0
            for cat in categories:
                v=row['phases'][cat['id']]['mean_pct']
                ax.barh(i,v,left=left,color=colors.get(cat['id'],MUTED),height=.73)
                if v>=9:ax.text(left+v/2,i,f'{v:.0f}%',ha='center',va='center',fontsize=8,color=INK if cat['id'] in ('other','merge') else 'white')
                left+=v
            ax.text(102,i,f'{row["window_ms"]["mean"]:,.3f} ms',va='center',fontsize=9)
        ax.set_yticks(range(len(phase_rows)),[NAMES[c]+' · '+l for c,l,_ in phase_rows],fontsize=9)
        ax.invert_yaxis();ax.set_xlim(0,100);ax.set_xlabel('Mean per-run share of measured window (%)');ax.tick_params(axis='y',length=0)
        ax.spines['left'].set_visible(False)
        handles=[plt.Rectangle((0,0),1,1,color=colors.get(c['id'],MUTED)) for c in categories]
        fig.legend(handles,[c['label'] for c in categories],loc='lower center',bbox_to_anchor=(.5,.095),ncol=4,frameon=False,fontsize=9)
        fig.text(.035,.045,'Mean shares add to 100%; independent medians do not. Background GDB work and external residual are separate below.',fontsize=10,color=MUTED)
        self.save(fig,stem+'-shares')
        fig,axes=plt.subplots(math.ceil(len(cases)/2),2,figsize=(14.5,2.8*math.ceil(len(cases)/2)+1.8),squeeze=False)
        fig.subplots_adjust(left=.085,right=.97,top=.90,bottom=.13,hspace=.63,wspace=.24)
        fig.text(.035,.965,'The same phase partition in milliseconds',fontsize=22,weight='bold')
        fig.text(.035,.935,spec.get('stage','Instrumented control / candidate')+' · per-case scales · input-mapping cleanup included',fontsize=11,color=MUTED)
        for ax,case in zip(axes.flat,cases):
            for i,label in enumerate(labels):
                row=data['cases'][case][label];left=0
                for cat in categories:
                    value=row['phases'][cat['id']]['mean_ms']
                    ax.barh(i,value,left=left,color=colors.get(cat['id'],MUTED),height=.55)
                    left+=value
            ax.set_yticks(range(len(labels)),labels);ax.invert_yaxis();ax.set_title(NAMES[case],loc='left',weight='bold');ax.set_xlabel('Mean foreground window (ms)');ax.grid(axis='x',alpha=.13);ax.set_axisbelow(True)
            ax.spines['left'].set_visible(False);ax.tick_params(axis='y',length=0)
        for ax in list(axes.flat)[len(cases):]:ax.axis('off')
        fig.legend(handles,[c['label'] for c in categories],loc='lower center',bbox_to_anchor=(.5,.045),ncol=4,frameon=False,fontsize=9)
        self.save(fig,stem+'-ms')
        table=[];provenance=[];overlays=[];window_cpu=[]
        for case,label,row in phase_rows:
            for cat in categories:
                v=row['phases'][cat['id']]
                table.append([NAMES[case],label,str(row['n']),cat['label'],f'{v["mean_ms"]:.4f}',f'{v["mean_pct"]:.2f}%',f'{v["median_ms"]:.4f}',f'{v["p10_ms"]:.4f}–{v["p90_ms"]:.4f}'])
            provenance.append([NAMES[case],label,str(row.get('workers','')),str(row['n']),row.get('source_commit','UNKNOWN'),row.get('profile_commit','UNKNOWN'),row.get('profile_binary_sha256','UNKNOWN'),row.get('output_sha256','UNKNOWN')])
            gdb=row.get('background_gdb',{})
            overlays.append([NAMES[case],label,f'{row["window_ms"]["mean"]:.4f}',f'{gdb.get("union_ms",{}).get("mean",0):.4f}',f'{gdb.get("overlap_with_foreground_ms",{}).get("mean",0):.4f}',f'{row.get("external_residual_ms",{}).get("mean",0):.4f}'])
            window_cpu.append([NAMES[case],label,f'{row["window_ms"]["mean"]:.3f}',f'{row["window_process_user_ms"]["mean"]:.3f}',f'{row["window_process_system_ms"]["mean"]:.3f}'])
        definitions=''.join('<p><strong>'+esc(label)+':</strong> '+esc(data.get(key,'Not provided'))+'</p>' for key,label in [('window_definition','Window'),('merge_scope','Merge scope'),('copy_scope','Copy scope'),('precision','Precision'),('performance_warning','Measurement limits')])
        highlights=[]
        for case in ['lld','clang','ra']:
            if case in cases:
                p=data['cases'][case][labels[0]]['phases']
                highlights.append(f'{NAMES[case]}: merge {p["merge"]["mean_pct"]:.0f}%, copy/relocate {p["copy"]["mean_pct"]:.0f}%')
        lead='<p><strong>'+esc(spec.get('stage','Instrumented phase attribution'))+'.</strong> '+esc(spec.get('scope_note',''))+'</p>'
        if highlights:lead+='<p>In this stage’s control window, '+esc('; '.join(highlights))+'. These are elapsed-time shares, not CPU shares or speedup estimates.</p>'
        if spec.get('findings'):
            lead+='<p>'+taglink('../'+spec['findings'],'Per-case profile findings and limits')+'</p>'
        other_html=''
        if data.get('other_categories'):
            other_rows=[]
            for case,label,row in phase_rows:
                parts=[row['other_breakdown'][c['id']]['mean_ms'] for c in data['other_categories']]
                if not math.isclose(sum(parts),row['phases']['other']['mean_ms'],rel_tol=1e-5,abs_tol=1e-5):self.warnings.append(f'Other partition does not sum: {case}/{label}')
                other_rows.append([NAMES[case],label]+[f'{v:.3f}' for v in parts]+[f'{row["phases"]["other"]["mean_ms"]:.3f}'])
            headers=['Case','Variant']+[c['label']+' (ms)' for c in data['other_categories']]+['Other total (ms)']
            other_html='<h3>What is inside Other?</h3><p>For the large cases, the gray remainder is mostly input/symbol resolution, output assembly/layout, and relocation scanning. The table below partitions only Other; these mean milliseconds are already included in the full chart.</p>'+self.table(headers,[r for r in other_rows if r[1]==labels[0]])+'<details><summary>Other breakdown for both variants</summary><p>'+esc(data.get('other_accounting',''))+'</p>'+self.table(headers,other_rows)+'</details>'
        return lead+self.embed(stem+'-shares','Measured foreground phase shares across eight workloads')+other_html+'<details><summary>Absolute phase time for every case</summary>'+self.embed(stem+'-ms','Absolute elapsed milliseconds by foreground phase for each workload')+'</details>'+'''<p>Each instant in the foreground window belongs to the most specific selected interval. Build-ID work is removed from its enclosing copy interval. Merge covers preparation, splitting, sizing, and insertion; later merged layout remains in Other. GDB background intervals are overlays, so they are not added to the foreground stack. Its reported overlap covers named phases, excluding Other. The external residual covers startup, trace rendering, and exit outside the measured window; it is not a production-overhead estimate. Instrumentation and separate run conditions mean these charts explain costs rather than establish speedups.</p><p>Timer CPU deltas count whole-process work during possibly overlapping intervals. They cannot assign exclusive CPU cost to phases and are not stacked. The paired unprofiled results above report total CPU; the kernel chart uses an explicitly different sample-period denominator.</p>'''+taglink('../'+spec['summary_file'],'Full phase summary and definitions')+' · '+taglink('../results/'+spec['file'],'Raw profile runs')+' · '+taglink('../profile-report/README.md','Profiling method')+'<details><summary>Observed whole-window user and system CPU by case</summary><p>These means describe the complete profile window. Each case can occupy a different cost state; a high-system-CPU Clang observation does not classify every workload in the session.</p>'+self.table(['Case','Variant','Mean window ms','Mean process user CPU ms','Mean process system CPU ms'],window_cpu)+'</details><details><summary>Exact phase scopes and measurement limits</summary>'+definitions+'</details><details><summary>Phase hard data · means, medians, and run spread</summary>'+self.table(['Case','Variant','Profiles','Phase','Mean ms','Mean share','Median ms','p10–p90 ms (run spread)'],table)+'</details><details><summary>Background overlays and external residual</summary>'+self.table(['Case','Variant','Mean window ms','Mean GDB union ms','Mean GDB / named-phase overlap ms','Mean external residual ms'],overlays)+'</details><details><summary>Exact profiling provenance</summary>'+self.table(['Case','Variant','Workers','Profiles','Production source','Profile source','Profile binary SHA256','Last output SHA256'],provenance)+'</details>'

    def cpu_composition(self):
        rows=self.rows(self.config.get('omnibus'))
        if not rows:return ''
        fig,ax=plt.subplots(figsize=(13.5,9.4))
        fig.subplots_adjust(left=.22,right=.82,top=.84,bottom=.17)
        fig.text(.035,.955,'User work and kernel work',fontsize=23,weight='bold')
        fig.text(.035,.912,self.config['omnibus']['file']+' · mean per-link CPU composition · total CPU at right',fontsize=11,color=MUTED)
        labels=[];i=0
        for case in CASES:
            if case not in rows:continue
            row=rows[case]
            for key,label in [('baseline',row['baseline_label']),('candidate',row['label'])]:
                cpu=row['cpu_mean'][key];total=cpu['user']+cpu['system'];share=100*cpu['user']/total
                ax.barh(i,share,color='#5b91b4',height=.73);ax.barh(i,100-share,left=share,color='#9b6a8e',height=.73)
                if share>=12:ax.text(share/2,i,f'{share:.0f}%',ha='center',va='center',fontsize=9,color='white')
                if 100-share>=12:ax.text((share+100)/2,i,f'{100-share:.0f}%',ha='center',va='center',fontsize=9,color='white')
                ax.text(102,i,f'{total*1000:,.2f} ms',va='center',fontsize=9)
                labels.append(NAMES[case]+' · '+label);i+=1
        ax.set_yticks(range(i),labels,fontsize=9);ax.invert_yaxis();ax.set_xlim(0,100);ax.set_xlabel('Share of mean per-link CPU (%)');ax.tick_params(axis='y',length=0);ax.spines['left'].set_visible(False)
        fig.legend([plt.Rectangle((0,0),1,1,color=c) for c in ['#5b91b4','#9b6a8e']],['User CPU','System CPU'],loc='lower center',bbox_to_anchor=(.5,.06),ncol=2,frameon=False)
        fig.text(.035,.035,'Means make the composition additive. Headline performance deltas remain paired ratios of medians.',fontsize=10,color=MUTED)
        self.save(fig,'cpu-composition')
        return '<details><summary>Whole-process user / system CPU composition</summary>'+self.embed('cpu-composition','Mean user and system CPU composition of the final paired comparison')+'</details>'

    def state_checks(self):
        refs=self.config.get('state_checks',[])
        if not refs:return ''
        cells=[];details='';identities=[]
        for ref in refs:
            rows=self.rows(ref);r=rows.get('clang')
            if not r:continue
            delta=lambda k:f'{r[k]["delta_pct"]:+.2f}% [{r[k]["ci95"][0]:+.2f}, {r[k]["ci95"][1]:+.2f}]'
            absolute=lambda k:f'{r[k]["baseline"]*1000:,.2f} → {r[k]["candidate"]*1000:,.2f}'
            cells.append([ref['title'],str(r['n']),absolute('wall'),delta('wall'),absolute('cpu'),delta('cpu')])
            if ref.get('same_pair'):identities.append((r['base_binary'],r['binary']))
            details+='<details><summary>'+esc(ref['title'])+' · exact evidence</summary>'+self.source_details(ref,rows)+self.details_table(rows)+self.cpu_table(rows)+'</details>'
        if len(set(identities))>1:self.warnings.append('State comparisons declared same_pair have different binary identities')
        if not cells:return ''
        figure=''
        paired=[(ref,self.rows(ref).get('clang')) for ref in refs if ref.get('same_pair')]
        if len(paired)==2 and all(row for _,row in paired):
            fig,axes=plt.subplots(1,2,figsize=(14.5,5.3))
            fig.subplots_adjust(left=.10,right=.95,top=.72,bottom=.23,wspace=.30)
            fig.text(.035,.94,'Clang: keep both observed states visible',fontsize=23,weight='bold')
            fig.text(.035,.875,'Same immutable control and combined binaries · separate paired campaigns · reused output',fontsize=11,color=MUTED)
            maximum=max(r['wall'][k]*1000 for _,r in paired for k in ('baseline','candidate'))*1.21
            for ax,(ref,row) in zip(axes,paired):
                values=[row['wall'][k]*1000 for k in ('baseline','candidate')]
                d=row['wall'];color=MUTED if d['ci95'][0]<=0<=d['ci95'][1] else (TEAL if d['delta_pct']<0 else RUST)
                ax.barh([0,1],values,color=['#8095a4',color],height=.55)
                for i,value in enumerate(values):ax.text(value+3,i,f'{value:.2f} ms',va='center',fontsize=10)
                ax.set_yticks([0,1],['Control','P1 + H1']);ax.invert_yaxis();ax.set_xlim(0,maximum);ax.set_xlabel('Median elapsed time (ms)');ax.grid(axis='x',alpha=.13);ax.set_axisbelow(True);ax.spines['left'].set_visible(False);ax.tick_params(axis='y',length=0)
                ax.set_title(f'{row["n"]} pairs · {d["delta_pct"]:+.2f}% [{d["ci95"][0]:+.2f}, {d["ci95"][1]:+.2f}]',loc='left',weight='bold',fontsize=11)
                ax.text(0,-.32,ref['file'],transform=ax.transAxes,fontsize=9,color=MUTED)
            fig.text(.035,.045,'Intervals are paired 95% estimates within each campaign. The later gain does not erase the primary slowdown.',fontsize=10,color=MUTED)
            self.save(fig,'clang-state-comparison');figure=self.embed('clang-state-comparison','Clang slowdown and later improvement, each against its own paired control')
        return '<h3>Clang: the same binaries in different observed states</h3><p class="notice">The primary 50-pair comparison shows a small slowdown. A later 80-pair repeat found a much more expensive control state and a substantial combined-branch gain. Both results remain valid for their observed conditions; the repeat does not erase the regression. Each row below compares only paired runs in its own campaign. No speedup is calculated between campaigns.</p>'+figure+self.table(['Observed state / comparison','Pairs','Wall ms, control → variant','Wall Δ [95% CI]','CPU ms, control → variant','CPU Δ [95% CI]'],cells)+'<p>P1 alone does not account for the later gain. The same-campaign combined-versus-P1 comparison isolates H1’s contribution in that observed state. This supports retaining H1 as a conditional experiment, with a small-regression tradeoff visible in the primary campaign.</p>'+details

    def s1(self):
        spec=self.config.get('s1',{});file=spec.get('file');data=self.raw.get(file,{})
        labels=sorted({label for variants in data.get('cases',{}).values() for label in variants if label.startswith('s1-') and label!=spec.get('baseline','baseline')})
        refs=[{'file':file,'label':label,'baseline':spec.get('baseline','baseline')} for label in labels]
        allrows={ref['label']:self.rows(ref) for ref in refs}
        cases=[c for c in CASES if any(c in r for r in allrows.values())]
        if not cases:return '<p class="pending">The phase-cap sweep is pending. It will be shown as a CPU/latency tradeoff, without selecting the best noisy cell.</p>'
        fig,axes=plt.subplots(math.ceil(len(cases)/2),2,figsize=(14,3.8*math.ceil(len(cases)/2)+1.3),squeeze=False)
        fig.subplots_adjust(left=.085,right=.96,top=.85,bottom=.12,hspace=.4,wspace=.25)
        fig.text(.035,.963,'Phase caps: elapsed time versus CPU use',fontsize=22,weight='bold')
        fig.text(.035,.927,f'{file} · paired against {spec.get("baseline","baseline")} in the same sweep',fontsize=11,color=MUTED)
        palette={'copy':TEAL,'merge':RUST,'gc':'#886caa'}
        for ax,case in zip(axes.flat,cases):
            ax.axhline(0,color='#aab9c1',lw=.8);ax.axvline(0,color='#aab9c1',lw=.8)
            ax.scatter([0],[0],marker='x',s=80,color=INK,zorder=5)
            for label,rows in allrows.items():
                if case not in rows:continue
                row=rows[case];mode=row['env'].get('MOLD_PHASE_BUDGET',label.removeprefix('s1-'))
                phase=mode.split(':')[0].rstrip('0123456789');color=palette.get(phase,'#7892a4')
                x,y=row['wall']['delta_pct'],row['cpu']['delta_pct']
                ax.errorbar(x,y,xerr=[[max(0,x-row['wall']['ci95'][0])],[max(0,row['wall']['ci95'][1]-x)]],yerr=[[max(0,y-row['cpu']['ci95'][0])],[max(0,row['cpu']['ci95'][1]-y)]],fmt='o',color=color,alpha=.8,ms=5,capsize=2)
                offsets={'control':(7,0),'gc:16':(7,13),'gc:8':(7,-13),'copy:16':(-50,9),'copy:8':(7,8),'merge:16':(7,-13),'merge:8':(7,8)}
                inactive=row.get('phase_cap',{}).get('active') is False
                ax.annotate(mode+(' inactive' if inactive else ''),(x,y),xytext=offsets.get(mode,(7,7)),textcoords='offset points',fontsize=8,color=color)
            ax.set_title(NAMES[case],loc='left',weight='bold');ax.set_xlabel('Elapsed-time change (%)');ax.set_ylabel('Total CPU change (%)');ax.grid(alpha=.13)
        for ax in list(axes.flat)[len(cases):]:ax.axis('off')
        fig.text(.035,.044,'Lower left saves both. Lower right saves CPU at a latency cost. Error bars: paired 95% intervals; pool startup remains included.',fontsize=10,color=MUTED)
        self.save(fig,'s1-tradeoff')
        detail=''.join(f'<details><summary>{esc(label)} · {esc(file)}</summary>{self.details_table(rows)}</details>' for label,rows in allrows.items())
        return self.embed('s1-tradeoff','Phase concurrency cap wall-time versus CPU-time tradeoff')+'''<p>The cap applies to one foreground phase, not the whole process. Background tasks may still use the normal pool. These are not throughput measurements. Separate instrumentation observed 1, 2, and 12 normal workers for C hello, Rust hello, and TableGen; the five larger cases use 32. Thus both proposed caps are inactive for the tiny cases, and cap 16 is inactive for TableGen. Effective caps are inferred from those observations and wrapper semantics, not counted during timings.</p>'''+taglink('../topics/s2-assignment-counts/counts.json','Observed default worker counts')+detail

    def details_table(self, rows):
        if not rows:return '<p class="pending">No complete paired group available for this declared comparison.</p>'
        cells=[]
        for case in CASES:
            if case not in rows:continue
            r=rows[case];d=lambda k:f'{r[k]["delta_pct"]:+.2f}% [{r[k]["ci95"][0]:+.2f}, {r[k]["ci95"][1]:+.2f}]'
            med=lambda k,scale:f'{r[k]["baseline"]*scale:,.2f} → {r[k]["candidate"]*scale:,.2f}'
            name=NAMES[case]
            if r.get('phase_cap',{}).get('active') is False:name+=' (cap inactive)'
            cells.append([name,r['output_mode'],str(r['n']),med('wall',1000),d('wall'),med('cpu',1000),d('cpu'),med('rss',1/1024),d('rss'),'match' if r['hash_match'] else 'MISMATCH'])
        return self.table(['Case','Output mode','Pairs','Wall ms, base → variant','Wall Δ [95% CI]','CPU ms, base → variant','CPU Δ [95% CI]','Peak RSS MiB, base → variant','RSS Δ [95% CI]','Last output hash'],cells)

    def cpu_table(self, rows):
        values=[[NAMES[c],f'{r["user"]["baseline"]:.3f} → {r["user"]["candidate"]:.3f}',f'{r["system"]["baseline"]:.3f} → {r["system"]["candidate"]:.3f}'] for c,r in rows.items()]
        return '<details><summary>User and system CPU separately</summary><p>Each column is a separately computed median. They need not add to the median total CPU above.</p>'+self.table(['Case','User CPU seconds','System CPU seconds'],values)+'</details>'

    @staticmethod
    def table(headers,rows):
        return '<div class="table-wrap"><table><thead><tr>'+''.join('<th>'+esc(h)+'</th>' for h in headers)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+esc(c)+'</td>' for c in row)+'</tr>' for row in rows)+'</tbody></table></div>'

    def source_details(self, ref, rows):
        if not ref:return '<p>No primary variant selected.</p>'
        lines=[f'<p><strong>{esc(self.config["campaign"])} / {esc(ref["file"])} / {esc(ref["label"])}</strong> · '+taglink('../results/'+ref['file'],'raw results')+'</p>']
        provenance=[];seen=set()
        for r in rows.values():
            key=(r['binary'],r['base_binary'],json.dumps(r['env'],sort_keys=True),r['ci_source'])
            if key in seen:continue
            seen.add(key)
            provenance.append(['variant: '+r['label'],r['binary'],r['source'],r['lineage'],r['anchor'],json.dumps(r['env'],sort_keys=True)])
            provenance.append(['control: '+r['baseline_label'],r['base_binary'],r['base_source'],r['base_lineage'],r['base_anchor'],'same result file'])
            lines.append('<p class="meta">CI source: '+esc(r['ci_source'])+' · affinity '+esc(r['cpus'])+' · output mode: '+esc(r['output_mode'])+'</p>')
        if provenance:lines.append(self.table(['Role','Binary SHA256','Source commit','Lineage','Base anchor','Environment'],provenance))
        return ''.join(lines)

    def heatmap_table(self, metric):
        result='<div class="table-wrap"><table class="matrix-table"><thead><tr><th>Declared variant</th>'+''.join('<th>'+esc(NAMES[c])+'</th>' for c in CASES)+'</tr></thead><tbody>'
        for t in self.config['topics']:
            ref=t.get('primary');rows=self.rows(ref);result+=f'<tr><th>{esc(t["id"].upper())}<br><small>{esc(t["status"])}</small></th>'
            for case in CASES:
                r=rows.get(case)
                if not r:result+='<td class="neutral">—</td>';continue
                d=r[metric];unclear=d['ci95'][0]<=0<=d['ci95'][1];cls='neutral' if unclear else ('gain' if d['delta_pct']<0 else 'loss')
                source=f'{self.config["campaign"]}/{r["file"]}/{r["label"]} (output {r["output_mode"]})'
                title=f'{source}; {r["n"]} paired rounds; 95% CI [{d["ci95"][0]:+.2f}, {d["ci95"][1]:+.2f}]; binary {r["binary"]}; source {r["source"]}'
                result+=f'<td class="{cls}" title="{esc(title)}"><a href="#topic-{esc(t["id"])}">{d["delta_pct"]:+.1f}%'+(' ·' if unclear else '')+f'<small>{esc(self.codes[r["file"]]+"/"+r["label"])}</small></a></td>'
            result+='</tr>'
        return result+'</tbody></table></div>'

    def run(self):
        self.matrix('wall');self.matrix('cpu')
        omnibus=self.state_checks()+self.omnibus()+self.cpu_composition();kernel=self.kernel();s1=self.s1()
        for i,ref in enumerate(self.config.get('omnibus_confirmations',[])):
            omnibus+='<h3>'+esc(ref.get('title',ref['file']))+'</h3>'+self.omnibus(ref,'omnibus-confirmation-'+str(i+1))
        count=len(self.config['topics'])
        control=self.config.get('final_control',{})
        baseline_note='<p>The individual topic experiments use frozen source <code>'+esc(self.config['baseline_commit'])+'</code>. '
        if control:
            baseline_note+='The final combined comparison instead uses <code>'+esc(control.get('label','current'))+'</code> at <code>'+esc(control['commit'])+'</code>, rebased onto upstream <code>'+esc(control['upstream_commit'])+'</code>. Its candidate is <code>'+esc(self.config['omnibus']['commit'])+'</code>. These lineages are not interchangeable.'
        baseline_note+='</p>'
        review=self.config.get('review_head')
        if review:baseline_note+='<p class="meta">Candidate code revision: <code>'+esc(review['commit'])+'</code> on <code>'+esc(review['branch'])+'</code>. '+esc(review['change'])+'</p>'
        validation=self.config.get('validation')
        validation_note=''
        if validation:
            validation_note='<p><strong>Validation:</strong> '+esc(validation['summary'])+'</p>'
            if validation.get('limits'):validation_note+='<p class="meta">'+esc(validation['limits'])+'</p>'
            validation_note+='<p>'+ ' · '.join(taglink('../'+link['path'],link['label']) for link in validation.get('links',[]))+'</p>'
        for earlier in self.config.get('validation_history',[]):
            validation_note+='<details><summary>'+esc(earlier['title'])+'</summary><p>'+esc(earlier['summary'])+'</p><p class="meta">'+esc(earlier.get('limits',''))+'</p><p>'+' · '.join(taglink('../'+link['path'],link['label']) for link in earlier.get('links',[]))+'</p></details>'
        phases=self.phases()
        for i,earlier in enumerate(self.config.get('profile_history',[])):
            phases+='<details><summary>'+esc(earlier['stage'])+'</summary>'+self.phases(earlier,'phase-history-'+str(i+1))+'</details>'
        detail=''
        for t in self.config['topics']:
            ref=t.get('primary');rows=self.rows(ref)
            evidence=f'../notes/{t["id"]}.md' if (ROOT/f'notes/{t["id"]}.md').exists() else f'../topics/{t["id"]}.md'
            detail+=f'<section id="topic-{esc(t["id"])}" class="topic"><h3>{esc(t["id"].upper()+" · "+t["title"])}</h3><p><span class="badge">{esc(t["status"])}</span> · {taglink(evidence,"Investigation / validation notes")}</p>'
            detail+='<details><summary>Declared primary comparison and provenance</summary>'+self.source_details(ref,rows)+self.details_table(rows)+self.cpu_table(rows)+'</details>'
            for group,refs in [('Confirmation',t.get('confirmations',[])),('Earlier revision',t.get('revisions',[]))]:
                for previous in refs:
                    rr=self.rows(previous)
                    detail+='<details><summary>'+esc(group+' · '+previous.get('title',previous['label'])+' · '+previous['file'])+'</summary>'
                    if previous.get('status'):detail+='<p>'+esc(previous['status'])+'</p>'
                    detail+=self.source_details(previous,rr)+self.details_table(rr)+self.cpu_table(rr)+'</details>'
            detail+='</section>'
        sourcekey=self.table(['Key','Campaign','Result file'],[[code,self.config['campaign'],filename] for filename,code in self.codes.items()])
        warnings=''.join('<li>'+esc(w)+'</li>' for w in sorted(set(self.warnings)))
        metadata=read_json(ROOT/'report-data/export-metadata.json',{})
        group_counts={'unprofiled':0,'profiled':0}
        for data in self.raw.values():
            for variants in data.get('cases',{}).values():
                for row in variants.values():
                    if row.get('binary_sha256') and row.get('sha256') and len(row.get('samples',[]))==data.get('args',{}).get('runs'):
                        group_counts['profiled' if data.get('args',{}).get('perf') or row.get('profiles') else 'unprofiled']+=1
        campaign_evidence=''
        if metadata:
            campaign_evidence=f'<p>The complete campaign export retains {metadata["summary_rows"]:,} case/variant groups: {metadata["completed_unprofiled_samples"]:,} production link samples and {metadata["completed_profiled_samples"]:,} instrumented samples. Hash coverage is {group_counts["unprofiled"]:,} final production-group outputs and {group_counts["profiled"]:,} final profile-group outputs, rather than every individual link.</p>'
        body=f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{esc(self.config['title'])}</title><style>
:root{{--ink:{INK};--muted:{MUTED};--teal:{TEAL};--paper:{PAPER}}}*{{box-sizing:border-box}}body{{margin:0;background:#edf2f4;color:var(--ink);font:16px/1.6 system-ui,-apple-system,sans-serif}}main{{max-width:1360px;margin:auto;background:var(--paper);padding:50px 52px 80px}}header{{border-bottom:2px solid #d5e1e6;padding-bottom:30px}}.eyebrow{{text-transform:uppercase;font-size:12px;letter-spacing:.13em;color:var(--teal);font-weight:750}}h1{{font-size:42px;line-height:1.13;max-width:900px;letter-spacing:-.025em;margin:12px 0 20px}}h2{{font-size:28px;margin:46px 0 14px;line-height:1.2}}h3{{font-size:20px;margin:25px 0 8px}}p{{max-width:1040px}}.lede{{font-size:20px;color:var(--muted)}}.meta,small{{font-size:12px;color:var(--muted)}}nav{{display:flex;gap:18px;flex-wrap:wrap;margin-top:24px}}a{{color:#087c81;text-decoration-thickness:1px;text-underline-offset:3px}}.badge{{padding:4px 9px;border-radius:4px;background:#e4eef0;font-size:12px;font-weight:650}}.notice,.pending{{padding:17px 20px;background:#eaf0f3;border-left:4px solid #86a1b0}}figure{{margin:22px 0}}img{{width:100%;height:auto;display:block}}figcaption{{font-size:12px;text-align:right;color:var(--muted)}}.table-wrap{{overflow:auto;margin:18px 0}}table{{border-collapse:collapse;width:100%;font-size:12px;font-variant-numeric:tabular-nums}}th,td{{text-align:left;border-bottom:1px solid #dbe5e9;padding:10px 11px;vertical-align:top}}th{{background:#edf3f5;color:#315165;font-weight:650}}td{{white-space:nowrap}}.topic td:nth-child(2),.topic td:nth-child(3){{overflow-wrap:anywhere}}.topic details table td{{max-width:450px}}.matrix-table td,.matrix-table th{{text-align:center}}.matrix-table td a{{display:block;color:inherit;text-decoration:none}}.matrix-table td small{{display:block;font-size:10px;color:inherit}}.matrix-table .neutral{{background:#edf0f2}}.matrix-table .gain{{background:#d8eeee}}.matrix-table .loss{{background:#f2dfd7}}details{{border:1px solid #dbe5e9;border-radius:6px;padding:13px 17px;margin:12px 0}}summary{{cursor:pointer;font-weight:620}}.topic{{padding-top:12px;border-top:1px solid #dbe5e9;margin-top:18px}}code{{font-size:.9em;background:#eaf0f2;padding:2px 4px}}footer{{margin-top:40px;font-size:12px;color:var(--muted)}}@media(max-width:760px){{main{{padding:28px 18px}}h1{{font-size:32px}}h2{{font-size:24px}}.lede{{font-size:18px}}}}@media print{{main{{padding:0}}details{{break-inside:avoid}}nav{{display:none}}}}
</style><main><header><div class="eyebrow">Measured on wx-workstation · {esc(self.config['campaign'])}</div><h1>{esc(self.config['title'])}</h1><p class="lede">{esc(self.config['subtitle'])}</p><p>{esc(self.config.get('overview',''))}</p><p class="notice">{esc(self.config.get('output_mode_note',''))}</p><span class="badge">{esc(self.config.get('selection_status','Review pending'))}</span><nav><a href="#combined">Combined result</a><a href="#topics">{count} topics</a><a href="#phases">Phase profiles</a><a href="#caps">Concurrency tradeoff</a><a href="#kernel">Kernel explanation</a><a href="#evidence">Hard data</a><a href="#method">Method</a></nav></header>
<section id="combined"><h2>The combined branch</h2>{baseline_note}{validation_note}{omnibus}</section>
<section id="topics"><h2>What each topic achieved</h2><p>Negative deltas mean less cost. Each row uses one explicitly declared variant for every case and both metrics. Confirmations and earlier revisions remain separate below. A gray cell with a dot has a 95% confidence interval crossing zero; it is not evidence of a reliable win.</p><p class="notice">Absolute host regimes changed between campaigns. Every delta compares a candidate with its baseline from the same result file, output-file mode, and paired round. Do not compare absolute medians across files or add topic gains to predict the combined branch.</p>{self.embed('wall-heatmap',f'{count}-topic by eight-workload elapsed-time delta heatmap')}{self.embed('cpu-heatmap',f'{count}-topic by eight-workload total-CPU delta heatmap')}<details><summary>Accessible elapsed-time matrix · hover for exact provenance</summary>{self.heatmap_table('wall')}</details><details><summary>Accessible CPU matrix · hover for exact provenance</summary>{self.heatmap_table('cpu')}</details><details><summary>Source key for every matrix cell</summary>{sourcekey}</details></section>
<section id="phases"><h2>Where the link spends time</h2>{phases}</section>
<section id="caps"><h2>The cost of capping one phase</h2>{s1}</section>
<section id="kernel"><h2>Where the kernel time went</h2>{kernel}</section>
<section id="evidence"><h2>Hard data and retained revisions</h2>{campaign_evidence}<p>Tables show baseline → candidate medians. CPU is user + system time for each link before taking the median. RSS is each link process’s peak resident memory, summarized across runs. Output-hash checks cover the last measured link in each case/label group, not every timed output.</p><p>{taglink('../report-data/all-case-summary.csv','All case summaries (CSV)')} · {taglink('../report-data/all-samples.csv','Every raw sample (CSV)')} · {taglink('../report-data/provenance.json','Frozen binary → source mapping')} · {taglink('../report-data/README.md','Evidence definitions')} · {taglink('../report-config.json','Declared report selections')}</p>{detail}</section>
<section id="method"><h2>How to read these results</h2><p>Screen and confirmation counts come from the raw data (24-link screens, 32-link final screens, and 50-link confirmations where present). Only completed, unprofiled groups with matching round IDs and recorded binary/output digests enter the comparisons. Three warmup rounds are discarded. Point estimates are ratios of sample medians. Intervals resample paired rounds 10,000 times; recorded summary intervals are used when available, otherwise a deterministic per-cell bootstrap is used. Intervals are exploratory and are not corrected for the many comparisons.</p><p>Link measurements use CPUs 32–63 on <code>ssh wx-workstation</code>. Builds, tests, and untimed counters hold a shared workstation gate; timing/profile runs hold it exclusively. Background host activity was recorded, and the unrelated GPU workload was left untouched. No host tuning, cache flushing, or interference with that workload is part of these results. Variants within a case write the same harness-owned output path. Reused-output campaigns retain that file between interleaved links. Fresh-output campaigns unlink that harness-owned file before each invocation, outside the stopwatch; inputs remain warm. Variant order rotates by round. These modes are reported separately and never pooled. </p>{baseline_note}<p>User CPU is work charged to userspace; system CPU is kernel work charged to the process. Total CPU is their per-link sum and can greatly exceed elapsed time when workers run concurrently. Phase timers, kernel samples, and instrumented counts are separate diagnostics; overlapping timers are not added to estimate end-to-end cost. A larger fraction of samples can reflect a smaller denominator rather than more absolute work.</p><p>Branch selection is explicit in the report configuration. A favorable isolated cell is insufficient: correctness, mechanism, repeatability, broader regressions, and combined-branch validation matter. Missing cases remain visible as missing; they are not filled from another campaign.</p>{'<ul>'+warnings+'</ul>' if warnings else ''}</section><footer>Rendered {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}. Static PNG/SVG figures are available beside this self-contained HTML report.</footer></main><script>document.querySelectorAll('.matrix-table a').forEach(a=>a.addEventListener('click',()=>{{const target=document.querySelector(a.getAttribute('href'));if(target)target.querySelectorAll('details').forEach(d=>d.open=true)}}));</script></html>'''
        (self.out/'report.html').write_text(body)
        snapshots=[]
        for key,rows in self.cache.items():snapshots.extend(rows.values())
        (self.out/'rendered-comparisons.json').write_text(json.dumps(snapshots,indent=2)+'\n')
        print(json.dumps({'report':str(self.out/'report.html'),'comparisons':len(snapshots),'warnings':sorted(set(self.warnings))},indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--config',type=Path,default=ROOT/'report-config.json')
    parser.add_argument('--out',type=Path,default=ROOT/'report')
    args=parser.parse_args()
    Report(read_json(args.config),args.out).run()
