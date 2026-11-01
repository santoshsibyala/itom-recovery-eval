# Main cohort approved by Santosh Sibyala

MAIN_APPROVAL.json and AMENDMENTS.md bind the one 200-run main cohort to the original freeze, approved A1 implementation, effective protocol hashes, and both reviewed smoke manifests. Historical main-not-approved statements describe the state before this approval. The manuscript is outside this task.

The original run.py, classify.py, pinned setup, and focused tests are byte-identical to the approved implementation. main_runner.py imports the original experiment, baseline, injection, health, and request methods. Its executor differs only in main phase routing and raw-output directory. Repetition metadata is recorded without changing any policy decision. No probe, timeout, status wait, force, retry, or mutation behavior changes.

Before launch, commit all sources and the receipt, then:

```
.venv/bin/python verify_main.py
.venv/bin/python preflight_main.py
make run
```

main_runner.py fixes session m20261101 and saves all 200 cells before execution. Each repetition uses the original SHA-256 ordering formula with phase main. A process lock prevents concurrent drivers. Completed raw files use exclusive creation. The main raw directory is results/raw. Both smoke cohorts remain separate.

After an interruption, ensure the previous driver has exited, then use:

```
make resume-main
```

The runner never repeats a started cell. It skips immutable final records, mechanically reconstructs interrupted records from available journal evidence, cleans only the affected owned namespace, and continues not-started cells. Recovery is never redispatched for an interrupted cell. Transport ambiguity remains unknown. Truncated journal tails are preserved; session continuation uses new append-only segments. Cleanup failure stops progression rather than permitting overlapping experiment namespaces. Resume requires the same schedule and execution commit. It cannot authorize another cohort.

The runner automatically invokes analyze.py after all scheduled cells have final records, then stops. Analysis reads raw records without changing them, retains ten as every cell's denominator, separates true/false/unknown/N/A and missing/interrupted/error counts, and never pools smoke data. Outputs under results/main-analysis include summary.csv, table.md, PROVENANCE_MANIFEST.json, PAPER_DRAFT.md and diagnostics. Re-running analysis creates a new analysis directory, never overwrites a prior analysis.

The proposed paper insert has a setup paragraph no longer than 120 words, a computed table, three result sentences computed from summary.csv, limitations, the A1 disclosure, and the original-smoke status-conflict interpretation. Exact controller storage timing was not observed, so the sentence records the attribution as journal-based. No result is inserted into the manuscript automatically.

For the long run, macOS caffeinate may hold an idle-sleep assertion while the process runs; it does not change Kubernetes policies or experiment timeouts. Keep the machine powered and the runtime available. Logs and final artifacts persist if the chat disconnects.
