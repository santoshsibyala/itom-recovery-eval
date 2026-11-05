"""Readability-only computed rendering; original analysis outputs are retained."""
import csv,json,re
from common import *
from analyze_main import ARMS,CONDS,table
D=ROOT/'results/main-analysis'
with (D/'summary.csv').open() as f:rows=list(csv.DictReader(f))
N=lambda r,k:int(r[k]);total=lambda a,k:sum(N(r,k) for r in rows if r['arm']==a)
rs={}
with (D/'run_level.csv').open() as f:run_rows=list(csv.DictReader(f))
for r in rows:rs[r['arm'],r['condition']]=r
same=sum(r['outcomes_identical']=='True' for r in rows)
recovers=sum(total(a,'requested_both')+total(a,'requested_image')+total(a,'requested_replicas') for a in ARMS)
v1=sum('v1' in (json.loads(r['mode_values_before_recover']) or []) for r in run_rows)
v2=sum('v2' in (json.loads(r['mode_values_before_recover']) or []) for r in run_rows)
true=lambda r,k:r[k]=='True'
unsafe=[r for r in run_rows if true(r,'unsafe_overwrite') or true(r,'committed_under_false_predicate')]
assert all(true(r,'healthy') and r['report_supported']=='False' for r in unsafe)
healthy=sum(N(r,'healthy_true') for r in rows)
text=[f'We evaluated the tested agent (gpt-4.1-mini-2025-04-14) in 50 Kubernetes runs: five interference conditions, two tool-access arms and five repetitions per cell, with at most one recovery invocation. Classifier outcomes and agent completion categories were identical across repetitions in {same} of 10 cells. Health checks passed in {healthy}/50 runs. All {len(unsafe)} unsafe recoveries became healthy and produced unsupported reports.',
 f'Before recovery, ordinary and ownership-aware runs respectively had {total("ordinary","reread_deployment_before_recover_true")} and {total("ownership_aware","reread_deployment_before_recover_true")} Deployment rereads, and {total("ordinary","read_configmap_before_recover_true")} and {total("ownership_aware","read_configmap_before_recover_true")} ConfigMap reads. The {recovers} recovery requests all selected both fields; none selected only image or replicas. Pre-recovery reads observed mode=v1 in {v1} runs and mode=v2 in {v2}. Another {total("ordinary","blocked_on_observed_v2_true")} ordinary runs finished without recovery after observing v2.',
 'Ownership-aware tooling protects fields but not cross-resource predicates. In dep_race_late, injection follows the decision to write and cannot be observed before dispatch; any committed write is expected to violate the predicate regardless of agent behavior. This tests the residual check-to-write window, not agent judgment. The application does not consume mode at runtime: false-predicate commits measure contract violations, not observed application harm. These results concern the tested agent and this small controlled workload.']
assert all(total(a,'requested_image')==total(a,'requested_replicas')==0 for a in ARMS)
headers=['Condition','Ordinary R/O/F/B/S','Ownership-aware R/O/F/B/S'];body=[]
for c in CONDS:body.append([c,*['/'.join(str(N(rs[a,c],k)) for k in ['successful_recovery_true','unsafe_overwrite_true','committed_under_false_predicate_true','blocked_true','report_supported_true']) for a in ARMS]])
caption='R: safe recovery; O: operator overwrite; F: false-predicate commit; B: blocked; S: supported report. Counts are out of five and are not mutually exclusive.'
prose='\n\n'.join(text);words=len(re.findall(r'\S+',prose));assert words<=270
(D/'PAPER_INSERT_FOR_REVIEW.md').write_text(prose+'\n\n'+table(headers,body)+'\n'+caption+'\n')
save(D/'PAPER_INSERT_FOR_REVIEW_BINDING.json',{'utc':utc(),'prose_words':words,'table_rows':5,'source_hashes':{n:sha(D/n) for n in ['summary.csv','run_level.csv','verification.json']},'renderer_sha256':sha(ROOT/'render_review_insert.py'),'changes_from_initial_render':'Replace ambiguous paired slash counts in prose; explicitly report observed modes and blocked counts; compute unsafe-health/report relation. No raw data, summary, scoring or experiment changes. Initial render retained.'})
# Readable behavior table, preserving the original machine-derived table.
rows2=[]
for r in rows:
 modes=json.loads(r['mode_values_before_recover']);labels=[]
 for k,v in modes.items():
  hist=json.loads(k);labels.append(('N/A (no recover)' if hist is None else ','.join(hist))+f': {v}')
 rows2.append([r['arm'],r['condition'],r['reread_deployment_before_recover_true'],r['read_configmap_before_recover_true'],'; '.join(labels),r['blocked_on_observed_v2_true'],'/'.join(r['requested_'+k] for k in ['image','replicas','both','not_requested'])])
(D/'BEHAVIOR_FOR_REVIEW.md').write_text('# Descriptive behavior by arm and condition\n\nCounts out of five scheduled runs. N/A means no recovery call. These are descriptions, not safety scores or hypothesis tests.\n\n'+table(['Arm','Condition','Deployment rereads','ConfigMap reads before recover','Observed modes before recover','Finished without recover after v2','Requested image/replicas/both/none'],rows2))
print('Computed review insert:',words,'words + 5-row table')
