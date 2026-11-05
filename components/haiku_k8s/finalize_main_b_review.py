"""Package computed main-b results for author review; no experimental actions."""
from common import *
from main_b_execution import verify_frozen
import collections,csv,re

def main():
 verify_frozen();dest=ROOT/'results/main-b-analysis';v=json.loads((dest/'verification.json').read_text());assert v['passed'] and v['main_records']==50
 cleanup=json.loads((dest/'CLUSTER_CLEANUP_CHECK.json').read_text());assert cleanup['passed']
 execution=json.loads((ROOT/'MAIN_B_EXECUTION_FREEZE.json').read_text())
 for n,h in execution['files'].items():assert sha(ROOT/n)==h,n
 bindings()
 raw=list((ROOT/'results/main-b').glob('*.json'));assert len(raw)==50
 old=list((ROOT/'results/main').glob('*.json'));assert len(old)==15
 assert not any((ROOT/'results/journals'/f'itom-k8s-llm1104h-main-{n:03d}.jsonl').exists() for n in range(16,51))
 invalid_events=[json.loads(l) for j in (ROOT/'results/journals').glob('itom-k8s-llm1104h-main-[0-9][0-9][0-9].jsonl') for l in j.read_text().splitlines()]
 assert not any(e['kind'] in ['model_request','model_response','token_count_request','agent_tool_call'] for e in invalid_events)
 failures=json.loads((dest/'trigger_failure_counts.json').read_text());outcomes=collections.Counter();triggers=collections.Counter()
 for row in failures:outcomes.update(row['agent_outcomes']);triggers.update(row['triggers'])
 stats=v['descriptive_totals'];ledger=v['shared_ledger'];now=datetime.datetime.now(datetime.timezone.utc).isoformat()
 text=f'''# ITOM-LLM-K8S-1.1-A1: main-b review handoff

Completed at handoff: {now}. Author review is pending. Completion and review deadline: November 8, 2026, 9 PM Pacific. v24 remains unchanged as the submission fallback.

## Execution and provenance

Amendment 1.1-A1 was approved by Santosh Sibyala on 2026-11-04. Amendment commit: `{json.loads((ROOT/'AMENDMENT_A1_RECEIPT.json').read_text())['commit']}`. Repaired execution commit: `{execution['commit']}`. All 56 tests passed, including the three lifecycle regression tests and the applied MainRun/canary checks. The live canary passed baseline → injection → full 90-second measurement → classification → cleanup, with zero model requests. Its records are excluded from analysis.

The 50 scheduled main-b runs completed with {v['errors']} recorded execution errors. Cleanup succeeded in every run: {v['all_cleanups']}. No replacements were made. The schedule uses `20261104|main-b|r|arm|condition`. The final cluster check found no remaining experiment namespaces.

A first main launch failed before any agent execution because of an orchestration defect; it made no model calls and is retained as an invalid cohort. Results come from a separately named rerun. Its 15 retained records and journals are unchanged. Original main cells 016–050 remain unstarted; main-b has separate IDs and all 50 cells. The invalid launch and canary are excluded from all reported main-b results.

## Computed outcomes

{(dest/'table.md').read_text()}

Outcomes were identical across all five repetitions in {stats['identical_cells']} of 10 cells. There were {stats['unsafe_runs']} unsafe recoveries; {stats['unsafe_healthy']} ended healthy and {stats['unsafe_unsupported']} had unsupported completion reports. These are descriptive results for this tested agent and workload.

## Behavior and ordered reads

{(dest/'behavior_table.md').read_text()}

The agent issued {stats['recovery_requests']} recovery requests. A successful ConfigMap read preceded {stats['configmap_before_recover']} requests; {stats['deployment_rereads_before_recover']} runs reread the Deployment before recovery; {stats['both_fields_requested']} requested both fields. Across all 50 runs, the first successful ConfigMap read preceded the first successful Deployment read in {stats['first_C_before_D']} runs and followed it in {stats['first_D_before_C']}. `ordered_reads.csv` contains per-run ordered reads before recovery or termination, including observed mode and event numbers.

## Triggers and agent outcomes

Agent outcomes: `{json.dumps(dict(outcomes),sort_keys=True)}`.

Trigger outcomes: `{json.dumps(dict(triggers),sort_keys=True)}`.

The late-race injection follows the decision to write; the agent cannot observe that injected change before dispatch. It tests the residual check-to-write window, not agent judgment. The application does not consume mode at runtime, so false-precondition commits measure violations of the declared contract, not observed application harm. Ownership-aware tooling protects fields, not cross-resource preconditions.

## Model, transport and cost

Every successful response returned `{v['model']}`: {v['responses']}/{v['responses']}. Main-b made {v['requests']} generation requests and {v['token_count_requests']} token-count requests. Strict-schema request counts: `{json.dumps(v['strict_modes'])}`. No alias was substituted. Model and transport changed together between cohorts; the comparison does not isolate a model effect or establish that either model is safer.

Main-b actual cost: ${v['main_cost_usd']:.8f}. Prior 1.0 smoke plus main: ${ledger['prior_1_0_usd']:.8f}. Cohort 1.1 smoke plus main-b: ${ledger['actual_1_1_usd']:.8f}. Shared total: ${ledger['total_bound_usd']:.8f}, with ${ledger['pending_reserved_usd']:.8f} pending reservations against the $25 cap. The invalid launch and canary made zero model requests.

## Deliverables

- `summary.csv`, `table.md`: classifier outcomes by arm and condition.
- `behavior.csv`, `behavior_table.md`, `ordered_reads.csv`: descriptive behavior and inspectable read order.
- `trigger_failure_counts.json`: all trigger/failure categories, including zeros.
- `model_id_confirmation.json`: response-level model-ID checks.
- `LLM_TABLE_ADDITIONS.md` and `LLM_BEHAVIOR_TABLE_ADDITIONS.md`: side-by-side two-cohort tables.
- `PAPER_INSERT_FOR_REVIEW.md`: {v['paper_insert_words']} computed prose words plus tables, including the required incident disclosure.
- `verification.json`, `PROVENANCE_MANIFEST.json`, `CLUSTER_CLEANUP_CHECK.json`: verification and source bindings.

No manuscript or v24 changes were made. No repository publication or visibility changes were made. Stop here for author review.
'''
 with (dest/'MAIN_B_REVIEW.md').open('x') as f:f.write(text)
 # Pattern scan of generated reports and main-b journal content; never emits matching secret values.
 patterns={'provider_key':r'\bsk-(?:ant-)?[A-Za-z0-9_-]{20,}', 'github_token':r'\b(?:ghp_|github_pat_)[A-Za-z0-9_]{20,}', 'private_key':r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----', 'bearer_secret':r'(?i)authorization[\"\s:]+bearer\s+[A-Za-z0-9._-]{16,}'}
 scanned=[p for p in dest.iterdir() if p.is_file()]+raw+list((ROOT/'results/journals').glob('itom-k8s-llm1104h-main-b-*.jsonl'));hits=[]
 for p in scanned:
  s=p.read_text()
  for label,pattern in patterns.items():
   if re.search(pattern,s):hits.append({'file':str(p.relative_to(ROOT)),'pattern':label})
 save(dest/'CREDENTIAL_PATTERN_SCAN.json',dict(scanned_files=len(scanned),findings=hits,passed=not hits,scope='Credential-pattern scan of main-b raw records, journals and generated reports; not a general guarantee against all sensitive material.'))
 assert not hits,'Potential credential patterns found; inspect without publishing.'
 files=set()
 for directory in ['results/main-b','results/main-b-analysis','results/canary','results/main-incident']:
  files.update(p for p in (ROOT/directory).rglob('*') if p.is_file())
 files.update((ROOT/'results/journals').glob('itom-k8s-llm1104h-main-b-*.jsonl'))
 files.update((ROOT/'results/journals').glob('itom-k8s-llm1104h-canary-*.jsonl'))
 for name in ['AMENDMENTS.md','AMENDMENT_A1_APPROVAL.json','AMENDMENT_A1_RECEIPT.json','MAIN_B_EXECUTION_FREEZE.json','MAIN_APPROVAL.json','PROTOCOL_FREEZE_RECEIPT.json','SMOKE_HANDOFF_MANIFEST.json','main_b_schedule.json','main_b_execution.py','live_canary.py','analyze_main_b.py','finalize_main_b_review.py','results/main-b-tests.json','results/main-b-preflight.json','results/cost.sqlite3']:
  files.add(ROOT/name)
 save(ROOT/'MAIN_B_HANDOFF_MANIFEST.json',dict(created_utc=now,review_pending=True,cohort='main-b',amendment='ITOM-LLM-K8S-1.1-A1',files={str(p.relative_to(ROOT)):sha(p) for p in sorted(files)}))
 print(json.dumps(dict(review=str(dest/'MAIN_B_REVIEW.md'),handoff_sha256=sha(ROOT/'MAIN_B_HANDOFF_MANIFEST.json'),files=len(files),credential_findings=len(hits))))
if __name__=='__main__':main()
