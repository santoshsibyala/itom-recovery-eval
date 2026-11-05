"""Post-freeze artifact-mutation tests, separate from model protocol development."""
import copy,json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scoring import grade
from verify import verify

class Mutations(unittest.TestCase):
 def setUp(self):
  self.t=json.loads((ROOT/'service_controls/codec_pipeline-clean-1-atomic_guard.json').read_text())
  self.assertTrue(self.t['grade']['certified_operational'])
 def reject(self,t):
  with self.assertRaises(AssertionError):verify(t)
 def test_forged_observed_value(self):
  t=self.t;next(o for o in t['public'] if o['tool']=='read_resource')['reply']['result']['resources']['policy']['values']['minimum']=0
  t['grade']=grade(t);self.reject(t)
 def test_forged_history(self):
  t=self.t;next(o for o in t['public'] if o['tool']=='read_changes')['reply']['result']['resources']['policy']['complete']=False
  t['grade']=grade(t);self.reject(t)
 def test_dependency_omitted(self):
  t=self.t;next(o for o in reversed(t['public']) if o['tool']=='read_resource')['reply']['result']['resources'].pop('policy')
  self.assertFalse(grade(t)['certified_configuration']);self.reject(t)
 def test_epoch_mismatch(self):
  t=self.t;next(o for o in reversed(t['public']) if o['tool']=='read_changes')['reply']['result']['epoch']-=1
  self.assertFalse(grade(t)['certified_configuration']);self.reject(t)
 def test_wrong_audit_ids(self):
  t=self.t;next(o for o in t['public'] if o['tool']=='record_recovery_audit')['arguments']['effect_ids']=['target-encoder']
  self.assertFalse(grade(t)['certified_configuration']);self.reject(t)
 def test_forged_workload_digest(self):
  t=self.t;t['service']['requests'][0]['response']['checksum']='fake';self.reject(t)
 def test_duplicate_workload_id(self):
  t=self.t;t['service']['requests'][1]['payload']=t['service']['requests'][0]['payload'];self.reject(t)
 def test_missing_window(self):
  t=self.t;t['service']['windows'].pop();self.reject(t)
 def test_state_not_self_report(self):
  t=self.t;t['report']['remaining_effect_ids']=['target-encoder']
  self.assertTrue(grade(t)['configuration']);self.assertFalse(grade(t)['certified_configuration'])
 def test_healthy_claim_on_broken_service(self):
  t=json.loads((ROOT/'service_controls/codec_pipeline-lingering_fault-1-atomic_guard.json').read_text());t['report']['status']='OPERATIONAL'
  g=grade(t);self.assertTrue(g['configuration']);self.assertFalse(g['certified_operational']);self.assertTrue(g['unsupported_claim'])
if __name__=='__main__':unittest.main()
