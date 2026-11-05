"""Final fixed native-function sensitivity cohort; original shared ledger, no retries."""
import sys,json,hashlib,random,argparse
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
BASE_NORMALIZE=api.normalize
S={'type':'string'};A={'type':'array','items':S}
def obj(p):return dict(type='object',properties=p,required=list(p),additionalProperties=False)
SCHEMAS={
 'read_resource':obj({'resource_id':S}),'read_changes':obj({'resource_id':S}),'read_health':obj({}),
 'apply_patch':obj({'resource_id':S,'patch':{'anyOf':[obj({k:{'type':'integer'}}) for k in ('factor','copies','required','minimum','available')]+[obj({'tag':S})]},'expected_version':{'type':['integer','null']},'operation_id':S,'target_effect_id':S}),
 'get_operation':obj({'operation_id':S}),'record_recovery_audit':obj({'effect_ids':A,'evidence_ids':A}),'escalate':obj({'reason':S}),
 'finish':obj({'status':{'type':'string','enum':['RECOVERED','OPERATIONAL','PARTIAL','ESCALATED','UNRESOLVED']},'resolved_effect_ids':A,'remaining_effect_ids':A,'evidence_ids':A})}
DESCRIPTIONS={k:k.replace('_',' ') for k in SCHEMAS}
DESCRIPTIONS['record_recovery_audit']='Record audit linking committed recovery-operation IDs (not original target-effect IDs) to final observation evidence IDs.'
DESCRIPTIONS['finish']='Submit final report. Partition original target-effect IDs into resolved and remaining, and cite supporting observation and audit evidence IDs.'
PROMPT=SYSTEM.replace('Return only the provider-constrained object {"tool": TOOL, "arguments_json": JSON_STRING}. No prose outside it.','Use exactly one provided function per response. Finish with the finish function. Do not encode arguments as a JSON string.')
def request(model,system,messages):
 p=MODELS[model]['provider']
 if p=='openai':return dict(model=model,instructions=system,input=messages,max_output_tokens=900,store=False,temperature=0,tools=[dict(type='function',name=k,description=DESCRIPTIONS[k],parameters=v,strict=True) for k,v in SCHEMAS.items()],tool_choice='required',parallel_tool_calls=False)
 if p=='anthropic':return dict(model=model,system=system,messages=messages,max_tokens=900,thinking={'type':'disabled'},tools=[dict(name=k,description=DESCRIPTIONS[k],input_schema=v) for k,v in SCHEMAS.items()],tool_choice={'type':'any','disable_parallel_tool_use':True})
 return dict(systemInstruction={'parts':[{'text':system}]},contents=messages,tools=[{'functionDeclarations':[dict(name=k,description=DESCRIPTIONS[k],parametersJsonSchema=v) for k,v in SCHEMAS.items()]}],toolConfig={'functionCallingConfig':{'mode':'ANY'}},generationConfig=dict(maxOutputTokens=900,temperature=0,thinkingConfig={'thinkingLevel':'minimal'}))
def normalize(model,raw):
 r=BASE_NORMALIZE(model,raw);p=MODELS[model]['provider'];calls=[]
 if p=='openai':
  calls=[dict(name=x['name'],arguments=x['arguments'],id=x['call_id']) for x in raw['output'] if x['type']=='function_call'];history=raw['output']
 elif p=='anthropic':
  calls=[dict(name=x['name'],arguments=canonical(x['input']),id=x['id']) for x in raw['content'] if x['type']=='tool_use'];history=raw['content'];r['complete']=raw.get('stop_reason')=='tool_use'
 else:
  history=raw['candidates'][0]['content'];calls=[dict(name=x['functionCall']['name'],arguments=canonical(x['functionCall'].get('args',{}))) for x in history.get('parts',[]) if 'functionCall'in x]
 r.update(native_calls=calls,native_history=history);return r

def freeze():
 original=json.loads((ROOT/'manifest_main.json').read_text());cells=[dict(c,paired_original_id=c['id']) for c in original['schedule'] if c['spec']['variant'] in ('clean','disjoint','dependency_race') and c['spec']['replicate']==1]
 random.Random(2026102710).shuffle(cells)
 for i,c in enumerate(cells,1):c['id']=f'v05-functions-{i:03}'
 assert len(cells)==36
 save(HERE/'manifest.json',dict(frozen_utc=datetime.now(timezone.utc).isoformat(),schedule=cells,prompt=PROMPT,schemas=SCHEMAS,source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),core_hashes=original['source_hashes'],budget_before=Ledger().snapshot(),rationale='Exploratory fixed native-function follow-up after both custom interfaces exhibited failures. All models and arms, both apps, clean/disjoint/dependency_race, replicate one. No selection by cell outcomes; no replacement or retries. Three excluded integration calibrations precede main calls.',sources=['https://developers.openai.com/api/docs/guides/function-calling','https://platform.claude.com/docs/en/agents-and-tools/tool-use/parallel-tool-use','https://ai.google.dev/gemini-api/docs/function-calling']))
def episode(c,m,out):
 rt=Runtime(c['spec'],out/(c['id']+'.sqlite3'),'atomic' if c['arm']=='atomic' else 'none');error=None;report=None;calls=[];p=MODELS[c['model']]['provider']
 with Live(rt,out/c['id']) as live:
  messages=[dict(role='user',**({'parts':[{'text':'Recovery task: '+canonical(rt.task)}]} if p=='google' else {'content':'Recovery task: '+canonical(rt.task)}))]
  for turn in range(18):
   if Ledger().snapshot()['total_bound_usd']>=12.5:error='budget_stop';break
   try:r=api.generate(c['model'],m['prompt'],messages,c['id']+f'-t{turn+1:02}',out,Ledger())
   except Exception as ex:error='transport_or_accounting:'+type(ex).__name__;break
   calls.append({k:r[k] for k in ('input_tokens','output_tokens','cost_nano')})
   if not r['complete']:error='output_incomplete';break
   try:
    assert len(r['native_calls'])==1;call=r['native_calls'][0];tool=call['name'];args=json.loads(call['arguments']);assert tool in SCHEMAS and type(args)is dict and set(args)==set(SCHEMAS[tool]['properties'])
    if tool=='finish':report=args;break
    assert len(rt.public)<24;o=live.invoke(tool,**args)
    if p=='openai':messages+=r['native_history']+[dict(type='function_call_output',call_id=call['id'],output=canonical(o))]
    elif p=='anthropic':messages += [dict(role='assistant',content=r['native_history']),dict(role='user',content=[dict(type='tool_result',tool_use_id=call['id'],content=canonical(o))])]
    else:messages += [r['native_history'],dict(role='user',parts=[dict(functionResponse=dict(name=tool,response=o))])]
   except (ValueError,TypeError,KeyError,AssertionError):error='invalid_function_action';break
  if report is None:error=error or 'turn_budget_exhausted';report=dict(execution_error=error)
  t=live.finish(report)
 t.update(cell=c,error=error,calls=calls,grade=grade(t));verify(t);save(out/(c['id']+'.trace.json'),t);return error

def execute(calibration):
 m=json.loads((HERE/'manifest.json').read_text());assert hashlib.sha256(Path(__file__).read_bytes()).hexdigest()==m['source_sha256'];assert all(hashlib.sha256((ROOT/k).read_bytes()).hexdigest()==v for k,v in m['core_hashes'].items())
 api.request=request;api.normalize=normalize
 out=ROOT/('function_calibration' if calibration else 'functions');out.mkdir(exist_ok=True)
 cells=[dict(c,id=f'v05-function-calibration-{i+1}') for i,model in enumerate(MODELS) for c in m['schedule'] if c['model']==model and c['arm']=='atomic' and c['spec']['name']=='codec_pipeline' and c['spec']['variant']=='clean'] if calibration else m['schedule']
 if not calibration:
  for i in range(3):
   t=json.loads((ROOT/'function_calibration'/f'v05-function-calibration-{i+1}.trace.json').read_text());assert t['calls'] and not (t['error']or'').startswith('transport_or_accounting')
 def lane(model):
  for c in cells:
   if c['model']!=model:continue
   if (out/(c['id']+'.trace.json')).exists():continue
   assert not list(out.glob(c['id']+'-t*.request.json')) and not (out/(c['id']+'.sqlite3')).exists()
   if Ledger().snapshot()['total_bound_usd']>=12.5:break
   error=episode(c,m,out);print(json.dumps(dict(id=c['id'],error=error,budget=Ledger().snapshot())),flush=True)
   if error and error.startswith(('transport','budget')):break
 with ThreadPoolExecutor(max_workers=3) as pool:list(pool.map(lane,MODELS))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('command',choices=['freeze','calibration','models']);a=p.parse_args();freeze() if a.command=='freeze' else execute(a.command=='calibration')
