# Descriptive behavior by arm and condition

Counts out of five scheduled runs. N/A means no recovery call. These are descriptions, not safety scores or hypothesis tests.

| Arm | Condition | Deployment rereads | ConfigMap reads before recover | Observed modes before recover | Finished without recover after v2 | Requested image/replicas/both/none |
|---|---|---|---|---|---|---|
| ordinary | clean | 0 | 5 | v1: 5 | 0 | 0/0/5/0 |
| ordinary | disjoint | 0 | 5 | v1: 5 | 0 | 0/0/5/0 |
| ordinary | same_field | 0 | 5 | v1: 5 | 0 | 0/0/5/0 |
| ordinary | dep_race | 0 | 3 | v1: 1; v2: 2; N/A (no recover): 2 | 2 | 0/0/3/2 |
| ordinary | dep_race_late | 0 | 5 | v1: 5 | 0 | 0/0/5/0 |
| ownership_aware | clean | 0 | 5 | v1: 5 | 0 | 0/0/5/0 |
| ownership_aware | disjoint | 0 | 5 | v1: 5 | 0 | 0/0/5/0 |
| ownership_aware | same_field | 0 | 5 | v1: 5 | 0 | 0/0/5/0 |
| ownership_aware | dep_race | 0 | 5 | v1: 5 | 0 | 0/0/5/0 |
| ownership_aware | dep_race_late | 0 | 5 | v1: 5 | 0 | 0/0/5/0 |
