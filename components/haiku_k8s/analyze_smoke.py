"""Offline smoke audit only. Does not run experiments or change raw evidence."""
import csv,collections,io
from common import *
from classify import classify

def write_csv(path,rows):
 out=io.StringIO();w=csv.DictWriter(out,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows);save_text(path,out.getvalue())
def save_text(path,text):
 with Path(path).open('x') as f:f.write(text)

def analyze():
 bindings();impl=json.loads((ROOT/'IMPLEMENTATION_FREEZE.json').read_text())
 for n,h in impl['files'].items():assert sha(ROOT/n)==h,n
 dest=ROOT/'results/smoke-analysis';dest.mkdir(exist_ok=False)
 sched=json.loads((ROOT/'smoke_schedule.json').read_text());rows=[];beh=[];requests=responses=count_calls=0;model_ids=collections.Counter();actual=0;manifest={};errors=[];strict_values=[];trigger=collections.Counter();outcomes=collections.Counter()
 for i,cell in enumerate(sched,1):
  ns=f'itom-k8s-llm1104h-smoke-{i:03d}';p=ROOT/'results/smoke'/(ns+'.json')
  if not p.exists():
   rows.append(dict(run_id=ns,arm=cell['policy'],condition=cell['condition'],scheduled=1,attempted=0,completed=False,agent_outcome='not_started',safe_recovery=None,overwrite=None,false_predicate=None,blocked=None,healthy=None,supported_report=None,cleanup=None,errors=None));continue
  r=json.loads(p.read_text());j=ROOT/'results/journals'/(ns+'.jsonl');assert sha(j)==r['journal_sha256'];assert r['protocol_commit']==FREEZE and r['implementation_commit']==impl['commit'];assert all(r[k]==v for k,v in cell.items());assert classify(r)==r['metrics'];es=[json.loads(l) for l in j.read_text().splitlines()];b=behavior(es);assert b==r['behavior']
  assert all(a['seq']<b['seq'] and a['monotonic']<=b['monotonic'] for a,b in zip(es,es[1:]));assert r['window_complete'] and r['window_elapsed']>=90
  manifest[str(p.relative_to(ROOT))]=sha(p);manifest[str(j.relative_to(ROOT))]=sha(j)
  req=[e for e in es if e['kind']=='model_request'];res=[e for e in es if e['kind']=='model_response'];counts=[e for e in es if e['kind']=='token_count_request'];requests+=len(req);responses+=len(res);count_calls+=len(counts)
  assert len(req)<=18 and sum(e['input_reservation'] for e in req)<=180000
  for e in req:
   bdy=e['body'];assert bdy['model']==MODEL and bdy['system']==prompt() and bdy['max_tokens']==900 and bdy['thinking']=={'type':'disabled'} and bdy['temperature']==0 and bdy['tool_choice']=={'type':'any','disable_parallel_tool_use':True};strict=all(t.get('strict') is True for t in bdy['tools']);strict_values.append(strict);assert bdy['tools']==tools_for(cell['policy'],strict);assert e['input_reservation']<=20000
  for e in res:
   if e['response']['http_status']==200:model_ids[e['response']['body']['model']]+=1
  for e in es:
   if e['kind']=='usage':
    u=e['usage'];charge=u['input_tokens']*1000+u.get('cache_read_input_tokens',0)*100+u['output_tokens']*5000;assert charge==e['actual_nano_usd'];actual+=charge
  mutation=[e for e in es if e['kind']=='api_request' and e['stage']=='recovery_dispatch'];assert len(mutation)<=1
  for e in mutation:assert e['method']=='PATCH' and e['endpoint'].endswith('/deployments/app') and ('force','true') not in [tuple(x) for x in e['query']]
  tr=[e for e in es if e['kind']=='trigger_reached'];assert len(tr)<=1
  if tr:
   ack=next(e for e in es if e['kind']=='injection_acknowledged')
   if cell['condition']=='dep_race_late':
    call=next(e for e in es if e['kind']=='agent_tool_call' and e['name']=='recover');assert call['seq']<tr[0]['seq']<ack['seq'];assert not mutation or ack['seq']<mutation[0]['seq']
   else:
    ret=next(e for e in es if e['kind']=='agent_read_return');delivery=next(e for e in es if e['kind']=='agent_tool_result' and e['name']=='read_deployment' and e['success']);assert ret['seq']<tr[0]['seq']<ack['seq']<delivery['seq']
  m=r['metrics'];rows.append(dict(run_id=ns,arm=cell['policy'],condition=cell['condition'],scheduled=1,attempted=1,completed=r['completed'],agent_outcome=r['agent_outcome'],safe_recovery=m['successful_recovery'],overwrite=m['unsafe_overwrite'],false_predicate=m['committed_under_false_predicate'],blocked=m['blocked'],healthy=m['healthy'],supported_report=m['report_supported'],cleanup=r['cleanup_complete'],errors=len(r['errors'])))
  beh.append(dict(run_id=ns,arm=cell['policy'],condition=cell['condition'],**{k:json.dumps(v) if isinstance(v,list) else v for k,v in b.items()}));trigger[r['trigger_outcome']]+=1;outcomes[r['agent_outcome']]+=1;errors+=r['errors']
 assert not (set(model_ids)-{MODEL}),model_ids
 ledger=Ledger().snapshot();assert abs(ledger['actual_1_1_usd']-actual/1e9)<1e-12
 write_csv(dest/'summary.csv',rows)
 if beh:write_csv(dest/'behavior.csv',beh)
 report=dict(protocol=bindings(),implementation_commit=impl['commit'],scheduled=10,attempted=sum(r['attempted'] for r in rows),completed=sum(r['completed'] for r in rows),main_authorized=False,requests=requests,responses=responses,token_count_requests=count_calls,returned_model_ids=dict(model_ids),all_returned_models_match=not(set(model_ids)-{MODEL}),strict_modes=dict(collections.Counter(map(str,strict_values))),trigger_counts=dict(trigger),agent_outcomes=dict(outcomes),errors=errors,all_cleanups=all(r['cleanup'] for r in rows if r['attempted']),cost=ledger)
 save(dest/'verification.json',report);save(dest/'PROVENANCE_MANIFEST.json',{'files':manifest})
 table='| Arm | Condition | Safe recovery | Overwrite | False precondition | Blocked | Healthy | Supported report |\n|---|---|---|---|---|---|---|---|\n'
 for r in rows:table+='| '+' | '.join(str(r[k]) for k in ['arm','condition','safe_recovery','overwrite','false_predicate','blocked','healthy','supported_report'])+' |\n'
 save_text(dest/'table.md',table)
 print(json.dumps(report,indent=2))
if __name__=='__main__':analyze()
