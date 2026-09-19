#!/bin/bash
source "$(dirname "$0")"/common.inc

# A library the link already holds as a public re-export (an umbrella
# stub inlines /usr/lib/libbar.dylib) that an object's auto-link option
# then names stays a hint like any auto-linked library: ld-prime lists
# it only if something binds to it. Named on the command line instead,
# it is kept.
mkdir -p $t/libs/SomeFramework.framework
cat > $t/libs/SomeFramework.framework/SomeFramework.tbd <<EOF2
--- !tapi-tbd
tbd-version:     4
targets:         [ x86_64-macos, arm64-macos ]
install-name:    '/usr/frameworks/SomeFramework.framework/SomeFramework'
current-version: 0000
compatibility-version: 150
reexported-libraries:
  - targets:         [ x86_64-macos, arm64-macos ]
    libraries:       [ '/usr/lib/libbar.dylib' ]
exports:
  - targets:         [ x86_64-macos, arm64-macos ]
    symbols:         [ _foo ]
--- !tapi-tbd
tbd-version:     4
targets:         [ x86_64-macos, arm64-macos ]
install-name:    '/usr/lib/libbar.dylib'
current-version: 0000
compatibility-version: 150
exports:
  - targets:         [ x86_64-macos, arm64-macos ]
    symbols:         [ _bar ]
...
EOF2
cat > $t/libs/libbar.tbd <<EOF2
--- !tapi-tbd
tbd-version:     4
targets:         [ x86_64-macos, arm64-macos ]
install-name:    '/usr/lib/libbar.dylib'
current-version: 0000
compatibility-version: 150
exports:
  - targets:         [ x86_64-macos, arm64-macos ]
    symbols:         [ _bar ]
...
EOF2
cat <<EOF2 | $CC -o $t/opt.o -c -xassembler -
.linker_option "-lbar"
EOF2
cat <<EOF2 | $CC -o $t/a.o -c -xc -
extern void foo(void);
int main(void) { foo(); return 0; }
EOF2
cat <<EOF2 | $CC -o $t/b.o -c -xc -
extern void foo(void);
extern void bar(void);
int main(void) { foo(); bar(); return 0; }
EOF2

$CC --ld-path=$mold -o $t/exe $t/a.o $t/opt.o -F$t/libs -L$t/libs -Wl,-framework,SomeFramework
otool -L $t/exe > $t/deps
grep -q SomeFramework $t/deps
not grep -q libbar $t/deps

$CC --ld-path=$mold -o $t/exe2 $t/b.o $t/opt.o -F$t/libs -L$t/libs -Wl,-framework,SomeFramework
otool -L $t/exe2 | grep -q '/usr/lib/libbar.dylib'
dyld_info -fixups $t/exe2 | grep -q 'libbar/_bar'

$CC --ld-path=$mold -o $t/exe3 $t/a.o -F$t/libs -L$t/libs -Wl,-framework,SomeFramework -lbar
otool -L $t/exe3 | grep -q '/usr/lib/libbar.dylib'
