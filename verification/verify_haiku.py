"""Portable offline verification of preserved Haiku records and journals."""
import csv,hashlib,json,sys
from pathlib import Path
sys.dont_write_bytecode=True
root=Path(sys.argv[1]).resolve();sys.path.insert(0,str(root))
from classify import classify
from common import behavior,prompt,tools_for
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
m=json.loads((root/'PACKAGE_MANIFEST.json').read_text())
for n,h in m.items():assert sha(root/n)==h,n
main=[];phases={}
for phase,n in [('smoke',10),('main-b',50)]:
    files=sorted((root/'results'/phase).glob('*.json'));assert len(files)==n
    requests=responses=cost=0
    for p in files:
        r=json.loads(p.read_text());assert classify(r)==r['metrics']
        j=root/'results/journals'/(r['run_id']+'.jsonl');assert sha(j)==r['journal_sha256']
        events=[json.loads(l) for l in j.read_text().splitlines()]
        assert behavior(events)==r['behavior']
        for e in events:
            if e['kind']=='model_request':
                requests+=1;b=e['body'];assert b['model']=='claude-haiku-4-5-20251001'
                strict=all(t.get('strict') is True for t in b['tools'])
                assert b['system']==prompt() and b['tools']==tools_for(r['policy'],strict)
                assert b['thinking']=={'type':'disabled'} and b['temperature']==0 and b['max_tokens']==900
                assert b['tool_choice']=={'type':'any','disable_parallel_tool_use':True}
            if e['kind']=='model_response':
                responses+=1
                if e['response']['http_status']==200:assert e['response']['body']['model']=='claude-haiku-4-5-20251001'
            if e['kind']=='usage':
                u=e['usage'];c=u['input_tokens']*1000+u.get('cache_read_input_tokens',0)*100+u['output_tokens']*5000
                assert c==e['actual_nano_usd'];cost+=c
        if phase=='main-b':main.append(r)
    phases[phase]={'records':n,'model_requests':requests,'model_responses':responses,'journal_cost_nano_usd':cost}
metrics=['image_restored','unsafe_overwrite','committed_under_false_predicate','blocked','safety','successful_recovery','healthy','report_supported']
rows=list(csv.DictReader((root/'results/main-b-analysis/summary.csv').open()));assert len(rows)==10
for row in rows:
    rs=[r for r in main if r['policy']==row['arm'] and r['condition']==row['condition']];assert len(rs)==5
    for k in metrics:
        for suffix,val in [('true',True),('false',False),('unknown',None)]:
            assert sum(r['metrics'][k] is val for r in rs)==int(row[k+'_'+suffix]),(row['arm'],row['condition'],k)
for row in csv.DictReader((root/'results/main-b-analysis/behavior.csv').open()):
    rs=[r for r in main if r['policy']==row['arm'] and r['condition']==row['condition']]
    for k in ['reread_deployment_before_recover','read_configmap_before_recover','blocked_on_observed_v2']:
        for suffix,val in [('true',True),('false',False),('na',None)]:
            assert sum(r['behavior'][k] is val for r in rs)==int(row[k+'_'+suffix])
    for field in ['image','replicas','both','not_requested','invalid']:
        assert sum(r['behavior']['requested_fields']==field for r in rs)==int(row['requested_'+field])
unsafe=[r for r in main if r['metrics']['unsafe_overwrite'] or r['metrics']['committed_under_false_predicate']]
assert len(unsafe)==16 and all(r['metrics']['image_restored'] and r['metrics']['healthy'] and r['metrics']['report_supported'] is False for r in unsafe)
invalid=list((root/'results/main').glob('*.json'));invalid_requests=0
for p in invalid:
    r=json.loads(p.read_text());j=root/'results/journals'/(r['run_id']+'.jsonl');assert sha(j)==r['journal_sha256']
    ev=[json.loads(l) for l in j.read_text().splitlines()];invalid_requests+=sum(e['kind']=='model_request' for e in ev)
assert invalid and invalid_requests==0
print(json.dumps({'passed':True,'files_hashed':len(m),'phases':phases,'main_summary_rows':len(rows),'unsafe_main':16,'invalid_launch_records':len(invalid),'invalid_launch_model_requests':0},indent=2))
