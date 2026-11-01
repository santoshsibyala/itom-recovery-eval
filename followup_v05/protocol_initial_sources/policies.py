from copy import deepcopy
from runtime import predicates
POLICIES=('noop','snapshot','object_cas','field','owner_guard','atomic_guard')
def run(rt,invoke,policy):
 effects={e['id']:e for e in rt.task['effects']};pending=list(effects);ordered=[];ops=[]
 while pending:
  ready=next(k for k in pending if all(a in ordered for a,b in rt.task['order'] if b==k));pending.remove(ready);ordered.append(ready)
 if policy!='noop':
  for tid in ordered:
   e=effects[tid];r=e['resource'];view=invoke('read_resource',resource_id='*')['reply']['result']['resources'];hist=invoke('read_changes',resource_id='*')['reply']['result']['resources']
   if policy in ('field','owner_guard','atomic_guard'):
    if not hist[r]['complete'] or any(view[r]['owners'][k]!=tid for k in e['before']):break
    candidate={rr:deepcopy(x['values']) for rr,x in view.items()};candidate[r].update(e['before'])
    if not predicates(rt.spec,candidate):break
   patch=deepcopy(e['before'])
   if policy=='snapshot':patch=deepcopy(rt.spec['initial'][r])
   oid='recovery-'+tid
   o=invoke('apply_patch',resource_id=r,patch=patch,expected_version=None if policy=='snapshot' else 1 if policy=='object_cas' else view[r]['version'],operation_id=oid,target_effect_id=tid)
   if not o['reply']['ok'] or not o['reply']['result']['committed']:break
   ops.append(oid)
 view=invoke('read_resource',resource_id='*');hist=invoke('read_changes',resource_id='*');health=invoke('read_health')
 cites=[x['evidence_id'] for x in (view,hist,health)]
 if ops:invoke('record_recovery_audit',effect_ids=ops,evidence_ids=cites)
 state=view['reply']['result']['resources'];done=[k for k,e in effects.items() if all(state[e['resource']]['values'][f]==v for f,v in e['before'].items())];left=[k for k in effects if k not in done]
 return dict(status=('OPERATIONAL' if health['reply']['result']['pass_window'] and health['reply']['result']['measured'] else 'RECOVERED') if not left else 'PARTIAL' if done else 'ESCALATED',resolved_effect_ids=done,remaining_effect_ids=left,evidence_ids=cites)
