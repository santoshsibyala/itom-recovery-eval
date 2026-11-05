"""Smoke-only entrypoint. Main deliberately unavailable pending author review."""
import argparse,json,fcntl
from common import *
from harness import ExtensionRun,base

def verify_code():
 record=json.loads((ROOT/'IMPLEMENTATION_FREEZE.json').read_text())
 for n,h in record['files'].items():assert sha(ROOT/n)==h,('implementation changed',n)
 assert git('rev-parse','HEAD')==record['commit'],'implementation commit changed'
 return record

def schedule(phase,reps):
 out=[]
 for r in range(1,reps+1):
  cells=[dict(policy=a,condition=c,repetition=r) for a in ['ordinary','ownership_aware'] for c in ['clean','disjoint','same_field','dep_race','dep_race_late']]
  cells.sort(key=lambda x:(hashlib.sha256(f"20261103|{phase}|{r}|{x['policy']}|{x['condition']}".encode()).hexdigest(),x['policy'],x['condition']))
  out+=cells
 return out

def interrupted(path,cell,prov,ordinal):
 # Preserve started execution; never re-enter the agent or replay writes.
 lines=path.read_text().splitlines();events=[]
 for line in lines:
  try:events.append(json.loads(line))
  except ValueError:break
 r=dict(run_id=path.stem,namespace=path.stem,phase='smoke',ordinal=ordinal,**cell,**prov,good_image=base.GOOD,fixture_valid=False,completed=False,report=None,agent_outcome='interrupted',mutation_outcome='unknown',trigger_outcome='unknown_interrupted',errors=[{'kind':'interrupted','stage':'resume'}],behavior=behavior(events),journal_sha256=sha(path))
 from classify import classify
 r['metrics']=classify(r);save(ROOT/'results/smoke'/(path.stem+'.json'),r)
 return r

def main():
 p=argparse.ArgumentParser();p.add_argument('phase',choices=['setup','smoke']);a=p.parse_args();gate()
 (ROOT/'results').mkdir(exist_ok=True)
 with (ROOT/'results/execution.lock').open('a') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  impl=verify_code();prov=bindings();pre=json.loads((ROOT/'results/preflight.json').read_text());assert pre['passed']
  tests=json.loads((ROOT/'results/tests.json').read_text());assert tests['passed'] and tests['implementation_commit']==impl['commit']
  prov.update(implementation_manifest_sha256=sha(ROOT/'IMPLEMENTATION_FREEZE.json'),preflight_sha256=sha(ROOT/'results/preflight.json'),tests_sha256=sha(ROOT/'results/tests.json'),dependency_lock_sha256=sha(ROOT/'requirements.lock'),schema_sha256=sha(ROOT/'schemas.json'),prompt_sha256=sha(ROOT/'prompt.txt'))
  session='llm1103'
  if a.phase=='setup':
   r=base.Run(session,'setup',1,'ordinary','clean',prov).execute();assert r.get('baseline_achieved') and r.get('cleanup_complete');return
  baseline=ROOT/'results/setup/itom-k8s-llm1103-setup-001.json';assert json.loads(baseline.read_text()).get('baseline_achieved');prov['baseline_sha256']=sha(baseline)
  sched=ROOT/'smoke_schedule.json';cells=json.loads(sched.read_text());assert cells==schedule('smoke',1);prov['schedule_sha256']=sha(sched)
  for i,cell in enumerate(cells,1):
   gate();ns=f'itom-k8s-{session}-smoke-{i:03d}';raw=ROOT/'results/smoke'/(ns+'.json');journal=ROOT/'results/journals'/(ns+'.jsonl')
   if raw.exists():
    r=json.loads(raw.read_text());assert all(r.get(k)==v for k,v in cell.items())
    if r.get('stop_cohort'):raise RuntimeError('Previous run stopped cohort; review needed')
    continue
   if journal.exists():
    interrupted(journal,cell,prov,i);raise RuntimeError('Interrupted attempt retained, no replacement; cleanup/review required before new cells')
   run=ExtensionRun(session,'smoke',i,cell['policy'],cell['condition'],prov);r=run.execute()
   if not r.get('cleanup_complete') or r.get('stop_cohort') or not r.get('fixture_valid'):break
  print('Stopped after smoke; main remains unauthorized.')
if __name__=='__main__':main()
