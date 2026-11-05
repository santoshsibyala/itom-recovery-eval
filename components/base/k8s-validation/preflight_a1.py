"""Read-only preflight: preserve old evidence and reuse the pinned environment."""
import pathlib,json,hashlib,subprocess,sys,datetime
from run import provenance,exclusive,ROOT,KUBECTL,KUBE,CTX
prov=provenance();calls=[]
def command(args):
 p=subprocess.run(args,cwd=ROOT,text=True,capture_output=True,timeout=30);calls.append(dict(argv=args,exit=p.returncode,stdout=p.stdout,stderr=p.stderr));assert p.returncode==0,p.stderr;return p.stdout
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
old=json.loads((ROOT/'results/smoke-review/HANDOFF_MANIFEST.json').read_text())
for p,h in old['files'].items():assert sha(ROOT/p)==h,p
assert len(list((ROOT/'results/smoke').glob('*.json')))==20
assert not list((ROOT/'results/raw').glob('*.json'))
env=json.loads((ROOT/'results/env.json').read_text());assert sys.version==env['python'];assert sys.executable==env['python_executable']
assert command([sys.executable,'-m','pip','freeze']).strip()==(ROOT/'requirements.lock').read_text().strip()
for name,h in env['tools_sha256'].items():assert sha(ROOT/'.tools'/name)==h
version=json.loads(command([KUBECTL,'--kubeconfig',str(KUBE),'--context',CTX,'version','-o','json']));assert version['serverVersion']['gitVersion']=='v1.34.0' and version['clientVersion']['gitVersion']=='v1.34.0'
ns=json.loads(command([KUBECTL,'--kubeconfig',str(KUBE),'--context',CTX,'get','namespaces','-l','itom-experiment=itom-k8s-validation','-o','json']));assert not ns['items'],'experimental namespace already present'
images=json.loads((ROOT/'results/images.json').read_text())
for tag,saved in images.items():
 current=json.loads(command(['docker','--context','orbstack','image','inspect',tag]))[0]
 assert all(current[k]==v for k,v in saved.items()),tag
node=json.loads(command(['docker','--context','orbstack','exec','itom-k8s-validation-control-plane','crictl','images','-o','json']))
original=json.loads((ROOT/'results/node-images.json').read_text())
for tag in ['docker.io/hashicorp/http-echo:1.0.0','docker.io/curlimages/curl:8.16.0']:
 a=next(i for i in original['images'] if tag in i['repoTags']);b=next(i for i in node['images'] if tag in i['repoTags']);assert a['id']==b['id'] and a['repoDigests']==b['repoDigests']
assert 'itom-k8s-absent-20261101' not in json.dumps(node)
record=dict(passed=True,utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),**prov,verified_original_files=len(old['files']),commands=calls,pinned_images_unchanged=True,no_experimental_namespaces=True,no_main_records=True)
exclusive(ROOT/'results/preflight-A1.json',record);print('A1 read-only preflight passed; original evidence and pinned environment verified.')
