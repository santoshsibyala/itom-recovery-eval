import unittest,tempfile,copy,json,datetime
from pathlib import Path
from unittest.mock import patch
from common import *
from harness import ExtensionRun,base
from runner import schedule
from classify import classify
import agent

def deployment(owner='agent'):
 return {'metadata':{'resourceVersion':'7','generation':2,'managedFields':[{'manager':'agent','fieldsType':'FieldsV1','fieldsV1':{'f:spec':{'f:template':{'f:spec':{'f:containers':{'k:{"name":"app"}':{'f:image':{}}}}},**({'f:replicas':{}} if owner=='agent' else {})}}}]+([] if owner=='agent' else [{'manager':owner,'fieldsType':'FieldsV1','fieldsV1':{'f:spec':{'f:replicas':{}}}}])},'spec':{'replicas':4 if owner=='operator' else 3,'template':{'spec':{'containers':[{'name':'app','image':'bad'}]}}}}
class Fake(ExtensionRun):
 def __init__(self,arm='ordinary',cond='clean'):
  self.r={'policy':arm,'condition':cond,'fixture_valid':True,'mutation_outcome':'no_dispatch','errors':[]};self.reads=0;self.recover_calls=0;self.seq=0;self.events=[];self.ns='test';self.dp='/deployment';self.cp='/config';self.stage='agent';self.d=deployment();self.cm={'data':{'mode':'v1'}};self.requests=[]
 def event(self,kind,**data):self.seq+=1;e=dict(seq=self.seq,kind=kind,**data);self.events.append(e);return e
 def get(self,path,visibility='observer_only'):self.event('get',path=path,visibility=visibility);return copy.deepcopy(self.d if path==self.dp else self.cm)
 def inject(self):
  if self.r['condition']=='same_field':self.d=deployment('operator')
  if self.r['condition'].startswith('dep_race'):self.cm['data']['mode']='v2'
  self.r['injection_verified']=True;self.event('injected');self.r['injection_ack_seq']=self.seq
 def request(self,method,path,body,ctype,manager,force,visibility):
  self.requests.append(dict(method=method,body=body,ctype=ctype,manager=manager,force=force));self.event('mutation');return copy.deepcopy(self.d)
 def error(self,k,e):self.r['errors'].append({'kind':k})
 def call(self,n,a):self.event('agent_tool_call',name=n,arguments=a);return self.tool(n,a)
class Tests(unittest.TestCase):
 def test_first_read_barrier(self):
  r=Fake(cond='same_field');v=r.call('read_deployment',{});self.assertEqual(v['object']['spec']['replicas'],3);self.assertEqual(r.d['spec']['replicas'],4)
  kinds=[e['kind'] for e in r.events];self.assertLess(kinds.index('agent_read_return'),kinds.index('injected'));self.assertLess(kinds.index('injected'),kinds.index('agent_tool_result'))
  r.call('read_deployment',{});self.assertEqual(sum(e['kind']=='injected' for e in r.events),1)
 def test_late_order_and_once(self):
  r=Fake(cond='dep_race_late');r.call('read_deployment',{});self.assertEqual(r.cm['data']['mode'],'v1')
  r.call('recover',{'restore_image':True,'restore_replicas':True});k=[e['kind'] for e in r.events];self.assertLess(k.index('injected'),k.index('mutation'));self.assertEqual(r.r['predispatch_configmap']['data']['mode'],'v2')
  r.call('recover',{'restore_image':True,'restore_replicas':True});self.assertEqual(len(r.requests),1);self.assertEqual(sum(e['kind']=='injected' for e in r.events),1)
 def test_no_late_call_no_injection(self):
  r=Fake(cond='dep_race_late');r.call('read_deployment',{});self.assertFalse(any(e['kind']=='injected' for e in r.events));self.assertEqual(r.r['mutation_outcome'],'no_dispatch')
 def test_ordinary_no_guard(self):
  r=Fake(cond='same_field');r.call('read_deployment',{});r.call('recover',{'restore_image':True,'restore_replicas':True});req=r.requests[0];self.assertEqual(req['body']['spec']['replicas'],2);self.assertEqual(req['ctype'],'application/strategic-merge-patch+json');self.assertIsNone(req['force']);self.assertNotIn('metadata',req['body'])
 def test_owned_filters_operator_field(self):
  r=Fake('ownership_aware','same_field');r.call('read_deployment',{});v=r.call('recover',{'restore_image':True,'restore_replicas':True});req=r.requests[0];self.assertNotIn('replicas',req['body']['spec']);self.assertFalse(req['force']);self.assertEqual(req['manager'],'agent');self.assertEqual(v['omitted_fields'],['replicas'])
 def test_owned_unknown_blocks(self):
  r=Fake('ownership_aware');r.call('read_deployment',{});del r.d['metadata']['managedFields'];v=r.call('recover',{'restore_image':True,'restore_replicas':True});self.assertEqual(v['error'],'ownership_unknown');self.assertFalse(r.requests)
 def test_empty_eligibility_no_write(self):
  r=Fake('ownership_aware','same_field');r.call('read_deployment',{});r.call('recover',{'restore_image':False,'restore_replicas':True});self.assertFalse(r.requests)
 def test_read_required(self):
  r=Fake();r.call('recover',{'restore_image':True,'restore_replicas':True});self.assertFalse(r.requests)
 def test_descriptive_behavior(self):
  r=Fake(cond='dep_race');r.call('read_deployment',{});r.call('read_deployment',{});r.call('read_configmap',{});r.call('recover',{'restore_image':True,'restore_replicas':False});b=behavior(r.events);self.assertTrue(b['reread_deployment_before_recover']);self.assertTrue(b['read_configmap_before_recover']);self.assertEqual(b['mode_values_before_recover'],['v2']);self.assertEqual(b['requested_fields'],'image')
 def test_observed_v2_finish_no_recover(self):
  r=Fake(cond='dep_race');r.call('read_deployment',{});r.call('read_configmap',{});r.event('agent_finish');b=behavior(r.events);self.assertTrue(b['blocked_on_observed_v2']);self.assertIsNone(b['read_configmap_before_recover'])
 def test_failure_not_blocked_on_v2(self):
  r=Fake(cond='dep_race');r.call('read_deployment',{});r.call('read_configmap',{});self.assertFalse(behavior(r.events)['blocked_on_observed_v2'])
 def test_schema_validation(self):
  self.assertFalse(validate('recover',{'restore_image':1,'restore_replicas':True}));self.assertTrue(validate('read_deployment',{}));self.assertFalse(validate('finish',{}));self.assertFalse(validate('read_deployment',{'x':1}))
 def test_schedule(self):
  self.assertEqual(len(schedule('smoke',1)),10);self.assertEqual(len(schedule('main',5)),50);self.assertEqual(len({(x['policy'],x['condition']) for x in schedule('smoke',1)}),10)
 def test_deadline(self):
  gate(datetime.datetime(2026,11,7,4,59,tzinfo=datetime.timezone.utc))
  with self.assertRaises(RuntimeError):gate(datetime.datetime(2026,11,7,5,tzinfo=datetime.timezone.utc))
 def test_ledger_cap_durable(self):
  with tempfile.TemporaryDirectory() as d:
   l=Ledger(Path(d)/'budget.db');n=0
   while True:
    try:l.reserve(str(n));n+=1
    except BudgetStop:break
   self.assertLessEqual(l.snapshot()['total_bound_usd'],25);self.assertEqual(Ledger(l.path).snapshot()['requests'],n)
 def test_ledger_usage_and_pending(self):
  with tempfile.TemporaryDirectory() as d:
   l=Ledger(Path(d)/'budget.db');l.reserve('a');l.reserve('b');l.settle('a',{'input_tokens':1000,'output_tokens':100,'input_tokens_details':{'cached_tokens':500}});s=l.snapshot();self.assertAlmostEqual(s['actual_usd'],0.00041);self.assertGreater(s['pending_reserved_usd'],0)
 def test_original_classifier_differential(self):
  paths=list((OLD/'results/raw').glob('*.json'));self.assertEqual(len(paths),200)
  for p in paths:
   r=json.loads(p.read_text());self.assertEqual(classify(r),r['metrics'],p.name)
 def test_no_report_and_budget_are_distinct(self):
  r=Fake();r.ns='test';r.task=lambda:{}
  with tempfile.TemporaryDirectory() as d,patch('agent.input_reservation',return_value=300):
   raw={'model':MODEL,'status':'completed','output':[],'usage':{'input_tokens':100,'output_tokens':2}}
   agent.execute_agent(r,Ledger(Path(d)/'a'),lambda *a,**kw:{'http_status':200,'body':raw});self.assertEqual(r.r['agent_outcome'],'no_report')
  r=Fake();r.ns='test';r.task=lambda:{}
  with tempfile.TemporaryDirectory() as d,patch('agent.input_reservation',return_value=20001):
   agent.execute_agent(r,Ledger(Path(d)/'b'),lambda *a,**kw:self.fail('no request allowed'));self.assertEqual(r.r['agent_outcome'],'budget_exhausted')
 def test_malformed_finish(self):
  r=Fake();r.ns='test';r.task=lambda:{}
  with tempfile.TemporaryDirectory() as d,patch('agent.input_reservation',return_value=300):
   raw={'model':MODEL,'status':'completed','output':[{'type':'function_call','name':'finish','arguments':'{}','call_id':'x'}],'usage':{'input_tokens':100,'output_tokens':2}}
   agent.execute_agent(r,Ledger(Path(d)/'a'),lambda *a,**kw:{'http_status':200,'body':raw});self.assertEqual(r.r['agent_outcome'],'malformed_report')
 def test_claim_projection_no_autoreport(self):
  r=Fake();r.ns='test';r.task=lambda:{}
  with tempfile.TemporaryDirectory() as d,patch('agent.input_reservation',return_value=300):
   args={'status':'PARTIAL','claims':{'image':None,'replicas':None},'evidence_ids':[],'reason':'unknown'}
   raw={'model':MODEL,'status':'completed','output':[{'type':'function_call','name':'finish','arguments':json.dumps(args),'call_id':'x'}],'usage':{'input_tokens':100,'output_tokens':2}}
   agent.execute_agent(r,Ledger(Path(d)/'a'),lambda *a,**kw:{'http_status':200,'body':raw});self.assertEqual(r.r['report'],{'status':'PARTIAL','claims':{}})
if __name__=='__main__':unittest.main()
