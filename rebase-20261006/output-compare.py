#!/usr/bin/env python3
"""Compare rebased candidates with current upstream; no timing claims."""
import hashlib,json,shlex,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parent
CORPUS=Path('/home/callen/work/mold-bench/wl')
CASES={'hello':('hello/cur',[]),'rhello':('rhello/cur',[]),
       'tblgen':('tblgen/cur',[]),'lld':('lld/cur',[]),
       'clang':('clang.d',[]),'clang-s':('clang.d',['--strip-debug']),
       'ra':('ra.d',[]),'ra-s':('ra.d',['--strip-debug'])}
def digest(path):
    with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
result={'binary_sha256':{label:digest(ROOT/'bin'/label) for label in ['base','rayon-idle','rayon-startup']},'checks':[]}
for threads in [1,8,32]:
    for case,(directory,flags) in CASES.items():
        wd=CORPUS/directory
        args=shlex.split((wd/'response.txt').read_text())
        out=wd/args[args.index('-C')+1]/'codex-rayon-rebase.out'
        row={'case':case,'threads':threads,'sha256':{}}
        for label in ['base','rayon-idle','rayon-startup']:
            cmd=['taskset','-c','32-63',str(ROOT/'bin'/label),'@response.txt','-o','codex-rayon-rebase.out','--no-fork',f'--threads={threads}']+flags
            proc=subprocess.run(cmd,cwd=wd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
            assert proc.returncode==0,(cmd,proc.stdout)
            row['sha256'][label]=digest(out)
            row['bytes']=out.stat().st_size
        assert len(set(row['sha256'].values()))==1,row
        result['checks'].append(row)
        (ROOT/'output-comparison.json').write_text(json.dumps(result,indent=2)+'\n')
        print(case,threads,'byte-identical',flush=True)
print('All 24 workload/worker-count combinations match current upstream.')
