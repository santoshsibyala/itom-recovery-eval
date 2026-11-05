"""Post-hoc offline specificity checks; not part of the frozen model cohort."""
import json,sys,tempfile
from copy import deepcopy
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parent;sys.path.insert(0,str(ROOT))
from runtime import Runtime
from scenarios import scenario,NAMES
from policies import run
from scoring import grade
from verify import verify

def execute():
 results=[];traces=[]
 for name in NAMES:
  for kind in ('late_disjoint','late_same_prior_value','late_noop_dependency'):
   for refresh in (False,True):
    s=scenario(name,'clean');s['variant']=kind;s['timing']='finish';e=s['effects'][0]
    if kind=='late_disjoint':external=dict(resource=e['resource'],patch={'tag':'approved-late'})
    elif kind=='late_same_prior_value':external=dict(resource=e['resource'],patch=e['before'])
    else:
     dep=next(r for r in s['initial'] if r not in {e['resource'] for e in s['effects']})
     external=dict(resource=dep,patch=deepcopy(s['initial'][dep]))
    s['external']=[external]
    with tempfile.TemporaryDirectory() as d:
     rt=Runtime(s,Path(d)/'state.sqlite3','atomic')
     rt.health=lambda:dict(measured=False,epoch=len(rt.finish({})['events']),stable_epoch=True,pass_window=True)
     report=run(rt,rt.invoke,'atomic_guard');rt.external()
     if refresh:
      observations=[rt.invoke('read_resource',resource_id='*'),rt.invoke('read_changes',resource_id='*'),rt.invoke('read_health')]
      report['evidence_ids']=[o['evidence_id'] for o in observations]
      ops=[e['operation_id'] for e in rt.finish({})['events'] if e['actor']=='recovery']
      rt.invoke('record_recovery_audit',effect_ids=ops,evidence_ids=report['evidence_ids'])
     t=rt.finish(report);t['grade']=grade(t);verify(t)
     assert t['grade']['configuration'] and t['grade']['certified_configuration']==refresh
     results.append(dict(name=name,condition=kind,refreshed=refresh,grade=t['grade']));traces.append(t)
 out=HERE/'evidence_specificity';out.mkdir(exist_ok=False)
 for i,t in enumerate(traces,1):(out/f'case-{i:02}.json').write_text(json.dumps(t,indent=2)+'\n')
 (out/'summary.json').write_text(json.dumps(dict(label='Post-hoc offline specificity and revalidation checks, no model calls',cases=results),indent=2)+'\n')
 print('24 specificity checks passed: benign epoch invalidation blocks certification; fresh evidence restores it.')
if __name__=='__main__':execute()
