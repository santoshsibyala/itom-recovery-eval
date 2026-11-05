# Approved supplementary smoke-A1 cohort

Santosh Sibyala approved A1: omit metadata.resourceVersion from snapshot's PUT and change no other recovery semantics. See AMENDMENTS.md for the approved record and A1_APPROVAL.json for its machine-readable receipt.

The original 20-cell smoke cohort remains under results/smoke, unchanged. Use the original commit to reproduce original-policy code. This checkout accepts only smoke-A1 execution; the main runner remains disabled. The prior setup baseline is referenced by hash, not repeated or replaced. Each supplementary cell still creates and checks its own baseline exactly as before.

After committing the implementation and provenance receipt:

```
.venv/bin/python verify_a1.py
.venv/bin/python preflight_a1.py
.venv/bin/python run.py smoke-A1 --session a120261101
```

The tests are offline. Preflight is read-only and verifies the original artifacts, dependencies, runtime image digests and dedicated cluster. Run exactly one new cell for each snapshot condition, in SHA-256 order of `20261101|smoke-A1|1|snapshot|<condition>`. Raw records are exclusively created under results/smoke-A1; namespace identifiers use lowercase smoke-a1. All calls, full 90-second windows, timeouts, no-retry behavior, and classifiers are unchanged. Request journals include effective protocol, original freeze, A1 approval, amendment and implementation commits, and source/environment/image hashes.

The implementation commit identifies source code; the execution commit may additionally contain the provenance-only receipt with that implementation commit ID. The runner checks that every Python source file matches the named implementation commit and the working tree is clean.

Stop after five cells. No automatic main authorization, replacement runs, or pooled original/A1 smoke result is allowed. Readiness for main requires a separate author review. Results, test logs and setup records are never overwritten.
