#!/usr/bin/env bash
set -euo pipefail
mkdir -p out/h2-check
cat > out/h2-check/probe.s <<'ASM'
.text
.globl _start
.type _start,@function
_start:
.byte 0xf3,0x0f,0x1e,0xfa
ret
.section .debug_large,"",@progbits
.fill 12582917,1,0xa5
.section .debug_pointer,"",@progbits
.quad _start
.section .note.GNU-stack,"",@progbits
ASM
cc -c out/h2-check/probe.s -o out/h2-check/probe.o
for flags in '--threads=1' '--threads=32' '--emit-relocs' '-r' '--compress-debug-sections=zlib' '--compress-debug-sections=zstd' '--gdb-index' '--strip-debug' '-z rewrite-endbr' '--build-id=md5' '--build-id=sha256'; do
 read -ra args <<< "$flags"
 out/baseline --no-fork --build-id out/h2-check/probe.o "${args[@]}" -o out/h2-check/oracle
 out/candidate --no-fork --build-id out/h2-check/probe.o "${args[@]}" -o out/h2-check/candidate
 cmp out/h2-check/oracle out/h2-check/candidate
 printf 'MATCH %s\n' "$flags"
done
