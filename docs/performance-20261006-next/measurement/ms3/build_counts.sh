#!/usr/bin/env bash
set -euo pipefail
for variant in baseline candidate; do
  cargo build --release --locked --manifest-path /work/counts-$variant/Cargo.toml -p mold-cli --no-default-features --features x86_64
  cp /target/release/mold /work/counts-$variant/mold-counts
  sha256sum /work/counts-$variant/mold-counts | tee /work/counts-$variant/binary.sha256
done
