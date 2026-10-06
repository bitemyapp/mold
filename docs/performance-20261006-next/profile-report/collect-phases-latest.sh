#!/usr/bin/env bash
# Coordinator only: caller holds EXCLUSIVE workstation gate via queue-run.sh.
set -euo pipefail
root=/home/callen/work/mold-next-20261006
MOLD_PROFILE_TRACE=1 python3 "$root/measure.py" --runs 12 --perf \
 --output "$root/results/final-phases-latest.json" \
 latest-control="$root/bin/latest-control-profile" latest-omnibus="$root/bin/latest-omnibus-profile"
python3 "$root/profile-report/analyze.py" \
 --input "$root/results/final-phases-latest.json" \
 --manifest "$root/profile-report/manifest-latest.json" \
 --output "$root/profile-report/phase-summary-latest.json"
