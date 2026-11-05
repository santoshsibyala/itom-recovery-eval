import unittest,tempfile,copy
from pathlib import Path
from unittest.mock import patch
import agent,common
from common import *
class FakeRun:
 def __init__(self):self.ns='unit';self.r={'policy':'ordinary','report':None};self.events=[];self.dispatched=[]
 def task(self):return {'task':'same'}
 def event(self,kind,**data):self.events.append(dict(kind=kind,**data))
 def tool(self,name,args):self.dispatched.append((name,args));return {'observation_id':'obs-1'}
class FakeLedger:
 def __init__(self):self.ids=[]
 def reserve(self,cid):self.ids.append(cid)
 def settle(self,cid,u):return 1
FIN={'status':'BLOCKED','claims':{'image':None,'replicas':None},'evidence_ids':[],'reason':'unsupported'}
def response(calls=None,model=MODEL):
 return {'http_status':200,'body':{'model':model,'stop_reason':'tool_use','usage':{'input_tokens':10,'output_tokens':20},'content':calls if calls is not None else [{'type':'tool_use','id':'c1','name':'finish','input':copy.deepcopy(FIN)}]}}
class Tests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.p=patch.object(agent,'mode_file',lambda:self.root/'mode.json');self.p.start();self.g=patch.object(agent,'gate',lambda:None);self.g.start()
 def tearDown(self):self.g.stop();self.p.stop();self.tmp.cleanup()
 def run_agent(self,responses):
  r=FakeRun();l=FakeLedger();out=iter(responses);seen=[]
  def transport(body=None,timeout=60,endpoint=None):
   seen.append((copy.deepcopy(body),endpoint));return {'http_status':200,'body':{'input_tokens':100}} if endpoint else next(out)
  agent.execute_agent(r,l,transport);return r,l,seen
 def test_native_fields_and_finish(self):
  r,l,s=self.run_agent([response()]);self.assertEqual(r.r['agent_outcome'],'valid_report');self.assertEqual(r.r['report']['claims'],{});b=s[1][0];self.assertEqual(b['tool_choice'],{'type':'any','disable_parallel_tool_use':True});self.assertEqual(b['thinking'],{'type':'disabled'});self.assertEqual(b['temperature'],0);self.assertNotIn('store',b);self.assertEqual(b['max_tokens'],900);self.assertEqual(b['system'],prompt());self.assertEqual([t['input_schema'] for t in b['tools']],list(SCHEMAS.values()))
 def test_multiple_calls_never_dispatch(self):
  c={'type':'tool_use','id':'c','name':'recover','input':{'restore_image':True,'restore_replicas':True}};r,_,_=self.run_agent([response([c,c])]);self.assertEqual(r.r['agent_outcome'],'malformed_tool_call');self.assertFalse(r.dispatched)
 def test_invalid_call_never_dispatch(self):
  r,_,_=self.run_agent([response([{'type':'tool_use','id':'c','name':'recover','input':{'restore_image':1,'restore_replicas':True}}])]);self.assertEqual(r.r['agent_outcome'],'malformed_tool_call');self.assertFalse(r.dispatched)
 def test_history_mapping(self):
  r,_,s=self.run_agent([response([{'type':'tool_use','id':'c','name':'read_deployment','input':{}}]),response()]);m=s[3][0]['messages'];self.assertEqual(m[1]['role'],'assistant');self.assertEqual(m[2]['content'][0]['tool_use_id'],'c');self.assertNotIn('is_error',m[2]['content'][0])
 def test_no_report_distinct(self):
  r,_,_=self.run_agent([response([])]);self.assertEqual(r.r['agent_outcome'],'no_report')
 def test_model_mismatch_stops(self):
  r,_,_=self.run_agent([response(model='alias')]);self.assertTrue(r.r['stop_cohort']);self.assertFalse(r.dispatched)
 def test_strict_rejection_narrow(self):
  b=agent.make_request('ordinary',[])
  self.assertTrue(agent.strict_rejection({'http_status':400,'error_message':'tools.0.strict: extra inputs are not permitted'},b))
  for msg in ['temperature not supported','model not available','Invalid schema','strict schema missing required properties']:
   self.assertFalse(agent.strict_rejection({'http_status':400,'error_message':msg},b))
  self.assertFalse(agent.strict_rejection({'http_status':429,'error_message':'strict not supported'},b))
 def test_count_strict_fallback_changes_only_strict(self):
  seen=[];r=FakeRun();l=FakeLedger()
  def tr(body=None,timeout=60,endpoint=None):
   seen.append((copy.deepcopy(body),endpoint))
   if len(seen)==1:return {'http_status':400,'error_type':'invalid_request_error','error_message':'strict is not supported for this model'}
   if endpoint:return {'http_status':200,'body':{'input_tokens':100}}
   return response()
  agent.execute_agent(r,l,tr);self.assertEqual(r.r['agent_outcome'],'valid_report');a=seen[0][0];b=seen[1][0]
  for t in a['tools']:t.pop('strict')
  self.assertEqual(a,b);self.assertFalse(agent.strict_enabled());self.assertEqual(len(l.ids),1)
 def test_generation_strict_rejection_retained(self):
  r,l,_=self.run_agent([{'http_status':400,'error_type':'invalid_request_error','error_message':'strict not supported'}]);self.assertEqual(r.r['agent_outcome'],'provider_error');self.assertFalse(r.r.get('stop_cohort',False));self.assertEqual(len(l.ids),1);self.assertFalse(agent.strict_enabled())
 def test_other_setting_rejection_stops(self):
  r,_,_=self.run_agent([{'http_status':400,'error_type':'invalid_request_error','error_message':'temperature not supported'}]);self.assertTrue(r.r['stop_cohort']);self.assertTrue(agent.strict_enabled())
 def test_input_cap_no_generation(self):
  r=FakeRun();l=FakeLedger();agent.execute_agent(r,l,lambda *a,**k:{'http_status':200,'body':{'input_tokens':20000}});self.assertEqual(r.r['agent_outcome'],'budget_exhausted');self.assertFalse(l.ids)
 def test_ledger_opening_pending_settlement(self):
  l=Ledger(self.root/'cost.sqlite3')
  with patch.object(l,'verify_prior',lambda:None):l.reserve('one');l.reserve('unknown')
  l.settle('one',{'input_tokens':100,'output_tokens':10});s=l.snapshot();self.assertAlmostEqual(s['prior_1_0_usd'],.1795376);self.assertAlmostEqual(s['pending_reserved_usd'],.2045);self.assertAlmostEqual(s['actual_1_1_usd'],.00015)
 def test_ledger_stops_at_cap(self):
  l=Ledger(self.root/'cap.sqlite3');n=0
  with patch.object(l,'verify_prior',lambda:None):
   while True:
    try:l.reserve(str(n));n+=1
    except BudgetStop:break
  self.assertLessEqual(l.snapshot()['total_bound_usd'],25);self.assertGreater(l.snapshot()['total_bound_usd']+.2045,25)
