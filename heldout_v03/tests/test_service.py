import tempfile,unittest
from pathlib import Path
from service_lab.client import LiveService
from recovery.scenarios import scenario
from recovery.policies import run
from recovery.scoring import grade
class ServiceTests(unittest.TestCase):
 def run_case(self,variant,lingering=False):
  with tempfile.TemporaryDirectory() as d:
   with LiveService(scenario('route_failover',variant),Path(d)/'s',lingering=lingering) as s:
    t=s.finish(run(s.task,s.invoke,'field_compensator'));g=grade(t)
    self.assertEqual(len(set(x['pid'] for x in t['service']['processes'])),3)
    self.assertEqual(t['service']['pre_correct'],0)
    self.assertEqual(len(t['service']['terminal_windows']),3)
    self.assertTrue(all(w['requests']==20 for w in t['service']['terminal_windows']))
    return t,g
 def test_clean_real_requests(self):
  t,g=self.run_case('clean');self.assertTrue(g['configuration_recovery']);self.assertTrue(t['service']['health_pass'])
 def test_lingering_fault_not_configuration(self):
  t,g=self.run_case('clean',True);self.assertTrue(g['configuration_recovery']);self.assertFalse(t['service']['health_pass'])
 def test_separate_operator_race(self):
  t,g=self.run_case('dependency_race');self.assertFalse(g['configuration_recovery']);self.assertFalse(t['service']['health_pass']);self.assertIsNotNone(t['service']['operator'])
  self.assertNotIn(t['service']['operator']['operator_pid'],[x['pid'] for x in t['service']['processes']])
 def test_hidden_owner_preserved(self):
  t,g=self.run_case('hidden_owner');self.assertTrue(g['history_safe']);self.assertFalse(g['configuration_recovery'])
if __name__=='__main__':unittest.main()
