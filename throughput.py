#!/usr/bin/env python3
import argparse, json, os, subprocess, time, tempfile
from pathlib import Path
from measure import command, quantile

def batch(binary, case, jobs, total, cpus):
    running={}; samples=[]; paths=set(); started=time.perf_counter()
    with tempfile.TemporaryFile() as log:
        launched=0
        while launched < total or running:
            while launched < total and len(running)<jobs:
                slot=next(i for i in range(jobs) if i not in {v[1] for v in running.values()})
                cmd, wd, out=command(binary,case,['--threads=32'],cpus)
                outname=f'codex-rayon-batch-{slot}.out';cmd[cmd.index('-o')+1]=outname
                paths.add(out.with_name(outname))
                p=subprocess.Popen(cmd,cwd=wd,stdout=log,stderr=log)
                running[p.pid]=(p,slot);launched+=1
            pid,status,u=os.wait4(-1,0)
            p,_=running.pop(pid);p.returncode=os.waitstatus_to_exitcode(status)
            if p.returncode:
                log.seek(0); raise RuntimeError(log.read().decode(errors='replace'))
            samples.append({'user':u.ru_utime,'sys':u.ru_stime,'rss_kib':u.ru_maxrss})
        wall=time.perf_counter()-started
    for p in paths:p.unlink(missing_ok=True)
    return {'wall':wall,'links_per_second':total/wall,'user':sum(s['user'] for s in samples),'sys':sum(s['sys'] for s in samples),'max_child_rss_kib':max(s['rss_kib'] for s in samples)}

def main():
    p=argparse.ArgumentParser();p.add_argument('--runs',type=int,default=10);p.add_argument('--output',required=True);p.add_argument('--cpus',default='32-63');p.add_argument('bins',nargs='+');a=p.parse_args()
    result={'args':vars(a),'cases':{}}
    for case,jobs,total in [('hello',32,640),('clang-s',8,48)]:
        rows=result['cases'][case]={'jobs':jobs,'total':total,'variants':{}}
        for i in range(a.runs+1):
            order=a.bins[i%len(a.bins):]+a.bins[:i%len(a.bins)]
            for spec in order:
                label,binary=spec.split('=',1);sample=batch(binary,case,jobs,total,a.cpus)
                if i:
                    rows['variants'].setdefault(label,[]).append(sample)
                    Path(a.output).write_text(json.dumps(result,indent=2))
            print(case,i,'/'.join(f'{k}: {v[-1]["wall"]:.3f}s' for k,v in rows['variants'].items()),flush=True)
    Path(a.output).write_text(json.dumps(result,indent=2))
if __name__=='__main__':main()
