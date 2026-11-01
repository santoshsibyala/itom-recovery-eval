"""Read-only smoke aggregation; never produces or pools main-study results."""
import collections,csv,hashlib,io,json,pathlib,sys
R=pathlib.Path(__file__).resolve().parent
session=sys.argv[1];schedule=R/'results'/f'{session}-smoke-schedule.json';s=json.loads(schedule.read_text());records=[]
for i,cell in enumerate(s['cells'],1):
    p=R/'results/smoke'/f'itom-k8s-{session}-smoke-{i:03d}.json'
    if p.exists():
        r=json.loads(p.read_text());assert (r['policy'],r['condition'])==(cell['policy'],cell['condition']);assert r['schedule_sha256']==hashlib.sha256(schedule.read_bytes()).hexdigest();records.append((p,r))
keys=['safety','successful_recovery','operator_preserved','healthy','blocked','unsafe_overwrite','committed_under_false_predicate','report_supported']
rows=[]
for cell in s['cells']:
    selected=[r for p,r in records if r['policy']==cell['policy'] and r['condition']==cell['condition']]
    row={**cell,'planned':1,'attempted':len(selected),'completed':sum(r.get('completed') is True for r in selected),'valid_fixture':sum(r.get('fixture_valid') is True for r in selected),'errors':sum(len(r.get('errors',[])) for r in selected)}
    for k in keys:
        for label,value in [('true',True),('false',False),('unknown',None),('na','N/A')]:row[k+'_'+label]=sum(r.get('metrics',{}).get(k)==value if value=='N/A' else r.get('metrics',{}).get(k) is value for r in selected)
    rows.append(row)
out=R/'results/smoke-review';out.mkdir(exist_ok=False)
with (out/'summary.csv').open('x',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
lines=['# Smoke review — not main-study results','',f'Completed records: {len(records)}/20. Complete execution: {sum(r.get("completed") is True for _,r in records)}. Valid fixtures: {sum(r.get("fixture_valid") is True for _,r in records)}.','', '| Policy | Condition | Safe | Recovery | Preserved | Healthy | Blocked | Report supported | Errors |','|---|---|---|---|---|---|---|---|---|']
def show(x):return 'unknown' if x is None else 'yes' if x is True else 'no' if x is False else str(x)
for p,r in records:
    m=r.get('metrics',{});lines.append('| '+' | '.join([r['policy'],r['condition']]+[show(m.get(k)) for k in ['safety','successful_recovery','operator_preserved','healthy','blocked','report_supported']]+[str(len(r.get('errors',[])))])+' |')
lines+=['','## Diagnostics','']
for p,r in records:
    lines.append(f"- {r['policy']}/{r['condition']}: settle={r.get('settle_achieved')}, bad-unhealthy={r.get('bad_unhealthy_confirmed')}, outcome={r.get('mutation_outcome')}, status={r.get('mutation_status','ack/no-dispatch')}, observation={r.get('window_elapsed')} s; errors={json.dumps(r.get('errors',[]))}")
lines+=['','Dependency mode is not consumed at runtime. False-predicate commits measure a declared recovery-contract violation, not observed application harm. Smoke denominators are one per cell. These data do not enter the 200-run main analysis. Main has not been started.','']
(out/'REPORT.md').write_text('\n'.join(lines))
files=[schedule,R/'results/env.json',R/'results/images.json',R/'requirements.lock',R/'results/tests.json',*[p for p,r in records],out/'summary.csv',out/'REPORT.md']
manifest={str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
(out/'PROVENANCE.json').write_text(json.dumps(dict(files=manifest,protocol_commit=s['protocol_commit'],implementation_commit=s['implementation_commit'],protocol_hashes=s['protocol_hashes']),indent=2)+'\n')
print('\n'.join(lines[:27]))
