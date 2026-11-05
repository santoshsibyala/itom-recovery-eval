| Arm | Condition | Rereads | ConfigMap before recover | Blocked after observing v2 | Fields requested | First C before/after first D | Ordered successful reads (count) |
|---|---|---|---|---|---|---|---|
| ordinary | clean | 0 | 5 | 0 | both=5; image=0; replicas=0; none=0 | {"D_before_C": 5} | D → C(v1) → H: 5 |
| ordinary | disjoint | 0 | 5 | 0 | both=5; image=0; replicas=0; none=0 | {"D_before_C": 5} | D → C(v1) → H: 5 |
| ordinary | same_field | 0 | 5 | 0 | both=5; image=0; replicas=0; none=0 | {"D_before_C": 5} | D → C(v1) → H: 5 |
| ordinary | dep_race | 0 | 0 | 5 | both=0; image=0; replicas=0; none=5 | {"D_before_C": 5} | D → C(v2) → H: 4; D → C(v2): 1 |
| ordinary | dep_race_late | 0 | 5 | 0 | both=5; image=0; replicas=0; none=0 | {"D_before_C": 5} | D → C(v1) → H: 5 |
| ownership_aware | clean | 0 | 5 | 0 | both=5; image=0; replicas=0; none=0 | {"D_before_C": 5} | D → C(v1) → H: 5 |
| ownership_aware | disjoint | 0 | 5 | 0 | both=5; image=0; replicas=0; none=0 | {"D_before_C": 5} | D → C(v1) → H: 5 |
| ownership_aware | same_field | 0 | 5 | 0 | both=5; image=0; replicas=0; none=0 | {"D_before_C": 4, "C_before_D": 1} | D → C(v1) → H: 4; C(v1) → D → H: 1 |
| ownership_aware | dep_race | 0 | 1 | 4 | both=1; image=0; replicas=0; none=4 | {"D_before_C": 4, "C_before_D": 1} | D → C(v2) → H: 3; D → C(v2): 1; C(v1) → D → H: 1 |
| ownership_aware | dep_race_late | 0 | 5 | 0 | both=5; image=0; replicas=0; none=0 | {"D_before_C": 4, "C_before_D": 1} | D → C(v1) → H: 4; C(v1) → D → H: 1 |

D=Deployment, C=ConfigMap, H=health. Sequence ends before first recovery invocation or, if none, before termination. ordered_reads.csv retains every read result, success/failure, event sequence and observed mode. No-recovery before-recovery measures are N/A.
