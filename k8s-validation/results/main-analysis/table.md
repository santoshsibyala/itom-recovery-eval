| Condition | Snapshot | Field compensation | Object CAS | Ownership |
|---|---|---|---|---|
| clean | 10/10/N/A/10 | 10/10/N/A/10 | 10/10/N/A/10 | 10/10/N/A/10 |
| disjoint | 0/0/0/10 | 10/10/10/10 | 10/0/10/0 | 10/10/10/10 |
| same_field | 0/0/0/10 | 0/0/0/10 | 10/0/10/0 | 10/10/10/10 |
| dep_race | 0/0/10/10 | 0/0/10/10 | 10/0/10/0 | 10/0/10/0 |
| dep_race_late | 0/0/10/10 | 0/0/10/10 | 0/0/10/10 | 0/0/10/10 |

Each cell is safe / successful recovery / operator preserved / healthy; each numeric count has a fixed denominator of ten. Clean preservation is N/A. Unknowns and errors are retained in summary.csv.
