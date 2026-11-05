"""Independent HTTP data paths: numeric codec pipeline and two durable receipt stores."""
from contextlib import contextmanager
import argparse,hashlib,json,os,sqlite3,subprocess,sys,time,urllib.request
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path

HERE=Path(__file__).resolve().parent
@contextmanager
def connect(path,**kwargs):
 db=sqlite3.connect(path,**kwargs)
 try:
  yield db
  db.commit()
 except Exception:
  db.rollback();raise
 finally:db.close()
def http(port,path,body):
 data=json.dumps(body).encode();req=urllib.request.Request(f'http://127.0.0.1:{port}{path}',data,{'Content-Type':'application/json'})
 with urllib.request.urlopen(req,timeout=5) as r:return json.loads(r.read())
def state(path):
 with connect('file:'+str(path)+'?mode=ro',uri=True) as db:
  db.execute('BEGIN');return {r:json.loads(b)['values'] for r,b in db.execute('SELECT id,body FROM resources')}
def serve(args):
 if args.role=='store':
  with connect(args.store) as db:db.execute('CREATE TABLE IF NOT EXISTS receipts(id TEXT PRIMARY KEY,value TEXT)')
 class Handler(BaseHTTPRequestHandler):
  def log_message(self,*a):pass
  def do_POST(self):
   try:
    a=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
    if args.role=='codec':
     factor=state(args.db)['decoder']['factor'];v=a['encoded']//factor
     if args.lingering:v+=1
     result=dict(checksum=hashlib.sha256(str(v).encode()).hexdigest(),pid=os.getpid())
    elif args.role=='store':
     with connect(args.store) as db:
      if self.path=='/put' and not args.lingering:db.execute('INSERT OR REPLACE INTO receipts VALUES (?,?)',(a['id'],a['checksum']))
      row=db.execute('SELECT value FROM receipts WHERE id=?',(a['id'],)).fetchone()
     result=dict(stored=row[0] if row else None,pid=os.getpid())
    else:
     v=state(args.db)
     if args.name=='codec_pipeline':
      result=http(args.ports[0],'/work',dict(encoded=a['value']*v['encoder']['factor']))
     else:
      receipts=[];checksum=hashlib.sha256(str(a['value']).encode()).hexdigest()
      copies=min(v['writer']['copies'],v['pool']['available'],len(args.ports))
      for port in args.ports[:copies]:http(port,'/put',dict(id=a['id'],checksum=checksum))
      for port in args.ports:receipts.append(http(port,'/get',dict(id=a['id']))['stored'])
      result=dict(receipts=receipts,acknowledged=sum(x==checksum for x in receipts)>=v['ack']['required'],pid=os.getpid())
    body=json.dumps(result).encode();self.send_response(200)
   except Exception as e:body=json.dumps(dict(error=type(e).__name__)).encode();self.send_response(500)
   self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
 server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
 print(json.dumps(dict(port=server.server_port,pid=os.getpid(),role=args.role)),flush=True);server.serve_forever()

class Live:
 def __init__(self,runtime,folder):
  self.runtime=runtime;self.spec=runtime.spec;self.folder=Path(folder);self.folder.mkdir(exist_ok=False);self.children=[];self.metadata=[];self.requests=[];self.operator=[];self.counter=0;self.write_attempts=0
  (self.folder/'spec.json').write_text(json.dumps(self.spec))
  try:
   roles=['codec'] if self.spec['name']=='codec_pipeline' else ['store','store'];ports=[]
   for i,role in enumerate(roles):
    args=['--role',role,'--db',str(runtime.path),'--store',str(self.folder/f'store-{i}.sqlite3')]
    if self.spec['lingering'] and i==0:args+=['--lingering']
    ports.append(self.spawn(args)['port'])
   self.port=self.spawn(['--role','gateway','--db',str(runtime.path),'--name',self.spec['name'],'--ports',*map(str,ports)])['port']
   runtime.health=lambda:self.measure('public',20)
  except Exception:self.close();raise
 def spawn(self,args):
  log=(self.folder/f'process-{len(self.children)}.stderr').open('w')
  p=subprocess.Popen([sys.executable,str(HERE/'services.py'),*args],stdout=subprocess.PIPE,stderr=log,text=True,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
  self.children.append((p,log));line=p.stdout.readline()
  if not line:raise RuntimeError('Service start failed')
  meta=json.loads(line);self.metadata.append(meta);return meta
 def external(self):
  time.sleep(self.spec['delay_ms']/1000)
  out=subprocess.run([sys.executable,str(HERE/'services.py'),'--operator','--db',str(self.runtime.path),'--spec',str(self.folder/'spec.json')],capture_output=True,text=True,timeout=10,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
  assert out.returncode==0,'Operator failed';self.operator.append(json.loads(out.stdout))
 def invoke(self,tool,**args):
  if tool=='apply_patch':
   self.write_attempts+=1
   if self.spec['timing']=='write' and self.write_attempts==2:self.external()
  return self.runtime.invoke(tool,**args)
 def measure(self,label,n):
  with self.runtime.db() as db:before=self.runtime.epoch(db)
  rows=[]
  for i in range(n):
   self.counter+=1;payload=dict(id=f'request-{self.counter}',value=1000+self.counter*7);start=time.perf_counter()
   try:
    result=http(self.port,'/work',payload);status=200;expected=hashlib.sha256(str(payload['value']).encode()).hexdigest()
    ok=(result.get('checksum')==expected) if self.spec['name']=='codec_pipeline' else (result.get('receipts')==[expected,expected] and result.get('acknowledged') is True)
   except Exception as e:result=dict(error=type(e).__name__);status=None;ok=False
   row=dict(label=label,payload=payload,response=result,http_status=status,correct=ok,elapsed_ms=(time.perf_counter()-start)*1000);rows.append(row)
   time.sleep(.001*self.spec['replicate'])
  self.requests.extend(rows)
  with self.runtime.db() as db:after=self.runtime.epoch(db)
  return dict(measured=True,epoch=after,stable_epoch=before==after,requests=n,correct=sum(r['correct'] for r in rows),pass_window=sum(r['correct'] for r in rows)>=n-1)
 def finish(self,report):
  if self.spec['timing']=='finish':self.external()
  windows=[self.measure('terminal-'+str(i),50) for i in range(3)]
  t=self.runtime.finish(report);t['service']=dict(processes=self.metadata,operators=self.operator,requests=self.requests,windows=windows,health=all(w['pass_window'] for w in windows));return t
 def close(self):
  for p,log in reversed(self.children):
   if p.poll()is None:
    p.terminate()
    try:p.wait(timeout=3)
    except subprocess.TimeoutExpired:p.kill();p.wait()
   if p.stdout:p.stdout.close()
   log.close()
 def __enter__(self):return self
 def __exit__(self,*a):self.close()

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--role');p.add_argument('--db');p.add_argument('--store');p.add_argument('--name');p.add_argument('--ports',nargs='*',type=int);p.add_argument('--lingering',action='store_true');p.add_argument('--operator',action='store_true');p.add_argument('--spec');args=p.parse_args()
 if args.operator:
  from runtime import Runtime
  Runtime(json.loads(Path(args.spec).read_text()),args.db,create=False).external();print(json.dumps(dict(pid=os.getpid(),completed=True)))
 else:serve(args)
