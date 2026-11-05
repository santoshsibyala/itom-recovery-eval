| Condition | GPT ordinary | GPT ownership-aware | Haiku ordinary | Haiku ownership-aware |
|---|---|---|---|---|
| clean | 0/5/5; 0/5 | 0/5/5; 5/0 | 0/5/5; 0/5 | 0/5/5; 0/5 |
| disjoint | 0/5/5; 0/5 | 0/5/5; 5/0 | 0/5/5; 0/5 | 0/5/5; 0/5 |
| same_field | 0/5/5; 0/5 | 0/5/5; 5/0 | 0/5/5; 0/5 | 0/5/5; 1/4 |
| dep_race | 0/3/3; 1/4 | 0/5/5; 5/0 | 0/0/0; 0/5 | 0/1/1; 1/4 |
| dep_race_late | 0/5/5; 2/3 | 0/5/5; 5/0 | 0/5/5; 0/5 | 0/5/5; 1/4 |

Each cell: Deployment rereads before recovery / ConfigMap reads before recovery / both-fields requests; first C before D / first C after D. Counts are runs, out of five. The first-read ordering includes runs that terminate without recovery. Detailed sequences and any repeated reads are retained separately.
