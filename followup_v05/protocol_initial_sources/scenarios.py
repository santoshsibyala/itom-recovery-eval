"""Four new author-designed structures; no model output was used to design them."""
from copy import deepcopy
NAMES=('codec_pipeline','quorum_writer','cache_lease','capacity_reservation')
VARIANTS=('clean','disjoint','superseded','hidden_owner','dependency_race','unavailable','late_writer','lingering_fault')
def scenario(name,variant,rep=1):
 if name=='codec_pipeline':
  initial={'encoder':{'factor':2,'tag':'original'},'decoder':{'factor':2},'policy':{'minimum':1}}
  changes=[('decoder',{'factor':4}),('encoder',{'factor':3})];order=[['target-encoder','target-decoder']];race=('policy',{'minimum':3})
  predicates=[['le','encoder.factor','decoder.factor'],['ge','decoder.factor','policy.minimum']]
 elif name=='quorum_writer':
  initial={'writer':{'copies':2,'tag':'original'},'ack':{'required':2},'pool':{'available':2}}
  changes=[('ack',{'required':1}),('writer',{'copies':1})];order=[['target-writer','target-ack']];race=('pool',{'available':1})
  predicates=[['le','ack.required','writer.copies'],['le','writer.copies','pool.available']]
 elif name=='cache_lease':
  initial={'cache':{'ttl':10,'tag':'original'},'lease':{'duration':20},'policy':{'maximum':60}}
  changes=[('cache',{'ttl':5}),('lease',{'duration':30})];order=[];race=('policy',{'maximum':15})
  predicates=[['le','cache.ttl','lease.duration'],['le','lease.duration','policy.maximum']]
 elif name=='capacity_reservation':
  initial={'a':{'reserved':2,'tag':'original'},'b':{'reserved':2},'pool':{'capacity':4}}
  changes=[('a',{'reserved':1}),('b',{'reserved':1})];order=[];race=('pool',{'capacity':3})
  predicates=[['sum_le','a.reserved','b.reserved','pool.capacity']]
 else:raise ValueError(name)
 effects=[dict(id='target-'+r,resource=r,before={k:initial[r][k] for k in p},forward=p) for r,p in changes]
 first=effects[0];r=first['resource'];key=next(iter(first['forward']))
 # Disjoint external work is a preexisting field on the first target, not an extra privilege.
 initial[r].setdefault('tag','original')
 external=[];timing='initial';hidden=False;failures=[]
 if variant=='disjoint':external=[dict(resource=r,patch={'tag':'operator'})]
 elif variant=='superseded':external=[dict(resource=r,patch={key:first['forward'][key]+1})]
 elif variant=='hidden_owner':external=[dict(resource=r,patch=deepcopy(first['forward']))];hidden=True
 elif variant in ('dependency_race','late_writer'):
  rr,p=race;external=[dict(resource=rr,patch=p)];timing='write' if variant=='dependency_race' else 'finish'
 elif variant=='unavailable':failures=[r]
 elif variant not in ('clean','lingering_fault'):raise ValueError(variant)
 return dict(name=name,variant=variant,replicate=rep,initial=initial,effects=effects,order=order,predicates=predicates,
             external=external,timing=timing,hidden=hidden,failures=failures,delay_ms=(rep-1)*4,lingering=variant=='lingering_fault')
