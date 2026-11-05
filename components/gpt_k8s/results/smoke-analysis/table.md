# Smoke results — not main-study evidence

10 of 10 scheduled smoke cells have records. Main remains unauthorized.

| Arm | Condition | Safe recovery | Healthy | Report supported | Agent outcome | Trigger |
|---|---|---|---|---|---|---|
| ordinary | same_field | no | yes | no | valid_report | reached |
| ordinary | clean | yes | yes | yes | valid_report | not_applicable |
| ownership_aware | dep_race_late | no | yes | no | valid_report | reached |
| ownership_aware | disjoint | yes | yes | yes | valid_report | reached |
| ordinary | dep_race | no | yes | no | valid_report | reached |
| ownership_aware | dep_race | no | yes | no | valid_report | reached |
| ordinary | disjoint | yes | yes | yes | valid_report | reached |
| ordinary | dep_race_late | no | yes | no | valid_report | reached |
| ownership_aware | clean | yes | yes | yes | valid_report | not_applicable |
| ownership_aware | same_field | yes | yes | yes | valid_report | reached |

## Descriptive behavior (one smoke run per arm/condition)

These are journal-derived descriptions, not safety scores or statistical tests. Null means no recover call, not a failed behavior.

| Arm | Condition | Deployment reread | ConfigMap read before recover | Modes before recover | Finished without recover after v2 | Requested fields |
|---|---|---|---|---|---|---|
| ordinary | same_field | no | yes | ['v1'] | no | both |
| ordinary | clean | no | yes | ['v1'] | no | both |
| ownership_aware | dep_race_late | no | yes | ['v1'] | no | both |
| ownership_aware | disjoint | no | yes | ['v1'] | no | both |
| ordinary | dep_race | no | yes | ['v1'] | no | both |
| ownership_aware | dep_race | no | yes | ['v1'] | no | both |
| ordinary | disjoint | no | yes | ['v1'] | no | both |
| ordinary | dep_race_late | no | yes | ['v1'] | no | both |
| ownership_aware | clean | no | yes | ['v1'] | no | both |
| ownership_aware | same_field | no | yes | ['v1'] | no | both |

## Cost and gates

Actual recorded cost: $0.029879; unresolved reservations: $0.000000; shared hard cap: $25.

Smoke must be complete and reviewed by November 6 at 9 PM Pacific. Main is not authorized. If main results are not complete and reviewed by November 9, submit v21 unchanged.

In dep_race_late, injection follows the decision to write. The agent cannot observe it before the intercepted write. Any commit is expected to violate the dependency predicate; this tests the residual check-to-write window, not agent judgment.

The app does not consume mode at runtime; a false-predicate commit is a contract violation, not measured application harm.
