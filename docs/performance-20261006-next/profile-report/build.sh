#!/usr/bin/env bash
# Build measurement-only binaries. Production binaries are never overwritten.
set -euo pipefail
root=/home/callen/work/mold-next-20261006
label=$1
[[ "$label" == current || "$label" == omnibus ]]
while [[ -e "$root/benchmark-window" ]]; do sleep 1; done
exec 9>/home/callen/work/mold-radical-20261006/workstation.lock
flock -s 9
exec 8>"$root/targets/$label-profile.lock"
flock -x 8
[[ ! -e "$root/bin/$label-profile" ]] || { echo 'Frozen profile binary already exists; refusing replacement' >&2; exit 1; }
mkdir -p "$root/targets/$label-profile" "$root/logs/$label-profile"
if [[ ! -f "$root/targets/$label-profile/.seeded" ]]; then
 cp -a --reflink=auto /home/callen/work/mold-efficiency-20261006/target/. "$root/targets/$label-profile/"
 touch "$root/targets/$label-profile/.seeded"
fi
docker run --rm --init --cpuset-cpus=8-15 --memory=24g --pids-limit=2048 \
 -v "$root/src/$label-profile:/work" -v "$root/targets/$label-profile:/target" \
 -v /home/callen/work/mold-efficiency-20261006/cargo:/home/ubuntu/.cargo/registry \
 -v "$root/cargo-git:/home/ubuntu/.cargo/git" \
 -e CARGO_NET_OFFLINE=true \
 -e CARGO_TARGET_DIR=/target -e CARGO_BUILD_JOBS=8 -e CARGO_INCREMENTAL=0 \
 -e CARGO_PROFILE_RELEASE_DEBUG=line-tables-only \
 -e RUSTFLAGS='-Cforce-frame-pointers=yes -Cllvm-args=-addrsig' \
 mold-upstream-ci bash -c 'cargo clean --release -p mold -p mold-cli -p mold-arch-x86_64 && cargo build --release --locked -p mold-cli --no-default-features --features x86_64' \
 > "$root/logs/$label-profile/build.log" 2>&1 || { tail -60 "$root/logs/$label-profile/build.log"; exit 1; }
cp "$root/targets/$label-profile/release/mold" "$root/bin/$label-profile"
sha256sum "$root/bin/$label-profile" | tee "$root/logs/$label-profile/binary.sha256"
python3 - "$root" "$label" <<'STAMP'
from pathlib import Path
import hashlib,json,sys
root=Path(sys.argv[1]);label=sys.argv[2];p=root/'profile-report/manifest.json'
d=json.loads(p.read_text());binary=root/f'bin/{label}-profile'
with binary.open('rb') as f:d['labels'][label]['profile_binary_sha256']=hashlib.file_digest(f,'sha256').hexdigest()
tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(d,indent=2)+'\n');tmp.replace(p)
STAMP
