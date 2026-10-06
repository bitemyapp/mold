#!/usr/bin/env python3
"""Untimed explanatory allocation counters. No durations or resource samples."""
import argparse, hashlib, json, re, shlex, subprocess
from pathlib import Path
ROOT = Path('/home/callen/work/mold-bench/wl')
CASES = {'hello': ('hello/cur', []), 'rhello': ('rhello/cur', []),
         'tblgen': ('tblgen/cur', []), 'lld': ('lld/cur', []),
         'clang': ('clang.d', []), 'clang-s': ('clang.d', ['--strip-debug']),
         'ra': ('ra.d', []), 'ra-s': ('ra.d', ['--strip-debug'])}
p = argparse.ArgumentParser()
p.add_argument('--output', type=Path, required=True)
p.add_argument('--goldens', type=Path, required=True)
p.add_argument('binaries', nargs='+', help='label=/absolute/path')
a = p.parse_args()
a.output.mkdir(parents=True, exist_ok=True)
expected = json.loads(a.goldens.read_text())['sha256']
def digest(path):
    with Path(path).open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()
result = {'purpose': 'untimed measurement-only Vec allocation counters', 'threads': 8,
          'cpus': '0-7', 'runs_per_case_variant': 3, 'rows': []}
for case, (directory, flags) in CASES.items():
    wd = ROOT / directory
    args = shlex.split((wd / 'response.txt').read_text())
    outdir = wd / args[args.index('-C') + 1]
    for run in range(3):
        order = a.binaries[run % len(a.binaries):] + a.binaries[:run % len(a.binaries)]
        for spec in order:
            label, binary = spec.split('=', 1)
            name = f'codex-ms3-counts-{label}-{run}.out'
            cmd = ['taskset', '-c', '0-7', binary, '@response.txt', '-o', name,
                   '--no-fork', '--threads=8', '--stats'] + flags
            proc = subprocess.run(cmd, cwd=wd, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            log = a.output / f'{case}-{label}-{run}.log'
            log.write_text(proc.stdout)
            if proc.returncode:
                raise RuntimeError(f'{case}/{label} failed: {proc.stdout}')
            sha = digest(outdir / name)
            if sha != expected[case]:
                raise RuntimeError(f'{case}/{label}: golden mismatch {sha}')
            counters = {}
            for line in proc.stdout.splitlines():
                if 'ms3_vec_' in line:
                    match = re.search(r'(ms3_vec_\w+)\s*[:=]\s*([0-9,]+)', line)
                    if not match:
                        match = re.search(r'([0-9,]+)\s+(ms3_vec_\w+)', line)
                        if match:
                            counters[match[2]] = int(match[1].replace(',', ''))
                    else:
                        counters[match[1]] = int(match[2].replace(',', ''))
            if not counters and case not in ('hello', 'ra-s'):
                raise RuntimeError(f'no counters parsed; inspect {log}')
            result['rows'].append({'case': case, 'variant': label, 'run': run,
               'binary_sha256': digest(binary), 'output_sha256': sha, 'command': cmd,
               'cwd': str(wd), 'counters': counters, 'log': log.name})
            (outdir / name).unlink()
            (a.output / 'counts.json').write_text(json.dumps(result, indent=2) + '\n')
            print(case, label, run, counters, flush=True)
