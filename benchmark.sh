#!/usr/bin/env bash
set -euo pipefail
root=/home/callen/work/mold-rayon-20261006
exec 9>/home/callen/work/mold-radical-20261006/workstation.lock
flock -x 9
cd "$root"
{
 date -Is
 uname -a
 lscpu
 free -h
 df -h "$root"
 findmnt -T "$root"
 cat /sys/devices/system/cpu/cpu32/cpufreq/scaling_governor
 docker image inspect mold-upstream-ci --format '{{.Id}}'
 docker run --rm mold-upstream-ci bash -c 'rustc -Vv; cargo -V'
 ps -eo pid,pcpu,comm --sort=-pcpu | head -20
 sha256sum bin/*
} > results/fingerprint.txt
bins=(base="$root/bin/base" original-idle="$root/bin/original-idle" rayon-idle="$root/bin/rayon-idle" original-startup="$root/bin/original-startup" rayon-startup="$root/bin/rayon-startup")
python3 measure.py --runs 40 --output results/latency.json "${bins[@]/%/,32}" >results/latency.log
python3 measure.py --runs 5 --perf --cases hello clang-s ra --output results/phases.json "${bins[@]/%/,32}" >results/phases.log
python3 throughput.py --runs 10 --output results/throughput.json "${bins[@]}" >results/throughput.log
python3 measure.py --runs 20 --cases hello clang-s ra-s --output results/threads8.json "${bins[@]/%/,8}" >results/threads8.log
python3 measure.py --runs 20 --cases hello clang-s ra-s --output results/threads1.json "${bins[@]/%/,1}" >results/threads1.log
{
 date -Is
 uptime
 ps -eo pid,pcpu,comm --sort=-pcpu | head -20
 sha256sum bin/*
} > results/fingerprint-after.txt
