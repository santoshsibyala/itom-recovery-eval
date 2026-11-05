"""Read-only journal audit and computed two-agent main-cohort comparison."""
import csv,io,collections
from common import *
from main_execution import verify_frozen
from classify import classify
ARMS=['ordinary','ownership_aware'];CONDS=['clean','disjoint','same_field','dep_race','dep_race_late']
METRICS=['image_restored','unsafe_overwrite','committed_under_false_predicate','blocked','safety','successful_recovery','healthy','report_supported']
FAILURES=['valid_report','malformed_report','malformed_tool_call','no_report','budget_exhausted','provider_error','interrupted','not_started']
TRIGGERS=['reached','not_applicable','late_trigger_not_reached','late_trigger_reached_no_commit','early_trigger_not_reached','injection_failed','unknown_interrupted','not_reached']
def write_text(p,s):
 with p.open('x') as f:f.write(s)
def csvwrite(p,rows):
 out=io.StringIO();keys=list(dict.fromkeys(k for r in rows for k in r));w=csv.DictWriter(out,fieldnames=keys);w.writeheader()
 for r in rows:w.writerow({k:json.dumps(v,sort_keys=True) if isinstance(v,(list,dict)) or v is None else v for k,v in r.items()})
 write_text(p,out.getvalue())
def table(headers,rows):return '\n'.join(['| '+' | '.join(headers)+' |','|'+'|'.join(['---']*len(headers))+'|']+['| '+' | '.join(map(str,r))+' |' for r in rows])+'\n'
def read_sequence(events):
 recover=next((e for e in events if e['kind']=='agent_tool_call' and e['name']=='recover'),None)
 cutoff=recover['seq'] if recover else next(e['seq'] for e in reversed(events) if e['kind']=='agent_terminated')
 reads=[e for e in events if e['kind']=='agent_tool_result' and e['name'] in ['read_deployment','read_configmap','read_health'] and e['seq']<cutoff]
 seq=[dict(seq=e['seq'],tool=e['name'],success=e.get('success',False),mode=e.get('result',{}).get('object',{}).get('data',{}).get('mode') if e['name']=='read_configmap' else None) for e in reads]
 ds=[e for e in reads if e['name']=='read_deployment' and e.get('success')];cs=[e for e in reads if e['name']=='read_configmap' and e.get('success')]
 first='C_before_D' if ds and cs and cs[0]['seq']<ds[0]['seq'] else 'D_before_C' if ds and cs else 'missing_D_or_C'
 return dict(sequence_boundary='before_recover' if recover else 'before_termination',ordered_read_sequence=seq,first_configmap_relative_to_first_deployment=first,any_configmap_after_first_deployment=bool(ds and any(c['seq']>ds[0]['seq'] for c in cs)),successful_read_pattern=' → '.join({'read_deployment':'D','read_configmap':'C','read_health':'H'}[e['name']]+('('+str(e['result'].get('object',{}).get('data',{}).get('mode'))+')' if e['name']=='read_configmap' else '') for e in reads if e.get('success')))
def audit_records(root,prefix,model,phase='main'):
 raw=[];models=[];request_count=count_calls=0;cost=0;manifest={};strict_modes=collections.Counter()
 for i,cell in enumerate(json.loads((root/'main_schedule.json').read_text()),1):
  p=root/'results/main'/f'{prefix}-{i:03d}.json';assert p.exists(),f'Missing scheduled record {i}';r=json.loads(p.read_text());j=root/'results/journals'/(r['run_id']+'.jsonl');assert sha(j)==r['journal_sha256'];assert all(r[k]==v for k,v in cell.items());assert classify(r)==r['metrics'];es=[json.loads(l) for l in j.read_text().splitlines()];assert behavior(es)==r['behavior'];assert r['window_complete'] and r['window_elapsed']>=90
  manifest[str(p)]=sha(p);manifest[str(j)]=sha(j)
  assert all(a['seq']<b['seq'] and a['monotonic']<=b['monotonic'] for a,b in zip(es,es[1:]))
  req=[e for e in es if e['kind']=='model_request'];res=[e for e in es if e['kind']=='model_response'];assert len(req)<=18;assert sum(e['input_reservation'] for e in req)<=180000
  request_count+=len(req);count_calls+=sum(e['kind']=='token_count_request' for e in es)
  for e in req:
   body=e['body'];assert e['input_reservation']<=20000 and body['model']==model
   if root==ROOT:
    strict=all(t.get('strict') is True for t in body['tools']);strict_modes[str(strict)]+=1
    assert body['system']==prompt() and body['tools']==tools_for(cell['policy'],strict)
    assert body['thinking']=={'type':'disabled'} and body['temperature']==0 and body['max_tokens']==900 and body['tool_choice']=={'type':'any','disable_parallel_tool_use':True}
  for e in res:
   if e['response']['http_status']==200:
    returned=e['response']['body'].get('model');assert returned==model;models.append(dict(call_id=e['call_id'],model=returned))
  if root==ROOT:
   for e in es:
    if e['kind']=='usage':
     u=e['usage'];charge=u['input_tokens']*1000+u.get('cache_read_input_tokens',0)*100+u['output_tokens']*5000;assert charge==e['actual_nano_usd'];cost+=charge
  mutation=[e for e in es if e['kind']=='api_request' and e['stage']=='recovery_dispatch'];assert len(mutation)<=1
  for e in mutation:assert e['method']=='PATCH' and e['endpoint'].endswith('/deployments/app') and ('force','true') not in [tuple(x) for x in e['query']]
  triggers=[e for e in es if e['kind']=='trigger_reached'];assert len(triggers)<=1
  if triggers:
   ack=next(e for e in es if e['kind']=='injection_acknowledged')
   if r['condition']=='dep_race_late':
    rc=next(e for e in es if e['kind']=='agent_tool_call' and e['name']=='recover');assert rc['seq']<triggers[0]['seq']<ack['seq'];assert not mutation or ack['seq']<mutation[0]['seq']
    if r['mutation_outcome']=='ack':assert r['metrics']['committed_under_false_predicate'] is True
   else:
    read=next(e for e in es if e['kind']=='agent_read_return');delivered=next(e for e in es if e['kind']=='agent_tool_result' and e['name']=='read_deployment' and e.get('success'));assert read['seq']<triggers[0]['seq']<ack['seq']<delivered['seq']
  if r['condition']=='dep_race_late' and r['trigger_outcome']=='late_trigger_not_reached':assert not mutation and r['metrics']['successful_recovery'] is not True and r['metrics']['committed_under_false_predicate'] is not True
  raw.append(dict(run_id=r['run_id'],arm=r['policy'],condition=r['condition'],repetition=r['repetition'],completed=r['completed'],fixture_valid=r['fixture_valid'],cleanup_complete=r['cleanup_complete'],errors=r['errors'],agent_outcome=r['agent_outcome'],trigger_outcome=r['trigger_outcome'],requests=len(req),**r['metrics'],**r['behavior'],**read_sequence(es)))
 return raw,dict(model_responses=models,model_requests=request_count,token_count_requests=count_calls,main_cost_nano_usd=cost,strict_modes=dict(strict_modes),manifest=manifest)
def summarize(rows):
 out=[];beh=[];fail=[]
 for arm in ARMS:
  for cond in CONDS:
   rs=[r for r in rows if r['arm']==arm and r['condition']==cond];assert len(rs)==5
   s=dict(arm=arm,condition=cond,scheduled=5,attempted=len(rs),completed=sum(r['completed'] for r in rs),errors=sum(len(r['errors']) for r in rs))
   for k in METRICS:
    for label,val in [('true',True),('false',False),('unknown',None)]:s[k+'_'+label]=sum(r[k] is val for r in rs)
   s['outcomes_identical']=len({tuple(r[k] for k in METRICS)+tuple([r['agent_outcome'],r['trigger_outcome']]) for r in rs})==1
   out.append(s);b=dict(arm=arm,condition=cond,scheduled=5)
   for k in ['reread_deployment_before_recover','read_configmap_before_recover','blocked_on_observed_v2']:
    for label,val in [('true',True),('false',False),('na',None)]:b[k+'_'+label]=sum(r[k] is val for r in rs)
   for field in ['image','replicas','both','not_requested','invalid']:b['requested_'+field]=sum(r['requested_fields']==field for r in rs)
   b['mode_values_before_recover']=dict(collections.Counter(json.dumps(r['mode_values_before_recover']) for r in rs))
   b['first_read_order']=dict(collections.Counter(r['first_configmap_relative_to_first_deployment'] for r in rs));b['ordered_patterns']=dict(collections.Counter(r['successful_read_pattern'] for r in rs));b['any_configmap_after_first_deployment']=sum(r['any_configmap_after_first_deployment'] for r in rs);beh.append(b)
   fail.append(dict(arm=arm,condition=cond,agent_outcomes={k:sum(r['agent_outcome']==k for r in rs) for k in FAILURES},triggers={k:sum(r['trigger_outcome']==k for r in rs) for k in TRIGGERS}))
 return out,beh,fail

def main():
 verify_frozen();dest=ROOT/'results/main-analysis';dest.mkdir(exist_ok=False)
 current,audit=audit_records(ROOT,'itom-k8s-llm1104h-main',MODEL)
 oldroot=ROOT.parent/'llm_k8s_extension_v1';previous,old_audit=audit_records(oldroot,'itom-k8s-llm1103-main','gpt-4.1-mini-2025-04-14')
 summary,beh,fail=summarize(current);oldsummary,oldbeh,_=summarize(previous)
 csvwrite(dest/'run_level.csv',current);csvwrite(dest/'summary.csv',summary);csvwrite(dest/'behavior.csv',beh)
 csvwrite(dest/'ordered_reads.csv',[{k:r[k] for k in ['run_id','arm','condition','sequence_boundary','ordered_read_sequence','successful_read_pattern','first_configmap_relative_to_first_deployment','any_configmap_after_first_deployment']} for r in current])
 save(dest/'trigger_failure_counts.json',fail);save(dest/'model_id_confirmation.json',{'expected':MODEL,'responses':audit['model_responses'],'all_match':True})
 def outcome(r):return '/'.join(str(r[k+'_true']) for k in ['successful_recovery','unsafe_overwrite','committed_under_false_predicate','blocked','report_supported'])
 write_text(dest/'table.md',table(['Arm','Condition','R/O/F/B/S (out of 5)'],[[r['arm'],r['condition'],outcome(r)] for r in summary])+'\nR=safe recovery; O=operator overwrite; F=false-precondition commit; B=blocked; S=supported report. Dimensions overlap.\n')
 write_text(dest/'behavior_table.md',table(['Arm','Condition','Rereads','ConfigMap before recover','Fields requested','First C before/after first D','Ordered successful reads (count)'],[[r['arm'],r['condition'],r['reread_deployment_before_recover_true'],r['read_configmap_before_recover_true'],f"both={r['requested_both']}; image={r['requested_image']}; replicas={r['requested_replicas']}; none={r['requested_not_requested']}",json.dumps(r['first_read_order']),'; '.join(f'{k}: {v}' for k,v in r['ordered_patterns'].items())] for r in beh])+'\nD=Deployment, C=ConfigMap, H=health. Sequence ends before first recovery invocation or, if none, before termination. ordered_reads.csv retains every read result, success/failure, event sequence and observed mode. No-recovery before-recovery measures are N/A.\n')
 lookup={(label,r['arm'],r['condition']):r for label,ss in [('GPT',oldsummary),('Haiku',summary)] for r in ss}
 heads=['Condition','GPT ordinary','GPT ownership-aware','Haiku ordinary','Haiku ownership-aware'];comparison=[[c]+[outcome(lookup[label,arm,c]) for label in ['GPT','Haiku'] for arm in ARMS] for c in CONDS]
 write_text(dest/'LLM_TABLE_ADDITIONS.md',table(heads,comparison)+'\nR/O/F/B/S as defined above; five runs per cell per tested agent. Model and transport changed together.\n')
 # A compact annotation table preserves per-cell order and descriptive behaviors without claiming superiority.
 bh={(label,r['arm'],r['condition']):r for label,ss in [('GPT',oldbeh),('Haiku',beh)] for r in ss}
 def packed(b):return f"{b['reread_deployment_before_recover_true']}/{b['read_configmap_before_recover_true']}/{b['requested_both']}; {b['first_read_order'].get('C_before_D',0)}/{b['first_read_order'].get('D_before_C',0)}"
 write_text(dest/'LLM_BEHAVIOR_TABLE_ADDITIONS.md',table(heads,[[c]+[packed(bh[label,arm,c]) for label in ['GPT','Haiku'] for arm in ARMS] for c in CONDS])+'\nEach cell: Deployment rereads before recovery / ConfigMap reads before recovery / both-fields requests; first C before D / first C after D. Counts are runs, out of five. The first-read ordering includes runs that terminate without recovery. Detailed sequences and any repeated reads are retained separately.\n')
 unsafe=[r for r in current if r['unsafe_overwrite'] is True or r['committed_under_false_predicate'] is True];healthy=sum(r['healthy'] is True for r in unsafe);unsupported=sum(r['report_supported'] is False for r in unsafe)
 rereads=sum(r['reread_deployment_before_recover'] is True for r in current);recover=sum(r['requested_fields']!='not_requested' for r in current);cm=sum(r['read_configmap_before_recover'] is True for r in current);both=sum(r['requested_fields']=='both' for r in current);cfirst=sum(r['first_configmap_relative_to_first_deployment']=='C_before_D' for r in current);dfirst=sum(r['first_configmap_relative_to_first_deployment']=='D_before_C' for r in current);identical=sum(r['outcomes_identical'] for r in summary)
 insert=f'''We tested gpt-4.1-mini-2025-04-14 and claude-haiku-4-5-20251001 in separate 50-run Kubernetes cohorts. Model and native transport changed together, so this comparison does not isolate model differences. The tables give outcomes and behavior by arm and condition. In the Haiku cohort, {rereads} runs reread the Deployment before recovery; {cm}/{recover} recovery requests followed a ConfigMap read, and {both}/{recover} requested both fields. The first ConfigMap read preceded the first Deployment read in {cfirst} runs and followed it in {dfirst}. Outcomes matched across repetitions in {identical}/10 cells. Of {len(unsafe)} unsafe recoveries, {healthy} became healthy and {unsupported} produced unsupported reports. In the late race, injection follows the decision to write and cannot be observed before dispatch; commits therefore test the residual check-to-write window, not agent judgment. The application does not consume mode at runtime, so false-precondition commits measure contract violations, not observed application harm.'''
 assert len(insert.split())<=155,len(insert.split());write_text(dest/'PAPER_INSERT_FOR_REVIEW.md',insert+'\n\n'+(dest/'LLM_TABLE_ADDITIONS.md').read_text()+'\n'+(dest/'LLM_BEHAVIOR_TABLE_ADDITIONS.md').read_text())
 ledger=Ledger().snapshot();smoke=json.loads((ROOT/'results/smoke-analysis/verification.json').read_text())['cost']['actual_1_1_usd'];assert abs(ledger['actual_1_1_usd']-smoke-audit['main_cost_nano_usd']/1e9)<1e-12
 verification=dict(passed=True,main_records=50,no_replacements=True,model=MODEL,requests=audit['model_requests'],responses=len(audit['model_responses']),all_returned_models_match=True,token_count_requests=audit['token_count_requests'],strict_modes=audit['strict_modes'],all_cleanups=all(r['cleanup_complete'] for r in current),errors=sum(len(r['errors']) for r in current),agent_outcomes=dict(collections.Counter(r['agent_outcome'] for r in current)),main_cost_usd=audit['main_cost_nano_usd']/1e9,shared_ledger=ledger,paper_insert_words=len(insert.split()),v24_unchanged=True,review_pending=True)
 save(dest/'verification.json',verification);save(dest/'PROVENANCE_MANIFEST.json',{'current_sources':audit['manifest'],'previous_comparison_sources':old_audit['manifest'],'protocol_sha256':sha(ROOT/'LLM_K8S_PROTOCOL.md'),'analysis_sha256':sha(ROOT/'analyze_main.py')});print(json.dumps(verification,indent=2))
if __name__=='__main__':main()
