#!/usr/bin/env python3
"""Export exact source-tree patches and verify them using a private Git index."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parent.parent
DEST = ROOT/'patches'
PLAN = json.loads((ROOT/'report-data/patch-plan.json').read_text())
PROVENANCE = json.loads((ROOT/'report-data/provenance.json').read_text())
REPO = Path(os.environ.get('MOLD_PATCH_REPO', str(ROOT)))
REPO = Path(subprocess.check_output(
    ['git', '-C', str(REPO), 'rev-parse', '--show-toplevel'], text=True).strip())
DEST.mkdir(exist_ok=True)


def git(*args, env=None):
    return subprocess.check_output(['git','-C',str(REPO),*args],env=env)


records = []
for entry in PLAN['patches']:
    base, source = entry['base_commit'], entry['source_commit']
    entry = entry | {'frozen_binaries': [dict(binary_sha256=sha,
        instrumented=p['instrumented'], evidence=p['evidence'])
        for sha,p in PROVENANCE.items() if p['source_commit']==source]}
    patch = git('diff','--binary','--full-index','--no-ext-diff','--no-renames',base,source)
    assert patch, entry
    filename = entry['name']+'.patch'
    path = DEST/filename
    path.write_bytes(patch)
    source_tree = git('rev-parse',source+'^{tree}').decode().strip()
    base_tree = git('rev-parse',base+'^{tree}').decode().strip()
    # No checkout, worktree, branch or user's index is modified by this check.
    with tempfile.TemporaryDirectory(prefix='mold-patch-index-') as tmp:
        env = os.environ | {'GIT_INDEX_FILE':str(Path(tmp)/'index')}
        git('read-tree',base,env=env)
        git('apply','--cached','--binary',str(path),env=env)
        applied_tree = git('write-tree',env=env).decode().strip()
    assert applied_tree==source_tree, (filename,applied_tree,source_tree)
    records.append(entry | dict(file=filename,bytes=len(patch),sha256=hashlib.sha256(patch).hexdigest(),
        base_tree_sha1=base_tree,source_tree_sha1=source_tree,verified_applied_tree_sha1=applied_tree))

manifest = dict(generated_utc=datetime.now(timezone.utc).isoformat(),scope=PLAN['scope'],
    public_anchors=PLAN['public_anchors'],patches=records,
    verification='Each full-index binary patch was applied to its declared base in a private Git index; resulting tree equals the declared source tree. No checkout or normal index was changed.')
(DEST/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
table=['| Patch | Base | Source | Role |','|---|---|---|---|']
for x in records:
    table.append(f"| [{x['file']}]({x['file']}) | `{x['base_commit'][:8]}` | `{x['source_commit'][:8]}` | {x['role']} |")
readme='''# Reproduce the investigated source revisions

These patches preserve every frozen production revision, the final topic heads, the original and rebased controls, final source compositions and final profiling instrumentation for the second campaign. They do not require publication of the sixteen experimental branches. The fixed plan is in `../report-data/patch-plan.json`; regenerate with `python3 ../report-data/export-patches.py` in the original repository containing those commits. Set `MOLD_PATCH_REPO` to that repository if the evidence directory is outside it.

`manifest.json` records full base/source commit IDs, tree IDs, patch SHA256 and frozen binary SHA256. **A source tree is reproducible from these patches; a byte-identical binary additionally requires the same compiler, dependencies, build flags and environment.** The recorded binary hashes identify what was actually measured and are not promises of a reproducible build on arbitrary machines.

Start in a clean clone at a declared public anchor. Keep this evidence directory outside the checkout while applying patches, since checking out an older source revision may remove the bundled report. Apply each patch with `git apply --index /absolute/path/to/patch.patch`; then `git write-tree` must equal its `source_tree_sha1`. No commit with the original source SHA needs to exist in the clone: the tree identity is the verification target.

For an original-baseline topic, start at public upstream `b2e5a7084f7391fca5c13631d20d36f64f72fe3a`, apply `original-topic-baseline.patch`, then exactly one selected topic revision patch. Do not stack independently based topic patches. A final-topic patch already includes its earlier topic changes; it is not an incremental patch over v1.

For the completed prior 1347-stage comparison, start at public upstream `1347ca95c906db060ecfbf838a792c5739970294` and apply `rebased-control.patch`. That is the measured control. Apply `omnibus-measured.patch` to obtain the measured P1+H1 candidate. `omnibus-final-tests.patch` adds only the later regression test. Alternatively, `omnibus-final-review.patch` applies both that test and the final formatting-only change directly over the measured composition; do not stack these two alternatives. That stage's frozen production binary remains tied to `omnibus-measured`.

The latest stage starts at public upstream `75200f107ee958227e87a96e67ad491567a4854a`. `latest-upstream-bridge.patch` reproduces that public tree from the prior1347 upstream anchor if needed. Apply `latest-control.patch`, then `latest-omnibus.patch` for the latest combined candidate. These sources and binaries are separate from the prior stage. `pr1696_p1-publication-latest.patch` applies to latest-control; `h1_upstream-publication-latest.patch` applies directly to latest upstream. The latest P1 source also has a separately built isolation binary; timing status comes from actual result groups, never from the moving publication ref alone.

For diagnostic profile sources, reconstruct the matching production control/candidate first, then apply `control-profile.patch` or `omnibus-profile.patch`. These add measurement instrumentation and must not replace the production speedup binaries. The separate latest stage uses latest-control-profile.patch or latest-omnibus-profile.patch after its matching latest production tree. Earlier standalone untimed allocation/locality probes retain their source patches and manifests in `../measurement/ms3/` and `../topics/*counts/`; their recorded counts are not performance timings.

Publication patches use their own declared base: H1 publication is directly on latest upstream, while the PR1696/P1 refinement is on the rebased control. Consult the frozen binary mappings and result groups for measurement status; a publication head alone does not establish timing evidence. The complete measured compositions are preserved separately.

All generated patches were verified by applying them in a private Git index and comparing the resulting tree hash with the declared source tree. This verification does not modify a checkout, branch or normal index. Later documentation-only report bundle commits do not change the frozen source plan.

'''
(DEST/'README.md').write_text(readme+'\n'.join(table)+'\n')
print(json.dumps(dict(patches=len(records),total_bytes=sum(x['bytes'] for x in records),all_trees_verified=True),indent=2))
