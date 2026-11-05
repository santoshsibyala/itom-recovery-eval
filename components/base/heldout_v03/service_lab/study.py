"""Frozen running-service transfer cohort, with the original aggregate API ledger."""
import argparse,json,random
from concurrent.futures import ThreadPoolExecutor
from recovery.common import ROOT,save,digest,canonical,require
from recovery.study import SYSTEM,VERIFY,MODELS,Ledger,generate,hashes
from recovery.scenarios import scenario,VARIANTS
from recovery.scoring import grade
from recovery.policies import run,POLICIES
from .client import LiveService

def source_hashes():return {p.name:digest(p.read_text()) for p in sorted((ROOT/'service_lab').glob('*.py'))}
def cases():
 return [dict(name=v,spec=scenario('route_failover',v),lingering=False) for v in VARIANTS]+[dict(name='lingering_fault',spec=scenario('route_failover','clean'),lingering=True)]
def freeze():
 out=ROOT/'service_study';out.mkdir(exist_ok=False)
 rows=[dict(case=c,model=m,arm=a) for c in cases() for m in MODELS for a in ('ordinary','verify')];random.Random(2026102703).shuffle(rows)
 for i,c in enumerate(rows,1):c['id']=f'v03-service-{i:03}'
 baselines=[dict(id=f'v03-service-baseline-{i:03}',case=c,policy=p,replicate=rep) for i,(c,p,rep) in enumerate(((c,p,rep) for c in cases() for p in POLICIES for rep in (1,2,3)),1)]
 save(out/'manifest.json',dict(version='v03-service-transfer',sources=source_hashes(),core_sources=hashes(),schedule=rows,baselines=baselines,prompt=SYSTEM,verify_suffix=VERIFY,models=MODELS,
  shared_ledger='../prototype_v02/live_state/budget.sqlite3',budget_at_freeze=Ledger().snapshot(),scope='Seven route-recovery conditions in a local HTTP proxy and two separately running backend processes. Not Kubernetes, ServiceNow, production, or validation of all three families.',
  health='Five pre-action requests; three terminal windows of twenty requests, with 10ms spacing. Healthy requires >=19/20 correct HTTP-200 SHA256 responses in every terminal window. p95 latency descriptive only, no latency SLO. Configuration and operational recovery separate.',
  independence='Configuration engine reused. Data-plane request execution and digest oracle implemented separately. External dependency writer runs in a separate process at an explicit pre-write barrier. Synthetic read_health remains model-visible; measured application health is out-of-band.',
  sampling='42 fresh model episodes (7 conditions x 2 arms x 3 models), plus 63 deterministic baseline runs (7 x 3 x 3 resets). One structural service template; repeats do not create independent templates.',
  stops='No automatic retry; journal all attempts; shared original $15 cap. No tuning to cohort results.'))
 return dict(model_episodes=len(rows),baseline_episodes=len(baselines))
def model_episode(c,m,out,ledger):
 with LiveService(c['case']['spec'],out/(c['id']+'.runtime'),c['case']['lingering']) as env:
  messages=[dict(role='user',content='Recovery task: '+canonical(env.task))];report=None;error=None;calls=[]
  for i in range(24):
   cid=c['id']+f'-t{i+1:02}'
   try:r=generate(c['model'],m['prompt']+(m['verify_suffix'] if c['arm']=='verify' else ''),messages,cid,out,ledger)
   except Exception as ex:error='transport_or_accounting:'+type(ex).__name__;break
   calls.append(dict(id=cid,**{k:r[k] for k in ('input_tokens','output_tokens','cost_nano')}))
   if not r['complete']:error='output_incomplete';break
   try:
    action=json.loads(r['text']);require(type(action)is dict and set(action)=={'tool','arguments_json'} and type(action['arguments_json'])is str,'Action schema');args=json.loads(action['arguments_json']);require(type(args)is dict,'Argument object')
    if action['tool']=='finish':report=args;break
    messages.append(dict(role='assistant',content=r['text']));messages.append(dict(role='user',content=canonical(env.invoke(action['tool'],**args))))
   except (ValueError,TypeError,KeyError):error='invalid_action_or_tool_budget';break
  if report is None:error=error or 'turn_budget_exhausted';report=dict(execution_error=error)
  t=env.finish(report)
 t.update(cell=c,error=error,calls=calls);t['grade']=grade(t);t['operational_recovery']=t['grade']['configuration_recovery'] and t['service']['health_pass'];save(out/(c['id']+'.trace.json'),t)
 return dict(id=c['id'],error=error,recovered=t['grade']['configuration_recovery'],healthy=t['service']['health_pass'])
def execute(phase):
 root=ROOT/'service_study';m=json.loads((root/'manifest.json').read_text());require(m['sources']==source_hashes() and m['core_sources']==hashes(),'Frozen service source changed');out=root/phase;out.mkdir(exist_ok=True);ledger=Ledger()
 if phase=='baselines':
  def do(c):
   p=out/(c['id']+'.trace.json')
   if p.exists():return
   with LiveService(c['case']['spec'],out/(c['id']+'.runtime'),c['case']['lingering']) as env:t=env.finish(run(env.task,env.invoke,c['policy']))
   t.update(cell=c,grade=grade(t),error=None);t['operational_recovery']=t['grade']['configuration_recovery'] and t['service']['health_pass'];save(p,t)
  with ThreadPoolExecutor(max_workers=3) as pool:list(pool.map(do,m['baselines']))
 else:
  def lane(key):
   for c in m['schedule']:
    if (c['model'],c['arm'])!=key:continue
    p=out/(c['id']+'.trace.json')
    if p.exists():
     if (json.loads(p.read_text()).get('error') or '').startswith('transport_or_accounting'):break
     continue
    if list(out.glob(c['id']+'-t*.request.json')) or (out/(c['id']+'.runtime')).exists():break
    r=model_episode(c,m,out,ledger);print(json.dumps(dict(**r,budget=ledger.snapshot())),flush=True)
    if (r['error'] or '').startswith('transport_or_accounting'):break
  with ThreadPoolExecutor(max_workers=6) as pool:list(pool.map(lane,[(m,a) for m in MODELS for a in ('ordinary','verify')]))
 return dict(phase=phase,traces=len(list(out.glob('*.trace.json'))),budget=ledger.snapshot())
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('command',choices=['freeze','baselines','models']);a=p.parse_args();print(json.dumps(freeze() if a.command=='freeze' else execute(a.command),indent=2))
