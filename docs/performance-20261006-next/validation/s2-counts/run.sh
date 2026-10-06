#!/usr/bin/env bash
set -euo pipefail
root=/home/callen/work/mold-next-20261006
while [[ -e "$root/benchmark-window" ]]; do sleep 1; done
exec 9>/home/callen/work/mold-radical-20261006/workstation.lock
flock -s 9
exec 8>"$root/targets/s2-counts.lock"
flock -x 8
mkdir -p "$root/src/s2-counts" "$root/targets/s2-counts" "$root/logs/s2-counts"
tar -xf "$root/logs/s2-counts/source.tar" -C "$root/src/s2-counts"
if [[ ! -f "$root/targets/s2-counts/.seeded" ]]; then
 cp -a --reflink=auto /home/callen/work/mold-efficiency-20261006/target/. "$root/targets/s2-counts/"
 touch "$root/targets/s2-counts/.seeded"
fi
cp "$root/src/s2-counts/src/input_sections.rs" "$root/logs/s2-counts/input_sections.before.rs"
python3 "$root/logs/s2-counts/instrument.py" "$root/src/s2-counts"
diff -u "$root/logs/s2-counts/input_sections.before.rs" "$root/src/s2-counts/src/input_sections.rs" > "$root/logs/s2-counts/instrumentation.patch" || [[ $? == 1 ]]
docker run --rm --cpuset-cpus=8-15 --memory=24g --pids-limit=2048 \
 -v "$root/src/s2-counts:/work" -v "$root/targets/s2-counts:/target" \
 -v /home/callen/work/mold-efficiency-20261006/cargo:/home/ubuntu/.cargo/registry \
 -e CARGO_TARGET_DIR=/target -e CARGO_BUILD_JOBS=8 -e CARGO_INCREMENTAL=0 \
 -e CARGO_PROFILE_RELEASE_DEBUG=line-tables-only \
 -e RUSTFLAGS='-Cforce-frame-pointers=yes -Cllvm-args=-addrsig' \
 mold-upstream-ci bash -c 'cargo clean -p mold -p mold-cli -p mold-arch-x86_64 --release && cargo build --release --locked -p mold-cli --no-default-features --features x86_64' > "$root/logs/s2-counts/build.log" 2>&1
cp "$root/targets/s2-counts/release/mold" "$root/bin/s2-counts"
python3 "$root/logs/s2-counts/collect.py" > "$root/logs/s2-counts/collect.log" 2>&1
cat "$root/logs/s2-counts/collect.log"
