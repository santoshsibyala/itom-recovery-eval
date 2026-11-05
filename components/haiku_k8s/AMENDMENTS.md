# ITOM-LLM-K8S-1.1-A1

Approved: Santosh Sibyala, 2026-11-04. The first main launch (`main`) is void as an experimental cohort because the orchestration lifecycle skipped the agent phase. All original records and journals are retained. There were zero model requests and no model-agent outcomes; no model results were observed or used to choose this rerun. The administrative interrupted marker on entry 015 is not a model outcome.

The separately named `main-b` cohort runs all 50 cells, sorted within repetitions by SHA-256 of `20261104|main-b|r|arm|condition`, with new IDs `itom-k8s-llm1104h-main-b-NNN`. Do not continue old entries 016–050. This approved rerun does not authorize replacements within main-b.

Apply the additive MainRun lifecycle repair so the experiment and classification execute for main-b and the canary. To meet the explicitly requested journal order, classification of already collected final evidence occurs before cleanup (the classifier remains byte-identical and pure). Add lifecycle milestone events. No changes to prompt, tools, schemas, transport, budgets, triggers, measurement windows, classifier, behavior measures, deadlines or shared $25 cap. All old experimental modules remain frozen.

Before main-b, one live `canary` run uses a deterministic stub agent, with no provider requests, in a fresh namespace. Its journal must prove baseline → interference injection → full 90-second measurement → classification → cleanup. A failed/skipped/out-of-order stage stops execution. The canary is excluded from every experimental analysis.

After successful canary, execute 50 main-b entries once, retaining failures and following the existing interrupted-resume rules. No replacement or hidden replay. Keep the invalid launch, canary, smoke and main-b separate.

Main-b results must be complete AND reviewed by November 8, 2026 at 9 PM Pacific, otherwise submit v24 unchanged. The paper insert must disclose: “A first main launch failed before any agent execution because of an orchestration defect; it made no model calls and is retained as an invalid cohort. Results come from a separately named rerun.”
