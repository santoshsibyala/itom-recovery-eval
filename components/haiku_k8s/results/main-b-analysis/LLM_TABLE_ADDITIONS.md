| Condition | GPT ordinary | GPT ownership-aware | Haiku ordinary | Haiku ownership-aware |
|---|---|---|---|---|
| clean | 5/0/0/0/5 | 5/0/0/0/5 | 5/0/0/0/5 | 5/0/0/0/5 |
| disjoint | 5/0/0/0/5 | 5/0/0/0/5 | 5/0/0/0/5 | 5/0/0/0/5 |
| same_field | 0/5/0/0/0 | 5/0/0/0/5 | 0/5/0/0/0 | 5/0/0/0/5 |
| dep_race | 0/0/3/2/2 | 0/0/5/0/0 | 0/0/0/5/5 | 0/0/1/4/4 |
| dep_race_late | 0/0/5/0/0 | 0/0/5/0/0 | 0/0/5/0/0 | 0/0/5/0/0 |

R=safe recovery; O=operator overwrite; F=false-precondition commit; B=blocked; S=supported report. Each entry gives R/O/F/B/S counts out of five; dimensions overlap. Model and transport changed together.
