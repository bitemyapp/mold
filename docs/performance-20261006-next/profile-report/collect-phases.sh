#!/usr/bin/env bash
# Coordinator only: caller holds EXCLUSIVE workstation gate via queue-run.sh.
set -euo pipefail
root=/home/callen/work/mold-next-20261006
MOLD_PROFILE_TRACE=1 python3 "$root/measure.py" --runs 12 --perf \
 --output "$root/results/final-phases.json" \
 current="$root/bin/current-profile" omnibus="$root/bin/omnibus-profile"
python3 "$root/profile-report/analyze.py" \
 --input "$root/results/final-phases.json" \
 --manifest "$root/profile-report/manifest.json" \
 --output "$root/profile-report/phase-summary.json"
