import unittest,tempfile,json
from pathlib import Path
from unittest.mock import patch
import main_b_execution as m
import test_proposed_main_repair as previous
class Tests(unittest.TestCase):
 def test_main_b_dispatches_and_classifies(self):
  with patch.object(previous,'repair',m):calls,r,n=previous.Tests().simulate(m.MainRun,'main-b')
  self.assertEqual(calls,['baseline','experiment','delete']);self.assertEqual(n,1);self.assertTrue(r['cleanup_complete']);self.assertFalse(r['errors'])
 def test_canary_dispatches_and_classifies(self):
  with patch.object(previous,'repair',m):calls,r,n=previous.Tests().simulate(m.MainRun,'canary')
  self.assertEqual(calls,['baseline','experiment','delete']);self.assertEqual(n,1)
 def test_setup_unchanged(self):
  with patch.object(previous,'repair',m):calls,r,n=previous.Tests().simulate(m.MainRun,'setup')
  self.assertEqual(calls,['baseline','delete']);self.assertEqual(n,0)
 def test_canary_order_checker(self):
  kinds=['lifecycle_baseline_completed','injection_acknowledged','lifecycle_measurement_completed','lifecycle_classification_completed','lifecycle_cleanup_completed']
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'journal';es=[dict(kind=k,seq=i+1,elapsed=90,window_complete=True) for i,k in enumerate(kinds)];p.write_text('\n'.join(json.dumps(e) for e in es));self.assertTrue(m.verify_lifecycle(p)['passed']);es[3]['seq'],es[4]['seq']=es[4]['seq'],es[3]['seq'];p.write_text('\n'.join(json.dumps(e) for e in es))
   with self.assertRaises(AssertionError):m.verify_lifecycle(p)
 def test_frozen_sources_and_invalid_cohort(self):m.verify_frozen()
