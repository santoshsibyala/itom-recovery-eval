"""Offline release validation. No model, network, Docker or Kubernetes calls."""
import argparse,collections,csv,hashlib,importlib.util,json,os,pathlib,subprocess,sys
sys.dont_write_bytecode=True
ROOT=pathlib.Path(__file__).resolve().parent

def load(path):return json.loads((ROOT/path).read_text())
def phase_initial():
 sys.path.insert(0,str(ROOT/'heldout_v03'))
 from recovery.replay import verify
 from analysis.results import service_verify
 counts={}
 for folder,pattern,n,fn in [('study/heldout','*.trace.json',216,verify),('study/baselines','*.json',108,verify),('study/calibration','*.trace.json',3,verify),('service_study/models','*.trace.json',42,service_verify),('service_study/baselines','*.trace.json',63,service_verify)]:
  paths=sorted((ROOT/'heldout_v03'/folder).glob(pattern));assert len(paths)==n,(folder,len(paths),n)
  for p in paths:fn(json.loads(p.read_text()))
  counts[folder]=len(paths)
 return counts

def phase_followup():
 sys.path.insert(0,str(ROOT/'followup_v05'))
 from verify import verify
 from scoring import grade
 cohorts=[('models','*.trace.json',288),('calibration','*.trace.json',3),('native','*.trace.json',72),('native_calibration','*.trace.json',3),('functions','*.trace.json',36),('function_calibration','*.trace.json',3),('offline_controls','*.json',576),('service_controls','*.json',144),('report/rac_offline','*.json',192),('report/rac_service','*.json',32),('report/rac_ordered_offline','*.json',192),('report/rac_ordered_service','*.json',32),('report/evidence_specificity','case-*.json',24)]
 counts={}
 for folder,pattern,n in cohorts:
  paths=sorted((ROOT/'followup_v05'/folder).glob(pattern));assert len(paths)==n,(folder,len(paths),n)
  for p in paths:
   t=json.loads(p.read_text())
   if folder=='calibration':t=dict(t,grade=grade(t))
   verify(t)
  counts[folder]=len(paths)
 return counts

def k8s():
 p=ROOT/'k8s-validation';spec=importlib.util.spec_from_file_location('released_k8s_classifier',p/'classify.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
 files=sorted((p/'results/raw').glob('*.json'));assert len(files)==200
 records=[json.loads(f.read_text()) for f in files]
 for r in records:assert mod.classify(r)==r['metrics'];assert r['completed'] and r['fixture_valid']
 rows=list(csv.DictReader((p/'results/main-analysis/summary.csv').open()));assert len(rows)==20
 metrics=['image_restored','operator_preserved','unsafe_overwrite','committed_under_false_predicate','blocked','healthy','safety','successful_recovery','report_supported']
 for row in rows:
  rs=[r for r in records if r['policy']==row['policy'] and r['condition']==row['condition']];assert len(rs)==10
  computed=dict(planned=10,attempted=len(rs),complete=sum(r.get('completed') is True for r in rs),valid_fixture=sum(r.get('fixture_valid') is True for r in rs),fixture_failures=sum(r.get('fixture_valid') is False for r in rs),fixture_unknown=sum(r.get('fixture_valid') is None for r in rs),missing=0,interrupted=sum(r.get('interrupted') is True for r in rs),harness_error_runs=sum(any(e.get('kind')!='fixture' for e in r.get('errors',[])) for r in rs),error_events=sum(len(r.get('errors',[])) for r in rs))
  for metric in metrics:
   vals=[r['metrics'].get(metric) for r in rs]
   for label,val in [('true',True),('false',False),('unknown',None),('na','N/A')]:computed[metric+'_'+label]=sum(x==val if val=='N/A' else x is val for x in vals)
  computed['unsupported_reports']=computed['report_supported_false'];computed['unassessable_attempted_reports']=computed['report_supported_unknown']
  assert set(computed)==set(row)-{'policy','condition'}
  for key,n in computed.items():assert n==int(row[key]),(row['policy'],row['condition'],key,n,row[key])
 return {'raw_records_reclassified':len(records),'summary_rows_recomputed':len(rows)}

def agreement(matrix):
 n=sum(map(sum,matrix));observed=sum(matrix[i][i] for i in range(len(matrix)))/n
 expected=sum(sum(matrix[i])*sum(row[i] for row in matrix) for i in range(len(matrix)))/(n*n)
 return {'n':n,'agreement':observed,'kappa':(observed-expected)/(1-expected)}

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--replay',action='store_true');ap.add_argument('--phase',choices=['initial','followup']);a=ap.parse_args()
 if a.phase:print(json.dumps(phase_initial() if a.phase=='initial' else phase_followup()));return
 manifest=load('PUBLIC_MANIFEST.json');expected=manifest['files'];actual={str(p.relative_to(ROOT)) for p in ROOT.rglob('*') if p.is_file() and p.name!='PUBLIC_MANIFEST.json' and '__pycache__' not in p.parts and '.git' not in p.relative_to(ROOT).parts};assert actual==set(expected),'Release file inventory mismatch'
 for rel,h in expected.items():assert hashlib.sha256((ROOT/rel).read_bytes()).hexdigest()==h,rel
 result={'release_files_verified':len(expected),'kubernetes':k8s()}
 m=load('human_review/aggregate_results.json')['independent_confusion_matrix'];full=agreement(m);sensitivity=agreement([row[1:] for row in m[1:]]);assert full['n']==32 and round(full['kappa'],2)==.95;assert sensitivity['n']==18 and round(sensitivity['kappa'],2)==.88
 result['aggregate_human_review']={'full':full,'assessable_only':sensitivity}
 services=load('followup_v05/analysis_final/results.json')['service_controls'];assert {r['arm']:r['n']-r['history_safe'] for r in services}=={'atomic_guard':0,'field':6,'owner_guard':6};assert all(r['n']==48 and r['configuration']==21 for r in services)
 result['headline_verified']=True
 counts=load('supplement/SOURCE_VERIFICATION.json')['offline_condition_computations']
 for name,c in counts.items():
  records=[]
  for rec in c['records']:
   f=ROOT/rec['file'];assert hashlib.sha256(f.read_bytes()).hexdigest()==rec['sha256'];records.append(json.loads(f.read_text()))
  assert len(records)==c['denominator'];assert sum(not r['grade']['history_safe'] for r in records)==c['history_violations']
  if name=='cas_disjoint':assert all(not r['grade']['configuration'] and r['grade']['history_safe'] and any(o['tool']=='apply_patch' and o['reply'].get('result',{}).get('reason')=='version_conflict' for o in r['public']) for r in records)
 result['offline_condition_comparisons_verified']=3
 if a.replay:
  env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1');result['replay']={}
  for phase in ('initial','followup'):
   proc=subprocess.run([sys.executable,str(pathlib.Path(__file__).resolve()),'--phase',phase],check=True,capture_output=True,text=True,env=env)
   result['replay'][phase]=json.loads(proc.stdout)
 print(json.dumps(result,indent=2))
if __name__=='__main__':main()
