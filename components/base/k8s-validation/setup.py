"""Idempotent installation verification; refuses an existing cluster during first setup."""
import datetime,hashlib,json,os,pathlib,platform,subprocess,sys
R=pathlib.Path(__file__).resolve().parent
LOG=R/'results/setup-install/commands.jsonl';LOG.parent.mkdir(parents=True,exist_ok=True)
def cmd(args,timeout=300):
    p=subprocess.run(args,text=True,capture_output=True,timeout=timeout,env={**os.environ,'DOCKER_CONTEXT':'orbstack','KIND_EXPERIMENTAL_PROVIDER':'docker'})
    with LOG.open('a') as f:f.write(json.dumps(dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),argv=args,stdout=p.stdout,stderr=p.stderr,exit=p.returncode))+'\n')
    if p.returncode:raise RuntimeError(f'{args}: {p.stderr}')
    return p.stdout

def save(p,obj):
    with (R/p).open('x') as f:json.dump(obj,f,indent=2);f.write('\n')
assert (3,11)<=sys.version_info[:2]<=(3,13)
assert hashlib.sha256((R/'.tools/kubectl').read_bytes()).hexdigest()==(R/'.tools/kubectl.sha256').read_text().strip()
kind=str(R/'.tools/kind');kubectl=str(R/'.tools/kubectl');kc=str(R/'.kubeconfig')
assert 'v0.30.0' in cmd([kind,'version'])
images={}
for tag in ['hashicorp/http-echo:1.0.0','curlimages/curl:8.16.0','kindest/node:v1.34.0@sha256:7416a61b42b1662ca6ca89f02028ac133a309a2a30ba309614e8ec94d976dc5a']:
    obj=json.loads(cmd(['docker','--context','orbstack','image','inspect',tag]))[0]
    assert obj['Architecture']=='arm64';assert obj['RepoDigests']
    images[tag]={k:obj[k] for k in ['Id','RepoDigests','Architecture','Os']}
if (R/'results/images.json').exists():
    assert json.loads((R/'results/images.json').read_text())==images
else: save('results/images.json',images)
existing=cmd([kind,'get','clusters']).splitlines()
if 'itom-k8s-validation' in existing:
    assert '--resume-install' in sys.argv and pathlib.Path(kc).exists(), 'existing cluster requires explicit setup resume'
    assert cmd([kubectl,'--kubeconfig',kc,'config','current-context']).strip()=='kind-itom-k8s-validation'
else: cmd([kind,'create','cluster','--name','itom-k8s-validation','--image','kindest/node:v1.34.0@sha256:7416a61b42b1662ca6ca89f02028ac133a309a2a30ba309614e8ec94d976dc5a','--kubeconfig',kc,'--wait','300s'],timeout=360)
for i,tag in enumerate(['hashicorp/http-echo:1.0.0','curlimages/curl:8.16.0']):
    archive=str(R/'.tools'/f'image-arm64-{i}.tar')
    cmd(['docker','--context','orbstack','image','save','--platform','linux/arm64','-o',archive,tag])
    cmd([kind,'load','image-archive',archive,'--name','itom-k8s-validation'])
nodeimages=cmd(['docker','--context','orbstack','exec','itom-k8s-validation-control-plane','crictl','images','-o','json'])
assert 'itom-k8s-absent-20261101' not in nodeimages
save('results/node-images.json',json.loads(nodeimages))
versions=json.loads(cmd([kubectl,'--kubeconfig',kc,'--context','kind-itom-k8s-validation','version','-o','json']))
assert versions['serverVersion']['gitVersion']=='v1.34.0'
env=dict(recorded_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),python=sys.version,python_executable=sys.executable,python_base_prefix=sys.base_prefix,platform=platform.platform(),architecture=platform.machine(),host_resources=cmd(['sysctl','hw.memsize','hw.ncpu']),docker=json.loads(cmd(['docker','--context','orbstack','version','--format','{{json .}}'])),docker_resources=cmd(['docker','--context','orbstack','info','--format','{{.NCPU}} CPUs; {{.MemTotal}} memory bytes; {{.Architecture}}']),kind=cmd([kind,'version']).strip(),kubernetes_versions=versions,client_version=cmd([sys.executable,'-c','import kubernetes; print(kubernetes.__version__)']).strip(),tools_sha256={name:hashlib.sha256((R/'.tools'/name).read_bytes()).hexdigest() for name in ['kind','kubectl']},dependencies=cmd([sys.executable,'-m','pip','freeze']).splitlines(),images=images,protocol_commit='caa6966197d7733fc69b0374155dd053262f076f',protocol_hashes={name:hashlib.sha256((R/name).read_bytes()).hexdigest() for name in ['K8S_PROTOCOL.md','PROTOCOL_DETAILS.md']})
save('results/env.json',env)
print(json.dumps(dict(setup='complete',python=sys.version,images=images),indent=2))
