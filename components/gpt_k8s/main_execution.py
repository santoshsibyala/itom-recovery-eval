"""Additive main authorization/orchestration; frozen experiment code is unchanged."""
import argparse,fcntl,inspect,textwrap,shutil
from common import *
from harness import ExtensionRun,base
import agent
from classify import classify
FixtureError=base.FixtureError;ApiError=base.ApiError;exclusive=base.exclusive;time=base.time;CLUSTER=base.CLUSTER
MAIN_DEADLINE=datetime.datetime(2026,11,10,0,tzinfo=ZoneInfo('America/Los_Angeles'))

def main_gate(now=None):
 now=now or datetime.datetime.now(datetime.timezone.utc)
 a=json.loads((ROOT/'MAIN_APPROVAL.json').read_text())
 assert a['main_authorized'] and a['smoke_reviewed_and_approved'] and a['approved_by']=='Santosh Sibyala'
 assert datetime.datetime.fromisoformat(a['recorded_utc'])<SMOKE_DEADLINE,'Smoke review missed deadline'
 if now>=MAIN_DEADLINE:raise RuntimeError('November 9 main review deadline passed; retain v21')

def verify_frozen():
 a=json.loads((ROOT/'MAIN_APPROVAL.json').read_text());r=json.loads((ROOT/'IMPLEMENTATION_FREEZE.json').read_text())
 assert r['commit']==a['implementation_commit']=='82555f65753f1c1c8446d07bbca4393d8ee33d1d'
 for n,h in r['files'].items():
  assert sha(ROOT/n)==h,('frozen implementation changed',n)
  assert hashlib.sha256(subprocess.check_output(['git','show',r['commit']+':'+n],cwd=ROOT)).hexdigest()==h
 assert git('rev-parse',FREEZE)==a['protocol_commit']=='421a365ec55ec364162cdf764082705ca6705374'
 assert sha(ROOT/'SMOKE_HANDOFF_MANIFEST.json')==a['smoke_handoff_sha256']
 handoff=json.loads((ROOT/'SMOKE_HANDOFF_MANIFEST.json').read_text())
 for n,h in handoff['files'].items():assert sha(ROOT/a['historical_snapshots'].get(n,n))==h,n
 sm=json.loads((ROOT/'results/smoke-analysis/PROVENANCE_MANIFEST.json').read_text())
 for n,h in sm['files'].items():assert sha(ROOT/a['historical_snapshots'].get(n,n))==h,n
 assert sha(ROOT/'main_schedule.json')==a['main_schedule_sha256']
 bindings();return a,r

class MainRun(ExtensionRun):
    def execute(self):
        try:
            self.baseline()
            if self.phase in ('smoke','smoke-A1','main'):self.experiment()
            else:self.r['fixture_valid']=True
            self.stage='final_observation';self.r['final_deployment']=self.get(self.dp);self.r['final_configmap']=self.get(self.cp);self.r['completed']=True
        except Exception as e:
            self.error('fixture' if isinstance(e,FixtureError) or not self.r['fixture_valid'] else 'harness',e);self.r['completed']=False
        finally:
            self.stage='cleanup'
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
                self.r['cleanup_complete']=True
            except Exception as e:self.error('cleanup',e);self.r['cleanup_complete']=False
            self.stage='classification'
            if self.phase in ('smoke','smoke-A1','main'):
                try:self.r['metrics']=classify(self.r)
                except Exception as e:self.error('classifier',e)
            self.event('finished',completed=self.r.get('completed'),metrics=self.r.get('metrics'),errors=len(self.r['errors']));self.f.close();self.api.close()
            self.r['journal_sha256']=sha(self.journal);exclusive(ROOT/'results'/self.phase/(self.ns+'.json'),self.r)
            print(json.dumps({'run':self.ns,'policy':self.r['policy'],'condition':self.r['condition'],'completed':self.r.get('completed'),'metrics':self.r.get('metrics'),'errors':len(self.r['errors'])}),flush=True)
        return self.r

def finalize_interrupted(journal,cell,prov,ordinal):
 events=[]
 for line in journal.read_text().splitlines():
  try:events.append(json.loads(line))
  except ValueError:break
 r=dict(run_id=journal.stem,namespace=journal.stem,phase='main',ordinal=ordinal,**cell,**prov,good_image=base.GOOD,fixture_valid=False,completed=False,report=None,agent_outcome='interrupted',mutation_outcome='unknown',trigger_outcome='unknown_interrupted',errors=[{'kind':'interrupted','stage':'resume'}],behavior=behavior(events),journal_sha256=sha(journal),stop_cohort=True)
 r['metrics']=classify(r);save(ROOT/'results/main'/(journal.stem+'.json'),r)
 return r

def main():
 main_gate();a,impl=verify_frozen()
 execution=json.loads((ROOT/'MAIN_EXECUTION_FREEZE.json').read_text())
 assert git('rev-parse','HEAD')==execution['commit']
 for n,h in execution['files'].items():assert sha(ROOT/n)==h,n
 pre=json.loads((ROOT/'results/main-preflight.json').read_text());tests=json.loads((ROOT/'results/main-tests.json').read_text());assert pre['passed'] and tests['passed']
 assert tests['execution_commit']==execution['commit']
 with (ROOT/'results/execution.lock').open('a') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  prov=bindings();prov.update(implementation_commit=a['implementation_commit'],execution_commit=execution['commit'],execution_manifest_sha256=sha(ROOT/'MAIN_EXECUTION_FREEZE.json'),main_approval_sha256=sha(ROOT/'MAIN_APPROVAL.json'),smoke_handoff_sha256=a['smoke_handoff_sha256'],preflight_sha256=sha(ROOT/'results/main-preflight.json'),tests_sha256=sha(ROOT/'results/main-tests.json'),dependency_lock_sha256=sha(ROOT/'requirements.lock'),schema_sha256=sha(ROOT/'schemas.json'),prompt_sha256=sha(ROOT/'prompt.txt'),schedule_sha256=sha(ROOT/'main_schedule.json'))
  cells=json.loads((ROOT/'main_schedule.json').read_text());assert len(cells)==50
  from runner import schedule
  assert cells==schedule('main',5)
  # The smoke deadline was satisfied by the bound approval. Only authorization
  # gate changes; model, tool, turn, token and wall-clock budgets remain frozen.
  agent.gate=main_gate
  for i,cell in enumerate(cells,1):
   main_gate();ns=f'itom-k8s-llm1103-main-{i:03d}';raw=ROOT/'results/main'/(ns+'.json');journal=ROOT/'results/journals'/(ns+'.jsonl')
   if raw.exists():
    r=json.loads(raw.read_text());assert all(r.get(k)==v for k,v in cell.items())
    assert r['journal_sha256']==sha(journal)
    if r.get('stop_cohort'):raise RuntimeError('Prior stopped/interrupted run retained; review needed; no replacement')
    if not r.get('cleanup_complete'):
     receipt=ROOT/'results/cleanup-addenda'/(ns+'.json')
     cleanup=json.loads(receipt.read_text())
     assert cleanup['cleanup_verified'] and cleanup['raw_sha256']==sha(raw) and cleanup['journal_sha256']==sha(journal)
     assert r['completed'] and all(e['kind']=='cleanup' for e in r['errors'])
    continue
   if journal.exists():
    finalize_interrupted(journal,cell,prov,i);raise RuntimeError('Interrupted attempt finalized without replay; cleanup/review before remaining cells')
   run=MainRun('llm1103','main',i,cell['policy'],cell['condition'],prov);run.r['repetition']=cell['repetition'];run.event('scheduled_cell',ordinal=i,cell=cell)
   r=run.execute()
   if not r.get('cleanup_complete') or r.get('stop_cohort') or not r.get('fixture_valid'):break
   if r.get('agent_failure_detail')=='shared_cost_cap':break
  print('Main execution stopped. No manuscript changes. Analysis and author review required.')
if __name__=='__main__':main()
