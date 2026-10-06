# K1 independent review

Reviewed commit6d24b45a in the dedicated K1 worktree. No blocking ownership, range, permissions, or byte-preservation issue found.

Every map_file caller sets the file’s current length before mapping. MmapMut supplies a writable, page-aligned mapping, and the new advice covers len rather than the twice-sized address reservation. The descriptor and mapping remain owned throughout the syscall. Mapping preparation precedes parallel output writes. Remapping during extension preserves existing contents; growth inside the original address reservation keeps the existing demand-fault path for appended bytes.

The Linux manual confirms that MADV_POPULATE_WRITE establishes writable page tables without performing the subsequent userspace store. It can return after partial population; unpopulated pages retain normal fault behavior. Page rounding can include the last partial file page, without reaching a following file page. Earlier memory commitment and serial preparation remain performance costs to measure. [madvise(2)](https://man7.org/linux/man-pages/man2/madvise.2.html)

Scope correction: EXT4_SUPER_MAGIC has the same0xef53 value as EXT2_SUPER_MAGIC and EXT3_SUPER_MAGIC. The gate therefore selects the ext filesystem family, although the measured machine and motivating stacks are ext4. The report should not promise an ext4-only selection. [statfs(2)](https://man7.org/linux/man-pages/man2/statfs.2.html)

No edits made. Recommended validation coverage includes ext4 population, a nonmatching filesystem fallback, current-file-length versus reserved-tail bounds, preserved written prefixes on remapping, and byte-identical linked outputs; parent is coordinating those tests.
