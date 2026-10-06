#!/usr/bin/env bash
# All remote build/test traffic participates in one shared/exclusive gate.
set -euo pipefail
root=/home/callen/work/mold-next-20261006
topic=$1
mode=$2
shift 2
[[ "$topic" =~ ^(baseline|ms1|ms2|ms3|ms4|cr1|cr2|cr3|cr4|cr5|s1|s2|g1|p1|h1|h2|k1|current|omnibus)$ ]]
while [[ -e "$root/benchmark-window" ]]; do sleep 1; done
exec 9>/home/callen/work/mold-radical-20261006/workstation.lock
flock -s 9
mkdir -p "$root/targets/$topic" "$root/logs/$topic"
exec 8>"$root/targets/$topic.lock"
flock -x 8
if [[ ! -f "$root/targets/$topic/.seeded" ]]; then
  cp -a --reflink=auto /home/callen/work/mold-efficiency-20261006/target/. "$root/targets/$topic/"
  touch "$root/targets/$topic/.seeded"
fi
case "$topic" in
 ms1|ms2|ms3|ms4) cpus=0-7;;
 cr5|s1|s2|g1) cpus=8-15;;
 cr1|cr2|cr3|cr4) cpus=16-23;;
 *) cpus=24-31;;
esac
case "$mode" in
 build) command='cargo clean --release -p mold -p mold-cli -p mold-arch-x86_64 && cargo build --release --locked -p mold-cli --no-default-features --features x86_64';;
 unit) command='cargo test --release --locked -p mold -p mold-tests --lib';;
 native) command='cargo test --release --locked -p mold-cli --no-default-features --features x86_64 --test integration -- --native --test-threads 8 "$@"';;
 check) command='cargo check --locked --workspace --all-targets';;
 full) command='cargo build --locked && cargo test --locked -p mold -p mold-tests --lib && cargo test --locked -p mold-cli --test integration -- --all --test-threads 8';;
 shell) command='exec "$@"';;
 *) exit 2;;
esac
stamp=$(date +%Y%m%dT%H%M%S)
log="$root/logs/$topic/$mode-$stamp.log"
printf '%s %s started; %s\n' "$topic" "$mode" "$log"
docker run --rm --init --cpuset-cpus="$cpus" --memory=24g --pids-limit=2048 \
 -v "$root/src/$topic:/work" -v "$root/targets/$topic:/target" \
 -v /home/callen/work/mold-efficiency-20261006/cargo:/home/ubuntu/.cargo/registry \
 -v "$root/cargo-git:/home/ubuntu/.cargo/git" \
 -e CARGO_NET_OFFLINE=true \
 -e CARGO_TARGET_DIR=/target -e CARGO_BUILD_JOBS=8 \
 -e CARGO_INCREMENTAL=0 -e CARGO_PROFILE_DEV_DEBUG=0 \
 -e CARGO_PROFILE_RELEASE_DEBUG=line-tables-only \
 -e RUSTFLAGS='-Cforce-frame-pointers=yes -Cllvm-args=-addrsig' \
 mold-upstream-ci bash -c "$command" bash "$@" > "$log" 2>&1 || { tail -60 "$log"; exit 1; }
if [[ "$mode" == build ]]; then
 cp "$root/targets/$topic/release/mold" "$root/bin/$topic"
 sha256sum "$root/bin/$topic"
fi
tail -8 "$log"
