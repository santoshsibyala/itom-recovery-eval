"""Separate OS processes for a proxy/control plane and two request-processing backends."""
import argparse,hashlib,json,threading,time,os
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer,BaseHTTPRequestHandler
from recovery.environment import Environment

def http(port,path,body=None):
 c=HTTPConnection('127.0.0.1',port,timeout=3)
 try:
  c.request('POST' if body is not None else 'GET',path,json.dumps(body) if body is not None else None,{'Content-Type':'application/json'});r=c.getresponse();return r.status,json.loads(r.read())
 finally:c.close()
def serve(a):
 lock=threading.RLock();settings={'enabled':True,'corrupt':a.name=='green'};env=None
 if a.role=='proxy':
  with open(a.spec) as f:env=Environment(json.load(f))
 ports={'blue':a.blue,'green':a.green};observed_requests=[]
 class Handler(BaseHTTPRequestHandler):
  def log_message(self,*args):pass
  def send(self,status,value):
   b=json.dumps(value).encode();self.send_response(status);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(b)));self.end_headers();self.wfile.write(b)
  def do_GET(self):
   if self.path.startswith('/work/'):
    payload=self.path[len('/work/'):]
    if a.role=='backend':
     with lock:s=dict(settings)
     if not s['enabled']:return self.send(503,{'error':'backend disabled','pid':os.getpid()})
     checksum=hashlib.sha256(payload.encode()).hexdigest()
     return self.send(200,dict(checksum='corrupt' if s['corrupt'] else checksum,backend=a.name,pid=os.getpid()))
    with lock:dest=env.state['route']['values']['destination']
    if dest not in ports:return self.send(503,{'error':'unconfigured backend'})
    try:status,reply=http(ports[dest],self.path)
    except Exception:return self.send(502,{'error':'backend transport failure'})
    return self.send(status,reply)
   if self.path=='/task' and env is not None:return self.send(200,env.task)
   return self.send(404,{'error':'not found'})
  def do_POST(self):
   try:
    data=json.loads(self.rfile.read(int(self.headers.get('Content-Length','0'))))
    if self.path=='/configure' and a.role=='backend':
     with lock:settings.update(data)
     return self.send(200,{'configured':True,'pid':os.getpid()})
    if self.path=='/operator' and env is not None:
     # This endpoint is called by a different OS process at the frozen barrier.
     with lock:
      env.external();status,reply=http(a.blue,'/configure',{'enabled':False})
      return self.send(200,dict(operator_applied=True,backend_response=reply,status=status,proxy_pid=os.getpid()))
    if self.path=='/invoke' and env is not None:
     with lock:o=env.invoke(data['tool'],**data['arguments'])
     return self.send(200,o)
    if self.path=='/finish' and env is not None:
     with lock:t=env.finish(data['report'])
     return self.send(200,t)
    return self.send(404,{'error':'not found'})
   except Exception as ex:self.send(500,{'error':type(ex).__name__})
 server=ThreadingHTTPServer(('127.0.0.1',0),Handler);print(json.dumps(dict(port=server.server_address[1],pid=os.getpid(),role=a.role)),flush=True)
 server.serve_forever(poll_interval=0.05)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--role',choices=['backend','proxy'],required=True);p.add_argument('--name',default='blue');p.add_argument('--spec');p.add_argument('--blue',type=int);p.add_argument('--green',type=int);serve(p.parse_args())
