#!/usr/bin/env bash
# Independent late-upstream rebuild. Old sources, targets, and binaries stay frozen.
set -euo pipefail
root=/home/callen/work/mold-next-20261006
topic=$1
mode=$2
shift 2
case "$topic" in
 latest-control) cpus=8-15; source_commit=f1dec0f067198959a1339e761f27f27ccc4179d1;;
 latest-p1) cpus=8-15; source_commit=e41a4bd5ecfd23d318d4ce4a0a089f2e35a60e95;;
 latest-omnibus) cpus=24-31; source_commit=8e522e5217adea17329e8e2eeb753fc482de4b16;;
 *) echo 'Expected latest-control, latest-omnibus, or latest-p1' >&2; exit 2;;
esac
case "$mode" in
 fetch) command='cargo fetch --locked';;
 build) command='cargo clean --release -p libmold -p mold -p mold-arch-x86_64 && cargo build --release --locked -p mold --no-default-features --features x86_64';;
 unit) command='cargo test --release --locked -p libmold -p mold-tests --lib';;
 native) command='cargo test --release --locked -p mold --no-default-features --features x86_64 --test integration -- --native --test-threads 8 "$@"';;
 check) command='cargo check --locked --workspace --all-targets';;
 full) command='cargo build --locked && cargo test --locked -p libmold -p mold-tests --lib && cargo test --locked -p mold --test integration -- --all --test-threads 8';;
 fmt) command='cargo fmt --all -- --check';;
 hosts) command='rustup target add armv7-unknown-linux-gnueabihf i686-unknown-linux-gnu powerpc-unknown-linux-gnu && for host_target in armv7-unknown-linux-gnueabihf i686-unknown-linux-gnu powerpc-unknown-linux-gnu; do cargo check --locked --workspace --all-targets --target "$host_target" || exit; done';;
 *) echo 'Expected fetch, build, unit, native, check, full, fmt, or hosts' >&2; exit 2;;
esac
while [[ -e "$root/benchmark-window" ]]; do sleep 1; done
exec 9>/home/callen/work/mold-radical-20261006/workstation.lock
flock -s 9
mkdir -p "$root/targets/$topic" "$root/logs/$topic" "$root/bin"
exec 8>"$root/targets/$topic.lock"
flock -x 8
if [[ "$mode" == build && -e "$root/bin/$topic" ]]; then
 echo "Frozen binary already exists: $root/bin/$topic; refusing replacement" >&2
 exit 1
fi
if [[ ! -f "$root/targets/$topic/.seeded" ]]; then
 cp -a --reflink=auto /home/callen/work/mold-efficiency-20261006/target/. "$root/targets/$topic/"
 touch "$root/targets/$topic/.seeded"
fi
stamp=$(date +%Y%m%dT%H%M%S)
log="$root/logs/$topic/$mode-$stamp.log"
printf '%s %s source %s started; %s\n' "$topic" "$mode" "$source_commit" "$log"
printf 'source_commit=%s\ncpu_set=%s\ncommand=%s\n' "$source_commit" "$cpus" "$command" > "$log"
sha256sum "$root/src/$topic/Cargo.lock" >> "$log"
docker run --rm --init --cpuset-cpus="$cpus" --memory=24g --pids-limit=2048 \
 -v "$root/src/$topic:/work" -v "$root/targets/$topic:/target" \
 -v /home/callen/work/mold-efficiency-20261006/cargo:/home/ubuntu/.cargo/registry \
 -v "$root/cargo-git:/home/ubuntu/.cargo/git" \
 -e CARGO_NET_OFFLINE=false \
 -e CARGO_TARGET_DIR=/target -e CARGO_BUILD_JOBS=8 \
 -e CARGO_INCREMENTAL=0 -e CARGO_PROFILE_DEV_DEBUG=0 \
 -e CARGO_PROFILE_RELEASE_DEBUG=line-tables-only \
 -e RUSTFLAGS='-Cforce-frame-pointers=yes -Cllvm-args=-addrsig' \
 mold-upstream-ci bash -c "$command" bash "$@" >> "$log" 2>&1 || { tail -60 "$log"; exit 1; }
if [[ "$mode" == build ]]; then
 cp "$root/targets/$topic/release/mold" "$root/bin/$topic"
 sha256sum "$root/bin/$topic" | tee "$root/logs/$topic/binary.sha256"
 printf '%s\n' "$source_commit" > "$root/logs/$topic/source-commit.txt"
fi
tail -8 "$log"
