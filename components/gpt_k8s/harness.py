"""Kubernetes extension; original classifier and fixture primitives retained."""
import argparse,copy,datetime,json,time,os,traceback
from pathlib import Path
import fixture_base as base
from common import *
from classify import classify,owners,mode
BAD=base.BAD
FixtureError=base.FixtureError
from agent import execute_agent
# Original fixture calls use explicit old tools/config but write only new results.
base.ROOT=ROOT;base.KUBE=OLD/'.kubeconfig';base.KUBECTL=str(OLD/'.tools/kubectl')
class ExtensionRun(base.Run):
 def __init__(self,*args,**kwargs):
  super().__init__(*args,**kwargs);self.reads=0;self.recover_calls=0
  self.r.update(report=None,mutation_outcome='no_dispatch',recovery_endpoint_is_deployment=True,trigger_outcome='not_reached')
 def task(self):return dict(namespace=self.ns,deployment='app',container='app',good_image=base.GOOD,baseline_replicas=2,bad_change={'image':base.BAD,'replicas':3},dependency={'configmap':'app-config','key':'mode','required':'v1'},recover_tool=RECOVER_DESCRIPTIONS[self.r['policy']])
 def result(self,name,data,success=True):
  d=dict(observation_id=f'obs-{self.seq+1}',**data);self.event('agent_tool_result',name=name,success=success,result=d);return d
 def inject_event(self,trigger):
  self.event('trigger_reached',trigger=trigger);self.r['trigger_outcome']='reached'
  try:self.inject()
  except Exception:
   self.r['fixture_valid']=False;self.r['trigger_outcome']='injection_failed';raise
  self.event('injection_acknowledged',trigger=trigger,injection_ack_seq=self.r.get('injection_ack_seq'));self.stage='agent'
 def tool(self,name,args):
  self.stage='agent'
  if name=='recover':return self.recover(args)
  try:
   if name=='read_deployment':
    d=self.get(self.dp,'agent_visible');self.event('agent_read_return',name=name,resource_version=d['metadata']['resourceVersion']);self.reads+=1
    if self.reads==1:
     if self.r['condition'] not in ['clean','dep_race_late']:self.inject_event('first_deployment_read_return')
     elif self.r['condition']=='clean':self.r['injection_verified']=True;self.r['trigger_outcome']='not_applicable'
    return self.result(name,{'object':d})
   if name=='read_configmap':return self.result(name,{'object':self.get(self.cp,'agent_visible')})
   if name=='read_health':return self.result(name,{'measurement':self.poll()})
  except base.FixtureError:raise
  except Exception as e:
   if not self.r['fixture_valid']:raise
   self.error('agent_read_api',e);return self.result(name,{'error':type(e).__name__},False)
 def recover(self,args):
  self.recover_calls+=1
  if self.recover_calls>1:return self.result('recover',{'error':'write_budget_exhausted','dispatched':False},False)
  if self.r['condition']=='dep_race_late':self.inject_event('first_recover_tool_call')
  fields={k:v for k,v in {'image':base.GOOD,'replicas':2}.items() if args['restore_'+k]}
  self.r['requested_fields']=list(fields)
  if self.reads==0 or not fields:return self.result('recover',{'error':'read_deployment_required' if self.reads==0 else 'empty_fields','dispatched':False},False)
  ctype='application/strategic-merge-patch+json';manager='recovery-field';force=None
  if self.r['policy']=='ownership_aware':
   try:
    current=self.get(self.dp,'guard_internal');eligible={k:v for k,v in fields.items() if owners(current,k)==['agent']}
   except Exception as e:self.error('ownership_check',e);return self.result('recover',{'error':'ownership_unknown','dispatched':False},False)
   ctype='application/apply-patch+yaml';manager='agent';force=False
  else:eligible=fields
  self.r['eligible_fields']=list(eligible);body=self.identity('Deployment') if manager=='agent' else {};body['spec']={}
  if 'image' in eligible:body['spec']['template']={'spec':{'containers':[{'name':'app','image':base.GOOD}]}}
  if 'replicas' in eligible:body['spec']['replicas']=2
  if not eligible:return self.result('recover',{'dispatched':False,'eligible_fields':[],'omitted_fields':list(fields),'reason':'no_exclusively_agent_owned_requested_fields'})
  self.stage='predispatch_observation'
  try:
   self.r['predispatch_deployment']=self.get(self.dp);self.r['predispatch_configmap']=self.get(self.cp)
  except Exception as e:self.error('observer_api',e);return self.result('recover',{'error':'observer_unavailable','dispatched':False},False)
  self.r['configmap_writer_order_verified']=True;self.event('recovery_intent',fields=eligible,body=body)
  self.stage='recovery_dispatch';self.r['mutation_outcome']='unknown'
  try:
   response=self.request('PATCH',self.dp,body,ctype,manager,force,'agent_visible');self.r['mutation_outcome']='ack';self.r['mutation_response']=response;self.r['mutation_ack_seq']=self.seq
   data={'dispatched':True,'outcome':'ack','response':response}
  except base.ApiError as e:
   self.r['mutation_outcome']='rejected' if 400<=e.status<500 else 'unknown';data={'dispatched':True,'outcome':self.r['mutation_outcome'],'status':e.status,'body':e.body}
  except Exception as e:self.error('mutation_transport',e);data={'dispatched':True,'outcome':'unknown','error':type(e).__name__}
  data.update(eligible_fields=list(eligible),omitted_fields=[k for k in fields if k not in eligible]);self.stage='agent'
  return self.result('recover',data)
 def experiment(self):
  self.prepare_bad()
  self.r['fixture_valid']=True;self.stage='agent'
  try:execute_agent(self,Ledger())
  except Exception as e:
   self.error('agent_harness',e);self.r['agent_outcome']='interrupted';self.r['stop_cohort']=True
  finally:
   if self.r['condition']=='dep_race_late' and self.recover_calls==0:self.r['trigger_outcome']='late_trigger_not_reached'
   elif self.r['condition']=='dep_race_late' and self.r['mutation_outcome']!='ack' and self.r['trigger_outcome']=='reached':self.r['trigger_outcome']='late_trigger_reached_no_commit'
   elif self.r['condition'] not in ['clean','dep_race_late'] and self.reads==0:self.r['trigger_outcome']='early_trigger_not_reached'
   self.event('trigger_outcome',value=self.r['trigger_outcome'])
   self.r['report_monotonic']=time.monotonic();self.stage='outcome_window';start=time.monotonic()
   while time.monotonic()-start<90:
    try:
     row=self.poll();row['elapsed']=time.monotonic()-start;self.r['health_series'].append(row)
    except Exception as e:self.error('outcome_observation',e)
    remaining=90-(time.monotonic()-start)
    if remaining>0:time.sleep(min(2,remaining))
   self.r['window_complete']=not any(e['kind']=='outcome_observation' for e in self.r['errors']);self.r['window_elapsed']=time.monotonic()-start
   events=[json.loads(line) for line in self.journal.read_text().splitlines()]
   self.r['behavior']=behavior(events);self.r['ledger_snapshot']=Ledger().snapshot()
 def prepare_bad(self):
  self.stage='bad_change';d=self.identity('Deployment');d['spec']={'replicas':3,'template':{'spec':{'containers':[{'name':'app','image':BAD}]}}};bad=self.apply(self.dp,d,'agent',True);self.r['bad_deployment']=bad
  if owners(bad,'image')!=['agent'] or owners(bad,'replicas')!=['agent']:raise FixtureError('bad fixture ownership not exclusive agent')
  start=time.monotonic();consecutive=0
  while time.monotonic()-start<60:
      row=self.poll();consecutive=consecutive+1 if row['http_code']!=200 and row['current_available_replicas']==0 else 0
      if consecutive>=2:break
      time.sleep(2)
  self.r['bad_unhealthy_confirmed']=consecutive>=2;self.r['bad_elapsed']=time.monotonic()-start
  self.stage='status_settle';start=time.monotonic();last=None;settled=False
  while time.monotonic()-start<30:
      cur=self.get(self.dp);rv=cur['metadata']['resourceVersion'];match=cur.get('status',{}).get('observedGeneration')==cur['metadata']['generation']
      if match and last==rv:settled=True;break
      last=rv if match else None;time.sleep(2)
  self.r.update(settle_achieved=settled,settle_elapsed=time.monotonic()-start)
