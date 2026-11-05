"""A1 additive lifecycle and main-b orchestration; frozen agent/tools untouched."""
import argparse,fcntl
from common import *
from harness import ExtensionRun,base
from classify import classify
from runner import schedule
from main_execution import verify_frozen as verify_original,main_gate
import agent
FixtureError=base.FixtureError;ApiError=base.ApiError;exclusive=base.exclusive;time=base.time;CLUSTER=base.CLUSTER
PHASES=('main-b','canary')

def verify_frozen():
 a,impl=verify_original();am=json.loads((ROOT/'AMENDMENT_A1_APPROVAL.json').read_text());assert am['new_cohort']=='main-b' and am['approved_by']=='Santosh Sibyala'
 for n,h in am['invalid_cohort_files'].items():assert sha(ROOT/n)==h,('invalid cohort changed',n)
 rec=json.loads((ROOT/'AMENDMENT_A1_RECEIPT.json').read_text())
 for n,h in rec['files'].items():assert sha(ROOT/n)==h,n
 return a,impl,am

class MainRun(ExtensionRun):
 def execute(self):
  try:
   self.event('lifecycle_baseline_started');self.baseline();self.event('lifecycle_baseline_completed')
   if self.phase in PHASES:
    self.event('lifecycle_experiment_started');self.experiment();self.event('lifecycle_measurement_completed',elapsed=self.r.get('window_elapsed'),window_complete=self.r.get('window_complete'))
   else:self.r['fixture_valid']=True
   self.stage='final_observation';self.r['final_deployment']=self.get(self.dp);self.r['final_configmap']=self.get(self.cp);self.r['completed']=True
  except Exception as e:
   self.error('fixture' if isinstance(e,FixtureError) or not self.r['fixture_valid'] else 'harness',e);self.r['completed']=False
  finally:
   # Pure classification uses retained evidence, before cleanup as required by A1.
   self.stage='classification'
   if self.phase in PHASES:
    try:self.r['metrics']=classify(self.r);self.event('lifecycle_classification_completed',metrics=self.r['metrics'])
    except Exception as e:self.error('classifier',e)
   self.stage='cleanup';self.event('lifecycle_cleanup_started')
   try:
    obj=self.get('/api/v1/namespaces/'+self.ns)
    if obj['metadata'].get('labels',{}).get('itom-experiment')!=CLUSTER:raise RuntimeError('namespace ownership check failed')
    self.request('DELETE','/api/v1/namespaces/'+self.ns,{'apiVersion':'v1','kind':'DeleteOptions','gracePeriodSeconds':0});start=time.monotonic()
    while True:
     try:self.get('/api/v1/namespaces/'+self.ns)
     except ApiError as e:
      if e.status==404:break
      raise
     if time.monotonic()-start>=60:raise TimeoutError('namespace deletion exceeded 60 seconds')
     time.sleep(2)
    self.r['cleanup_complete']=True;self.event('lifecycle_cleanup_completed')
   except Exception as e:self.error('cleanup',e);self.r['cleanup_complete']=False
   self.event('finished',completed=self.r.get('completed'),metrics=self.r.get('metrics'),errors=len(self.r['errors']));self.f.close();self.api.close();self.r['journal_sha256']=sha(self.journal);exclusive(ROOT/'results'/self.phase/(self.ns+'.json'),self.r)
   print(json.dumps({'run':self.ns,'policy':self.r['policy'],'condition':self.r['condition'],'completed':self.r.get('completed'),'metrics':self.r.get('metrics'),'errors':len(self.r['errors'])}),flush=True)
  return self.r

def verify_lifecycle(journal):
 es=[json.loads(l) for l in journal.read_text().splitlines()]
 kinds=['lifecycle_baseline_completed','injection_acknowledged','lifecycle_measurement_completed','lifecycle_classification_completed','lifecycle_cleanup_completed']
 seq=[next(e['seq'] for e in es if e['kind']==k) for k in kinds];assert seq==sorted(seq) and len(set(seq))==5
 measurement=next(e for e in es if e['kind']=='lifecycle_measurement_completed');assert measurement['window_complete'] and measurement['elapsed']>=90
 assert not any(e['kind'] in ['model_request','token_count_request'] for e in es)
 return dict(passed=True,milestones=dict(zip(kinds,seq)),measurement_elapsed=measurement['elapsed'],model_requests=0,excluded_from_analysis=True,journal_sha256=sha(journal))

def finalize_interrupted(journal,cell,prov,ordinal):
 events=[]
 for line in journal.read_text().splitlines():
  try:events.append(json.loads(line))
  except ValueError:break
 r=dict(run_id=journal.stem,namespace=journal.stem,phase='main-b',ordinal=ordinal,**cell,**prov,good_image=base.GOOD,fixture_valid=False,completed=False,report=None,agent_outcome='interrupted',mutation_outcome='unknown',trigger_outcome='unknown_interrupted',errors=[{'kind':'interrupted','stage':'resume'}],behavior=behavior(events),journal_sha256=sha(journal),stop_cohort=True)
 r['metrics']=classify(r);save(ROOT/'results/main-b'/(journal.stem+'.json'),r);return r

def provenance():
 a,impl,am=verify_frozen();execution=json.loads((ROOT/'MAIN_B_EXECUTION_FREEZE.json').read_text());assert git('rev-parse','HEAD')==execution['commit']
 for n,h in execution['files'].items():assert sha(ROOT/n)==h,n
 pre=json.loads((ROOT/'results/main-b-preflight.json').read_text());tests=json.loads((ROOT/'results/main-b-tests.json').read_text());assert pre['passed'] and tests['passed'] and tests['execution_commit']==execution['commit']
 prov=bindings();prov.update(implementation_commit=impl['commit'],execution_commit=execution['commit'],execution_manifest_sha256=sha(ROOT/'MAIN_B_EXECUTION_FREEZE.json'),amendment='ITOM-LLM-K8S-1.1-A1',amendment_receipt_sha256=sha(ROOT/'AMENDMENT_A1_RECEIPT.json'),main_approval_sha256=sha(ROOT/'AMENDMENT_A1_APPROVAL.json'),smoke_handoff_sha256=a['smoke_handoff_sha256'],preflight_sha256=sha(ROOT/'results/main-b-preflight.json'),tests_sha256=sha(ROOT/'results/main-b-tests.json'),dependency_lock_sha256=sha(ROOT/'requirements.lock'),schema_sha256=sha(ROOT/'schemas.json'),prompt_sha256=sha(ROOT/'prompt.txt'),schedule_sha256=sha(ROOT/'main_b_schedule.json'))
 return prov

def main():
 main_gate();prov=provenance();receipt=ROOT/'results/canary/CANARY_VERIFICATION.json';v=json.loads(receipt.read_text());assert v['passed'] and v['execution_commit']==git('rev-parse','HEAD');j=ROOT/v['journal'];assert verify_lifecycle(j)['journal_sha256']==v['journal_sha256'];raw=ROOT/v['raw'];assert sha(raw)==v['raw_sha256'];prov['canary_verification_sha256']=sha(receipt)
 with (ROOT/'results/execution.lock').open('a') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);Ledger().verify_prior();agent.gate=main_gate
  cells=json.loads((ROOT/'main_b_schedule.json').read_text());assert cells==schedule('main-b',5) and len(cells)==50
  for i,cell in enumerate(cells,1):
   main_gate();ns=f'itom-k8s-llm1104h-main-b-{i:03d}';raw=ROOT/'results/main-b'/(ns+'.json');journal=ROOT/'results/journals'/(ns+'.jsonl')
   if raw.exists():
    r=json.loads(raw.read_text());assert all(r.get(k)==v for k,v in cell.items());assert r['journal_sha256']==sha(journal)
    if r.get('stop_cohort') or not r.get('cleanup_complete'):raise RuntimeError('Prior stopped/interrupted attempt retained; review/cleanup needed')
    continue
   if journal.exists():finalize_interrupted(journal,cell,prov,i);raise RuntimeError('Interrupted main-b attempt retained; no replacement')
   run=MainRun('llm1104h','main-b',i,cell['policy'],cell['condition'],prov);run.r['repetition']=cell['repetition'];run.event('scheduled_cell',ordinal=i,cell=cell);r=run.execute()
   # Fail closed if lifecycle is ever skipped again, before another cell starts.
   if not r.get('window_complete') or not r.get('metrics') or 'agent_outcome' not in r:raise RuntimeError('Main-b lifecycle incomplete; stop immediately')
   if not r.get('cleanup_complete') or r.get('stop_cohort') or not r.get('fixture_valid') or r.get('agent_failure_detail')=='shared_cost_cap':break
  print('main-b stopped; no manuscript edits; review required.')
if __name__=='__main__':main()
