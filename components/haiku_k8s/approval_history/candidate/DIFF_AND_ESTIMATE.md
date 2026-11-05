# ITOM-LLM-K8S-1.1 — review handoff

Status: candidate only, not approved/frozen; no implementation, tests, setup, provider calls or runs performed. Full line diff: PROTOCOL_DIFF.patch. Full proposed protocol: LLM_K8S_PROTOCOL.md.

| Change | 1.0 | 1.1 candidate |
|---|---|---|
| Model | gpt-4.1-mini-2025-04-14 | claude-haiku-4-5-20251001, thinking disabled, temperature 0 |
| Native transport | OpenAI Responses | Anthropic Messages; required single tool; strict schemas |
| Schedule seed | 20261103 | 20261104; same per-round SHA-256 ordering, smoke phase separate |
| Input counting | local OpenAI tokenizer estimate +512 | native Anthropic estimate +512; same token ceilings |
| Cost ledger | 1.0 shared smoke/main | NEW shared cross-cohort ledger, prior costs/reserves imported once; original ledger read-only |
| Cost bound | completed spend $0.1795376 | $15.66 ceiling for 60 runs; $23.44414645 including earlier paper bound and 1.0 |
| Smoke gate | Nov 6, 9 PM Pacific | unchanged; author review required |
| Main review gate | Nov 9 | Nov 8, 9 PM Pacific |
| Fallback | v21 | v24 unchanged |

Unchanged: 10 smoke cells; 50 main runs; five conditions; two write arms; five main repetitions/cell; system prompt, task payload semantics, tools and descriptions; event triggers including first-write late interception; 18 turns/tools, one recovery invocation, 900 output/request, 20K input/request, 180K cumulative input, 600-second agent limit; full 90-second observation; no retries/replacements; byte-identical classifier and behavior logic; failures retained; smoke never pooled with main. Model and native transport vary together, so comparisons cannot isolate model weights from provider-interface effects.

## Time estimate after approval

Reusing the tested fixture, tools, classifier and analysis should reduce implementation time compared with 1.0. These are estimates, not promises.

| Stage | Estimate |
|---|---:|
| Anthropic adapter, shared-ledger import, provenance and phase-aware gates | 3–5 active hours |
| Offline serialization/schema/budget/resume tests and differential fixture/classifier checks | 2–3 active hours |
| Environment/access check and baseline | 0.5–1 hour |
| Ten sequential smoke runs and handoff | 0.5–1.5 hours execution + 0.5–1 hour verification |
| Author smoke review | Allow 0.5–1 hour; availability-dependent |
| Fifty sequential main runs | 2–4 hours expected + 0.5 hour monitoring |
| Analysis, model-ID/trigger/failure/behavior audit and computed insert | 2–3 active hours |
| Author main review | Allow 0.5–1 hour; availability-dependent |

Approximately 9–14 active hours plus 2.5–5.5 hours experiment execution and author review, usually 2–3 calendar days. The main observation windows alone require 75 minutes. If all 50 runs use their full 600-second agent allowance, agent + observation time alone reaches 9 hours 35 minutes, before setup/cleanup. Outages, count-endpoint latency or defects can exceed estimates.

Preferred plan: approve and implement Nov 4–5; smoke and review Nov 5 or early Nov 6; main Nov 6–7; audit and author review by Nov 8 afternoon. Hard gates remain Nov 6 21:00 Pacific for reviewed smoke and Nov 8 21:00 Pacific for reviewed main. Do not launch when remaining time cannot reasonably fit measurement and review. Missing either gate preserves v24 as submission.

## Accounting scope

Interpreting “all LLM cohorts” conservatively includes the earlier paper's $7.60460885 bound, not just Kubernetes. Add 1.0's $0.1795376: initial committed/reserved balance $7.78414645. At $1/M input and $5/M output, 60*(180000*1 + 16200*5)/1e6 = $15.66. Total planned ceiling $23.44414645 < $25. Remaining margin $1.55585355. This can still stop early due to conservative unknown-request reservations; never loosen caps or replace runs to finish. Source ledgers remain unchanged.

## Approval boundary

Only candidate documents and a hash manifest are produced now. After author approval, record approval/time, freeze approved protocol hashes in a separate 1.1 receipt, implement and freeze the transport/schedules/dependencies, run tests/setup and ten smoke cells, then stop. Main remains unauthorized until a separate timely smoke review and main approval. No changes or upload to v24.
