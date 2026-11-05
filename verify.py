#!/usr/bin/env python3
"""Verify this extracted artifact offline; write only temporary replay files."""
import hashlib,json,os,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.dont_write_bytecode=True
if sys.flags.optimize:raise SystemExit('Run without -O or PYTHONOPTIMIZE; preserved verifiers use assertions.')
sys.path.insert(0,str(ROOT/'verification/guard'))
import sitecustomize

def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def inventory():
    actual={}
    for p in ROOT.rglob('*'):
        if '.git' in p.relative_to(ROOT).parts:continue
        if p.is_symlink():raise RuntimeError('Symlink in artifact: '+str(p.relative_to(ROOT)))
        if p.is_file() and p!=ROOT/'ARTIFACT_MANIFEST.json':actual[str(p.relative_to(ROOT))]=digest(p)
    return actual

def main():
    expected=json.loads((ROOT/'ARTIFACT_MANIFEST.json').read_text())['files']
    before=inventory()
    if before!=expected:
        mismatches=sorted(k for k in set(before)|set(expected) if before.get(k)!=expected.get(k))
        raise RuntimeError('Artifact integrity mismatch: '+', '.join(mismatches[:20]))
    env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONPATH=str(ROOT/'verification/guard'))
    for key in list(env):
        if key.upper().endswith(('API_KEY','ACCESS_TOKEN','AUTH_TOKEN')):env.pop(key)
    tasks=[('base_replay',ROOT/'components/base/verify_public.py',['--replay']),('gpt_k8s',ROOT/'components/gpt_k8s/verify_extension.py',[]),('haiku_k8s',ROOT/'verification/verify_haiku.py',[str(ROOT/'components/haiku_k8s')])]
    result={'passed':True,'artifact_files_hashed':len(expected),'network_guard':True,'checks':{}}
    for name,script,args in tasks:
        print('Checking '+name+' ...',file=sys.stderr,flush=True)
        p=subprocess.run([sys.executable,'-B','-s',str(script),*args],cwd=ROOT,env=env,capture_output=True,text=True)
        if p.returncode:raise RuntimeError(name+' failed:\n'+p.stdout+p.stderr)
        result['checks'][name]=json.loads(p.stdout)
    if inventory()!=before:raise RuntimeError('Verification modified the artifact')
    result['artifact_unchanged_after_verification']=True
    print(json.dumps(result,indent=2))
if __name__=='__main__':main()
