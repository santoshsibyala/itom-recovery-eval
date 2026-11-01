"""Bounded integration of an unmodified pinned RAC rollback core. No model calls."""
import argparse,hashlib,itertools,json,logging,sys
from copy import deepcopy
from datetime import datetime,timezone
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parent
UPSTREAM=HERE/'rac_external/research-rac-068c327ab3f9b79a86a39503946e26320b74b97a'
sys.path[:0]=[str(ROOT),str(UPSTREAM/'src')]
from react_agent_compensation.core.recovery_manager import RecoveryManager
from react_agent_compensation.core.extraction.passthrough import PassthroughStrategy
from runtime import Runtime,predicates
from scenarios import scenario,NAMES,VARIANTS
from services import Live
from scoring import grade
from verify import verify
logging.disable(logging.CRITICAL)

def rollback(rt,invoke):
 effects={e['id']:e for e in rt.spec['effects']};ops=[]
 class Executor:
  def execute(self,action,params):
   e=effects[params['target_effect_id']];r=e['resource']
   view=invoke('read_resource',resource_id='*')['reply']['result']['resources'];hist=invoke('read_changes',resource_id='*')['reply']['result']['resources']
   if not hist[r]['complete'] or any(view[r]['owners'][k]!=e['id'] for k in e['before']):raise RuntimeError('Handler: incomplete history or changed ownership')
   candidate={r:deepcopy(v['values']) for r,v in view.items()};candidate[r].update(e['before'])
   if not predicates(rt.spec,candidate):raise RuntimeError('Handler: candidate predicate false')
   oid='recovery-'+e['id'];o=invoke('apply_patch',resource_id=r,patch=e['before'],expected_version=view[r]['version'],operation_id=oid,target_effect_id=e['id'])
   if not o['reply']['ok'] or not o['reply']['result']['committed']:raise RuntimeError('Handler: write refused')
   ops.append(oid);return o['reply']['result']
 manager=RecoveryManager(compensation_pairs={e['id']:'undo-'+e['id'] for e in effects.values()},extraction_strategy=PassthroughStrategy(),action_executor=Executor(),infer_dependencies=False,enable_tool_alternatives=False)
 # Register the actual committed remediation order, using explicit target IDs as adapter metadata.
 for e in rt.spec['effects']:
  record=manager.record_action(e['id'],dict(target_effect_id=e['id']))
  manager.mark_completed(record.id,result=dict(target_effect_id=e['id']))
 try:outcome=manager.rollback().model_dump();success=outcome['success']
 except Exception as ex:outcome=dict(success=False,error_type=type(ex).__name__,message=str(ex));success=False
 view=invoke('read_resource',resource_id='*');hist=invoke('read_changes',resource_id='*');health=invoke('read_health');cites=[o['evidence_id'] for o in (view,hist,health)]
 if ops:invoke('record_recovery_audit',effect_ids=ops,evidence_ids=cites)
 values=view['reply']['result']['resources'];done=[k for k,e in effects.items() if all(values[e['resource']]['values'][f]==v for f,v in e['before'].items())];left=[k for k in effects if k not in done]
 # This report is OUR adapter, not a native RAC evidence certificate.
 report=dict(status=('OPERATIONAL' if health['reply']['result']['measured'] and health['reply']['result']['pass_window'] else 'RECOVERED') if success else 'PARTIAL' if done and left else 'UNRESOLVED',resolved_effect_ids=done,remaining_effect_ids=left,evidence_ids=cites)
 return report,outcome

def freeze():
 manifest=dict(frozen_utc=datetime.now(timezone.utc).isoformat(),tree='068c327ab3f9b79a86a39503946e26320b74b97a',upstream_unchanged=True,
  source_hashes={str(p.relative_to(UPSTREAM)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (UPSTREAM/'src').rglob('*.py')},
  adapter_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
  offline='4 configurations x 8 conditions x 3 repetitions x 2 runtime contracts = 192',service='2 topologies x 8 conditions x 1 process reset x 2 runtime contracts = 32',
  scope='Unmodified RAC RecoveryManager.rollback, TransactionLog planning and PassthroughStrategy. Explicit compensation pairs; infer_dependencies=False; no LLM alternatives or retries. ITOM adapter checks public ownership/predicates, then writes with object CAS. Compare same adapter under none vs atomic v05 runtime. Not LangChain integration, tau-bench, REALM-Bench, or a full RAC paper reproduction.',
  phase='Separately frozen diagnostic integration after main model study began; not primary/confirmatory evidence. No model data selected for inclusion.',
  reporting='Adapter provides v05 final observations and audit/report envelope; these features are not attributed to upstream RAC. Upstream rollback outcome is retained separately. No general RAC safety or superiority claim.',
  license='Upstream LICENSE is Apache-2.0 and is retained alongside unmodified source. Adapter authored separately; no upstream source changes.')
 with (HERE/'rac_protocol.json').open('x') as f:json.dump(manifest,f,indent=2)

def execute(live):
 m=json.loads((HERE/'rac_protocol.json').read_text());assert hashlib.sha256(Path(__file__).read_bytes()).hexdigest()==m['adapter_sha256']
 assert all(hashlib.sha256((UPSTREAM/p).read_bytes()).hexdigest()==h for p,h in m['source_hashes'].items())
 out=HERE/('rac_service' if live else 'rac_offline');out.mkdir(exist_ok=True);summary=[]
 for name,var,rep,arm in itertools.product(NAMES[:2] if live else NAMES,VARIANTS,(1,) if live else (1,2,3),('none','atomic')):
  cid=f'{name}-{var}-{rep}-{arm}';path=out/(cid+'.json')
  if path.exists():continue
  rt=Runtime(scenario(name,var,rep),out/(cid+'.sqlite3'),arm)
  if live:
   with Live(rt,out/cid) as svc:report,result=rollback(rt,svc.invoke);t=svc.finish(report)
  else:
   rt.health=lambda:dict(measured=False,epoch=len(rt.finish({})['events']),stable_epoch=True,pass_window=True);count=[0]
   def invoke(tool,**a):
    if tool=='apply_patch':
     count[0]+=1
     if var=='dependency_race' and count[0]==2:rt.external()
    return rt.invoke(tool,**a)
   report,result=rollback(rt,invoke)
   if rt.spec['timing']=='finish':rt.external()
   t=rt.finish(report)
  t.update(policy='RAC-adapter-'+arm,upstream_rollback=result,grade=grade(t));verify(t)
  with path.open('x') as f:json.dump(t,f,indent=2)
  summary.append(dict(id=cid,grade=t['grade'],upstream_success=result['success']))
 (out/'receipt.txt').write_text(f'{len(list(out.glob("*.json")))} completed, no model calls\n')
 print(out.name,len(list(out.glob('*.json'))),'complete')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('command',choices=['freeze','offline','service']);a=p.parse_args();freeze() if a.command=='freeze' else execute(a.command=='service')
