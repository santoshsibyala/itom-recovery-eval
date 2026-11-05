import json,pathlib,subprocess,sys,datetime
R=pathlib.Path(__file__).resolve().parent
p=subprocess.run([sys.executable,'-m','unittest','-v','test_classify'],cwd=R,capture_output=True,text=True)
print(p.stdout+p.stderr)
with (R/'results/tests.json').open('x') as f:json.dump(dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),passed=p.returncode==0,exit=p.returncode,stdout=p.stdout,stderr=p.stderr,implementation_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip()),f,indent=2)
sys.exit(p.returncode)
