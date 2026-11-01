from copy import deepcopy
from .common import digest,require

def evaluate(expr,values):
 if not isinstance(expr,dict):return expr
 if 'ref' in expr:r,k=expr['ref'];return values[r][k]
 name,args=next(iter(expr.items()));xs=[evaluate(a,values) for a in args]
 if name=='eq':return xs[0]==xs[1]
 if name=='ge':return xs[0]>=xs[1]
 if name=='le':return xs[0]<=xs[1]
 if name=='sum':return sum(xs)
 if name=='implies':return not xs[0] or xs[1]
 raise ValueError('Unknown predicate')

class Environment:
 def __init__(self,spec):
  self.spec=deepcopy(spec);self.state={r:dict(values=deepcopy(v),version=0,provenance={k:'initial' for k in v}) for r,v in spec['initial'].items()};self.events=[];self.public=[];self.operations={};self.external_done=False;self.finished=False
  for e in spec['effects']:self.commit(e['resource'],e['forward'],e['id'],'remediator',None)
  self.task={k:deepcopy(spec[k]) for k in ('effects','constraints','order')};self.task.update(resource_ids=list(self.state),capability='single-resource CAS only; no cross-resource atomicity',goal='Restore target before values while preserving approved external writes, including same-value reauthorization. Never overwrite a superseding owner. Honor predicates after every recovery write. RECOVERED asserts configuration, not measured service health.',expression_language='A ref is [resource,field]. eq/ge/le compare two terms, sum adds terms, implies is logical implication. Literal scalars evaluate to themselves.',history_contract='complete=false or null provenance is unknown, not evidence of no intervening write.')
  if spec['timing']=='before_read':self.external()
 def event(self,kind,**data):
  e=dict(seq=len(self.events)+1,previous=self.events[-1]['hash'] if self.events else '',kind=kind,**deepcopy(data));e['hash']=digest(e);self.events.append(e)
 def commit(self,r,patch,oid,actor,target):
  before=deepcopy(self.state[r]);self.state[r]['values'].update(patch);self.state[r]['version']+=1
  for k in patch:self.state[r]['provenance'][k]=oid
  self.event('effect',resource=r,patch=patch,operation_id=oid,actor=actor,target=target,before=before,after=self.state[r])
  result=dict(committed=True,operation_id=oid,resource=r,version=self.state[r]['version']);self.operations[oid]=dict(result=result,patch=deepcopy(patch),target=target)
  return result
 def external(self):
  if self.external_done:return
  self.external_done=True
  for e in self.spec['external']:self.commit(e['resource'],e['patch'],e['id'],'operator',None)
 def invoke(self,tool,**a):
  require(not self.finished and len(self.public)<self.spec['max_tools'],'Tool budget exhausted')
  self.event('dispatch',tool=tool,arguments=a)
  try:reply=dict(ok=True,result=self.dispatch(tool,a))
  except (ValueError,TypeError,KeyError) as ex:reply=dict(ok=False,error=type(ex).__name__,message=str(ex))
  o=dict(evidence_id=f'obs-{len(self.public)+1}',tool=tool,arguments=deepcopy(a),reply=reply);self.public.append(deepcopy(o));self.event('observation',observation=o)
  return deepcopy(o)
 def dispatch(self,tool,a):
  schema={'read_resource':{'resource_id'},'read_changes':{'resource_id'},'read_health':set(),'apply_patch':{'resource_id','patch','expected_version','operation_id','target_effect_id'},'get_operation':{'operation_id'},'record_recovery_audit':{'effect_ids','evidence_ids'},'escalate':{'reason'}}
  require(tool in schema and set(a)==schema[tool],'Unknown tool or argument fields')
  if tool in ('read_resource','read_changes'):
   r=a['resource_id'];require(r in self.state,'Unknown resource')
   if tool=='read_resource':
    v=deepcopy(self.state[r])
    if self.spec['history']=='redacted':v['provenance']={k:None for k in v['provenance']}
    return dict(resource_id=r,**v)
   changes=[{k:e[k] for k in ('actor','operation_id','patch','target')} for e in self.events if e['kind']=='effect' and e['resource']==r]
   return dict(complete=self.spec['history']=='complete',current_version=self.state[r]['version'],changes=changes if self.spec['history']=='complete' else [])
  if tool=='read_health':return dict(synthetic=True,constraints_satisfied=all(evaluate(x,{r:v['values'] for r,v in self.state.items()}) for x in self.spec['constraints']))
  if tool=='get_operation':return deepcopy(self.operations.get(a['operation_id'],{}).get('result',{'committed':False}))
  if tool=='apply_patch':
   r=a['resource_id'];p=a['patch'];oid=a['operation_id'];target=a['target_effect_id']
   require(r in self.state and type(p)is dict and p and all(k in self.state[r]['values'] and type(v)is type(self.state[r]['values'][k]) for k,v in p.items()),'Invalid patch')
   require(type(oid)is str and oid.startswith('recovery-') and target in {e['id'] for e in self.spec['effects']},'Invalid operation/target')
   require(a['expected_version'] is None or type(a['expected_version'])is int,'Invalid CAS version')
   if oid in self.operations:
    old=self.operations[oid];require(old['patch']==p and old['target']==target and old['result']['resource']==r,'Idempotency collision');return dict(old['result'],replayed=True)
   self.external()
   if a['expected_version'] is not None and self.state[r]['version']!=a['expected_version']:return dict(committed=False,conflict=True)
   if r in self.spec['failures']:return dict(committed=False,error='PermanentUnavailable',retryable=False)
   return self.commit(r,p,oid,'recovery',target)
  if tool=='record_recovery_audit':
   require(all(type(v)is list and all(type(x)is str for x in v) for v in a.values()),'Invalid audit')
   require(bool(a['effect_ids']) and bool(a['evidence_ids']),'Empty audit')
   require(all(x in self.operations and self.operations[x]['target'] is not None for x in a['effect_ids']),'Unknown recovery operation')
   require(set(a['evidence_ids'])<={o['evidence_id'] for o in self.public},'Unknown evidence');self.event('audit',**a);return dict(recorded=True)
  require(type(a['reason'])is str and bool(a['reason']),'Missing reason');self.event('escalation',**a);return dict(recorded=True)
 def finish(self,report):
  require(not self.finished,'Already finished');self.finished=True;self.event('terminal',report=report)
  return deepcopy(dict(spec=self.spec,task=self.task,events=self.events,public=self.public,report=report,final=self.state))
