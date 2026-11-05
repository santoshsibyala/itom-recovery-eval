import inspect,unittest,datetime,json,tempfile
from pathlib import Path
from unittest.mock import patch
import main_execution as m
from common import ROOT,sha
class MainTests(unittest.TestCase):
 def test_only_phase_dispatch_changed(self):
  expected=inspect.getsource(m.base.Run.execute).replace("('smoke','smoke-A1')","('smoke','smoke-A1','main')")
  self.assertEqual(expected,inspect.getsource(m.MainRun.execute))
 def test_frozen_source_and_smoke(self):m.verify_frozen()
 def test_deadline(self):
  m.main_gate(datetime.datetime(2026,11,9,20,tzinfo=m.ZoneInfo('America/Los_Angeles')))
  with self.assertRaises(RuntimeError):m.main_gate(datetime.datetime(2026,11,10,0,tzinfo=m.ZoneInfo('America/Los_Angeles')))
 def test_schedule_repetitions(self):
  from runner import schedule
  cells=json.loads((ROOT/'main_schedule.json').read_text());self.assertEqual(cells,schedule('main',5))
  self.assertEqual(len({(x['policy'],x['condition'],x['repetition']) for x in cells}),50)
 def test_interrupted_not_replayed(self):
  with tempfile.TemporaryDirectory() as d,patch.object(m,'ROOT',Path(d)):
   p=Path(d)/'itom-k8s-test-main-001.jsonl';p.write_text('{"seq":1,"kind":"started"}\n')
   r=m.finalize_interrupted(p,{'policy':'ordinary','condition':'clean','repetition':1},{},1)
   self.assertEqual(r['agent_outcome'],'interrupted');self.assertTrue(r['stop_cohort']);self.assertIsNone(r['metrics']['successful_recovery'])
   with self.assertRaises(FileExistsError):m.finalize_interrupted(p,{'policy':'ordinary','condition':'clean','repetition':1},{},1)
class CleanupTests(unittest.TestCase):
 def test_complete_main_execute_cleanup(self):
  import io,contextlib
  from unittest.mock import Mock
  from test_extension import deployment
  with tempfile.TemporaryDirectory() as d,patch.object(m,'ROOT',Path(d)):
   r=m.MainRun.__new__(m.MainRun);r.ns='test-main';r.phase='main';r.stage='initialization';r.seq=0
   r.r=dict(condition='clean',policy='ordinary',fixture_valid=True,errors=[],good_image='good',health_series=[],mutation_outcome='no_dispatch')
   r.journal=Path(d)/'journal.jsonl';r.f=r.journal.open('w');r.api=Mock();r.dp='/deployment';r.cp='/config'
   r.baseline=lambda:None;r.experiment=lambda:None
   seen=[];deleted=[]
   def get(path):
    if path=='/deployment':return deployment()
    if path=='/config':return {'data':{'mode':'v1'}}
    if path=='/api/v1/namespaces/test-main':
     seen.append(path)
     if len(seen)>1:raise m.ApiError(404,{})
     return {'metadata':{'labels':{'itom-experiment':'itom-k8s-validation'}}}
    raise AssertionError(path)
   r.get=get;r.request=lambda *args,**kwargs:deleted.append(args)
   with contextlib.redirect_stdout(io.StringIO()):record=r.execute()
   self.assertTrue(record['cleanup_complete']);self.assertFalse(record['errors']);self.assertEqual(deleted[0][0],'DELETE')
if __name__=='__main__':unittest.main()
