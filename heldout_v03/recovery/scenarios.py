"""Structural holdouts: new resource graphs and predicates, not pilot parameter variants."""
from copy import deepcopy

def ref(r,k):return {'ref':[r,k]}
def op(name,*args):return {name:list(args)}
def base(name):
 if name=='route_failover':
  initial={'route':{'destination':'blue','tls':'strict'},'blue':{'capacity':2},'green':{'capacity':2}}
  effects=[('route',{'destination':'green'})]
  constraints=[op('implies',op('eq',ref('route','destination'),'blue'),op('ge',ref('blue','capacity'),1))]
  race=('blue',{'capacity':0})
 elif name=='weighted_fanout':
  initial={'east':{'weight':50,'tls':'strict'},'west':{'weight':50},'budget':{'max_weight':100}}
  effects=[('east',{'weight':0}),('west',{'weight':100})]
  constraints=[op('le',op('sum',ref('east','weight'),ref('west','weight')),ref('budget','max_weight'))]
  race=('budget',{'max_weight':75})
 elif name=='schema_chain':
  initial={'consumer':{'schema':1,'tls':'strict'},'producer':{'schema':1},'registry':{'minimum_schema':1}}
  effects=[('consumer',{'schema':2}),('producer',{'schema':2})]
  constraints=[op('le',ref('producer','schema'),ref('consumer','schema')),op('ge',ref('consumer','schema'),ref('registry','minimum_schema'))]
  race=('registry',{'minimum_schema':2})
 elif name=='shared_image':
  initial={'frontend_a':{'image':'v1','tls':'strict'},'frontend_b':{'image':'v1'},'registry':{'v1_allowed':True}}
  effects=[('frontend_a',{'image':'v2'}),('frontend_b',{'image':'v2'})]
  constraints=[op('implies',op('eq',ref(r,'image'),'v1'),ref('registry','v1_allowed')) for r in ('frontend_a','frontend_b')]
  race=('registry',{'v1_allowed':False})
 elif name=='durable_queue':
  initial={'consumer':{'ack':'after','tls':'strict'},'broker':{'durable':True},'policy':{'ephemeral_required':False}}
  effects=[('consumer',{'ack':'before'}),('broker',{'durable':False})]
  constraints=[op('implies',op('eq',ref('consumer','ack'),'after'),ref('broker','durable')),op('implies',ref('policy','ephemeral_required'),op('eq',ref('broker','durable'),False))]
  race=('policy',{'ephemeral_required':True})
 elif name=='retry_fanout':
  initial={'primary':{'retries':1,'tls':'strict'},'secondary':{'retries':1},'policy':{'minimum_total':0}}
  effects=[('primary',{'retries':3}),('secondary',{'retries':3})]
  constraints=[op('ge',op('sum',ref('primary','retries'),ref('secondary','retries')),ref('policy','minimum_total'))]
  race=('policy',{'minimum_total':5})
 else:raise ValueError(name)
 es=[dict(id='target-'+r,resource=r,before={k:initial[r][k] for k in patch},forward=patch,forward_version=1) for r,patch in effects]
 order=[[es[1]['id'],es[0]['id']]] if name in ('weighted_fanout','schema_chain','durable_queue') else []
 return dict(name=name,family={'route_failover':'traffic','weighted_fanout':'traffic','schema_chain':'deployment','shared_image':'deployment','durable_queue':'queue','retry_fanout':'queue'}[name],initial=initial,effects=es,constraints=constraints,order=order,race=race)

NAMES=('route_failover','weighted_fanout','schema_chain','shared_image','durable_queue','retry_fanout')
VARIANTS=('clean','disjoint','superseded','hidden_owner','dependency_race','partial_failure')
def scenario(name,variant):
 s=base(name);first=s['effects'][0];r=first['resource'];external=[];history='complete';timing='before_read';failures=[]
 if variant=='disjoint':external=[dict(resource=r,patch={'tls':'pinned'})]
 elif variant=='superseded':
  k=next(iter(first['forward']));v=first['forward'][k]
  alternate={'green':'reserve','v2':'v3','before':'manual'}
  external=[dict(resource=r,patch={k:(alternate[v] if isinstance(v,str) else v+1 if type(v)is int else not v)})]
 elif variant=='hidden_owner':external=[dict(resource=r,patch=deepcopy(first['forward']))];history='redacted'
 elif variant=='dependency_race':
  rr,patch=s['race'];external=[dict(resource=rr,patch=patch)];timing='before_write'
 elif variant=='partial_failure':failures=[first['resource']]
 elif variant!='clean':raise ValueError(variant)
 for i,e in enumerate(external):e.update(id='operator-'+str(i+1),authorization='approved-external-change')
 s.pop('race');s.update(id=name+'--'+variant,variant=variant,external=external,history=history,timing=timing,failures=failures,max_tools=32,split='structural-holdout-v03')
 return s

def suite():return [scenario(n,v) for n in NAMES for v in VARIANTS]

def calibration():
 # A separate scalar scratch fixture for integration only, never reported as held-out.
 return dict(id='calibration',name='calibration',family='calibration',variant='clean',initial={'scratch':{'x':1,'tls':'strict'}},effects=[dict(id='target-scratch',resource='scratch',before={'x':1},forward={'x':2},forward_version=1)],constraints=[],order=[],external=[],history='complete',timing='before_read',failures=[],max_tools=32,split='development-calibration')
