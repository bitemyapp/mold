#!/usr/bin/env bash
set -euo pipefail
root=/home/callen/work/mold-next-20261006
while [[ -e "$root/benchmark-window" ]]; do sleep 1; done
exec 9>/home/callen/work/mold-radical-20261006/workstation.lock
flock -s 9
python3 "$root/logs/cr5-counts/collect.py"
