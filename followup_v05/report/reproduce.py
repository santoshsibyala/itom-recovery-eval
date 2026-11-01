"""Offline verification after extraction; no provider requests and no IAM requirement."""
import hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from verify import verify
from scoring import grade
from analyze import accounting
def main():
 m=json.loads((ROOT/'manifest_main.json').read_text())
 assert all(hashlib.sha256((ROOT/k).read_bytes()).hexdigest()==h for k,h in m['source_hashes'].items())
 native=json.loads((ROOT/'native_protocol/manifest_main.json').read_text())
 assert hashlib.sha256((ROOT/'native_protocol/run.py').read_bytes()).hexdigest()==native['source_sha256']
 fm=json.loads((ROOT/'function_protocol/manifest.json').read_text());assert hashlib.sha256((ROOT/'function_protocol/run.py').read_bytes()).hexdigest()==fm['source_sha256']
 for protocol,script in [('rac_protocol.json','rac_integration.py'),('rac_ordered_protocol.json','rac_ordered_integration.py')]:
  rm=json.loads((ROOT/'report'/protocol).read_text());assert hashlib.sha256((ROOT/'report'/script).read_bytes()).hexdigest()==rm['adapter_sha256']
  upstream=ROOT/'report/rac_external'/('research-rac-'+rm['tree'])
  assert all(hashlib.sha256((upstream/k).read_bytes()).hexdigest()==v for k,v in rm['source_hashes'].items())
 counts={}
 for folder,glob in [('report/rac_ordered_offline','*.json'),('report/rac_ordered_service','*.json'),('functions','*.trace.json'),('function_calibration','*.trace.json'),('models','*.trace.json'),('native','*.trace.json'),('calibration','*.trace.json'),('native_calibration','*.trace.json'),('offline_controls','*.json'),('service_controls','*.json'),('report/rac_offline','*.json'),('report/rac_service','*.json'),('report/evidence_specificity','case-*.json')]:
  files=list((ROOT/folder).glob(glob));counts[folder]=len(files)
  for p in files:
   t=json.loads(p.read_text())
   if folder=='calibration':t=dict(t,grade=grade(t)) # Initial-score records remain preserved; amended scoring diagnostic only.
   verify(t)
 expected={'report/rac_ordered_offline':192,'report/rac_ordered_service':32,'functions':36,'function_calibration':3,'models':288,'native':72,'calibration':3,'native_calibration':3,'offline_controls':576,'service_controls':144,'report/rac_offline':192,'report/rac_service':32,'report/evidence_specificity':24}
 assert counts==expected,(counts,expected)
 result=dict(verified=counts,budget=accounting(),note='Offline replay, not a fresh runtime/model replication. IAM intentionally absent from public artifact; preservation receipt pertains to author workspace.')
 print(json.dumps(result,indent=2))
if __name__=='__main__':main()
