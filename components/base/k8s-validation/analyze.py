"""Read-only main analysis; fixed denominators, no smoke pooling or raw edits."""
import csv,datetime,hashlib,json,pathlib,subprocess,sys
from main_runner import ROOT,SESSION,POLICIES,CONDITIONS,frozen_schedule,verify_smoke,approval
from run import sha,exclusive
METRICS=['image_restored','operator_preserved','unsafe_overwrite','committed_under_false_predicate','blocked','healthy','safety','successful_recovery','report_supported']
def summarize(cells,records):
    rows=[]
    for p in POLICIES:
        for c in CONDITIONS:
            indices=[i for i,x in enumerate(cells,1) if x['policy']==p and x['condition']==c];rs=[records.get(i) for i in indices];actual=[r for r in rs if r is not None]
            row=dict(policy=p,condition=c,planned=len(indices),attempted=len(actual),complete=sum(r.get('completed') is True for r in actual),valid_fixture=sum(r.get('fixture_valid') is True for r in actual),fixture_failures=sum(r.get('fixture_valid') is False for r in actual),fixture_unknown=sum(r.get('fixture_valid') is None for r in actual),missing=len(indices)-len(actual),interrupted=sum(r.get('interrupted') is True for r in actual),harness_error_runs=sum(any(e.get('kind')!='fixture' for e in r.get('errors',[])) for r in actual),error_events=sum(len(r.get('errors',[])) for r in actual))
            for metric in METRICS:
                values=[r.get('metrics',{}).get(metric) if r else None for r in rs]
                for label,val in [('true',True),('false',False),('unknown',None),('na','N/A')]:row[metric+'_'+label]=sum(x==val if val=='N/A' else x is val for x in values)
            row['unsupported_reports']=row['report_supported_false'];row['unassessable_attempted_reports']=sum(r.get('metrics',{}).get('report_supported') is None for r in actual)
            rows.append(row)
    return rows

def render(rows,smoke_count=20,a1_count=5,end_health_verified=False):
    lookup={(r['policy'],r['condition']):r for r in rows}
    n=lambda p,c,k:lookup[(p,c)][k]
    table=['| Condition | Snapshot | Field compensation | Object CAS | Ownership |','|---|---|---|---|---|']
    for c in CONDITIONS:
        cells=[]
        for p in POLICIES:
            r=lookup[(p,c)];pres='N/A' if c=='clean' else str(r['operator_preserved_true']);cells.append(f"{r['safety_true']}/{r['successful_recovery_true']}/{pres}/{r['healthy_true']}")
        table.append('| '+c+' | '+' | '.join(cells)+' |')
    table_text='\n'.join(table)+'\n\nEach cell is safe / successful recovery / operator preserved / healthy; each numeric count has a fixed denominator of ten. Clean preservation is N/A. Unknowns and errors are retained in summary.csv.\n'
    totals={k:sum(r[k] for r in rows) for k in ['planned','attempted','complete','valid_fixture','missing','interrupted','fixture_failures','harness_error_runs','unsupported_reports','unassessable_attempted_reports']}
    uniform=(len(rows)==len(POLICIES)*len(CONDITIONS) and all(r['planned']==10 and r['complete']==10 and r['valid_fixture']==10 and all(v in (0,10) for k,v in r.items() if k not in ('policy','condition')) and all(r[m+'_unknown']==0 for m in METRICS) for r in rows))
    symbols={}
    for r in rows:
        ncell=r['planned'];matches=[]
        if r['safety_true']==ncell and r['successful_recovery_true']==ncell:matches.append('R')
        if r['unsafe_overwrite_true']==ncell:matches.append('O')
        if r['blocked_true']==ncell:matches.append('B')
        if r['committed_under_false_predicate_true']==ncell:matches.append('F')
        symbols[(r['policy'],r['condition'])]=matches[0] if uniform and len(matches)==1 else '?'
    violation_rows=[r for r in rows if r['unsafe_overwrite_true'] or r['committed_under_false_predicate_true']]
    checks=dict(identical_repetitions=uniform,violations_healthy=uniform and bool(violation_rows) and all(r['healthy_true']==r['planned'] for r in violation_rows),violations_unsupported=uniform and bool(violation_rows) and all(r['report_supported_false']==r['planned'] for r in violation_rows),cas_blocked_unhealthy_ownership_recovered=uniform and all(lookup[('object_cas',c)]['safety_true']==10 and lookup[('object_cas',c)]['blocked_true']==10 and lookup[('object_cas',c)]['healthy_false']==10 and lookup[('ownership',c)]['successful_recovery_true']==10 and lookup[('ownership',c)]['safety_true']==10 for c in ['disjoint','same_field']),late_race_unprevented=uniform and all(lookup[(p,'dep_race_late')]['committed_under_false_predicate_true']==10 for p in POLICIES),end_health_verified=end_health_verified)
    compact=['| Condition | Snapshot | Field comp. | Object CAS | Ownership |','|---|---|---|---|---|']
    for c in CONDITIONS:compact.append('| '+c+' | '+' | '.join(symbols[(p,c)] for p in POLICIES)+' |')
    legend='R = safe successful recovery; O = unsafe overwrite of operator work; B = blocked with no commit; F = commit under false predicate. Full counts remain in table.md and summary.csv.'
    setup=(f"We tested {len({r['policy'] for r in rows})} deterministic recovery policies under {len({r['condition'] for r in rows})} controlled interference conditions on a local Kubernetes cluster, with a Deployment, ConfigMap dependency, and Service probe. All {totals['complete']} scheduled runs completed with valid fixtures.") if uniform else 'Incomplete or nonuniform outcomes require a count-based presentation; the compact claims below are withheld.'
    results=[]
    if checks['identical_repetitions']:results.append('Outcomes were identical across all ten repetitions in every cell.')
    if checks['violations_healthy'] and end_health_verified:results.append('Every run with an unsafe overwrite or false-predicate commit ended healthy.')
    if checks['violations_unsupported']:results.append('Every such run produced an unsupported completion report.')
    if checks['cas_blocked_unhealthy_ownership_recovered']:results.append('In disjoint and same_field, object CAS was safe but blocked, leaving the service unhealthy, whereas ownership recovered safely.')
    if checks['late_race_unprevented']:results.append('No policy prevented the late dependency race.')
    draft='\n\n'.join(['# Preliminary Kubernetes validation — proposed paper insert',setup,'\n'.join(compact),legend,' '.join(results),f"Before main, approved amendment A1 removed snapshot PUTs’ resourceVersion precondition to restore unconditional baseline replacement; the original smoke and separate smoke-A1 cohorts were retained and excluded from main analysis.","Original-smoke version-checked snapshot failures were consistent with controller status updates; exact server-side write timing was not observed.","The application does not consume mode at runtime and no policy writes the ConfigMap, so operator preservation in dep_race and dep_race_late is expected to be trivial; committed_under_false_predicate measures a violation of the declared recovery contract, not observed application harm.","This validation is limited to a local single-node kind cluster, one assessed workload resource type with a ConfigMap dependency, controlled injection points rather than natural races, deterministic policies without an LLM agent, and ten repetitions per cell."])+ '\n'
    assert len(setup.split())<=120
    return table_text,draft,dict(setup_word_count=len(setup.split()),insert_word_count=len(draft.split()),result_sentences=results,totals=totals,computed_checks=checks,symbols={p+'/'+c:v for (p,c),v in symbols.items()})

def paper_only():
    """Editorial regeneration from reviewed CSV; preserve original analysis and raw data."""
    import shutil
    source=ROOT/'results/main-analysis';manifest=json.loads((source/'PROVENANCE_MANIFEST.json').read_text())
    for name,h in manifest['files'].items():
        path=ROOT/name
        if sha(path)==h:continue
        assert name in ('analyze.py','test_main.py'),'unexpected original artifact change: '+name
        data=subprocess.check_output(['git','show',manifest['execution_commit']+':'+name],cwd=ROOT)
        assert hashlib.sha256(data).hexdigest()==h
    # CSV health counts are window-based. Corroborate "ended healthy" using
    # last health samples and final Deployment state, without adding paper counts.
    end_health_verified=True
    for path in (ROOT/'results/raw').glob('*.json'):
        r=json.loads(path.read_text());m=r['metrics']
        if m['unsafe_overwrite'] is True or m['committed_under_false_predicate'] is True:
            d=r['final_deployment'];st=d.get('status',{})
            end_health_verified &= bool(r['health_series'] and r['health_series'][-1]['healthy'] is True and st.get('observedGeneration',0)>=d['metadata']['generation'] and st.get('availableReplicas',0)>=d['spec']['replicas'] and any(c.get('type')=='Available' and c.get('status')=='True' for c in st.get('conditions',[])))
    with (source/'summary.csv').open() as f:rows=[{k:v if k in ('policy','condition') else int(v) for k,v in r.items()} for r in csv.DictReader(f)]
    table,draft,info=render(rows,end_health_verified=end_health_verified)
    assert all(info['computed_checks'].values()),info['computed_checks']
    assert table==(source/'table.md').read_text(),'full-count table must remain unchanged'
    suffix=1
    while (ROOT/f'results/paper-revision-{suffix:03d}').exists():suffix+=1
    out=ROOT/f'results/paper-revision-{suffix:03d}';out.mkdir()
    for name in ['summary.csv','table.md']:shutil.copyfile(source/name,out/name)
    (out/'PAPER_DRAFT.md').write_text(draft);exclusive(out/'analysis_checks.json',info)
    exclusive(out/'PROVENANCE_MANIFEST.json',dict(kind='editorial_regeneration_from_reviewed_summary',source_manifest=str(source.relative_to(ROOT)/'PROVENANCE_MANIFEST.json'),source_manifest_sha256=sha(source/'PROVENANCE_MANIFEST.json'),original_execution_commit=manifest['execution_commit'],renderer_sha256=sha(ROOT/'analyze.py'),raw_modified=False,manuscript_modified=False,files={str(p.relative_to(ROOT)):sha(p) for p in [ROOT/'analyze.py',out/'summary.csv',out/'table.md',out/'PAPER_DRAFT.md',out/'analysis_checks.json']}))
    print(str(out/'PAPER_DRAFT.md'));print(json.dumps(info,indent=2));print(draft)

def main():
    s_path=ROOT/f'results/{SESSION}-main-schedule.json';s=json.loads(s_path.read_text());assert s['phase']=='main' and s['cells']==frozen_schedule();verify_smoke(approval());records={};inputs=[s_path,ROOT/'MAIN_APPROVAL.json',ROOT/'AMENDMENTS.md',ROOT/'K8S_PROTOCOL.md',ROOT/'PROTOCOL_DETAILS.md',ROOT/'requirements.lock',ROOT/'results/env.json',ROOT/'results/images.json',ROOT/'results/tests-main.json',ROOT/'results/preflight-main.json'];audit=[]
    for i,cell in enumerate(s['cells'],1):
        path=ROOT/'results/raw'/f'itom-k8s-{SESSION}-main-{i:03d}.json'
        if not path.exists():continue
        r=json.loads(path.read_text());assert r['phase']=='main';assert (r['policy'],r['condition'],r['repetition'])==(cell['policy'],cell['condition'],cell['repetition']);assert r['schedule_sha256']==sha(s_path);assert r['implementation_commit']==s['implementation_commit'] and r['execution_commit']==s['execution_commit']
        for name,h in r['protocol_hashes'].items():assert sha(ROOT/name)==h
        for name,h in r['source_hashes'].items():assert sha(ROOT/name)==h
        for key,p in [('main_approval_sha256','MAIN_APPROVAL.json'),('amendments_sha256','AMENDMENTS.md'),('environment_sha256','results/env.json'),('image_manifest_sha256','results/images.json'),('dependency_lock_sha256','requirements.lock')]:assert r[key]==sha(ROOT/p)
        j=ROOT/'results/journals'/(r['run_id']+'.jsonl')
        if j.exists():
            assert sha(j)==r['journal_sha256'];inputs.append(j)
            from main_runner import read_journal
            es,fragment=read_journal(j);requests=[e for e in es if e.get('stage')=='recovery_dispatch' and e['kind']=='api_request'];assert len(requests)<=1
            for e in requests:
                assert ['force','true'] not in e['query']
                if r['policy']=='snapshot':assert 'resourceVersion' not in e['body']['metadata'] and e['body']['spec']==r['baseline_deployment']['spec']
        else:requests=[];assert r.get('interrupted')
        if r.get('completed'):assert r['window_complete'] and r['window_elapsed']>=90
        audit.append(dict(run_id=r['run_id'],completed=r.get('completed'),fixture_valid=r.get('fixture_valid'),mutation_count=len(requests),interrupted=r.get('interrupted',False),settle_achieved=r.get('settle_achieved'),window_complete=r.get('window_complete'),cleanup_complete=r.get('cleanup_complete')))
        records[i]=r;inputs.append(path)
    known={f'itom-k8s-{SESSION}-main-{i:03d}.json' for i in range(1,201)};assert all(p.name in known for p in (ROOT/'results/raw').glob('*.json'))
    out=ROOT/'results/main-analysis'
    if out.exists():
        # Never overwrite a completed/partial analysis; use a new audit generation.
        suffix=1
        while (ROOT/f'results/main-analysis-{suffix:03d}').exists():suffix+=1
        out=ROOT/f'results/main-analysis-{suffix:03d}'
    out.mkdir();rows=summarize(s['cells'],records)
    with (out/'summary.csv').open('x',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    # All numeric paper findings are rendered from the written summary.csv.
    with (out/'summary.csv').open() as f:loaded=[{k:v if k in ('policy','condition') else int(v) for k,v in row.items()} for row in csv.DictReader(f)]
    table,draft,info=render(loaded,len(list((ROOT/'results/smoke').glob('*.json'))),len(list((ROOT/'results/smoke-A1').glob('*.json'))))
    (out/'table.md').write_text(table);(out/'PAPER_DRAFT.md').write_text(draft);exclusive(out/'analysis_checks.json',info);exclusive(out/'integrity_audit.json',dict(records=audit,expected=200,present=len(records),missing=200-len(records)))
    diagnostics=['# Main execution diagnostics','',json.dumps(info['totals'],indent=2),'','Unknown counts include missing scheduled cells; unassessable_attempted_reports excludes missing cells. Smoke data are not pooled.','', '| Policy | Condition | Attempted | Complete | Valid | Missing | Interrupted | Fixture failures | Harness-error runs | Unsupported reports | Unassessable attempted reports |','|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for r in loaded:diagnostics.append('| '+' | '.join(str(r[k]) for k in ['policy','condition','attempted','complete','valid_fixture','missing','interrupted','fixture_failures','harness_error_runs','unsupported_reports','unassessable_attempted_reports'])+' |')
    (out/'DIAGNOSTICS.md').write_text('\n'.join(diagnostics)+'\n')
    inputs.extend(ROOT.glob('*.py'));inputs.extend((ROOT/'results').glob(f'{SESSION}*jsonl'));inputs.extend([ROOT/p for p in s['smoke_manifest_hashes']]);inputs.extend(out.glob('*'))
    exclusive(out/'PROVENANCE_MANIFEST.json',dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),phase='main',session=SESSION,protocol_commit=s['protocol_commit'],original_protocol_commit=s['original_protocol_commit'],amendment_commit=s['amendment_commit'],implementation_commit=s['implementation_commit'],execution_commit=s['execution_commit'],files={str(p.relative_to(ROOT)):sha(p) for p in inputs if p.is_file()},raw_records=len(records),planned_runs=200,smoke_pooled=False))
    print(json.dumps(dict(analysis_directory=str(out),**info),indent=2),flush=True)
if __name__=='__main__':
    if sys.argv[1:]==['--paper-only']:paper_only()
    elif sys.argv[1:]:raise SystemExit('Usage: analyze.py [--paper-only]')
    else:main()
