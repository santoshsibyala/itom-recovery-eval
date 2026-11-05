"""Replay all public tool results; independently recompute every HTTP workload judgment."""
import json,tempfile,hashlib
from pathlib import Path
from runtime import Runtime
from scoring import grade

def verify(t):
 assert grade(t)==t['grade'],'Grade mismatch'
 if 'service' in t:
  service=t['service'];rows=service['requests'];windows=[]
  assert len({p['pid'] for p in service['processes']})==len(service['processes'])
  assert all(o['completed'] and o['pid'] not in {p['pid'] for p in service['processes']} for o in service['operators'])
  for i,r in enumerate(rows,1):
   assert r['payload']==dict(id=f'request-{i}',value=1000+i*7)
   expected=hashlib.sha256(str(r['payload']['value']).encode()).hexdigest();resp=r['response']
   correct=r['http_status']==200 and ((resp.get('checksum')==expected) if t['spec']['name']=='codec_pipeline' else (resp.get('receipts')==[expected,expected] and resp.get('acknowledged') is True))
   assert r['correct']==correct and r['elapsed_ms']>=0,'Workload judgment mismatch'
  public=[r for r in rows if r['label']=='public'];health=[(o,step) for o,step in zip(t['public'],t['steps']) if o['tool']=='read_health' and o['reply']['ok']]
  assert len(public)==20*len(health)
  for n,(o,step) in enumerate(health):
   segment=public[n*20:(n+1)*20];correct=sum(x['correct'] for x in segment)
   assert o['reply']['result']==dict(measured=True,epoch=step['after_epoch'],stable_epoch=step['before_epoch']==step['after_epoch'],requests=20,correct=correct,pass_window=correct>=19)
  for i,w in enumerate(service['windows']):
   segment=[r for r in rows if r['label']=='terminal-'+str(i)];assert len(segment)==50
   assert w==dict(measured=True,epoch=len(t['events']),stable_epoch=True,requests=50,correct=sum(x['correct'] for x in segment),pass_window=sum(x['correct'] for x in segment)>=49)
  assert len(service['windows'])==3 and service['health']==all(w['pass_window'] for w in service['windows'])
  assert len(rows)==20*len(health)+150
 with tempfile.TemporaryDirectory() as d:
  rt=Runtime(t['spec'],Path(d)/'replay.sqlite3',t['guard']);assert rt.task==t['task']
  assert len(t['steps'])==len(t['public'])
  for o,step in zip(t['public'],t['steps']):
   with rt.db() as db:epoch=rt.epoch(db)
   if epoch<step['before_epoch']:rt.external()
   with rt.db() as db:assert rt.epoch(db)==step['before_epoch']
   if o['tool']=='read_health':rt.health=lambda:o['reply']['result']
   got=rt.invoke(o['tool'],**o['arguments']);assert got==o,'Public replay mismatch'
   with rt.db() as db:assert rt.epoch(db)==step['after_epoch']
  with rt.db() as db:epoch=rt.epoch(db)
  if epoch<len(t['events']):rt.external()
  rebuilt=rt.finish(t['report']);assert rebuilt['events']==t['events'] and rebuilt['final']==t['final'],'State replay mismatch'
 return True
