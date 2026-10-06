#!/usr/bin/env python3
"""Measurement-only trace output plus two coarse cleanup/window boundaries."""
from pathlib import Path
import argparse

p=argparse.ArgumentParser()
p.add_argument('worktree',type=Path)
a=p.parse_args()
path=a.worktree/'src/util/perf.rs'
s=path.read_text()
assert 'PROFILE_FORMAT' not in s
needle='        nest_records(&mut records);\n'
assert s.count(needle)>=1
s=s.replace(needle,'''        // Preserve explicit parentage before display-only containment inference.
        let trace = std::env::var_os("MOLD_PROFILE_TRACE").is_some();
        let explicit: Vec<_> = if trace {
            records.iter().map(|r| r.parent).collect()
        } else {
            Vec::new()
        };
'''+needle+'''
        // Measurement-only output. No additional per-record timed clock reads.
        if trace {
            let origin = records.first().map(|r| r.start).unwrap_or(now);
            println!("PROFILE_FORMAT\\t2");
            println!("PROFILE_THREADS\\t{}", rayon::current_num_threads());
            for (i, r) in records.iter().enumerate() {
                let name: String = r.name.as_bytes().iter().map(|b| format!("{b:02x}")).collect();
                println!("PROFILE\\t{}\\t{}\\t{}\\t{}\\t{}\\t{:.9}\\t{:.9}\\t{}",
                    i, r.parent.map_or(-1, |p| p as i64),
                    explicit[i].map_or(-1, |p| p as i64),
                    r.start.duration_since(origin).as_nanos(),
                    r.end.unwrap().duration_since(origin).as_nanos(),
                    r.user, r.sys, name);
            }
            return;
        }
''',1)
path.write_text(s)
path=a.worktree/'src/driver.rs';s=path.read_text()
needle='    let t_all = ctx.timer("all");\n';assert s.count(needle)==1
s=s.replace(needle,'''    let profile_trace = ctx.args.perf && std::env::var_os("MOLD_PROFILE_TRACE").is_some();
    let profile_window = profile_trace.then(|| ctx.timer("profile_window"));
'''+needle,1)
needle='''    if ctx.args.perf {
        ctx.timers.print();
    }
''';assert s.count(needle)==1
s=s.replace(needle,'''    if ctx.args.perf && !profile_trace {
        ctx.timers.print();
    }
''',1)
needle='    crate::mapped_file::drop_mappings();\n';assert s.count(needle)==1
s=s.replace(needle,'''    let profile_cleanup = profile_trace.then(|| ctx.timer("release_input_mappings"));
'''+needle+'''    drop(profile_cleanup);
    drop(profile_window);
    if profile_trace {
        ctx.timers.print();
    }
''',1)
path.write_text(s)
