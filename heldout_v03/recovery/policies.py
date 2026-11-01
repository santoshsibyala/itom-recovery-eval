"""Conventional baselines. Only public task and observations are accessible."""
from copy import deepcopy
from .environment import evaluate
POLICIES=('snapshot','object_cas','field_compensator')
def run(task,invoke,policy):
 evidence=[];done=[];left=[e['id'] for e in task['effects']];stopped=False
 def call(tool,**a):
  o=invoke(tool,**a);evidence.append(o['evidence_id'])
  if not o['reply']['ok']:raise ValueError(o['reply'].get('message','Tool error'))
  return o['reply']['result']
 effects=deepcopy(task['effects']);ordered=[]
 while effects:
  ready=[e for e in effects if all(first in {x['id'] for x in ordered} for first,second in task['order'] if second==e['id'])]
  if not ready:raise ValueError('Cyclic order')
  e=ready[0];ordered.append(e);effects.remove(e)
 for e in ordered:
  r=e['resource'];view=call('read_resource',resource_id=r);h=call('read_changes',resource_id=r)
  if policy=='field_compensator':
   if not h['complete'] or any(view['provenance'][k]!=e['id'] for k in e['before']):stopped=True;break
   values={r:view['values']}
   for rr in task['resource_ids']:
    if rr!=r:values[rr]=call('read_resource',resource_id=rr)['values']
   candidate=deepcopy(values);candidate[r].update(e['before'])
   if not all(evaluate(x,candidate) for x in task['constraints']):stopped=True;break
  patch=deepcopy(e['before'])
  if policy=='snapshot':
   # Reconstruct the recorded pre-remediation object from full public history.
   # Unrelated initial TLS is explicitly in this conventional snapshot fixture.
   if 'tls' in view['values']:patch['tls']='strict'
  version=None if policy=='snapshot' else e['forward_version'] if policy=='object_cas' else view['version']
  oid='recovery-'+e['id'];result=call('apply_patch',resource_id=r,patch=patch,expected_version=version,operation_id=oid,target_effect_id=e['id'])
  if not result['committed']:stopped=True;break
  call('read_resource',resource_id=r);call('record_recovery_audit',effect_ids=[oid],evidence_ids=evidence[:]);done.append(e['id']);left.remove(e['id'])
 if stopped:call('escalate',reason='Conditional recovery cannot continue safely or resource unavailable')
 return dict(status='PARTIAL' if done and left else 'ESCALATED' if left else 'RECOVERED',resolved_effect_ids=done,remaining_effect_ids=left,evidence_ids=evidence)
