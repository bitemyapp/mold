#!/usr/bin/env python3
from pathlib import Path
import difflib,sys
root=Path(sys.argv[1]);patch=[]
def edit(path,old,new):
 p=root/path;s=p.read_text();assert old in s,path;t=s.replace(old,new,1);p.write_text(t)
 patch.extend(difflib.unified_diff(s.splitlines(True),t.splitlines(True),fromfile=path,tofile=path))
edit('src/input_sections.rs','    frag_offsets: Vec<u32>,','    pub(crate) frag_offsets: Vec<u32>,')
edit('src/driver.rs','    let threads = thread_count(&ctx.args);','    let threads = thread_count(&ctx.args);\n    eprintln!("S2_WORKERS {threads}");')
needle='    for (id, sketch) in parts.into_iter().flatten() {\n'
insert='    let profile: Vec<_> = jobs.iter().enumerate().flat_map(|(worker, slot)| {\n        let jobs = slot.lock().unwrap();\n        jobs.iter().map(|(id, members)| [\n            worker, *id, members.iter().map(|m| m.data.len()).sum::<usize>(),\n            members.iter().map(|m| m.merge_info.frag_offsets.len()).sum::<usize>(),\n            members.len(),\n        ]).collect::<Vec<_>>()\n    }).collect();\n    eprintln!("S2_ASSIGN {:?}", profile);\n'
edit('src/chunks/merged.rs',needle,insert+needle)
(root/'measurement.patch').write_text(''.join(patch))
