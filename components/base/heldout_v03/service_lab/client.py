import hashlib,json,subprocess,sys,time,os,statistics
from pathlib import Path
from recovery.common import ROOT,require
from .server import http
class LiveService:
 def __init__(self,spec,path,lingering=False):
  self.spec=spec;self.path=Path(path);self.path.mkdir(exist_ok=False);self.processes=[];self.metadata=[];self.probes=[];self.operator=None;self.counter=0
  self.specfile=self.path/'scenario.json';self.specfile.write_text(json.dumps(spec,indent=2)+'\n')
  try:
   blue=self.spawn(['--role','backend','--name','blue']);green=self.spawn(['--role','backend','--name','green'])
   if lingering:require(http(blue['port'],'/configure',{'corrupt':True})[0]==200,'Backend calibration failed')
   proxy=self.spawn(['--role','proxy','--spec',str(self.specfile),'--blue',str(blue['port']),'--green',str(green['port'])]);self.port=proxy['port']
   status,self.task=http(self.port,'/task');require(status==200,'Task unavailable');self.pre=self.measure('before',5)
  except Exception:self.close();raise
 def spawn(self,args):
  log=(self.path/f'process-{len(self.processes)}.stderr.log').open('w');p=subprocess.Popen([sys.executable,'-m','service_lab.server',*args],cwd=ROOT,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'},stdout=subprocess.PIPE,stderr=log,text=True);self.processes.append((p,log))
  line=p.stdout.readline();require(bool(line),'Service startup failed');meta=json.loads(line);self.metadata.append(meta);return meta
 def measure(self,label,n=20):
  rows=[]
  for i in range(n):
   self.counter+=1;payload=f'itom-{self.counter}';start=time.perf_counter()
   try:status,reply=http(self.port,'/work/'+payload);ok=status==200 and reply.get('checksum')==hashlib.sha256(payload.encode()).hexdigest();error=None
   except Exception as ex:status=None;reply={};ok=False;error=type(ex).__name__
   rows.append(dict(request_id=self.counter,label=label,payload=payload,returned_checksum=reply.get('checksum'),http_status=status,correct=ok,elapsed_ms=(time.perf_counter()-start)*1000,backend_pid=reply.get('pid'),error=error));time.sleep(.01)
  self.probes.extend(rows);return rows
 def invoke(self,tool,**args):
  if tool=='apply_patch' and self.spec['timing']=='before_write' and self.operator is None:
   r=subprocess.run([sys.executable,'-m','service_lab.operator',str(self.port)],cwd=ROOT,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'},capture_output=True,text=True,timeout=10);require(r.returncode==0,'Operator barrier failed');self.operator=json.loads(r.stdout)
  status,obs=http(self.port,'/invoke',dict(tool=tool,arguments=args));require(status==200,'Service tool transport failed')
  if tool=='apply_patch':self.measure('after-write',3)
  return obs
 def finish(self,report):
  windows=[self.measure(f'terminal-{i+1}',20) for i in range(3)]
  status,t=http(self.port,'/finish',dict(report=report));require(status==200,'Service finish failed')
  t['service']=dict(processes=self.metadata,operator=self.operator,requests=self.probes,terminal_windows=[dict(requests=len(w),correct=sum(x['correct'] for x in w),p95_ms=sorted(x['elapsed_ms'] for x in w)[18]) for w in windows],health_pass=all(sum(x['correct'] for x in w)>=19 for w in windows),pre_correct=sum(x['correct'] for x in self.pre),implementation='Shared configuration engine; separate proxy/backend OS processes and independently checked HTTP response digests. read_health tool remains synthetic; measured service health is out-of-band and not shown to agents.')
  return t
 def close(self):
  for p,log in reversed(self.processes):
   if p.poll() is None:
    p.terminate()
    try:p.wait(timeout=5)
    except subprocess.TimeoutExpired:p.kill();p.wait(timeout=5)
   if p.stdout:p.stdout.close()
   log.close()
 def __enter__(self):return self
 def __exit__(self,*args):self.close()
