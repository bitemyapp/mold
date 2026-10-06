#!/usr/bin/env python3
"""Untimed single-link statistics collection; never use for benchmarks."""
import hashlib,json,shlex,subprocess
from pathlib import Path
root=Path('/home/callen/work/mold-next-20261006')
wl=Path('/home/callen/work/mold-bench/wl')
result={'source_commit':'6789e6c53fa9a82e27bc8295d88f212575a030e0','purpose':'untimed eligibility/work counts; instrumentation changes execution cost','cases':{}}
expected=json.loads(Path('/home/callen/work/mold-radical-20261006/golden-hashes.json').read_text())['sha256']
cases={'hello':('hello/cur',[]),'rhello':('rhello/cur',[]),'tblgen':('tblgen/cur',[]),'lld':('lld/cur',[]),'clang':('clang.d',[]),'clang-s':('clang.d',['--strip-debug']),'ra':('ra.d',[]),'ra-s':('ra.d',['--strip-debug'])}
for case,(directory,flags) in cases.items():
 wd=wl/directory
 command=['taskset','-c','32-63',str(root/'bin/cr5'),'@response.txt','-o','codex-cr5-counts.out','--no-fork','--stats']+flags
 p=subprocess.run(command,cwd=wd,capture_output=True,text=True,check=True)
 log=p.stdout+p.stderr
 (root/f'logs/cr5-counts/{case}.log').write_text(log)
 counts={}
 for line in log.splitlines():
  if '=' not in line:continue
  name,value=line.split('=',1)
  if name.strip().startswith('copy_flat_'):counts[name.strip()]=counts.get(name.strip(),0)+int(value)
 args=shlex.split((wd/'response.txt').read_text())
 output=wd/args[args.index('-C')+1]/'codex-cr5-counts.out'
 with output.open('rb') as f: sha=hashlib.file_digest(f,'sha256').hexdigest()
 assert sha==expected[case],(case,sha,expected[case])
 result['cases'][case]={'command':command,'counts':counts,'output_sha256':sha,'golden_matches':True}
 print(case,json.dumps(counts),flush=True)
result['binary_sha256']=hashlib.file_digest((root/'bin/cr5').open('rb'),'sha256').hexdigest()
(root/'logs/cr5-counts/counts.json').write_text(json.dumps(result,indent=2)+'\n')
