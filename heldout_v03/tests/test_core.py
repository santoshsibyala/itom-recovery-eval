import unittest
from copy import deepcopy
from recovery.environment import Environment,evaluate
from recovery.scenarios import suite,scenario,calibration,NAMES
from recovery.scoring import grade,constraints
from recovery.policies import run,POLICIES
from recovery.replay import verify
from recovery.common import digest

def episode(s,p):
 e=Environment(s);t=e.finish(run(e.task,e.invoke,p));t['grade']=grade(t);return t
class CoreTests(unittest.TestCase):
 def test_all_baselines_reconstruct_and_replay(self):
  for s in suite():
   for p in POLICIES:verify(episode(s,p))
 def test_clean_witnesses(self):
  for n in NAMES:self.assertTrue(episode(scenario(n,'clean'),'field_compensator')['grade']['configuration_recovery'],n)
 def test_disjoint_cas_tradeoff(self):
  for n in NAMES:
   self.assertTrue(episode(scenario(n,'disjoint'),'field_compensator')['grade']['configuration_recovery'])
   self.assertFalse(episode(scenario(n,'disjoint'),'object_cas')['grade']['configuration_recovery'])
 def test_hidden_owner_deferral(self):
  for n in NAMES:
   t=episode(scenario(n,'hidden_owner'),'field_compensator');self.assertFalse(t['grade']['configuration_recovery']);self.assertTrue(t['grade']['history_safe'])
 def test_races_visible(self):
  for n in NAMES:self.assertFalse(episode(scenario(n,'dependency_race'),'field_compensator')['grade']['configuration_recovery'])
 def test_scope_loss_not_success(self):
  for n in NAMES:self.assertFalse(episode(scenario(n,'disjoint'),'snapshot')['grade']['history_safe'])
 def test_unavailable_no_commit(self):
  for n in NAMES:
   t=episode(scenario(n,'partial_failure'),'field_compensator');self.assertFalse(t['grade']['configuration_recovery'])
   self.assertFalse(any(e['kind']=='effect' and e['actor']=='recovery' and e['resource'] in t['spec']['failures'] for e in t['events']))
 def test_mutated_transition(self):
  t=episode(calibration(),'field_compensator');t['events'][0]['after']['version']=44;prev=''
  for e in t['events']:e['previous']=prev;e.pop('hash',None);e['hash']=digest(e);prev=e['hash']
  with self.assertRaises(ValueError):grade(t)
 def test_mutated_public(self):
  t=episode(calibration(),'field_compensator');t['public'][0]['reply']['result']['version']=44
  with self.assertRaises(ValueError):verify(t)
 def test_no_hidden_owner_leak(self):
  e=Environment(scenario('route_failover','hidden_owner'));r=e.invoke('read_resource',resource_id='route')['reply']['result'];h=e.invoke('read_changes',resource_id='route')['reply']['result']
  self.assertTrue(all(v is None for v in r['provenance'].values()));self.assertFalse(h['complete']);self.assertEqual(h['changes'],[])
 def test_idempotence(self):
  e=Environment(calibration());a=dict(resource_id='scratch',patch={'x':1},expected_version=1,operation_id='recovery-x',target_effect_id='target-scratch')
  e.invoke('apply_patch',**a);self.assertTrue(e.invoke('apply_patch',**a)['reply']['result']['replayed']);a['patch']={'x':3};self.assertFalse(e.invoke('apply_patch',**a)['reply']['ok'])
 def test_independent_predicates(self):
  for s in suite():
   e=Environment(s);worlds=[s['initial'],{r:v['values'] for r,v in e.state.items()}]
   for target in s['effects']:
    w=deepcopy(worlds[-1]);w[target['resource']].update(target['before']);worlds.append(w)
   for w in worlds:self.assertEqual(all(evaluate(c,w) for c in s['constraints']),constraints(s['name'],w))
if __name__=='__main__':unittest.main()
