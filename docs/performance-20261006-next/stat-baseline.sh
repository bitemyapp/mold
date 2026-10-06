#!/usr/bin/env bash
set -euo pipefail
root=/home/callen/work/mold-next-20261006
for spec in lld:lld/cur clang:clang.d ra:ra.d; do
 name=${spec%%:*}
 directory=${spec#*:}
 docker run --rm --user 0 --cap-add PERFMON --security-opt seccomp=unconfined \
 -v /usr:/host/usr:ro -v /lib:/host/lib:ro \
 -v "$root:$root" -v /home/callen/work/mold-bench/wl:/home/callen/work/mold-bench/wl \
 -w "/home/callen/work/mold-bench/wl/$directory" \
 mold-upstream-ci /host/lib/x86_64-linux-gnu/ld-linux-x86-64.so.2 \
 --library-path /host/lib/x86_64-linux-gnu /host/usr/lib/linux-tools/7.0.0-34-generic/perf \
 stat -r 10 -x, -e cycles:u,instructions:u,cache-references:u,cache-misses:u,cpu-migrations,context-switches \
 -o "$root/results/baseline-$name.stat.csv" -- \
 taskset -c 32-63 "$root/bin/baseline" @response.txt -o codex-next.out --no-fork
 done
