import json,pathlib,subprocess,sys,datetime,hashlib
R=pathlib.Path(__file__).resolve().parent
p=subprocess.run([sys.executable,'-m','unittest','-v','test_classify','test_requests_a1','test_main'],cwd=R,capture_output=True,text=True)
record=dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),passed=p.returncode==0,exit=p.returncode,stdout=p.stdout,stderr=p.stderr,implementation_commit='0ff095f2db1bdf45e6c4b003c0714658fd623f88',execution_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip(),source_hashes={x.name:hashlib.sha256(x.read_bytes()).hexdigest() for x in R.glob('*.py')})
with (R/'results/tests-main.json').open('x') as f:json.dump(record,f,indent=2)
print(p.stdout+p.stderr);sys.exit(p.returncode)
