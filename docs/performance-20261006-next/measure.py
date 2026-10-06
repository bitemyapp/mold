#!/usr/bin/env python3
"""Interleaved link timings and per-process resource usage; preserve raw samples."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import shlex
import statistics
import subprocess
import tempfile
import time

ROOT = Path('/home/callen/work/mold-bench/wl')
CASES = {'hello': ('hello/cur', []), 'rhello': ('rhello/cur', []),
         'tblgen': ('tblgen/cur', []), 'lld': ('lld/cur', []),
         'clang': ('clang.d', []), 'clang-s': ('clang.d', ['--strip-debug']),
         'ra': ('ra.d', []), 'ra-s': ('ra.d', ['--strip-debug'])}

def command(binary, case, extra, cpus):
    directory, flags = CASES[case]
    wd = ROOT / directory
    args = shlex.split((wd / 'response.txt').read_text())
    output = wd / args[args.index('-C') + 1] / 'codex-next.out'
    output.parent.mkdir(parents=True, exist_ok=True)
    cmd = ['taskset', '-c', cpus, binary, '@response.txt', '-o',
           'codex-next.out', '--no-fork'] + flags + extra
    return cmd, wd, output

def run(cmd, wd, env=None):
    with tempfile.TemporaryFile() as log:
        start = time.perf_counter()
        process = subprocess.Popen(cmd, cwd=wd, stdout=log, stderr=log, env=env)
        _, status, usage = os.wait4(process.pid, 0)
        wall = time.perf_counter() - start
        process.returncode = os.waitstatus_to_exitcode(status)
        log.seek(0)
        text = log.read().decode(errors='replace')
        if process.returncode:
            raise RuntimeError(text)
    return {'wall': wall, 'user': usage.ru_utime, 'sys': usage.ru_stime,
            'rss_kib': usage.ru_maxrss, 'voluntary_cs': usage.ru_nvcsw,
            'involuntary_cs': usage.ru_nivcsw, 'minor_faults': usage.ru_minflt,
            'major_faults': usage.ru_majflt}, text

def digest(path):
    with path.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()

def quantile(xs, q):
    return sorted(xs)[max(0, math.ceil(q * len(xs)) - 1)]

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--runs', type=int, default=20)
    p.add_argument('--cases', nargs='+', default=list(CASES))
    p.add_argument('--cpus', default='32-63')
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--perf', action='store_true')
    p.add_argument('--fresh-output', action='store_true',
                   help='Remove only this harness output before each link; input cache stays warm')
    p.add_argument('--label-env', type=Path, help='JSON mapping label to environment overrides')
    p.add_argument('bins', nargs='+', help='LABEL=PATH[,THREADS]')
    a = p.parse_args()
    envs = json.loads(a.label_env.read_text()) if a.label_env else {}
    result = {'args': vars(a) | {'output': str(a.output), 'label_env': str(a.label_env) if a.label_env else None}, 'cases': {}}
    a.output.parent.mkdir(parents=True, exist_ok=True)
    for case in a.cases:
        rows = result['cases'][case] = {}
        for i in range(a.runs + 3):
            order = a.bins[i % len(a.bins):] + a.bins[:i % len(a.bins)]
            for spec in order:
                label, value = spec.split('=', 1)
                binary, *threads = value.split(',')
                binary = str(Path(binary).resolve())
                extra = ['--threads=' + threads[0]] if threads else []
                if a.perf:
                    extra.append('--perf')
                cmd, wd, out = command(binary, case, extra, a.cpus)
                if a.fresh_output:
                    out.unlink(missing_ok=True)
                overrides = envs.get(label, {})
                sample, log = run(cmd, wd, os.environ | overrides)
                sample['round'] = i - 3
                sample['position'] = order.index(spec)
                if i >= 3:
                    row = rows.setdefault(label, {'command': cmd, 'cwd': str(wd), 'env': overrides, 'samples': []})
                    row['samples'].append(sample)
                    if a.perf:
                        row.setdefault('profiles', []).append(log)
                    if i == a.runs + 2:
                        row['sha256'] = digest(out)
                        row['bytes'] = out.stat().st_size
                        row['binary_sha256'] = digest(Path(binary))
                        expected = json.loads(Path(__file__).with_name('golden-hashes.json').read_text())['sha256'][case]
                        if row['sha256'] != expected:
                            raise RuntimeError(f'{case} {label}: output hash mismatch: {row["sha256"]} != {expected}')
                time.sleep(0.05)
        for label, row in rows.items():
            xs = [s['wall'] for s in row['samples']]
            row['summary'] = {'p50_ms': statistics.median(xs) * 1000,
                              'p95_ms': quantile(xs, .95) * 1000,
                              'p99_ms': quantile(xs, .99) * 1000,
                              'p999_ms': quantile(xs, .999) * 1000,
                              'max_ms': max(xs) * 1000,
                              'links_per_second': 1 / statistics.mean(xs),
                              'bytes_per_second': row['bytes'] / statistics.mean(xs),
                              'cpu_ms': statistics.median([s['user'] + s['sys'] for s in row['samples']]) * 1000,
                              'rss_mib': max(s['rss_kib'] for s in row['samples']) / 1024}
            print(case, label, json.dumps(row['summary']), flush=True)
        a.output.write_text(json.dumps(result, indent=2) + '\n')

if __name__ == '__main__':
    main()
