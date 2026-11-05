"""One live A1 canary; deterministic stub only, excluded from analysis."""
import fcntl
from unittest.mock import patch
from main_b_execution import *
import harness

def stub(run,ledger):
 run.event('stub_agent_started',no_model_calls=True)
 for name,args in [('read_deployment',{}),('read_configmap',{}),('recover',{'restore_image':True,'restore_replicas':True})]:
  run.event('agent_tool_call',name=name,arguments=args,call_id='stub-'+name);run.tool(name,args)
 run.r['report']={'status':'RECOVERED','claims':{'image':base.GOOD,'replicas':2}};run.r['agent_outcome']='stub_report';run.event('agent_finish',report=run.r['report']);run.event('agent_terminated',outcome='stub_report',detail='canary only')

def forbidden(*args,**kwargs):raise AssertionError('Canary attempted provider transport')
def main():
 main_gate();prov=provenance();phase='canary';ns='itom-k8s-llm1104h-canary-001';journal=ROOT/'results/journals'/(ns+'.jsonl');raw=ROOT/'results/canary'/(ns+'.json');assert not journal.exists() and not raw.exists(),'One canary only; preserve failed attempt'
 with (ROOT/'results/execution.lock').open('a') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);before=Ledger().snapshot()
  with patch.object(harness,'execute_agent',stub),patch.object(agent,'transport',forbidden):
   run=MainRun('llm1104h',phase,1,'ordinary','disjoint',prov);run.r['excluded_from_analysis']=True;r=run.execute()
  assert r['completed'] and r['cleanup_complete'] and not r['errors'];assert Ledger().snapshot()==before
  v=verify_lifecycle(journal);v.update(raw=str(raw.relative_to(ROOT)),raw_sha256=sha(raw),journal=str(journal.relative_to(ROOT)),execution_commit=git('rev-parse','HEAD'),ledger_before=before,ledger_after=Ledger().snapshot());save(ROOT/'results/canary/CANARY_VERIFICATION.json',v);print('CANARY PASSED: ordered lifecycle, no model calls, excluded from analysis.')
if __name__=='__main__':main()
