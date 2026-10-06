# G1 measured results

Source 25c7f28ff8360e5aeba3c1a8880eb318dbf39d5c; binary SHA-256 83c8aa3650b328a8e8c44fbc07d08d7d73452ca20a166b04196c0a7ba1f0a57d. Negative deltas are improvements. Every row matched golden output.

## Initial screen

| Case | Pairs | Wall change (95% interval) | CPU change (95% interval) | RSS change |
|---|---:|---:|---:|---:|
| hello | 24 | -1.6% [-6.5, +1.2] | -1.6% [-6.3, +1.2] | +0.0% |
| rhello | 24 | +2.4% [-1.9, +6.1] | +3.9% [-2.6, +8.4] | +4.0% |
| tblgen | 24 | -2.1% [-5.5, +2.9] | -3.6% [-6.9, +5.7] | -0.2% |
| lld | 24 | +1.2% [-0.4, +2.1] | +4.4% [-9.0, +21.9] | +0.1% |
| clang | 24 | +0.1% [-5.7, +3.8] | -0.6% [-2.2, +1.7] | +0.0% |
| clang-s | 24 | -3.3% [-5.1, +2.0] | +2.7% [+0.1, +5.4] | +0.2% |
| ra | 24 | -3.9% [-8.7, -0.2] | +0.5% [-2.2, +3.0] | -0.0% |
| ra-s | 24 | -2.0% [-5.2, +1.6] | +0.0% [-2.7, +1.9] | +0.0% |

## Independent confirmation

| Case | Pairs | Wall change (95% interval) | CPU change (95% interval) | RSS change |
|---|---:|---:|---:|---:|
| lld | 50 | +0.6% [-1.2, +1.6] | +2.5% [-5.0, +11.6] | +0.3% |
| clang | 50 | +0.7% [-0.7, +1.6] | -1.9% [-11.1, +11.1] | -0.0% |
| ra | 50 | -1.9% [-4.0, +1.2] | +0.1% [-1.3, +1.6] | +0.1% |
| ra-s | 50 | -1.3% [-3.1, +0.4] | +0.3% [-1.3, +1.8] | +0.2% |

Decision: reject from the omnibus. The initial rust-analyzer latency hint did not become a repeatable wall/CPU improvement in independent confirmation. Its unchanged relocation graph and compact target cache remain available for review in the independent branch.
