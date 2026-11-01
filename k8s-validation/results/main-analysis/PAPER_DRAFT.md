# Preliminary Kubernetes validation — proposed paper insert

We evaluated four deterministic recovery policies across five controlled interference conditions on a local, single-node kind cluster running Kubernetes v1.34.0. A Deployment served fixed HTTP content through a ClusterIP Service; a ConfigMap supplied the declared recovery predicate. The design prescribed ten repetitions per policy–condition cell (200 runs), ordered using seed 20261101. Each run used a fresh namespace, an induced bad-image change, one recovery decision without retries, and a fixed 90-second outcome window. The cohort produced 200 records, of which 200 completed and 200 had valid fixtures. All scheduled cells remained in the denominators.

| Condition | Snapshot | Field compensation | Object CAS | Ownership |
|---|---|---|---|---|
| clean | 10/10/N/A/10 | 10/10/N/A/10 | 10/10/N/A/10 | 10/10/N/A/10 |
| disjoint | 0/0/0/10 | 10/10/10/10 | 10/0/10/0 | 10/10/10/10 |
| same_field | 0/0/0/10 | 0/0/0/10 | 10/0/10/0 | 10/10/10/10 |
| dep_race | 0/0/10/10 | 0/0/10/10 | 10/0/10/0 | 10/0/10/0 |
| dep_race_late | 0/0/10/10 | 0/0/10/10 | 0/0/10/10 | 0/0/10/10 |

Each cell is safe / successful recovery / operator preserved / healthy; each numeric count has a fixed denominator of ten. Clean preservation is N/A. Unknowns and errors are retained in summary.csv.

Successful recovery occurred in 10/50 runs for snapshot, 20/50 runs for field_comp, 10/50 runs for object_cas, 30/50 runs for ownership. Unsafe overwrites in the disjoint and same-field conditions totaled 20/20 for snapshot, 10/20 for field_comp, 0/20 for object_cas, 0/20 for ownership. Late dependency-race commits under the false predicate occurred in 10/10 runs for snapshot, 10/10 runs for field_comp, 10/10 runs for object_cas, 10/10 runs for ownership.

Before main, author-approved amendment A1 removed metadata.resourceVersion from snapshot PUTs to restore the specified unconditional baseline-replacement policy; the original 20-run smoke cohort and the separate 5-cell snapshot smoke-A1 cohort were retained and excluded from main analysis.

The original smoke’s two version-checked snapshot failures (HTTP 409) were attributed to controller status updates from the recorded status and resource-version changes, although exact server-side write timing was not observed.

The application does not consume mode at runtime and no policy writes the ConfigMap, so operator preservation in dep_race and dep_race_late is expected to be trivial; committed_under_false_predicate measures a violation of the declared recovery contract, not observed application harm.

This validation is limited to a local single-node kind cluster, one assessed workload resource type with a ConfigMap dependency, controlled injection points rather than natural races, deterministic policies without an LLM agent, and ten repetitions per cell.
