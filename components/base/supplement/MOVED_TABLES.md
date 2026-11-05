# Tables retained in the artifact

Original full-length numbering is retained here. Tables 1, 2, 10, 16, and 17 map to workshop Tables I–V; workshop Table III also adds history-violation counts from the existing surrounding prose.

| Template | Trials | Safe config. | Partial | Unsafe claims |
| --- | --- | --- | --- | --- |
| durable_queue | 36 | 9 | 6 | 18 |
| retry_fanout | 36 | 8 | 2 | 19 |
| route_failover | 36 | 12 | 0 | 16 |
| schema_chain | 36 | 6 | 4 | 21 |
| shared_image | 36 | 9 | 4 | 12 |
| weighted_fanout | 36 | 5 | 3 | 13 |

Table 3. Template-level outcomes, pooling only the equally scheduled model/arm cells for descriptive coverage. These are six structural units, not 216 independent templates.

| Condition | Trials | Safe config. | History violations | Unsafe claims |
| --- | --- | --- | --- | --- |
| clean | 36 | 26 | 2 | 5 |
| dependency_race | 36 | 0 | 29 | 25 |
| disjoint | 36 | 23 | 3 | 7 |
| hidden_owner | 36 | 0 | 30 | 32 |
| partial_failure | 36 | 0 | 0 | 3 |
| superseded | 36 | 0 | 26 | 27 |

Table 4. Outcomes by deliberately selected intervention condition. History violations include scope, order, protected-work, and predicate violations. These frequencies are not estimates of production incidence.

| Model | Endpoint | Verify - ordinary (pp) | 95% descriptive interval (pp) |
| --- | --- | --- | --- |
| GPT-4.1 mini | Unsafe claims | +0.0 | [-13.9, +13.9] |
| GPT-4.1 mini | Clean/disjoint recovery | -25.0 | [-33.3, -16.7] |
| Claude Haiku 4.5 | Unsafe claims | +2.8 | [-11.1, +16.7] |
| Claude Haiku 4.5 | Clean/disjoint recovery | +8.3 | [+0.0, +16.7] |
| Gemini 3.1 Flash-Lite | Unsafe claims | +5.6 | [-11.1, +22.2] |
| Gemini 3.1 Flash-Lite | Clean/disjoint recovery | -41.7 | [-66.7, -16.7] |

Table 5. Paired template-level differences. Negative unsafe-claim differences favor verify; positive recovery differences favor verify. Intervals use the predeclared stratified template bootstrap. They should not be read as model rankings or evidence of equivalence when near zero.

| Model | Arm | Safe config. / 7 | Healthy / 7 | Operational / 7 |
| --- | --- | --- | --- | --- |
| Claude Haiku 4.5 | ordinary | 3 | 4 | 2 |
| Claude Haiku 4.5 | verify | 3 | 4 | 2 |
| Gemini 3.1 Flash-Lite | ordinary | 3 | 4 | 2 |
| Gemini 3.1 Flash-Lite | verify | 3 | 4 | 2 |
| GPT-4.1 mini | ordinary | 3 | 3 | 2 |
| GPT-4.1 mini | verify | 3 | 3 | 2 |

Table 6. Fresh model-driven local service runs, seven conditions per arm. Healthy means V alone. Operational recovery requires both C and V.

| Service baseline | Safe config. / 21 | Healthy / 21 | Operational / 21 |
| --- | --- | --- | --- |
| field_compensator | 9 | 6 | 6 |
| object_cas | 6 | 3 | 3 |
| snapshot | 6 | 12 | 3 |

Table 7. Service baseline runs. Three resets per condition test execution repeatability; they do not supply three independent application structures.

| Model | Endpoint | Full contrast (pp) | Leave-one-family-out range (pp) |
| --- | --- | --- | --- |
| Claude Haiku 4.5 | Unsafe claims | +2.8 | [+0.0, +4.2] |
| Claude Haiku 4.5 | Clean/disjoint recovery | +8.3 | [+0.0, +12.5] |
| Gemini 3.1 Flash-Lite | Unsafe claims | +5.6 | [+0.0, +8.3] |
| Gemini 3.1 Flash-Lite | Clean/disjoint recovery | -41.7 | [-62.5, -25.0] |
| GPT-4.1 mini | Unsafe claims | +0.0 | [-12.5, +8.3] |
| GPT-4.1 mini | Clean/disjoint recovery | -25.0 | [-37.5, +0.0] |

Table 8. Post-hoc influence analysis. Contrasts are verify minus ordinary. Ranges describe three omissions, not confidence intervals; remaining families receive equal weight.

| Policy | N | Safe config. | History violations | Evidence-qualified config. |
| --- | --- | --- | --- | --- |
| atomic_guard | 96 | 39 | 0 | 39 |
| field | 96 | 39 | 12 | 39 |
| noop | 96 | 0 | 0 | 0 |
| object_cas | 96 | 27 | 12 | 27 |
| owner_guard | 96 | 39 | 12 | 39 |
| snapshot | 96 | 0 | 90 | 0 |

Table 9. Offline follow-up controls. Repeated cases are not independent structural units. Scope semantics and privileged snapshot information are described in the text.

| Model | Arm | N | Safe config. | History violations | Terminal-inconsistent claims | Qualified config. | Qualified operational |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Claude Haiku 4.5 | atomic | 48 | 12 | 0 | 4 | 0 | 0 |
| Claude Haiku 4.5 | evidence_only | 48 | 7 | 9 | 10 | 0 | 0 |
| Gemini 3.1 Flash-Lite | atomic | 48 | 9 | 0 | 3 | 0 | 0 |
| Gemini 3.1 Flash-Lite | evidence_only | 48 | 15 | 15 | 18 | 0 | 0 |
| GPT-4.1 mini | atomic | 48 | 0 | 0 | 0 | 0 | 0 |
| GPT-4.1 mini | evidence_only | 48 | 1 | 1 | 0 | 1 | 0 |

Table 11. All scheduled main follow-up trajectories. Qualified denotes the new evidence contract, not the earlier strict endpoint. Terminal-inconsistent claims include operational claims failing measured health. Protocol failures remain in denominators.

| Model | Endpoint | Atomic minus evidence (pp) | 95% descriptive interval (pp) |
| --- | --- | --- | --- |
| Claude Haiku 4.5 | History violations | -18.8 | [-33.3, -6.2] |
| Claude Haiku 4.5 | Safe configuration | +10.4 | [+0.0, +25.0] |
| Claude Haiku 4.5 | Qualified configuration | +0.0 | [+0.0, +0.0] |
| Claude Haiku 4.5 | Qualified operational | +0.0 | [+0.0, +0.0] |
| Claude Haiku 4.5 | Inconsistent claims | -12.5 | [-29.2, +2.1] |
| Gemini 3.1 Flash-Lite | History violations | -31.2 | [-56.2, -12.5] |
| Gemini 3.1 Flash-Lite | Safe configuration | -12.5 | [-37.5, +12.5] |
| Gemini 3.1 Flash-Lite | Qualified configuration | +0.0 | [+0.0, +0.0] |
| Gemini 3.1 Flash-Lite | Qualified operational | +0.0 | [+0.0, +0.0] |
| Gemini 3.1 Flash-Lite | Inconsistent claims | -31.2 | [-56.2, -12.5] |
| GPT-4.1 mini | History violations | -2.1 | [-6.2, -0.0] |
| GPT-4.1 mini | Safe configuration | -2.1 | [-6.2, +0.0] |
| GPT-4.1 mini | Qualified configuration | -2.1 | [-6.2, +0.0] |
| GPT-4.1 mini | Qualified operational | +0.0 | [+0.0, +0.0] |
| GPT-4.1 mini | Inconsistent claims | +0.0 | [+0.0, +0.0] |

Table 12. Paired follow-up contrasts. Lower history-violation/claim values and higher recovery values favor the atomic arm. Sixteen application/condition blocks do not represent sixteen independent applications.

| Model | Interface | N | Errors | Safe config. | Qualified config. | Qualified operational |
| --- | --- | --- | --- | --- | --- | --- |
| Claude Haiku 4.5 | JSON string | 24 | 0 | 7 | 0 | 0 |
| Gemini 3.1 Flash-Lite | JSON string | 24 | 6 | 10 | 0 | 0 |
| GPT-4.1 mini | JSON string | 24 | 22 | 1 | 1 | 0 |
| Claude Haiku 4.5 | Typed fields | 24 | 3 | 0 | 0 | 0 |
| Gemini 3.1 Flash-Lite | Typed fields | 24 | 0 | 12 | 0 | 0 |
| GPT-4.1 mini | Typed fields | 24 | 2 | 3 | 0 | 0 |

Table 13. Matched task specifications, not paired model random draws. Counts pool runtime arms for interface description; arm-level results and all raw responses remain available.

| Model | Interface | N | Errors | Safe config. | Qualified config. | Qualified operational |
| --- | --- | --- | --- | --- | --- | --- |
| Claude Haiku 4.5 | String matched | 12 | 0 | 3 | 0 | 0 |
| Gemini 3.1 Flash-Lite | String matched | 12 | 3 | 5 | 0 | 0 |
| GPT-4.1 mini | String matched | 12 | 11 | 0 | 0 | 0 |
| Claude Haiku 4.5 | Function calls | 12 | 0 | 3 | 2 | 2 |
| Gemini 3.1 Flash-Lite | Function calls | 12 | 0 | 8 | 7 | 7 |
| GPT-4.1 mini | Function calls | 12 | 0 | 8 | 5 | 1 |

Table 14. Fixed 36-case function-calling sensitivity cohort and its original matched subset. Later execution, descriptions and schemas confound pure interface effects; no provider ranking is inferred.

| Cohort | Adapter runtime | N | Safe config. | History violations | Qualified config. |
| --- | --- | --- | --- | --- | --- |
| offline | RAC-adapter-atomic | 96 | 39 | 0 | 36 |
| offline | RAC-adapter-none | 96 | 39 | 12 | 36 |
| service | RAC-adapter-atomic | 16 | 7 | 0 | 6 |
| service | RAC-adapter-none | 16 | 7 | 2 | 6 |

Table 15. Bounded execution of the same pinned RAC rollback core and adapter under two runtime contracts. Single service resets per cell; no model calls in this integration.
