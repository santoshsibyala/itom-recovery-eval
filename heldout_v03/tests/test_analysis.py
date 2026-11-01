import json,unittest
from pathlib import Path
from copy import deepcopy
from analysis.results import service_verify
class AnalysisTests(unittest.TestCase):
 def fixture(self):return json.loads(next(Path('service_study/baselines').glob('*.trace.json')).read_text())
 def test_actual_digest_recomputed(self):
  t=self.fixture();t['service']['requests'][-1]['returned_checksum']='forged'
  # Pick a healthy trace when the first baseline is intentionally unhealthy.
  for p in Path('service_study/baselines').glob('*.trace.json'):
   x=json.loads(p.read_text())
   if x['service']['health_pass']:t=x;t['service']['requests'][-1]['returned_checksum']='forged';break
  with self.assertRaises(ValueError):service_verify(t)
 def test_health_aggregation_not_trusted(self):
  t=self.fixture();t['service']['health_pass']=not t['service']['health_pass']
  with self.assertRaises(ValueError):service_verify(t)
 def test_omitted_probe_rejected(self):
  t=self.fixture();t['service']['requests'].pop()
  with self.assertRaises(ValueError):service_verify(t)
if __name__=='__main__':unittest.main()
