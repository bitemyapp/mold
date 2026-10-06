#!/usr/bin/env bash
set -euo pipefail
cargo build --release --locked -p mold-cli --no-default-features --features x86_64
cp /target/release/mold /work/mold-ms2-v2
sha256sum /work/mold-ms2-v2
