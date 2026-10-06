#!/usr/bin/env bash
set -euo pipefail
root=/home/callen/work/mold-next-20261006
exec 9>/home/callen/work/mold-radical-20261006/workstation.lock
flock -s 9
for label in baseline h1; do
 docker run --rm --user 0 --cap-add SYSLOG --cpuset-cpus=24-31 \
 -v /usr:/host/usr:ro -v /lib:/host/lib:ro -v "$root:$root" \
 mold-upstream-ci /host/lib/x86_64-linux-gnu/ld-linux-x86-64.so.2 \
 --library-path /host/lib/x86_64-linux-gnu /host/usr/lib/linux-tools/7.0.0-34-generic/perf \
 report --stdio --no-children --no-inline --symbol-filter native_queued_spin_lock_slowpath \
 --call-graph graph,0.5,caller --sort symbol,dso --field-separator '|' \
 -i "$root/results/lld-$label-cycles.data" > "$root/results/lld-$label-lock-callers.txt"
done
