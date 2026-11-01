"""Explicitly authorized paid research, durable shared $15 ledger, no retries."""
import http.client,json,os,re,ssl,sqlite3
from contextlib import contextmanager
from pathlib import Path
from datetime import datetime,timezone
from .common import canonical,digest,require

ROOT=Path(__file__).resolve().parents[1]
STATE=ROOT/'live_state'
MODELS={
 'gpt-4.1-mini-2025-04-14':dict(provider='openai',host='api.openai.com',path='/v1/responses',key='OPENAI_API_KEY',context=1047576,ir=400,orr=1600),
 'claude-haiku-4-5-20251001':dict(provider='anthropic',host='api.anthropic.com',path='/v1/messages',key='ANTHROPIC_API_KEY',context=200000,ir=1000,orr=5000),
 'gemini-3.1-flash-lite':dict(provider='google',host='generativelanguage.googleapis.com',path='/v1beta/models/gemini-3.1-flash-lite:generateContent',key='GEMINI_API_KEY',context=1048576,ir=250,orr=1500)}
ACTION_SCHEMA={"type":"object","properties":{"tool":{"type":"string","enum":["read_resource","read_changes","read_health","apply_patch","get_operation","record_recovery_audit","escalate","finish"]},"arguments_json":{"type":"string"}},"required":["tool","arguments_json"],"additionalProperties":False}
MAX_OUTPUT=900
CAP=15_000_000_000 # nano-dollars


def credential(name):
    value=os.environ.get(name)
    if not value:
        # Existing user-configured credentials; values never printed or archived.
        path=ROOT.parents[2]/'.env'
        require(path.is_file(),'Credential file unavailable')
        matches=[]
        for line in path.read_text().splitlines():
            m=re.match(r'^\s*(?:export\s+)?'+re.escape(name)+r'\s*=\s*(.*?)\s*$',line)
            if m:matches.append(m.group(1).strip().strip('"\''))
        require(len(matches)==1,'Missing or ambiguous credential assignment')
        value=matches[0]
    require(bool(value) and '\n' not in value and '\r' not in value,'Invalid credential')
    return value


def transport(model,body=None):
    spec=MODELS[model];key=credential(spec['key'])
    headers={'Content-Type':'application/json'}
    if spec['provider']=='google':headers['x-goog-api-key']=key
    else:headers['Authorization']='Bearer '+key
    if spec['provider']=='anthropic':headers['anthropic-version']='2026-10-21'
    context=ssl.create_default_context(cafile='/etc/ssl/cert.pem')
    require(context.check_hostname and context.verify_mode==ssl.CERT_REQUIRED,'TLS disabled')
    conn=http.client.HTTPSConnection(spec['host'],timeout=55,context=context)
    path=spec['path'] if body is not None else ('/v1beta/models/' if spec['provider']=='google' else '/v1/models/')+model
    try:
        conn.request('POST' if body is not None else 'GET',path,body=canonical(body).encode() if body is not None else None,headers=headers)
        response=conn.getresponse();raw=response.read(4*1024*1024+1)
        if response.status!=200:
            try:
                error=json.loads(raw).get('error',{})
                message=str(error.get('message','')).replace(key,'[REDACTED]')
                message=re.sub(r'(?:sk-|AIza)[A-Za-z0-9_-]+','[REDACTED]',message)
                return dict(http_status=response.status,error_type=error.get('type'),message=message[:500])
            except Exception:
                return dict(http_status=response.status)
        require(len(raw)<=4*1024*1024,'Response too large')
        return dict(http_status=200,body=json.loads(raw))
    except Exception as ex:
        return dict(http_status=None,error_type=type(ex).__name__)
    finally:conn.close()


class Ledger:
    def __init__(self,path=STATE/'budget.sqlite3'):
        self.path=Path(path);self.path.parent.mkdir(parents=True,exist_ok=True)
        with self.connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS config (id INTEGER PRIMARY KEY CHECK(id=1), cap INTEGER NOT NULL)')
            db.execute('INSERT OR IGNORE INTO config VALUES (1,?)',(CAP,))
            db.execute('CREATE TABLE IF NOT EXISTS calls (id TEXT PRIMARY KEY, model TEXT, reserved INTEGER, settled INTEGER, request_hash TEXT, response_hash TEXT)')
            require(db.execute('SELECT cap FROM config').fetchone()[0]==CAP,'Budget config changed')
    @contextmanager
    def connect(self):
        db=sqlite3.connect(self.path,timeout=30)
        try:
            db.execute('PRAGMA synchronous=FULL')
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()
    def snapshot(self):
        with self.connect() as db:
            settled,pending,count=db.execute('SELECT COALESCE(SUM(settled),0),COALESCE(SUM(CASE WHEN settled IS NULL THEN reserved ELSE 0 END),0),COUNT(*) FROM calls').fetchone()
        return dict(cap_usd=15,settled_upper_usd=settled/1e9,pending_reserved_usd=pending/1e9,
                    total_bound_usd=(settled+pending)/1e9,calls=count)
    def reserve(self,call_id,model,body):
        s=MODELS[model]
        # Entire model context at standard input rates; Claude cache creation up to 2x.
        bound=s['context']*s['ir']*(2 if s['provider']=='anthropic' else 1)+MAX_OUTPUT*s['orr']
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            used=db.execute('SELECT COALESCE(SUM(COALESCE(settled,reserved)),0) FROM calls').fetchone()[0]
            require(used+bound<=CAP,'Shared $15 budget would be exceeded')
            db.execute('INSERT INTO calls VALUES (?,?,?,?,?,?)',(call_id,model,bound,None,digest(body),None))
        return bound
    def settle(self,call_id,cost,response):
        require(type(cost) is int and cost>=0,'Invalid cost')
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row=db.execute('SELECT reserved,settled FROM calls WHERE id=?',(call_id,)).fetchone()
            require(row is not None and row[1] is None and cost<=row[0],'Cost exceeds reservation or already settled')
            db.execute('UPDATE calls SET settled=?,response_hash=? WHERE id=?',(cost,digest(response),call_id))


def request(model,system,messages):
    p=MODELS[model]['provider']
    if p=='openai':return dict(model=model,instructions=system,input=messages,max_output_tokens=MAX_OUTPUT,store=False,temperature=0,text={"format":{"type":"json_schema","name":"action","strict":True,"schema":ACTION_SCHEMA}})
    if p=='anthropic':return dict(model=model,system=system,messages=messages,max_tokens=MAX_OUTPUT,thinking={'type':'disabled'},stream=False,output_config={'format':{'type':'json_schema','schema':ACTION_SCHEMA}})
    return dict(systemInstruction={'parts':[{'text':system}]},contents=[dict(role='model' if x['role']=='assistant' else 'user',parts=[{'text':x['content']}]) for x in messages],
                generationConfig=dict(responseMimeType='application/json',responseJsonSchema=ACTION_SCHEMA,maxOutputTokens=MAX_OUTPUT,temperature=0,thinkingConfig={'thinkingLevel':'minimal'}))


def normalize(model,raw):
    s=MODELS[model];p=s['provider']
    if p=='openai':
        require(raw.get('model')==model,'Returned model mismatch');u=raw['usage'];i=u['input_tokens'];o=u['output_tokens']
        text=''.join(c.get('text','') for x in raw['output'] if x['type']=='message' for c in x['content'] if c['type']=='output_text')
        complete=raw.get('status')=='completed';cost=i*s['ir']+o*s['orr']
    elif p=='anthropic':
        require(raw.get('model')==model,'Returned model mismatch');u=raw['usage'];i=u['input_tokens'];o=u['output_tokens']
        create=u.get('cache_creation_input_tokens',0);read=u.get('cache_read_input_tokens',0)
        require(not any(u.get('server_tool_use',{}).values()),'Unpriced server tools')
        require(u.get('service_tier','standard')=='standard' and u.get('speed','standard')=='standard','Unexpected price tier')
        i+=create+read;cost=(u['input_tokens']+2*create+read)*s['ir']+o*s['orr']
        text=''.join(x['text'] for x in raw['content'] if x['type']=='text');complete=raw.get('stop_reason')=='end_turn'
    else:
        require(raw.get('modelVersion')==model,'Returned model mismatch');u=raw['usageMetadata'];i=u['promptTokenCount'];o=u.get('candidatesTokenCount',0)+u.get('thoughtsTokenCount',0)
        require(not u.get('toolUsePromptTokenCount'),'Unpriced tool usage')
        require(u['totalTokenCount']==i+o,'Usage inconsistency')
        candidates=raw.get('candidates',[]);require(len(candidates)==1,'Missing/extra candidate')
        require(not candidates[0].get('groundingMetadata'),'Unexpected server tools')
        text=''.join(x.get('text','') for x in candidates[0].get('content',{}).get('parts',[]) if not x.get('thought'))
        complete=candidates[0].get('finishReason')=='STOP';cost=i*s['ir']+o*s['orr']
    require(type(i) is int and type(o) is int and 0<=i<=s['context'] and 0<=o<=MAX_OUTPUT,'Usage exceeds bound')
    return dict(text=text,complete=complete,cost_nano=cost,input_tokens=i,output_tokens=o)


def save(path,value):
    with Path(path).open('x') as f:json.dump(value,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())


def generate(model,system,messages,call_id,folder,ledger):
    body=request(model,system,messages);folder=Path(folder)
    save(folder/(call_id+'.request.json'),body)
    ledger.reserve(call_id,model,body)
    response=transport(model,body);save(folder/(call_id+'.response.json'),response)
    require(response['http_status']==200,'Provider request failed; reservation retained')
    result=normalize(model,response['body']);ledger.settle(call_id,result['cost_nano'],response)
    return result
