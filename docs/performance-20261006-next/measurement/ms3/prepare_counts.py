#!/usr/bin/env python3
"""Prepare measurement-only source; never modify a production checkout."""
import argparse, io, json, subprocess, tarfile
from pathlib import Path
p = argparse.ArgumentParser()
p.add_argument("source", type=Path)
p.add_argument("commit")
p.add_argument("output", type=Path)
a = p.parse_args()
a.output.mkdir(parents=True, exist_ok=False)
archive = subprocess.check_output(["git", "archive", a.commit], cwd=a.source)
with tarfile.open(fileobj=io.BytesIO(archive)) as t:
    t.extractall(a.output, filter="data")
path = a.output / "src/input_sections.rs"
s = path.read_text()
needle = "        let entsize = parent.hdr.shdr.sh_entsize.get() as usize;\n"
assert s.count(needle) == 1
helper = r'''        // Measurement only: observe allocation changes without timing them.
        // If the pointer changes, len * size_of<T> live bytes must survive
        // at the new allocation; this is not a count of hardware traffic.
        fn changed<T>(old: (*const T, usize, usize), vec: &Vec<T>, counts: &mut [i64; 4]) {
            if vec.capacity() != old.2 {
                counts[0] += 1;
                if old.2 != 0 { counts[1] += 1; }
                if old.1 != 0 && vec.as_ptr() != old.0 {
                    counts[2] += 1;
                    counts[3] += (old.1 * size_of::<T>()) as i64;
                }
            }
        }
        fn measured_push<T>(vec: &mut Vec<T>, value: T, counts: &mut [i64; 4]) {
            let old = (vec.as_ptr(), vec.len(), vec.capacity());
            vec.push(value);
            changed(old, vec, counts);
        }
        fn measured_reserve<T>(vec: &mut Vec<T>, additional: usize, exact: bool, counts: &mut [i64; 4]) {
            let old = (vec.as_ptr(), vec.len(), vec.capacity());
            if exact { vec.reserve_exact(additional); } else { vec.reserve(additional); }
            changed(old, vec, counts);
        }
        let mut vec_counts = [0i64; 4];
'''
s = s.replace(needle, needle + helper)
for field, val in [("frag_offsets", "pos as u32"), ("hashes", "hash")]:
    old = f"            self.{field}.push({val});"
    assert s.count(old) == 1
    s = s.replace(old, f"            measured_push(&mut self.{field}, {val}, &mut vec_counts);")
    old = f"            self.{field}.reserve(data.len() / entsize);"
    assert s.count(old) == 1
    s = s.replace(old, f"            measured_reserve(&mut self.{field}, data.len() / entsize, false, &mut vec_counts);")
    old = f"                self.{field}.reserve_exact(capacity - self.{field}.len());"
    if old in s:
        s = s.replace(old, f"                let additional = capacity - self.{field}.len();\n                measured_reserve(&mut self.{field}, additional, true, &mut vec_counts);")
needle = '        static COUNTER: Counter = Counter::new("string_fragments");'
assert s.count(needle) == 1
counters = r'''        static ALLOCATIONS: Counter = Counter::new("ms3_vec_allocations");
        static REALLOCATIONS: Counter = Counter::new("ms3_vec_reallocations");
        static MOVING: Counter = Counter::new("ms3_vec_moving_reallocations");
        static MOVED_BYTES: Counter = Counter::new("ms3_vec_live_bytes_moved");
        static CAPACITY_BYTES: Counter = Counter::new("ms3_vec_final_capacity_bytes");
        static LIVE_BYTES: Counter = Counter::new("ms3_vec_final_live_bytes");
        static SECTIONS: Counter = Counter::new("ms3_vec_sections");
        ALLOCATIONS.add(vec_counts[0]);
        REALLOCATIONS.add(vec_counts[1]);
        MOVING.add(vec_counts[2]);
        MOVED_BYTES.add(vec_counts[3]);
        CAPACITY_BYTES.add((self.frag_offsets.capacity() * 4 + self.hashes.capacity() * 8) as i64);
        LIVE_BYTES.add((self.frag_offsets.len() * 4 + self.hashes.len() * 8) as i64);
        SECTIONS.add(1);
'''
s = s.replace(needle, counters + needle)
path.write_text(s)
(a.output / "measurement-source.json").write_text(json.dumps({"commit": a.commit, "purpose": "untimed Vec allocation counts only", "instrumented": True}, indent=2) + "\n")
