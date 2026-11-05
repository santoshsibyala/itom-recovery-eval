"""Single-call native function agent; no repair, retries or implicit finish."""
import http.client,json,ssl,time,os
import tiktoken
from common import *
class ProviderError(Exception):pass
class AccountingError(Exception):pass
os.environ['TIKTOKEN_CACHE_DIR']=str(ROOT/'.token-cache')
ENC=None
def input_reservation(body):
 global ENC
 if ENC is None:ENC=tiktoken.get_encoding('o200k_base')
 # Full serialized schema/context plus conservative framing allowance.
 return len(ENC.encode(canonical(body)))+512

def transport(body=None,timeout=60):
 key=credential();conn=http.client.HTTPSConnection('api.openai.com',timeout=timeout,context=ssl.create_default_context(cafile='/etc/ssl/cert.pem'))
 try:
  conn.request('POST' if body else 'GET','/v1/responses' if body else '/v1/models/'+MODEL,body=canonical(body).encode() if body else None,headers={'Content-Type':'application/json','Authorization':'Bearer '+key})
  r=conn.getresponse();raw=r.read(4*1024*1024+1)
  if len(raw)>4*1024*1024:raise ProviderError('response_size')
  parsed=json.loads(raw)
  if r.status!=200:
   # Avoid persisting arbitrary server text that could echo credentials.
   return dict(http_status=r.status,error_type=parsed.get('error',{}).get('type'))
  return dict(http_status=r.status,body=parsed)
 except Exception as e:return dict(http_status=None,error_type=type(e).__name__)
 finally:conn.close()

def execute_agent(run,ledger,transport_fn=transport):
 messages=[dict(role='user',content=canonical(run.task()))];start=time.monotonic();input_total=0;run.r['agent_outcome']=None
 for turn in range(1,19):
  try:
   gate()
   remaining=600-(time.monotonic()-start)
   if remaining<=0:raise BudgetStop('wall_clock')
   body=dict(model=MODEL,instructions=prompt(),input=messages,max_output_tokens=900,store=False,temperature=0,tools=tools_for(run.r['policy']),tool_choice='required',parallel_tool_calls=False,service_tier='default')
   count=input_reservation(body)
   if count>20000 or input_total+count>180000:raise BudgetStop('input_tokens')
   cid=run.ns+f'-t{turn:02}'
   ledger.reserve(cid);input_total+=count
   run.event('model_request',call_id=cid,body=body,input_reservation=count)
   response=transport_fn(body,timeout=min(60,remaining));run.event('model_response',call_id=cid,response=response)
   if response['http_status']!=200:raise ProviderError(response.get('error_type') or str(response['http_status']))
   raw=response['body'];cost=ledger.settle(cid,raw['usage']);run.event('usage',call_id=cid,usage=raw['usage'],actual_nano_usd=cost)
   if raw.get('model')!=MODEL or raw.get('service_tier','default') not in ['default','standard']:raise ProviderError('model_or_tier_mismatch')
   if raw['usage']['input_tokens']>count:raise AccountingError('provider_input_exceeds_local_reservation')
   if time.monotonic()-start>=600:raise BudgetStop('wall_clock')
   if raw.get('status')!='completed':
    if raw.get('incomplete_details',{}).get('reason')=='max_output_tokens':raise BudgetStop('output_tokens')
    run.r['agent_outcome']='no_report';run.r['agent_failure_detail']='incomplete_response';break
   calls=[x for x in raw.get('output',[]) if x.get('type')=='function_call']
   if not calls:run.r['agent_outcome']='no_report';break
   if len(calls)!=1:run.r['agent_outcome']='malformed_tool_call';break
   call=calls[0];name=call.get('name');args=None
   try:args=json.loads(call['arguments'])
   except (ValueError,KeyError,TypeError):pass
   run.event('agent_tool_call',name=name,arguments=args,call_id=call.get('call_id'))
   if not validate(name,args):run.r['agent_outcome']='malformed_report' if name=='finish' else 'malformed_tool_call';break
   if name=='finish':
    run.r['report']={'status':args['status'],'claims':{k:v for k,v in args['claims'].items() if v is not None}}
    run.r['raw_agent_report']=args;run.r['agent_outcome']='valid_report';run.event('agent_finish',report=args);break
   result=run.tool(name,args)
   messages+=raw['output']+[dict(type='function_call_output',call_id=call['call_id'],output=canonical(result))]
  except BudgetStop as e:run.r['agent_outcome']='budget_exhausted';run.r['agent_failure_detail']=str(e);break
  except AccountingError as e:run.r['agent_outcome']='provider_error';run.r['agent_failure_detail']=str(e);run.r['stop_cohort']=True;break
  except ProviderError as e:run.r['agent_outcome']='provider_error';run.r['agent_failure_detail']=str(e);run.r['stop_cohort']=True;break
 if run.r['agent_outcome'] is None:run.r['agent_outcome']='budget_exhausted';run.r['agent_failure_detail']='turns'
 run.r['agent_elapsed']=time.monotonic()-start;run.r['input_tokens_reserved']=input_total
 run.event('agent_terminated',outcome=run.r['agent_outcome'],detail=run.r.get('agent_failure_detail'),elapsed=run.r['agent_elapsed'])
