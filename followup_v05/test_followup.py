import copy,itertools,json,tempfile,unittest
from pathlib import Path
from scenarios import scenario,NAMES,VARIANTS
from runtime import Runtime,predicates
from scoring import grade,valid_state
from policies import run

class Core(unittest.TestCase):
 def make(self,name='codec_pipeline',variant='clean',policy='field',guard='none',post=True):
  spec=scenario(name,variant);d=tempfile.TemporaryDirectory();self.addCleanup(d.cleanup);rt=Runtime(spec,Path(d.name)/'state.sqlite3',guard)
  rt.health=lambda:dict(measured=False,epoch=len(rt.finish({})['events']),stable_epoch=True,pass_window=True)
  count=[0]
  def invoke(tool,**a):
   if tool=='apply_patch':
    count[0]+=1
    if spec['timing']=='write' and count[0]==2:rt.external()
   return rt.invoke(tool,**a)
  report=run(rt,invoke,policy)
  if spec['timing']=='finish':rt.external()
  return rt,rt.finish(report)
 def test_clean_and_disjoint_witnesses(self):
  for name,var in itertools.product(NAMES,('clean','disjoint')):
   _,t=self.make(name,var,guard='atomic');g=grade(t);self.assertTrue(g['configuration']);self.assertTrue(g['certified_configuration'])
 def test_atomic_blocks_dependency_race(self):
  for name in NAMES:
   _,t=self.make(name,'dependency_race',guard='atomic');self.assertTrue(grade(t)['history_safe']);self.assertFalse(grade(t)['configuration'])
 def test_field_is_not_atomic(self):
  for name in NAMES:
   _,t=self.make(name,'dependency_race');self.assertFalse(grade(t)['history_safe'])
 def test_ownership_only_ablation(self):
  _,t=self.make(variant='dependency_race',guard='owner');self.assertFalse(grade(t)['history_safe'])
 def test_late_writer_invalidates_certificate(self):
  _,t=self.make(variant='late_writer',guard='atomic');g=grade(t);self.assertFalse(g['configuration']);self.assertFalse(g['evidence_complete'])
 def test_hidden_owner(self):
  _,t=self.make(variant='hidden_owner',guard='atomic');g=grade(t);self.assertTrue(g['history_safe']);self.assertFalse(g['evidence_complete'])
 def test_missing_dependency_evidence(self):
  _,t=self.make();t=copy.deepcopy(t)
  for o in t['public']:
   if o['tool'] in ('read_resource','read_changes'):o['reply']['result']['resources'].pop('policy',None)
  self.assertFalse(grade(t)['certified_configuration'])
 def test_stale_history_rejected(self):
  _,t=self.make()
  last=next(o for o in reversed(t['public']) if o['tool']=='read_changes');last['reply']['result']['epoch']-=1
  self.assertFalse(grade(t)['certified_configuration'])
 def test_extra_known_citations_do_not_require_extra_audit_links(self):
  _,t=self.make();t['report']['evidence_ids'].append(t['public'][0]['evidence_id'])
  self.assertTrue(grade(t)['certified_configuration'])
 def test_audit_evidence_link_required(self):
  _,t=self.make()
  for o in t['public']:
   if o['tool']=='record_recovery_audit':o['arguments']['evidence_ids']=[]
  self.assertFalse(grade(t)['certified_configuration'])
 def test_partial_final_predicate(self):
  _,t=self.make(variant='unavailable',guard='atomic');self.assertTrue(grade(t)['partial'])
 def test_independent_predicates(self):
  for name in NAMES:
   s=scenario(name,'clean');fields=[(r,k) for r,v in s['initial'].items() for k,x in v.items() if type(x)is int]
   for values in itertools.product((0,1,2,3,5),repeat=len(fields)):
    v=copy.deepcopy(s['initial'])
    for (r,k),x in zip(fields,values):v[r][k]=x
    self.assertEqual(predicates(s,v),valid_state(name,v))
 def test_corrupt_event(self):
  _,t=self.make();t['events'][0]['after']['version']+=1
  with self.assertRaises(AssertionError):grade(t)
 def test_idempotency(self):
  rt,t=self.make();o=next(o for o in t['public'] if o['tool']=='apply_patch');n=len(t['events'])
  self.assertTrue(rt.invoke('apply_patch',**o['arguments'])['reply']['result']['replayed']);self.assertEqual(n,len(rt.finish({})['events']))

class Service(unittest.TestCase):
 def test_real_topologies_and_lingering_fault(self):
  from services import Live
  for name,var in itertools.product(NAMES[:2],('clean','lingering_fault','dependency_race','late_writer')):
   with tempfile.TemporaryDirectory() as d:
    rt=Runtime(scenario(name,var),Path(d)/'state.sqlite3','atomic')
    with Live(rt,Path(d)/'processes') as live:t=live.finish(run(rt,live.invoke,'atomic_guard'))
    t['grade']=grade(t)
    from verify import verify
    self.assertTrue(verify(t))
    corrupt=copy.deepcopy(t);corrupt['service']['requests'][0]['correct']=not corrupt['service']['requests'][0]['correct']
    with self.assertRaises(AssertionError):verify(corrupt)
    g=grade(t);self.assertEqual(g['configuration'],var in ('clean','lingering_fault'));self.assertEqual(g['certified_operational'],var=='clean')
    self.assertEqual(len({p['pid'] for p in t['service']['processes']}),2 if name=='codec_pipeline' else 3)

if __name__=='__main__':unittest.main()
