import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def canonical(x):return json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False)
def digest(x):return hashlib.sha256(canonical(x).encode()).hexdigest()
def require(ok,msg):
 if not ok:raise ValueError(msg)
def save(p,x):
 with Path(p).open('x') as f:json.dump(x,f,indent=2);f.write('\n')
