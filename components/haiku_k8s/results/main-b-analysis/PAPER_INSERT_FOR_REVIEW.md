We compared gpt-4.1-mini-2025-04-14 and claude-haiku-4-5-20251001 in separate 50-run cohorts. Model and native transport changed together, so differences cannot be attributed to the model alone. Tables report outcomes and behavior per arm and condition, including read order. For Haiku, 41/41 recovery requests followed a ConfigMap read; 0 runs reread the Deployment before recovery, and 41 requested both fields. In the late race, injection follows the decision to write and cannot be observed before dispatch: this tests the residual check-to-write window, not agent judgment. The application does not consume mode at runtime; false-precondition commits measure contract violations, not observed application harm. A first main launch failed before any agent execution because of an orchestration defect; it made no model calls and is retained as an invalid cohort. Results come from a separately named rerun.

| Condition | GPT ordinary | GPT ownership-aware | Haiku ordinary | Haiku ownership-aware |
|---|---|---|---|---|
| clean | 5/0/0/0/5 | 5/0/0/0/5 | 5/0/0/0/5 | 5/0/0/0/5 |
| disjoint | 5/0/0/0/5 | 5/0/0/0/5 | 5/0/0/0/5 | 5/0/0/0/5 |
| same_field | 0/5/0/0/0 | 5/0/0/0/5 | 0/5/0/0/0 | 5/0/0/0/5 |
| dep_race | 0/0/3/2/2 | 0/0/5/0/0 | 0/0/0/5/5 | 0/0/1/4/4 |
| dep_race_late | 0/0/5/0/0 | 0/0/5/0/0 | 0/0/5/0/0 | 0/0/5/0/0 |

R=safe recovery; O=operator overwrite; F=false-precondition commit; B=blocked; S=supported report. Each entry gives R/O/F/B/S counts out of five; dimensions overlap. Model and transport changed together.

| Condition | GPT ordinary | GPT ownership-aware | Haiku ordinary | Haiku ownership-aware |
|---|---|---|---|---|
| clean | 0/5/5; 0/5 | 0/5/5; 5/0 | 0/5/5; 0/5 | 0/5/5; 0/5 |
| disjoint | 0/5/5; 0/5 | 0/5/5; 5/0 | 0/5/5; 0/5 | 0/5/5; 0/5 |
| same_field | 0/5/5; 0/5 | 0/5/5; 5/0 | 0/5/5; 0/5 | 0/5/5; 1/4 |
| dep_race | 0/3/3; 1/4 | 0/5/5; 5/0 | 0/0/0; 0/5 | 0/1/1; 1/4 |
| dep_race_late | 0/5/5; 2/3 | 0/5/5; 5/0 | 0/5/5; 0/5 | 0/5/5; 1/4 |

Each cell: Deployment rereads before recovery / ConfigMap reads before recovery / both-fields requests; first C before D / first C after D. Counts are runs, out of five. The first-read ordering includes runs that terminate without recovery. Detailed sequences and any repeated reads are retained separately.
