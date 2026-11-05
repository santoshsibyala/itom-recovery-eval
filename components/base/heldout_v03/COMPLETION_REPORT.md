# ITOM held-out evaluation, running-service validation, and draft

Completed 26 October 2026 (local time). IAM remains unchanged.

## Deliverables and verification

- A nine-page [research draft PDF](paper/ITOM_Research_Draft_v01.pdf), plus [editable Markdown](paper/ITOM_Research_Draft_v01.md) and a data-driven build script.
- 216/216 scheduled structural held-out traces, across six new structures and three families. Three malformed inner-argument responses are retained as execution failures; 213 episodes finished without that error. Overall, 205 terminal records satisfy the report format; eight additional malformed terminal reports are retained in grading.
- 108 deterministic held-out baseline trajectories and three calibration traces, kept separate from the model evaluation denominator.
- 42/42 fresh model-driven local HTTP service episodes and 63/63 deterministic service runs, with separate proxy/backend processes and controlled external-writer interference. Across these service runs, 7,143 workload requests are recorded. Their correctness is verified from stored payloads and response digests.
- 19 passing checks: 12 core/trace tests, four real-process integration tests, and three workload-analysis mutation tests. Synthetic traces replay exactly; service verification reconstructs control responses and independently rechecks observed response digests. It does not claim exact replay of wall-clock timing.
- A 36-trace blinded-review packet and two blank reviewer forms. Independent human review has not been performed.
- A pinned RAC source inspection and explicit comparison limits in ARTIFACT_COMPARISON.md.
- All 11,784 original IAM file/symlink entries verified unchanged, with no additional files.

## Findings

Models achieved safe configuration recovery in 49/72 clean/disjoint held-out trials with full-recovery witnesses. Across all 216 deliberately balanced trials, 99 RECOVERED claims were unsupported by the recovery contract, 19 trajectories achieved safe partial recovery, and 26 passed the stricter configuration/audit/report/citation endpoint. Fault-condition rates do not estimate production incidence.

The verification checklist did not reduce observed unsupported-completion counts: GPT 19 to 19, Claude 15 to 16, Gemini 14 to 16. The six-template, single-draw design supports descriptive comparisons only. Recovery counts on clean/disjoint cases changed from 10 to 7, 9 to 10, and 9 to 4, respectively; this is not a provider ranking or a population-level claim that verification instructions are harmful.

The conventional field-compensation baseline recovered all 12 clean/disjoint configurations, compared with six for object CAS. It nevertheless had four historically unsafe dependency-race trajectories and one unsupported completion claim. The implementation's limitations are visible rather than omitted.

In the 42 model-driven service runs, 18 configurations recovered safely, 22 passed response-health windows, and only 12 satisfied both. Six recovered configurations remained unhealthy; ten healthy runs were unsafe/incomplete under the configuration contract. The service experiment uses one local routing application, a shared configuration engine, controlled faults, and short workload windows. It is not production or ServiceNow validation.

## Original shared API budget

The original $15 cap was never reset. Across ALL ITOM cohorts, the reconciled ledger records 3554 attempts, a conservative token-usage estimate of $4.08061065, and $0.4045 retained for the earlier uncertain failed request. The combined bound is **$4.48511065**, below $15. This is a local estimate, not a provider invoice.

The authoritative continuing ledger is ../prototype_v02/live_state/budget.sqlite3. Its working bytes changed because this request authorized additional calls; the original v0.2 ZIP remains the historical snapshot. Future calls must use that same ledger. The new archive contains a consistent snapshot, not permission to reset the cap.

## Manuscript status

The draft describes completed experiments, negative results, uncertainty, protocol failures, relationship to IAM, and prior-art overlap. It contains no invented human review, no production-performance claim, no new transaction-protocol claim, and no superiority claim over named research systems that were not executed. Independent contract/scorer review and broader service/template validation remain necessary before stronger submission claims. The current draft is ready for author and reviewer revision.
