#!/usr/bin/env bash
set -euo pipefail
root=/home/callen/work/mold-rayon-rebase-20261006
label=$1
mode=$2
exec 9>/home/callen/work/mold-radical-20261006/workstation.lock
flock -s 9
mkdir -p "$root/target" "$root/logs" "$root/bin"
exec 8>"$root/build.lock"
flock -x 8
case "$mode" in
 build) command='cargo clean --release -p mold -p mold-cli -p mold-arch-x86_64 -p rayon-core -p rayon && cargo build --release --locked -p mold-cli --no-default-features --features x86_64';;
 test) command='cargo clean -p mold -p mold-cli -p mold-tests -p mold-arch-x86_64 -p rayon-core -p rayon && cargo fmt --all --check && cargo test --locked -p mold -p mold-tests --lib && cargo test --locked -p mold-cli --no-default-features --features x86_64 --test integration -- --native --test-threads 8';;
 format) command='cargo fmt --all --check && cargo fmt --manifest-path vendor/rayon-core/Cargo.toml --check';;
 rayon) command='ulimit -c 0; cargo test --manifest-path vendor/rayon-core/Cargo.toml';;
 *) exit 2;;
esac
log="$root/logs/$label-$mode.log"
docker run --rm --cpuset-cpus=0-15 -v "$root/src/$label:/work" -v "$root/target:/target" -v /home/callen/work/mold-efficiency-20261006/cargo:/home/ubuntu/.cargo/registry -e CARGO_TARGET_DIR=/target -e CARGO_BUILD_JOBS=16 -e CARGO_INCREMENTAL=0 -e CARGO_PROFILE_DEV_DEBUG=0 -e CARGO_PROFILE_RELEASE_DEBUG=line-tables-only -e RUSTFLAGS='-Cforce-frame-pointers=yes -Cllvm-args=-addrsig' mold-upstream-ci bash -c "$command" >"$log" 2>&1 || { tail -60 "$log"; exit 1; }
if [[ "$mode" == build ]]; then cp "$root/target/release/mold" "$root/bin/$label"; sha256sum "$root/bin/$label"; fi
tail -8 "$log"
