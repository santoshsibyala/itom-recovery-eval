# Main execution incident — stopped for review

The new additive main runner incorrectly instantiated ExtensionRun, whose inherited fixture lifecycle recognizes only smoke and smoke-A1. It therefore executed baseline/cleanup but skipped the agent, interference experiment and measurement window. The agent, tools, transport, classifier and frozen 1.1 implementation were not changed.

The assistant introduced this orchestration defect. The prelaunch tests checked authorization, deadlines, interruption and the frozen modules, but missed main-phase lifecycle dispatch. Their pass result was insufficient to establish main execution readiness.

## Preserved state

- 50 scheduled entries; 15 started, 35 never started.
- Entries 001–014: baseline-only raw records retained byte-for-byte. Their original completed=true flag describes the wrapper finishing, NOT a valid main experiment. Supplemental status labels them invalid_harness_baseline_only. They must not be scored as recoveries, blocks, agent failures or evidence of model behavior.
- Entry 015: interruption occurred during cleanup; journal retained, and an interrupted raw record was finalized using the frozen resume function without replay.
- Zero model requests or additional model charges. Shared spend remains $0.4441556.
- Final cluster check: no experimental namespaces remain.
- No replacement runs. v24, 1.0 and the 1.1 smoke evidence remain unchanged.

## Concrete repair proposed, not applied

proposed_main_repair.py supplies an additive MainRun lifecycle that recognizes main in the two phase guards: experiment dispatch and classification. It calls the unchanged baseline, experiment, measurement and cleanup primitives and explicitly binds CLUSTER to avoid the earlier 1.0 cleanup binding error. The active wrapper would instantiate this class instead of ExtensionRun. No prompt, tool, schema, schedule, budget, transport, classifier or behavior change is proposed.

A targeted lifecycle regression test must demonstrate that main invokes experiment exactly once, classifies once and cleans up; setup must not invoke experiment. The original main phase must fail that test. The repair is held for review and is not a new experimental run.

If continuation is approved, only entries 016–050 may run under the current no-replacement rule. The first 15 entries remain in the denominator as invalid/interrupted scheduled attempts. A complete 50-valid-run cohort cannot be claimed. Do not quietly restart or replace the affected cells. Alternatively, stop this extension and retain v24.

## Requested deliverables

Results, behavior comparisons and a scientific paper insert are withheld because there are no valid main experiments yet. results/main-incident/scheduled_status.csv accounts for all 50 entries; INCIDENT.json and PRESERVED_RECORDS_MANIFEST.json document the failure and preserved evidence. Do not use the unfinished analyze_main.py to produce a complete-cohort result.

## Repair test result

Three offline lifecycle tests passed: reproduction of the original main-phase skip, proposed main experiment/classification exactly once with cleanup, and unchanged setup behavior. The repair remains unapplied. See results/main-incident/PROPOSED_REPAIR_TESTS.json.
