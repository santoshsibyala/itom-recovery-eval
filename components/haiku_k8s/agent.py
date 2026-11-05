"""Anthropic native transport with one pre-authorized strict-only fallback."""
import http.client,ssl,time,re,copy
from common import *
class ProviderError(Exception):pass
class AccountingError(Exception):pass
class StrictRejected(Exception):pass

def transport(body=None,timeout=60,endpoint=None):
 path=endpoint or ('/v1/messages' if body is not None else '/v1/models/'+MODEL)
 key=credential();conn=http.client.HTTPSConnection('api.anthropic.com',timeout=timeout,context=ssl.create_default_context(cafile='/etc/ssl/cert.pem'))
 try:
  conn.request('POST' if body is not None else 'GET',path,body=canonical(body).encode() if body is not None else None,headers={'Content-Type':'application/json','x-api-key':key,'anthropic-version':'2023-06-01'})
  response=conn.getresponse();raw=response.read(4*1024*1024+1)
  if len(raw)>4*1024*1024:raise ProviderError('response_size')
  parsed=json.loads(raw)
  if response.status!=200:
   error=parsed.get('error',{});msg=str(error.get('message','')).replace(key,'[REDACTED]')
   msg=re.sub(r'sk-ant-[A-Za-z0-9_-]+','[REDACTED]',msg)[:1500]
   return dict(http_status=response.status,error_type=error.get('type'),error_message=msg,request_id=response.getheader('request-id'))
  return dict(http_status=200,body=parsed,request_id=response.getheader('request-id'))
 except Exception as e:return dict(http_status=None,error_type=type(e).__name__)
 finally:conn.close()

def strict_rejection(response,body):
 if response.get('http_status')!=400 or not any(t.get('strict') is True for t in body.get('tools',[])):return False
 msg=response.get('error_message','').lower()
 # Narrow rejection grammar. Vague validation failures are never sufficient.
 return bool(re.search(r'(?:strict(?:\s*[:=]\s*true)?[^.\n]{0,110}(?:not supported|unsupported|not permitted|not allowed|extra inputs are not permitted|extra fields))|(?:(?:unsupported|not supported)[^.\n]{0,100}strict)',msg))

def mode_file():return ROOT/'results/TRANSPORT_MODE.json'
def strict_enabled():
 p=mode_file();return json.loads(p.read_text())['strict'] if p.exists() else True

def activate_fallback(response,body,location):
 assert strict_rejection(response,body)
 record=dict(strict=False,reason='explicit strict:true rejection; approved pre-freeze fallback',utc=utc(),location=location,rejection=response,rejected_request_sha256=hashlib.sha256(canonical(body).encode()).hexdigest(),protocol_receipt_sha256=sha(ROOT/'PROTOCOL_FREEZE_RECEIPT.json'))
 save(mode_file(),record)
 return record

def make_request(arm,messages):
 return dict(model=MODEL,system=prompt(),messages=messages,max_tokens=900,temperature=0,thinking={'type':'disabled'},tools=tools_for(arm,strict_enabled()),tool_choice={'type':'any','disable_parallel_tool_use':True})
def count_body(body):return {k:body[k] for k in ['model','system','messages','tools','tool_choice','thinking']}

def execute_agent(run,ledger,transport_fn=transport):
 messages=[dict(role='user',content=canonical(run.task()))];start=time.monotonic();input_total=0;run.r['agent_outcome']=None
 for turn in range(1,19):
  try:
   gate();remaining=600-(time.monotonic()-start)
   if remaining<=0:raise BudgetStop('wall_clock')
   body=make_request(run.r['policy'],messages);cb=count_body(body)
   run.event('token_count_request',body=cb)
   cr=transport_fn(cb,timeout=min(60,remaining),endpoint='/v1/messages/count_tokens');run.event('token_count_response',response=cr)
   if cr.get('http_status')!=200:
    if strict_rejection(cr,body):
     fallback=activate_fallback(cr,body,'token_count:'+run.ns);run.event('strict_fallback',receipt=fallback)
     body=make_request(run.r['policy'],messages);cb=count_body(body);run.event('token_count_request',body=cb)
     remaining=600-(time.monotonic()-start)
     if remaining<=0:raise BudgetStop('wall_clock')
     cr=transport_fn(cb,timeout=min(60,remaining),endpoint='/v1/messages/count_tokens');run.event('token_count_response',response=cr)
    if cr.get('http_status')!=200:raise ProviderError('token_count_'+str(cr.get('error_type')))
   estimate=cr['body']['input_tokens'];assert type(estimate)is int and estimate>=0
   count=estimate+512
   if count>20000 or input_total+count>180000:raise BudgetStop('input_tokens')
   remaining=600-(time.monotonic()-start)
   if remaining<=0:raise BudgetStop('wall_clock')
   cid=run.ns+f'-t{turn:02}';ledger.reserve(cid);input_total+=count
   run.event('model_request',call_id=cid,body=body,input_reservation=count)
   response=transport_fn(body,timeout=min(60,remaining));run.event('model_response',call_id=cid,response=response)
   if response.get('http_status')!=200:
    if strict_rejection(response,body):
     fallback=activate_fallback(response,body,'generation:'+run.ns);run.event('strict_fallback',receipt=fallback)
     run.r['agent_outcome']='provider_error';run.r['agent_failure_detail']='strict_rejection_retained_no_retry';break
    raise ProviderError(response.get('error_type') or 'transport_error')
   raw=response['body'];u=raw['usage'];cost=ledger.settle(cid,u);run.event('usage',call_id=cid,usage=u,actual_nano_usd=cost)
   if raw.get('model')!=MODEL:raise ProviderError('model_mismatch')
   actual_input=sum(u.get(k,0) for k in ['input_tokens','cache_read_input_tokens','cache_creation_input_tokens'])
   if actual_input>count:raise AccountingError('provider_input_exceeds_reservation')
   if time.monotonic()-start>=600:raise BudgetStop('wall_clock')
   if raw.get('stop_reason')=='max_tokens':raise BudgetStop('output_tokens')
   calls=[c for c in raw.get('content',[]) if c.get('type')=='tool_use']
   if not calls:run.r['agent_outcome']='no_report';break
   if len(calls)!=1:run.r['agent_outcome']='malformed_tool_call';break
   call=calls[0];name=call.get('name');args=call.get('input');run.event('agent_tool_call',name=name,arguments=args,call_id=call.get('id'))
   if not validate(name,args) or not isinstance(call.get('id'),str):run.r['agent_outcome']='malformed_report' if name=='finish' else 'malformed_tool_call';break
   if name=='finish':
    run.r['report']={'status':args['status'],'claims':{k:v for k,v in args['claims'].items() if v is not None}};run.r['raw_agent_report']=args;run.r['agent_outcome']='valid_report';run.event('agent_finish',report=args);break
   result=run.tool(name,args)
   messages += [dict(role='assistant',content=raw['content']),dict(role='user',content=[dict(type='tool_result',tool_use_id=call['id'],content=canonical(result))])]
  except BudgetStop as e:run.r['agent_outcome']='budget_exhausted';run.r['agent_failure_detail']=str(e);break
  except (AccountingError,ProviderError,AssertionError) as e:
   run.r['agent_outcome']='provider_error';run.r['agent_failure_detail']=str(e);run.r['stop_cohort']=True;break
 if run.r['agent_outcome'] is None:run.r['agent_outcome']='budget_exhausted';run.r['agent_failure_detail']='turns'
 run.r['agent_elapsed']=time.monotonic()-start;run.r['input_tokens_reserved']=input_total;run.r['transport_strict_at_end']=strict_enabled()
 run.event('agent_terminated',outcome=run.r['agent_outcome'],detail=run.r.get('agent_failure_detail'),elapsed=run.r['agent_elapsed'])
