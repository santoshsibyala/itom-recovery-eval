"""Read-only environment checks; never generates model tokens."""
import sys,subprocess,shutil,json,platform
from common import *
from agent import transport
from main_b_execution import main_gate,verify_frozen

def check():
 main_gate();verify_frozen();prov=bindings();calls=[]
 def cmd(args):
  p=subprocess.run(args,text=True,capture_output=True,timeout=35);calls.append(dict(argv=args,exit=p.returncode,stdout=p.stdout,stderr=p.stderr));assert p.returncode==0,p.stderr;return p.stdout
 assert (3,11)<=sys.version_info[:2]<=(3,13)
 assert Path(sys.prefix).resolve()==(ROOT/'.venv').resolve()
 assert shutil.disk_usage(ROOT).free>5*1024**3
 env=json.loads((OLD/'results/env.json').read_text())
 for n,h in env['tools_sha256'].items():assert sha(OLD/'.tools'/n)==h,n
 k=[str(OLD/'.tools/kubectl'),'--kubeconfig',str(OLD/'.kubeconfig'),'--context','kind-itom-k8s-validation']
 v=json.loads(cmd(k+['version','-o','json']));assert v['serverVersion']['gitVersion']==v['clientVersion']['gitVersion']=='v1.34.0'
 ns=json.loads(cmd(k+['get','namespaces','-l','itom-experiment=itom-k8s-validation','-o','json']));assert not ns['items'],'existing experimental namespace; do not overwrite'
 images=json.loads((OLD/'results/images.json').read_text())
 for tag,saved in images.items():
  current=json.loads(cmd(['docker','--context','orbstack','image','inspect',tag]))[0]
  assert all(current[k]==v for k,v in saved.items()),tag
 node=json.loads(cmd(['docker','--context','orbstack','exec','itom-k8s-validation-control-plane','crictl','images','-o','json']))
 original=json.loads((OLD/'results/node-images.json').read_text())
 for tag in ['docker.io/hashicorp/http-echo:1.0.0','docker.io/curlimages/curl:8.16.0']:
  a=next(i for i in original['images'] if tag in i['repoTags']);b=next(i for i in node['images'] if tag in i['repoTags']);assert a['id']==b['id'] and a['repoDigests']==b['repoDigests']
 assert 'itom-k8s-absent-20261101' not in json.dumps(node)
 installed=cmd([sys.executable,'-m','pip','freeze']).strip();assert installed==(ROOT/'requirements.lock').read_text().strip()
 access=transport();assert access.get('http_status')==200 and access['body']['id']==MODEL,access
 report=dict(passed=True,utc=utc(),python=sys.version,python_executable=sys.executable,platform=platform.platform(),commands=calls,model_access={'http_status':200,'id':MODEL},pricing=json.loads((ROOT/'PRICING.json').read_text()),dependency_lock_sha256=sha(ROOT/'requirements.lock'),**prov)
 save(ROOT/'results/main-b-preflight.json',report);print('Preflight passed: pinned tools/images, empty experimental namespaces, model access; no generated tokens.')
if __name__=='__main__':check()
