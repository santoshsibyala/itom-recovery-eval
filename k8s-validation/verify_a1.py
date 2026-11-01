"""Record offline classifier and focused request tests in a separate A1 artifact."""
import json,pathlib,subprocess,sys,datetime,hashlib
R=pathlib.Path(__file__).resolve().parent
approval=json.loads((R/'A1_APPROVAL.json').read_text());p=subprocess.run([sys.executable,'-m','unittest','-v','test_classify','test_requests_a1'],cwd=R,capture_output=True,text=True)
record=dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),passed=p.returncode==0,exit=p.returncode,stdout=p.stdout,stderr=p.stderr,implementation_commit=approval['implementation_commit'],execution_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip(),source_hashes={x.name:hashlib.sha256(x.read_bytes()).hexdigest() for x in R.glob('*.py')})
with (R/'results/tests-A1.json').open('x') as f:json.dump(record,f,indent=2)
print(p.stdout+p.stderr);sys.exit(p.returncode)
