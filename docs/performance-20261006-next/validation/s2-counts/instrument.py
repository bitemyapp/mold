#!/usr/bin/env python3
from pathlib import Path
import sys
root=Path(sys.argv[1]);p=root/'src/input_sections.rs';s=p.read_text()
assert 'profile_split_cpu' not in s
s=s.replace('''    hashes: Vec<u64>,
}''','''    hashes: Vec<u64>,
    // Measurement-only split-to-resolve handoff metadata.
    profile_split_cpu: i32,
    profile_split_worker: usize,
}''',1)
s=s.replace('''            hashes: Vec::new(),''','''            hashes: Vec::new(),
            profile_split_cpu: -1,
            profile_split_worker: usize::MAX,''')
needle='''        if data.len() > u32::MAX as usize {''';assert needle in s
s=s.replace(needle,'''        // SAFETY: sched_getcpu does not access Rust-owned memory.
        let profile_start_cpu = unsafe { libc::sched_getcpu() };
'''+needle,1)
needle='''        COUNTER.add(self.frag_offsets.len() as i64);
    }''';assert needle in s
s=s.replace(needle,'''        COUNTER.add(self.frag_offsets.len() as i64);
        // SAFETY: sched_getcpu does not access Rust-owned memory.
        self.profile_split_cpu = unsafe { libc::sched_getcpu() };
        self.profile_split_worker = rayon::current_thread_index().unwrap_or(usize::MAX);
        if profile_start_cpu != self.profile_split_cpu {
            static MIGRATIONS: Counter = Counter::new("s2_split_endpoint_migrations");
            MIGRATIONS.increment();
        }
    }''',1)
needle='''        let n = self.frag_offsets.len();
        self.fragments.reserve(n);''';assert needle in s
s=s.replace(needle,'''        let n = self.frag_offsets.len();
        // SAFETY: sched_getcpu does not access Rust-owned memory.
        let profile_cpu = unsafe { libc::sched_getcpu() };
        let profile_worker = rayon::current_thread_index().unwrap_or(usize::MAX);
        static SECTIONS: Counter = Counter::new("s2_handoff_sections");
        static FRAGMENTS: Counter = Counter::new("s2_handoff_fragments");
        SECTIONS.increment();
        FRAGMENTS.add(n as i64);
        if profile_worker == self.profile_split_worker {
            static SAME_WORKER: Counter = Counter::new("s2_same_worker_fragments");
            SAME_WORKER.add(n as i64);
        }
        if profile_cpu == self.profile_split_cpu {
            static SAME_CPU: Counter = Counter::new("s2_same_cpu_fragments");
            SAME_CPU.add(n as i64);
        }
        // Exact topology for wx-workstation's current CPU numbering, captured
        // with lscpu: CPUs0..63 are physical cores,64..127 their SMT siblings;
        // each consecutive group of8 physical cores shares one L3.
        let domain = |cpu: i32| if (0..128).contains(&cpu) { (cpu % 64) / 8 } else { -1 };
        if domain(profile_cpu) >= 0 && domain(profile_cpu) == domain(self.profile_split_cpu) {
            static SAME_L3: Counter = Counter::new("s2_same_l3_fragments");
            SAME_L3.add(n as i64);
        } else {
            static CROSS_L3: Counter = Counter::new("s2_cross_l3_fragments");
            CROSS_L3.add(n as i64);
        }
        self.fragments.reserve(n);''',1)
needle='''        // Reclaim memory as we'll never use this vector again.
        self.hashes = Vec::new();''';assert needle in s
s=s.replace(needle,'''        // SAFETY: sched_getcpu does not access Rust-owned memory.
        if profile_cpu != unsafe { libc::sched_getcpu() } {
            static MIGRATIONS: Counter = Counter::new("s2_resolve_endpoint_migrations");
            MIGRATIONS.increment();
        }
'''+needle,1)
p.write_text(s)
