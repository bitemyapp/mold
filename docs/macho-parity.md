# The Mach-O linker and its parity with ld-prime

mold links Mach-O when invoked as `ld64.mold` (the installer creates
the symlink next to `ld.mold`; clang's `--ld-path=` takes it). The
Mach-O linker lives in `src/macho/` and shares the ELF linker's
diagnostics, input-file mapping, archive reading, file-type detection,
forking and small helpers; its shell tests are `tests/macho/*.sh`, run
by `cargo test -p mold-cli --test macho` on macOS for the host
architecture and, under Rosetta, for x86-64.

The reference is Apple's linker as shipped with Xcode 26 ("ld-prime",
`ld -version_details` reports 27037). Parity was measured by running
every test script with both linkers from the same directory and
comparing every Mach-O file both produced: load commands and section
attributes (`otool -l`), the symbol table (`nm -m`), the export trie,
fixups and dependent libraries (`dyld_info`), the header flags and the
code signature. What differed was made to match, with a test pinning
each rule, except for the cases below.

## Documented exceptions

- **Output is written with `pwrite`, not through a shared mapping.**
  The ELF linker maps its output file and writes into it. On macOS a
  vnode that has ever had a writable shared mapping fails ad-hoc
  code-signature validation at exec time (the binary is killed even
  though `codesign -v` passes), so the Mach-O linker builds the image
  in memory and streams it out with `pwrite` from writer threads. The
  file is registered with the shared cleanup path, so a failed link
  removes it like an ELF one.

- **The linker's tool entry in `LC_BUILD_VERSION`.** Both linkers write
  one `build_tool_version` entry; ld-prime's is tool 3 (`ld`) with its
  own version, mold's is tool 54321 (sold's number, so
  `otool -l | grep 'tool 54321'` identifies our output) with version 1.
  Claiming to be Apple's linker would mislead tooling that keys on the
  version.

- **A defined class's folded class reference.** From macOS 15 on both
  linkers fold `__objc_classrefs` into the GOT. For a class the image
  itself defines, ld-prime sometimes keeps a rebased GOT slot and
  sometimes relaxes the load to a direct address computation, by a
  per-reference heuristic that is not documented. mold always relaxes
  such a reference (no slot), which is self-consistent and smaller;
  the class address and every runtime check are identical either way.

- **Order of the read-only Objective-C string pools.** Within `__TEXT`,
  ld-prime places the merged selector-name pool (`__objc_methname`)
  after `__objc_methtype`, and after `__cstring` when the selector
  names are synthesized, by a rule that does not reduce to first-seen
  order. mold keeps these pools in first-seen order. The contents are
  identical; only the relative position of the pools differs.

- **Synthetic local names in a `-r` output.** Both linkers name the
  anonymous atoms of a relocatable output themselves: cstring literals
  `LC<n>`, the records of `__cfstring`, `__objc_selrefs` and
  `__objc_classrefs` `l<nnn>`. ld-prime runs one counter over the atoms
  in address order across sections; mold numbers the literals first,
  and which atoms get a name is matched in kind but not one for one.
  The names carry no meaning (a later link reads the relocations, which
  are equivalent), so the numbering is not matched.

- **`ltmp` labels on empty sections.** A whole-section object (one
  without `MH_SUBSECTIONS_VIA_SYMBOLS`) contributes its `ltmp` labels to
  a `-r` output as ld-prime does, except for a label on an empty
  section (an assembler input that only carries `.linker_option`
  directives), which names nothing and is dropped.

- **Options ld-prime does not have.** `--print-dependencies` and a few
  other mold conveniences are accepted; ld-prime rejects them. They
  change nothing about the output for a command line ld-prime accepts.

- **Bytes that cannot match by construction.** `LC_UUID` hashes the
  image, so two images that differ anywhere differ there too; the
  ad-hoc code signature covers the whole file likewise. Both match
  whenever everything else does.
