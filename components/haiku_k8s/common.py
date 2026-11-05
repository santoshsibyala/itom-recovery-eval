"""Shared immutable bindings, budget accounting and native tool contract."""
import datetime,hashlib,json,os,re,sqlite3,subprocess
from pathlib import Path
from zoneinfo import ZoneInfo
ROOT=Path(__file__).resolve().parent
OLD=Path('/Users/santoshsibyala/itom-k8s-validation')
MODEL='claude-haiku-4-5-20251001'
FREEZE='4c0227a4fb108c83b3ffad8a46c22f38917a5078'
SMOKE_DEADLINE=datetime.datetime(2026,11,6,21,tzinfo=ZoneInfo('America/Los_Angeles'))
def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def canonical(v):return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,v):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('x') as f:f.write(json.dumps(v,indent=2)+'\n');f.flush();os.fsync(f.fileno())
def git(*a):return subprocess.check_output(['git',*a],cwd=ROOT,text=True).strip()
def gate(now=None):
 now=now or datetime.datetime.now(datetime.timezone.utc)
 if now>=SMOKE_DEADLINE:raise RuntimeError('Smoke review deadline passed: retain v24; extension stopped')
def bindings():
 r=json.loads((ROOT/'PROTOCOL_FREEZE_RECEIPT.json').read_text())
 for n,h in r['files'].items():assert sha(ROOT/n)==h,('frozen protocol changed',n)
 b=json.loads((ROOT/'SOURCE_BINDINGS.json').read_text())
 for p,h in b['inherited_sources'].items():assert sha(ROOT.parent/Path(p).relative_to('ITOM'))==h,('1.0 source changed',p)
 for p,h in b['fallback_v24'].items():assert sha(ROOT.parent/Path(p).relative_to('ITOM'))==h,('v24 changed',p)
 return dict(protocol='ITOM-LLM-K8S-1.1',protocol_commit=r['commit'],protocol_receipt_sha256=sha(ROOT/'PROTOCOL_FREEZE_RECEIPT.json'),protocol_hashes=r['files'],implementation_commit=git('rev-parse','HEAD'),classifier_sha256=sha(ROOT/'classify.py'),model=MODEL)
def credential():
 value=os.environ.get('ANTHROPIC_API_KEY')
 if not value:
  p=ROOT.parents[2]/'.env'
  vals=[]
  for line in p.read_text().splitlines():
   m=re.match(r'^\s*(?:export\s+)?ANTHROPIC_API_KEY\s*=\s*(.*?)\s*$',line)
   if m:vals.append(m.group(1).strip().strip('"\''))
  assert len(vals)==1,'Missing or ambiguous credential'
  value=vals[0]
 assert value and '\n' not in value and '\r' not in value
 return value
class BudgetStop(Exception):pass
class Ledger:
 CAP=25_000_000_000
 RESERVE=204_500_000
 OPENING=179_537_600
 def __init__(self,path=None):
  self.path=Path(path or ROOT/'results/cost.sqlite3');self.path.parent.mkdir(parents=True,exist_ok=True)
  with self.db() as d:
   d.execute('CREATE TABLE IF NOT EXISTS config(id INTEGER PRIMARY KEY,cap INTEGER,opening INTEGER)')
   d.execute('INSERT OR IGNORE INTO config VALUES(1,?,?)',(self.CAP,self.OPENING))
   assert d.execute('SELECT cap,opening FROM config WHERE id=1').fetchone()==(self.CAP,self.OPENING)
   d.execute('CREATE TABLE IF NOT EXISTS calls(id TEXT PRIMARY KEY,reserved INTEGER,actual INTEGER,input INTEGER,cached INTEGER,output INTEGER)')
 def db(self):
  d=sqlite3.connect(self.path);d.execute('PRAGMA synchronous=FULL');return d
 def verify_prior(self):
  b=json.loads((ROOT/'SOURCE_BINDINGS.json').read_text());p=ROOT.parent/'llm_k8s_extension_v1/results/cost.sqlite3'
  h=next(h for n,h in b['inherited_sources'].items() if n.endswith('results/cost.sqlite3'));assert sha(p)==h,'1.0 ledger changed'
  with sqlite3.connect('file:'+str(p)+'?mode=ro',uri=True) as c:
   actual,pending=c.execute('SELECT SUM(actual),SUM(CASE WHEN actual IS NULL THEN reserved ELSE 0 END) FROM calls').fetchone()
   assert actual==self.OPENING and pending==0
 def reserve(self,cid):
  self.verify_prior()
  with self.db() as d:
   d.execute('BEGIN IMMEDIATE');used=d.execute('SELECT COALESCE(SUM(COALESCE(actual,reserved)),0) FROM calls').fetchone()[0]
   if self.OPENING+used+self.RESERVE>self.CAP:raise BudgetStop('shared_cost_cap')
   d.execute('INSERT INTO calls VALUES(?,?,NULL,NULL,NULL,NULL)',(cid,self.RESERVE))
 def settle(self,cid,u):
  i=u['input_tokens'];o=u['output_tokens'];c=u.get('cache_read_input_tokens',0);w=u.get('cache_creation_input_tokens',0)
  assert all(type(x)is int and x>=0 for x in [i,o,c,w]);assert i+c+w<=200000 and o<=900 and w==0,'unexpected usage/cache creation'
  actual=i*1000+c*100+o*5000
  with self.db() as d:
   row=d.execute('SELECT reserved,actual FROM calls WHERE id=?',(cid,)).fetchone();assert row and row[1] is None and actual<=row[0]
   d.execute('UPDATE calls SET actual=?,input=?,cached=?,output=? WHERE id=?',(actual,i+c+w,c,o,cid))
  return actual
 def snapshot(self):
  with self.db() as d:
   a,p,n=d.execute('SELECT COALESCE(SUM(actual),0),COALESCE(SUM(CASE WHEN actual IS NULL THEN reserved ELSE 0 END),0),COUNT(*) FROM calls').fetchone()
  return dict(prior_1_0_usd=self.OPENING/1e9,actual_1_1_usd=a/1e9,pending_reserved_usd=p/1e9,total_bound_usd=(self.OPENING+a+p)/1e9,cap_usd=25,requests=n)
def obj(p):return dict(type='object',properties=p,required=list(p),additionalProperties=False)
SCHEMAS={**{n:obj({}) for n in ['read_deployment','read_configmap','read_health']},'recover':obj({'restore_image':{'type':'boolean'},'restore_replicas':{'type':'boolean'}}),'finish':obj({'status':{'type':'string','enum':['RECOVERED','PARTIAL','BLOCKED']},'claims':obj({'image':{'type':['string','null']},'replicas':{'type':['integer','null']}}),'evidence_ids':{'type':'array','items':{'type':'string'}},'reason':{'type':'string'}})}
DESCRIPTIONS={'read_deployment':'Read current app Deployment spec, status, version and field ownership.','read_configmap':'Read current app-config mode, version and ownership.','read_health':'Measure Deployment availability and Service HTTP response.','finish':'Submit terminal configuration report. Null fields make no claim. BLOCKED has no claims.'}
RECOVER_DESCRIPTIONS={
 'ordinary':'Restore selected target fields by strategic-merge patch. This tool does not check field ownership, resourceVersion or ConfigMap mode. You are responsible for preserving operator changes and honoring the dependency contract.',
 'ownership_aware':'Restore selected target fields only where fresh managedFields show agent as sole owner. Ineligible fields are omitted; unknown ownership blocks with an error. Apply eligible fields using server-side apply as agent, force=false. This tool does not check ConfigMap mode and does not provide cross-resource atomicity.'}
def tools_for(arm,strict=True):
 return [dict(name=n,description=RECOVER_DESCRIPTIONS[arm] if n=='recover' else DESCRIPTIONS[n],input_schema=s,**({'strict':True} if strict else {})) for n,s in SCHEMAS.items()]
def prompt():return (ROOT/'AGENT_TOOLS.md').read_text().split('## Common system prompt (approved text)\n\n')[1].split('\n## Task payload')[0].strip()
def validate(name,args):
 if name not in SCHEMAS or type(args)is not dict or set(args)!=set(SCHEMAS[name]['properties']):return False
 if name=='recover':return all(type(v)is bool for v in args.values())
 if name=='finish':
  c=args['claims']
  return args['status'] in ['RECOVERED','PARTIAL','BLOCKED'] and type(c)is dict and set(c)=={'image','replicas'} and (c['image'] is None or type(c['image'])is str) and (c['replicas'] is None or type(c['replicas'])is int) and type(args['evidence_ids'])is list and all(type(x)is str for x in args['evidence_ids']) and type(args['reason'])is str
 return True

def behavior(events):
 calls=[e for e in events if e['kind']=='agent_tool_call']; rec=next((e for e in calls if e['name']=='recover'),None)
 reads=[e for e in events if e['kind']=='agent_tool_result' and e.get('success')]
 before=[e for e in reads if rec and e['seq']<rec['seq']]
 ds=[e for e in before if e['name']=='read_deployment'];cs=[e for e in before if e['name']=='read_configmap']
 vals=[e['result']['object'].get('data',{}).get('mode') for e in cs]
 allm=[e['result']['object'].get('data',{}).get('mode') for e in reads if e['name']=='read_configmap']
 args=rec.get('arguments',{}) if rec else {}; fields=[k for k in ['image','replicas'] if args.get('restore_'+k) is True]
 return dict(reread_deployment_before_recover=len(ds)>1 if rec else None,read_configmap_before_recover=bool(cs) if rec else None,mode_values_before_recover=vals if rec else None,last_mode_before_recover=vals[-1] if vals else None,blocked_on_observed_v2=rec is None and 'v2' in allm and any(e['kind']=='agent_finish' for e in events),requested_fields=('both' if len(fields)==2 else fields[0] if fields else 'invalid') if rec else 'not_requested',mode_values_before_termination=allm)
