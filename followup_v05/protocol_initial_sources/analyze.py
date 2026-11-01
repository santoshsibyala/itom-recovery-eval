import argparse,hashlib,json,random,sqlite3,sys
from pathlib import Path
from collections import defaultdict,Counter
from verify import verify
from runtime import digest
HERE=Path(__file__).resolve().parent
METRICS=('configuration','partial','history_safe','health','operational','certified_configuration','certified_operational','unsupported_claim','status_valid','evidence_complete')
def load(p):return json.loads(p.read_text())
def aggregate(ts,keys):
 groups=defaultdict(list)
 for t in ts:
  info=dict(model=t.get('cell',{}).get('model','baseline'),arm=t.get('cell',{}).get('arm',t.get('policy')),name=t['spec']['name'],variant=t['spec']['variant'])
  groups[tuple(info[k] for k in keys)].append(t)
 return [dict(zip(keys,key),n=len(v),errors=sum(bool(t.get('error')) for t in v),**{k:sum(t['grade'][k] for t in v) for k in METRICS}) for key,v in sorted(groups.items())]
def accounting():
 sys.path.insert(0,str(HERE.parent/'prototype_v02'))
 from itom.live import normalize
 journal={}
 for base in (HERE.parent/'prototype_v02/study_v02',HERE.parent/'heldout_v03/study',HERE.parent/'heldout_v03/service_study',HERE):
  for p in base.glob('*/*.request.json'):
   cid=p.name.removesuffix('.request.json');assert cid not in journal;journal[cid]=p
 db=sqlite3.connect('file:'+str(HERE.parent/'prototype_v02/live_state/budget.sqlite3')+'?mode=ro',uri=True)
 try:rows=db.execute('SELECT id,model,reserved,settled,request_hash,response_hash FROM calls').fetchall();cap=db.execute('SELECT cap FROM config').fetchone()[0]
 finally:db.close()
 assert {r[0] for r in rows}==set(journal)
 settled=pending=0
 for cid,model,reserve,cost,rq,rs in rows:
  p=journal[cid];assert digest(load(p))==rq
  if cost is None:pending+=reserve
  else:
   response=load(p.with_name(cid+'.response.json'));assert digest(response)==rs and normalize(model,response['body'])['cost_nano']==cost<=reserve;settled+=cost
 assert settled+pending<=cap
 return dict(calls=len(rows),settled_upper_usd=settled/1e9,pending_reserved_usd=pending/1e9,total_bound_usd=(settled+pending)/1e9,cap_usd=cap/1e9)
def analyze(output):
 m=load(HERE/'manifest.json');assert all(hashlib.sha256((HERE/k).read_bytes()).hexdigest()==v for k,v in m['source_hashes'].items())
 cohorts={};verification={}
 for name,glob in [('models','*.trace.json'),('calibration','*.trace.json'),('offline_controls','*.json'),('service_controls','*.json')]:
  ts=[load(p) for p in sorted((HERE/name).glob(glob))]
  for t in ts:verify(t)
  cohorts[name]=ts;verification[name]=len(ts)
 schedule={c['id']:c for c in m['schedule']};actual={t['cell']['id']:t for t in cohorts['models']}
 assert set(actual)<=set(schedule)
 for key,t in actual.items():assert t['cell']==schedule[key] and t['spec']==schedule[key]['spec']
 missing=sorted(set(schedule)-set(actual));paired=[];rng=random.Random(2026102706)
 for model in sorted({c['model'] for c in schedule.values()}):
  for metric in ('history_safe','configuration','certified_configuration','certified_operational','unsupported_claim'):
   blocks=defaultdict(dict)
   for t in cohorts['models']:
    if t['cell']['model']==model:blocks[(t['spec']['name'],t['spec']['variant'])][(t['spec']['replicate'],t['cell']['arm'])]=t['grade'][metric]
   if len(blocks)!=16 or any(len(v)!=6 for v in blocks.values()):continue
   ds={str(k):sum(int(v[(r,'atomic')])-int(v[(r,'evidence_only')]) for r in (1,2,3))/3 for k,v in blocks.items()}
   vals=list(ds.values());draws=sorted(sum(rng.choice(vals) for _ in vals)/len(vals) for _ in range(10000))
   paired.append(dict(model=model,metric=metric,difference=sum(vals)/16,interval=[draws[249],draws[9749]],block_differences=ds,warning='Descriptive 16 task-condition blocks from only two author-designed applications; repeated runs do not add application diversity.'))
 ablation=[]
 for t in cohorts['models']:
  g=t['grade'];r=t['report'];claim=r.get('status') if isinstance(r,dict) else None
  base=g['configuration'] and g['status_valid'] and g['effect_claims_consistent'] and claim in ('RECOVERED','OPERATIONAL')
  ablation.append(dict(id=t['cell']['id'],model=t['cell']['model'],arm=t['cell']['arm'],configuration_and_report=bool(base),full_evidence=bool(g['certified_configuration']),evidence_failures=g['evidence_failures']))
 result=dict(design=m['design'],scheduled=len(schedule),missing_ids=missing,verification=verification,
  models=aggregate(cohorts['models'],('model','arm')),by_condition=aggregate(cohorts['models'],('name','variant','arm')),by_replicate=[dict(id=t['cell']['id'],cell=t['cell'],grade=t['grade'],error=t.get('error')) for t in cohorts['models']],
  offline_controls=aggregate(cohorts['offline_controls'],('policy',)) if False else aggregate(cohorts['offline_controls'],('arm',)),
  service_controls=aggregate(cohorts['service_controls'],('arm',)),service_control_conditions=aggregate(cohorts['service_controls'],('name','variant','arm')),
  paired=paired,evidence_ablation=ablation,budget=accounting(),request_count=sum(len(t.get('service',{}).get('requests',[])) for ts in cohorts.values() for t in ts),
  definitions='All sensitivity contrasts concern this new protocol; no pooling with v03. Certified endpoints include authoritative correctness plus the stated evidence contract.')
 output=Path(output);output.mkdir(exist_ok=False);(output/'results.json').write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps({k:result[k] for k in ('scheduled','missing_ids','verification','models','service_controls','budget')},indent=2))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output',required=True);a=p.parse_args();analyze(a.output)
