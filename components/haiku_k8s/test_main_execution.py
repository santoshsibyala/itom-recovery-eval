import unittest,tempfile,json,datetime
from pathlib import Path
from unittest.mock import patch
import main_execution as m
class Tests(unittest.TestCase):
 def test_main_gate_accepts_after_smoke_cutoff_before_main_cutoff(self):
  m.main_gate(datetime.datetime(2026,11,8,20,tzinfo=m.ZoneInfo('America/Los_Angeles')))
 def test_main_deadline_stops(self):
  with self.assertRaises(RuntimeError):m.main_gate(m.MAIN_DEADLINE)
 def test_authorization_required(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);(p/'MAIN_APPROVAL.json').write_text(json.dumps(dict(main_authorized=False,smoke_reviewed_and_approved=True,approved_by='Santosh Sibyala')))
   with patch.object(m,'ROOT',p),self.assertRaises(AssertionError):m.main_gate()
 def test_interrupt_retains_unknown_and_prevents_replacement(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);j=p/'retained.jsonl';j.write_text('{"kind":"started"}\n{incomplete')
   with patch.object(m,'ROOT',p):
    r=m.finalize_interrupted(j,dict(policy='ordinary',condition='dep_race_late',repetition=1),{},1)
    self.assertEqual(r['agent_outcome'],'interrupted');self.assertEqual(r['mutation_outcome'],'unknown');self.assertTrue(r['stop_cohort'])
    with self.assertRaises(FileExistsError):m.finalize_interrupted(j,dict(policy='ordinary',condition='dep_race_late',repetition=1),{},1)
 def test_frozen_bindings(self):m.verify_frozen()
