#!/usr/bin/env bash
set -euo pipefail
root=/home/callen/work/mold-next-20261006
name=$1
shift
cd "$root"
exec 9>/home/callen/work/mold-radical-20261006/workstation.lock
flock -x 9
{
 date -Is
 uptime
 free -h
 ps -eo pid,comm,pcpu,pmem --sort=-pcpu | head -15
} > "results/$name.host-before.txt"
vmstat -t 2 > "results/$name.vmstat.txt" &
monitor=$!
trap 'kill "$monitor" 2>/dev/null || true' EXIT
"$@" > "results/$name.log" 2>&1
{
 date -Is
 uptime
 free -h
 ps -eo pid,comm,pcpu,pmem --sort=-pcpu | head -15
} > "results/$name.host-after.txt"
printf 'Completed %s\n' "$name"
