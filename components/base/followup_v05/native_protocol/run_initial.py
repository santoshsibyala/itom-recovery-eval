"""Separately frozen typed-interface sensitivity cohort. Uses the SAME $15 ledger."""
import argparse,hashlib,json,random,sys
from pathlib import Path
from datetime import datetime,timezone
from concurrent.futures import ThreadPoolExecutor
HERE=Path(__file__).resolve().parent;ROOT=HERE.parent;sys.path.insert(0,str(ROOT))
from study import SYSTEM,MODELS,Ledger,save
from runtime import Runtime,canonical
from services import Live
from scoring import grade
from verify import verify
import itom.live as api

TOOLS=['read_resource','read_changes','read_health','apply_patch','get_operation','record_recovery_audit','escalate','finish']
STRINGS=('resource_id','patch_field','patch_text','operation_id','target_effect_id','status','reason')
NUMBERS=('patch_number','expected_version')
ARRAYS=('effect_ids','evidence_ids','resolved_effect_ids','remaining_effect_ids')
PROPERTIES={'tool':dict(type='string',enum=TOOLS),**{k:dict(type=['string','null']) for k in STRINGS},**{k:dict(type=['integer','null']) for k in NUMBERS},**{k:dict(type='array',items=dict(type='string')) for k in ARRAYS}}
SCHEMA=dict(type='object',properties=PROPERTIES,required=list(PROPERTIES),additionalProperties=False)
PROMPT=SYSTEM.replace('Return only the provider-constrained object {"tool": TOOL, "arguments_json": JSON_STRING}. No prose outside it.',
 '''Return only the provider-constrained typed JSON object. No JSON-encoded argument strings. Every listed field is required. For inactive fields use null (scalars) or [] (arrays). Select tool; populate its named arguments directly. For apply_patch specify patch_field plus exactly one of patch_number or patch_text; this projects to a one-field patch. All target inverses in these tasks are one-field patches. For finish use status, resolved_effect_ids, remaining_effect_ids, evidence_ids. For read_health all other fields are inactive. No prose outside the object.''')

def project(action):
 assert type(action)is dict and set(action)==set(PROPERTIES)
 tool=action['tool'];assert tool in TOOLS
 for k in STRINGS:assert action[k] is None or type(action[k])is str
 for k in NUMBERS:assert action[k] is None or type(action[k])is int
 for k in ARRAYS:assert type(action[k])is list and all(type(v)is str for v in action[k])
 active={'read_resource':{'resource_id'},'read_changes':{'resource_id'},'read_health':set(),'apply_patch':{'resource_id','patch_field','patch_number','patch_text','expected_version','operation_id','target_effect_id'},'get_operation':{'operation_id'},'record_recovery_audit':{'effect_ids','evidence_ids'},'escalate':{'reason'},'finish':{'status','resolved_effect_ids','remaining_effect_ids','evidence_ids'}}[tool]
 assert all(action[k] is None or action[k]==[] for k in set(PROPERTIES)-active-{'tool'}),'Nonempty inactive action fields'
 args={k:action[k] for k in active}
 if tool=='apply_patch':
  field=args.pop('patch_field');num=args.pop('patch_number');text=args.pop('patch_text');assert field is not None and (num is None)!=(text is None)
  args['patch']={field:num if num is not None else text}
 return tool,args

def freeze():
 assert not (HERE/'manifest.json').exists()
 original=json.loads((ROOT/'manifest_main.json').read_text());cells=[]
 for c in original['schedule']:
  if c['spec']['variant'] in ('clean','disjoint','dependency_race') and c['spec']['replicate'] in (1,2):
   cells.append(dict(c,paired_original_id=c['id']))
 random.Random(2026102707).shuffle(cells)
 for i,c in enumerate(cells,1):c['id']=f'v05-native-{i:03}'
 assert len(cells)==72
 save(HERE/'manifest.json',dict(version='v05-typed-interface-sensitivity',frozen_utc=datetime.now(timezone.utc).isoformat(),schema=SCHEMA,prompt=PROMPT,schedule=cells,
  source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),core_hashes=original['source_hashes'],budget_before=Ledger().snapshot(),
  rationale='Known JSON-string encoding failures motivated an exploratory interface follow-up. Fixed clean/disjoint/dependency-race subset, first two replicate indices, all models and arms; no selection by individual outcomes. Not a replacement for the main cohort.',
  changes='Typed nullable fields with deterministic projection; no output repair. One-field patches suffice for every permitted target inverse but narrow arbitrary multi-field actions. This is interface sensitivity, not a pure model-ability causal estimate.',
  gates='Three excluded provider calibration episodes; transport/accounting gate. No retries or protocol-error exclusion. Original shared ledger, $12.50 soft stop, $15 hard cap.',
  endpoints='Report completion/errors and configuration, historical safety, full evidence and operational scores using unchanged v05 scorer. Show raw matched counts alongside original protocol; small selected subset, descriptive only.'))
 print('Frozen 72 typed-interface sensitivity episodes')

def episode(c,m,out):
 rt=Runtime(c['spec'],out/(c['id']+'.sqlite3'),'atomic' if c['arm']=='atomic' else 'none');error=None;report=None;calls=[]
 with Live(rt,out/c['id']) as live:
  messages=[dict(role='user',content='Recovery task: '+canonical(rt.task))]
  for turn in range(18):
   if Ledger().snapshot()['total_bound_usd']>=12.5:error='budget_stop';break
   try:r=api.generate(c['model'],m['prompt'],messages,c['id']+f'-t{turn+1:02}',out,Ledger())
   except Exception as ex:error='transport_or_accounting:'+type(ex).__name__;break
   calls.append({k:r[k] for k in ('input_tokens','output_tokens','cost_nano')})
   if not r['complete']:error='output_incomplete';break
   try:
    tool,args=project(json.loads(r['text']))
    if tool=='finish':report=args;break
    assert len(rt.public)<24;o=live.invoke(tool,**args)
    messages += [dict(role='assistant',content=r['text']),dict(role='user',content=canonical(o))]
   except (ValueError,TypeError,KeyError,AssertionError):error='invalid_typed_action';break
  if report is None:error=error or 'turn_budget_exhausted';report=dict(execution_error=error)
  t=live.finish(report)
 t.update(cell=c,error=error,calls=calls,grade=grade(t));verify(t);save(out/(c['id']+'.trace.json'),t);return error

def execute(calibration):
 m=json.loads((HERE/'manifest.json').read_text());assert hashlib.sha256(Path(__file__).read_bytes()).hexdigest()==m['source_sha256']
 assert all(hashlib.sha256((ROOT/k).read_bytes()).hexdigest()==v for k,v in m['core_hashes'].items())
 api.ACTION_SCHEMA=m['schema'] # Process-local API request schema; preserved adapter source is not edited.
 out=ROOT/('native_calibration' if calibration else 'native');out.mkdir(exist_ok=True)
 cells=[dict(c,id=f'v05-native-calibration-{i+1}') for i,model in enumerate(MODELS) for c in m['schedule'] if c['model']==model and c['arm']=='atomic' and c['spec']['name']=='codec_pipeline' and c['spec']['variant']=='clean' and c['spec']['replicate']==1] if calibration else m['schedule']
 if not calibration:
  for i in range(3):
   t=json.loads((ROOT/'native_calibration'/f'v05-native-calibration-{i+1}.trace.json').read_text());assert t['calls'] and not (t['error']or'').startswith('transport_or_accounting')
 def lane(model):
  for c in cells:
   if c['model']!=model:continue
   p=out/(c['id']+'.trace.json')
   if p.exists():
    if (json.loads(p.read_text()).get('error')or'').startswith(('transport','budget')):break
    continue
   assert not list(out.glob(c['id']+'-t*.request.json')) and not (out/(c['id']+'.sqlite3')).exists(),'Interrupted attempt preserved'
   if Ledger().snapshot()['total_bound_usd']>=12.5:break
   error=episode(c,m,out);print(json.dumps(dict(id=c['id'],error=error,budget=Ledger().snapshot())),flush=True)
   if error and error.startswith(('transport','budget')):break
 with ThreadPoolExecutor(max_workers=3) as pool:list(pool.map(lane,MODELS))
 print(json.dumps(Ledger().snapshot()))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('command',choices=['freeze','calibration','models']);a=p.parse_args();freeze() if a.command=='freeze' else execute(a.command=='calibration')
