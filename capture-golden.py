#!/usr/bin/env python3
import json
from pathlib import Path
from measure import CASES, command, run, digest
root=Path(__file__).resolve().parent
result={'binary_sha256':digest(root/'bin/base'),'sha256':{}}
for case in CASES:
    cmd,wd,out=command(str(root/'bin/base'),case,['--threads=32','--perf'],'32-63')
    sample,log=run(cmd,wd)
    result['sha256'][case]=digest(out)
    (root/'results'/f'baseline-{case}-perf.txt').write_text(log)
(root/'golden-hashes.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))
