"""Repair only the retained run's post-measurement namespace cleanup."""
import subprocess
from common import *
rp=ROOT/'results/main/itom-k8s-llm1103-main-001.json';r=json.loads(rp.read_text());ns=r['namespace']
assert ns=='itom-k8s-llm1103-main-001' and r['completed'] and r['window_complete']
assert len(r['errors'])==1 and r['errors'][0]['kind']=='cleanup' and r['errors'][0]['type']=='NameError'
jp=ROOT/'results/journals'/(ns+'.jsonl');assert sha(jp)==r['journal_sha256'];commands=[]
k=[str(OLD/'.tools/kubectl'),'--kubeconfig',str(OLD/'.kubeconfig'),'--context','kind-itom-k8s-validation']
def cmd(args):
 p=subprocess.run(args,text=True,capture_output=True,timeout=65);commands.append({'argv':args,'returncode':p.returncode,'stdout':p.stdout,'stderr':p.stderr});return p
p=cmd(k+['get','namespace',ns,'-o','json']);assert p.returncode==0
obj=json.loads(p.stdout);assert obj['metadata']['labels']['itom-experiment']=='itom-k8s-validation'
p=cmd(k+['delete','namespace',ns,'--grace-period=0','--wait=true','--timeout=60s']);assert p.returncode==0
p=cmd(k+['get','namespace',ns,'--ignore-not-found','-o','name']);assert p.returncode==0 and not p.stdout.strip()
save(ROOT/'results/cleanup-addenda'/(ns+'.json'),{'utc':utc(),'cleanup_verified':True,'raw_sha256':sha(rp),'journal_sha256':sha(jp),'reason':'Post-measurement wrapper NameError: missing CLUSTER binding. Original run, outcomes and error retained without replay.','commands':commands})
print('Retained run namespace cleaned. Original raw record and journal unchanged.')
