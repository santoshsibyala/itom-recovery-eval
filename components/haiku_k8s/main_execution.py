"""Additive main orchestration only; frozen experiment modules remain unchanged."""
import fcntl
from common import *
from harness import ExtensionRun,base
from classify import classify
from runner import schedule
import agent
MAIN_DEADLINE=datetime.datetime(2026,11,8,21,tzinfo=ZoneInfo('America/Los_Angeles'))
def main_gate(now=None):
 a=json.loads((ROOT/'MAIN_APPROVAL.json').read_text());now=now or datetime.datetime.now(datetime.timezone.utc)
 assert a['main_authorized'] and a['smoke_reviewed_and_approved'] and a['approved_by']=='Santosh Sibyala'
 assert datetime.datetime.fromisoformat(a['review_recorded_utc'])<SMOKE_DEADLINE
 if now>=MAIN_DEADLINE:raise RuntimeError('Main completion/review deadline reached; retain v24')
def verify_frozen():
 main_gate();a=json.loads((ROOT/'MAIN_APPROVAL.json').read_text());impl=json.loads((ROOT/'IMPLEMENTATION_FREEZE.json').read_text());assert impl['commit']==a['implementation_commit']=='e705eb165cece267cb5207fb7095200cf7480aa6'
 assert a['protocol_commit']==FREEZE=='4c0227a4fb108c83b3ffad8a46c22f38917a5078'
 for n,h in impl['files'].items():
  assert sha(ROOT/n)==h,n
  assert hashlib.sha256(subprocess.check_output(['git','show',impl['commit']+':'+n],cwd=ROOT)).hexdigest()==h,n
 assert sha(ROOT/'SMOKE_HANDOFF_MANIFEST.json')==a['smoke_handoff_sha256']
 for n,h in json.loads((ROOT/'SMOKE_HANDOFF_MANIFEST.json').read_text())['files'].items():assert sha(ROOT/a['historical_snapshots'].get(n,n))==h,n
 assert sha(ROOT/'main_schedule.json')==a['main_schedule_sha256'];bindings();return a,impl

def finalize_interrupted(journal,cell,prov,ordinal):
 events=[]
 for line in journal.read_text().splitlines():
  try:events.append(json.loads(line))
  except ValueError:break
 r=dict(run_id=journal.stem,namespace=journal.stem,phase='main',ordinal=ordinal,**cell,**prov,good_image=base.GOOD,fixture_valid=False,completed=False,report=None,agent_outcome='interrupted',mutation_outcome='unknown',trigger_outcome='unknown_interrupted',errors=[{'kind':'interrupted','stage':'resume'}],behavior=behavior(events),journal_sha256=sha(journal),stop_cohort=True)
 r['metrics']=classify(r);save(ROOT/'results/main'/(journal.stem+'.json'),r);return r

def main():
 a,impl=verify_frozen();execution=json.loads((ROOT/'MAIN_EXECUTION_FREEZE.json').read_text());assert git('rev-parse','HEAD')==execution['commit']
 for n,h in execution['files'].items():assert sha(ROOT/n)==h,n
 pre=json.loads((ROOT/'results/main-preflight.json').read_text());tests=json.loads((ROOT/'results/main-tests.json').read_text());assert pre['passed'] and tests['passed'];assert tests['execution_commit']==execution['commit']
 with (ROOT/'results/execution.lock').open('a') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);Ledger().verify_prior()
  prov=bindings();prov.update(implementation_commit=impl['commit'],execution_commit=execution['commit'],execution_manifest_sha256=sha(ROOT/'MAIN_EXECUTION_FREEZE.json'),main_approval_sha256=sha(ROOT/'MAIN_APPROVAL.json'),smoke_handoff_sha256=a['smoke_handoff_sha256'],preflight_sha256=sha(ROOT/'results/main-preflight.json'),tests_sha256=sha(ROOT/'results/main-tests.json'),dependency_lock_sha256=sha(ROOT/'requirements.lock'),schema_sha256=sha(ROOT/'schemas.json'),prompt_sha256=sha(ROOT/'prompt.txt'),schedule_sha256=sha(ROOT/'main_schedule.json'))
  cells=json.loads((ROOT/'main_schedule.json').read_text());assert cells==schedule('main',5) and len(cells)==50
  # Only replace the phase authorization gate. All experimental logic is frozen.
  agent.gate=main_gate
  for i,cell in enumerate(cells,1):
   main_gate();ns=f'itom-k8s-llm1104h-main-{i:03d}';raw=ROOT/'results/main'/(ns+'.json');journal=ROOT/'results/journals'/(ns+'.jsonl')
   if raw.exists():
    r=json.loads(raw.read_text());assert all(r.get(k)==v for k,v in cell.items());assert r['journal_sha256']==sha(journal)
    if r.get('stop_cohort'):raise RuntimeError('Stopped run retained; review required, no replacement')
    if not r.get('cleanup_complete'):raise RuntimeError('Cleanup incomplete; cleanup-only repair required before continuing')
    continue
   if journal.exists():
    finalize_interrupted(journal,cell,prov,i);raise RuntimeError('Interrupted run retained without replay; cleanup/review required')
   run=ExtensionRun('llm1104h','main',i,cell['policy'],cell['condition'],prov);run.r['repetition']=cell['repetition'];run.event('scheduled_cell',ordinal=i,cell=cell);r=run.execute()
   if not r.get('cleanup_complete') or r.get('stop_cohort') or not r.get('fixture_valid') or r.get('agent_failure_detail')=='shared_cost_cap':break
  print('Main execution stopped. No manuscript edits; analysis and author review required.')
if __name__=='__main__':main()
