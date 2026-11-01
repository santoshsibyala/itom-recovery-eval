# Approved A1 supplementary smoke results

Five snapshot-only supplementary cells; original 20-cell smoke remains separate and unchanged. Main has not started.

Approval: Santosh Sibyala; recorded UTC 2026-11-01T01:10:29.691488+00:00.
Amendment commit: `9e5e04e7ac6591035f51f7bf5b4727fe1a9fb01c`.
Implementation commit: `0ff095f2db1bdf45e6c4b003c0714658fd623f88`.
Execution/provenance commit: `9a55e7f2e347ff64aa85bb8fccdce19e892a09fb`.

- Effective `K8S_PROTOCOL.md` SHA-256: `08fd3e7f6f40361b8a7da4a6dec67d5152698bb1d35fcb2e7da13cc5ded11aa2`
- Effective `PROTOCOL_DETAILS.md` SHA-256: `345300a594b0c8a295623f677b4170ed00760b5a4c0220fcb5aa0be5e094821c`

Tests: 24/24 passed (15 existing classifier tests and 9 focused request-construction/behavior tests). The focused tests cover absent snapshot RV/status/managedFields, full baseline spec and retained live metadata, early/late injection order, initial predicate block, rejection/timeout without retry or force, unchanged CAS original-RV test and predicate recheck, and unchanged field-compensation request.

Completed: 5/5; valid fixtures: 5/5; recorded errors: 0.

| Condition | PUT HTTP | Safe | Recovery | Operator preserved | Healthy | Report supported | Errors |
|---|---:|---|---|---|---|---|---:|
| dep_race_late | 200 | no | no | yes | yes | no | 0 |
| same_field | 200 | no | no | no | yes | no | 0 |
| dep_race | 200 | no | no | yes | yes | no | 0 |
| clean | 200 | yes | yes | N/A | yes | yes | 0 |
| disjoint | 200 | no | no | no | yes | no | 0 |

## Observations

- dep_race_late: outcome=ack; unsafe_overwrite=no; committed_under_false_predicate=yes; blocked=no.
- same_field: outcome=ack; unsafe_overwrite=yes; committed_under_false_predicate=no; blocked=no.
- dep_race: outcome=ack; unsafe_overwrite=no; committed_under_false_predicate=yes; blocked=no.
- clean: outcome=ack; unsafe_overwrite=no; committed_under_false_predicate=no; blocked=no.
- disjoint: outcome=ack; unsafe_overwrite=yes; committed_under_false_predicate=no; blocked=no.

## Original snapshot versus A1 (separate cohorts)

This comparison reports single smoke observations per condition, not a causal estimate or a pooled benchmark. The original failures are not replaced.

| Condition | Original outcome / HTTP | A1 outcome / HTTP |
|---|---|---|
| dep_race_late | ack / success | ack / 200 |
| same_field | rejected / 409 | ack / 200 |
| dep_race | ack / success | ack / 200 |
| clean | ack / success | ack / 200 |
| disjoint | rejected / 409 | ack / 200 |

## Integrity and interpretation

Every supplementary snapshot PUT omitted metadata.resourceVersion and used the full baseline spec. No forced recovery or repeated mutation was found. Status settling passed in 5/5; complete observation windows: 5/5. All experiment namespaces were removed.
The dependency mode is not consumed by the application and no policy writes the ConfigMap. Dependency preservation is therefore trivial; commits under mode v2 are declared-contract violations, not observed application harm. Health alone does not establish successful recovery under the frozen metrics.
All 59 original handoff files match their preserved hashes. Effective protocol, implementation, approval, journal, schedule, dependency, image and environment hashes were verified for every supplementary record.

## Stop gate

Stop here for author review. A1 approval does not approve main. No policies were adjusted after observing supplementary outcomes. No main run or manuscript update occurred.
