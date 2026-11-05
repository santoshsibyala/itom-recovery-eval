import tempfile,unittest,csv,json
from pathlib import Path
from analyze_main import ARMS,CONDS,render_insert,csvwrite
class AnalysisTests(unittest.TestCase):
 def test_insert_is_computed_and_bounded(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);(p/'verification.json').write_text('{}');rows=[]
   for a in ARMS:
    for c in CONDS:
     row=dict(arm=a,condition=c,outcomes_identical=True)
     for k in ['healthy_true','reread_deployment_before_recover_true','read_configmap_before_recover_true','requested_image','requested_replicas','requested_both','requested_not_requested','blocked_on_observed_v2_true','successful_recovery_true','unsafe_overwrite_true','committed_under_false_predicate_true','report_supported_true']:row[k]=0
     row.update(healthy_true=5,requested_both=5,read_configmap_before_recover_true=5)
     rows.append(row)
   csvwrite(p/'summary.csv',rows);render_insert(p/'summary.csv',p,{})
   text=(p/'PAPER_INSERT.md').read_text();self.assertIn('Health checks passed in 50/50',text);self.assertIn('25/25',text);self.assertIn('the tested agent (gpt-4.1-mini-2025-04-14)',text);self.assertIn('every cell',text)
   self.assertLessEqual(json.loads((p/'PAPER_INSERT_BINDING.json').read_text())['prose_words'],270)
 def test_variation_not_flattened(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);(p/'verification.json').write_text('{}');rows=[]
   for a in ARMS:
    for c in CONDS:
     row=dict(arm=a,condition=c,outcomes_identical=False)
     for k in ['healthy_true','reread_deployment_before_recover_true','read_configmap_before_recover_true','requested_image','requested_replicas','requested_both','requested_not_requested','blocked_on_observed_v2_true','successful_recovery_true','unsafe_overwrite_true','committed_under_false_predicate_true','report_supported_true']:row[k]=1
     rows.append(row)
   csvwrite(p/'summary.csv',rows);render_insert(p/'summary.csv',p,{})
   text=(p/'PAPER_INSERT.md').read_text();self.assertIn('0 of 10 cells',text);self.assertIn('10/50',text);self.assertIn('1/1/1/1',text)
if __name__=='__main__':unittest.main()
