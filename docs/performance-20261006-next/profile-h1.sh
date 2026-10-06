#!/usr/bin/env bash
set -euo pipefail
root=/home/callen/work/mold-next-20261006
for label in baseline h1; do
 docker run --rm -i --user 0 --cap-add PERFMON --cap-add SYSLOG --security-opt seccomp=unconfined \
 -v /usr:/host/usr:ro -v /lib:/host/lib:ro \
 -v "$root:$root" -v /home/callen/work/mold-bench/wl:/home/callen/work/mold-bench/wl \
 -w /home/callen/work/mold-bench/wl/lld/cur \
 mold-upstream-ci bash -s -- "$root" "$label" <<'INNER'
set -euo pipefail
root=$1
label=$2
perf() { /host/lib/x86_64-linux-gnu/ld-linux-x86-64.so.2 --library-path /host/lib/x86_64-linux-gnu /host/usr/lib/linux-tools/7.0.0-34-generic/perf "$@"; }
perf record -e cycles -F 999 --call-graph fp -o "$root/results/lld-$label-cycles.data" -- \
 taskset -c 32-63 bash -c 'for ((i=0;i<30;i++)); do "$1" @response.txt -o codex-next.out --no-fork || exit; done' bash "$root/bin/$label"
perf report --stdio --no-children --no-inline -g none --percent-limit 0 --field-separator '|' --sort symbol,dso \
 -i "$root/results/lld-$label-cycles.data" > "$root/results/lld-$label-cycles.txt"
chmod a+r "$root/results/lld-$label-cycles.data"
INNER
done
