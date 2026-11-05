"""Offline lifecycle regression: no cluster or provider access."""
import unittest,tempfile,types,io,contextlib
from pathlib import Path
from unittest.mock import patch
import proposed_main_repair as repair
from harness import ExtensionRun,base
class Tests(unittest.TestCase):
 def simulate(self,parent,phase):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp)
   class Fake(parent):
    def __init__(self):
     self.phase=phase;self.ns='test';self.dp='deployment';self.cp='configmap';self.stage='init';self.calls=[];self.deleted=False;self.r=dict(errors=[],fixture_valid=False,policy='ordinary',condition='clean');self.journal=root/'journal.jsonl';self.f=self.journal.open('w');self.api=types.SimpleNamespace(close=lambda:None)
    def baseline(self):self.calls.append('baseline')
    def experiment(self):self.calls.append('experiment');self.r['fixture_valid']=True
    def get(self,path):
     if path.startswith('/api/v1/namespaces/'):
      if self.deleted:raise base.ApiError(404,{})
      return {'metadata':{'labels':{'itom-experiment':base.CLUSTER}}}
     return {}
    def request(self,*args):self.calls.append('delete');self.deleted=True
    def event(self,*args,**kw):self.f.write('{}\n');self.f.flush()
    def error(self,k,e):self.r['errors'].append({'kind':k,'error':str(e)})
   r=Fake();scores=[]
   def classify(x):scores.append(True);return {'test_scored':True}
   with patch.object(repair,'ROOT',root),patch.object(base,'ROOT',root),patch.object(repair,'classify',classify),patch.object(base,'classify',classify),contextlib.redirect_stdout(io.StringIO()):r.execute()
   return r.calls,r.r,len(scores)
 def test_reproduces_original_main_skip(self):
  calls,r,n=self.simulate(ExtensionRun,'main');self.assertNotIn('experiment',calls);self.assertEqual(n,0)
 def test_proposed_main_runs_and_scores_once(self):
  calls,r,n=self.simulate(repair.MainRun,'main');self.assertEqual(calls,['baseline','experiment','delete']);self.assertEqual(n,1);self.assertTrue(r['cleanup_complete']);self.assertFalse(r['errors'])
 def test_setup_still_no_experiment(self):
  calls,r,n=self.simulate(repair.MainRun,'setup');self.assertEqual(calls,['baseline','delete']);self.assertEqual(n,0)
