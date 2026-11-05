"""Read-only A1 analysis, integrity checks, and original/A1 descriptive comparison."""
import csv,hashlib,json,pathlib,subprocess,datetime,shutil
R=pathlib.Path('/Users/santoshsibyala/itom-k8s-validation');S=R/'results/a120261101-smoke-A1-schedule.json';schedule=json.loads(S.read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();approval=json.loads((R/'A1_APPROVAL.json').read_text())
original_manifest=json.loads((R/'results/smoke-review/HANDOFF_MANIFEST.json').read_text())
for p,h in original_manifest['files'].items():assert sha(R/p)==h,p
files=sorted((R/'results/smoke-A1').glob('*.json'));assert len(files)==5
records=[];rows=[];audits=[]
for i,p in enumerate(files,1):
 r=json.loads(p.read_text());assert r['phase']=='smoke-A1' and r['policy']=='snapshot';assert r['condition']==schedule['cells'][i-1]['condition'];assert r['schedule_sha256']==sha(S)
 assert r['implementation_commit']==approval['implementation_commit'] and r['amendment_commit']==approval['amendment_commit']
 assert r['original_protocol_commit']==approval['original_protocol_commit'];assert r['approved_by']=='Santosh Sibyala'
 for name,h in r['protocol_hashes'].items():assert sha(R/name)==h
 for name,h in r['source_hashes'].items():assert sha(R/name)==h
 for key,path in [('approval_sha256','A1_APPROVAL.json'),('amendments_sha256','AMENDMENTS.md'),('environment_sha256','results/env.json'),('image_manifest_sha256','results/images.json'),('dependency_lock_sha256','requirements.lock'),('tests_sha256','results/tests-A1.json'),('preflight_sha256','results/preflight-A1.json')]:assert r[key]==sha(R/path)
 j=R/'results/journals'/(r['run_id']+'.jsonl');assert sha(j)==r['journal_sha256'];events=[json.loads(x) for x in j.read_text().splitlines()];mut=[e for e in events if e['stage']=='recovery_dispatch' and e['kind']=='api_request'];assert len(mut)<=1
 for e in mut:
  assert e['method']=='PUT' and 'resourceVersion' not in e['body']['metadata'];assert 'managedFields' not in e['body']['metadata'] and 'status' not in e['body'];assert e['body']['spec']==r['baseline_deployment']['spec'];assert ['force','true'] not in e['query']
 fresh=[e for e in events if e['kind']=='api_response' and e.get('visibility')=='policy_metadata_only'];assert len(fresh)==1
 if r['condition'] in ('disjoint','same_field','dep_race'):assert fresh[0]['seq']>r['injection_ack_seq']
 if r['condition']=='dep_race_late':assert fresh[0]['seq']<r['injection_ack_seq']<mut[0]['seq']
 a=dict(run_id=r['run_id'],journal_hash_verified=True,all_provenance_hashes_verified=True,mutation_count=len(mut),unconditional_snapshot_put_verified=True,baseline_full_spec_verified=True,fresh_get_order_verified=True,no_force=True,window_complete=r.get('window_complete'),window_elapsed=r.get('window_elapsed'),settle_achieved=r.get('settle_achieved'),bad_unhealthy_confirmed=r.get('bad_unhealthy_confirmed'),cleanup_complete=r.get('cleanup_complete'))
 audits.append(a);records.append((p,r));rows.append(dict(condition=r['condition'],completed=r.get('completed'),fixture_valid=r['fixture_valid'],mutation_outcome=r.get('mutation_outcome'),http_status=next((e['status'] for e in events if e['kind']=='api_response' and e['stage']=='recovery_dispatch'),None),**r.get('metrics',{}),errors=len(r['errors'])))
assert not list((R/'results/raw').glob('*.json'));assert len(list((R/'results/smoke').glob('*.json')))==20
ns=json.loads(subprocess.check_output([str(R/'.tools/kubectl'),'--kubeconfig',str(R/'.kubeconfig'),'--context','kind-itom-k8s-validation','get','namespaces','-l','itom-experiment=itom-k8s-validation','-o','json'],text=True));assert not ns['items']
out=R/'results/smoke-A1-review';out.mkdir(exist_ok=False)
with (out/'summary.csv').open('x',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
shutil.copyfile(__file__,out/'review_A1.py')
(out/'INTEGRITY_AUDIT.json').write_text(json.dumps(dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),records=audits,original_handoff_files_verified=len(original_manifest['files']),original_smoke_records=20,supplementary_records=5,main_records=0,no_experimental_namespaces_remaining=True),indent=2)+'\n')
def show(x):return 'yes' if x is True else 'no' if x is False else 'unknown' if x is None else str(x)
lines=['# Approved A1 supplementary smoke results','', 'Five snapshot-only supplementary cells; original 20-cell smoke remains separate and unchanged. Main has not started.','',f"Approval: Santosh Sibyala; recorded UTC {approval['approval_recorded_utc']}.",f"Amendment commit: `{approval['amendment_commit']}`.",f"Implementation commit: `{approval['implementation_commit']}`.",f"Execution/provenance commit: `{schedule['execution_commit']}`.",'']
lines += [f'- Effective `{n}` SHA-256: `{h}`' for n,h in schedule['protocol_hashes'].items()]
lines+=['', 'Tests: 24/24 passed (15 existing classifier tests and 9 focused request-construction/behavior tests). The focused tests cover absent snapshot RV/status/managedFields, full baseline spec and retained live metadata, early/late injection order, initial predicate block, rejection/timeout without retry or force, unchanged CAS original-RV test and predicate recheck, and unchanged field-compensation request.','', f"Completed: {sum(r['completed'] is True for r in rows)}/5; valid fixtures: {sum(r['fixture_valid'] is True for r in rows)}/5; recorded errors: {sum(r['errors'] for r in rows)}.",'', '| Condition | PUT HTTP | Safe | Recovery | Operator preserved | Healthy | Report supported | Errors |','|---|---:|---|---|---|---|---|---:|']
for r in rows:lines.append('| '+' | '.join([r['condition'],str(r['http_status'])]+[show(r.get(k)) for k in ['safety','successful_recovery','operator_preserved','healthy','report_supported']]+[str(r['errors'])])+' |')
lines+=['','## Observations','']
for r in rows:lines.append(f"- {r['condition']}: outcome={r['mutation_outcome']}; unsafe_overwrite={show(r.get('unsafe_overwrite'))}; committed_under_false_predicate={show(r.get('committed_under_false_predicate'))}; blocked={show(r.get('blocked'))}.")
lines+=['', '## Original snapshot versus A1 (separate cohorts)','', 'This comparison reports single smoke observations per condition, not a causal estimate or a pooled benchmark. The original failures are not replaced.','', '| Condition | Original outcome / HTTP | A1 outcome / HTTP |','|---|---|---|']
for row in rows:
 old=next(json.loads(p.read_text()) for p in (R/'results/smoke').glob('*.json') if json.loads(p.read_text())['policy']=='snapshot' and json.loads(p.read_text())['condition']==row['condition'])
 status=old.get('mutation_status','success' if old.get('mutation_outcome')=='ack' else 'none')
 lines.append(f"| {row['condition']} | {old.get('mutation_outcome')} / {status} | {row['mutation_outcome']} / {row['http_status']} |")
lines+=['', '## Integrity and interpretation','', f"Every supplementary snapshot PUT omitted metadata.resourceVersion and used the full baseline spec. No forced recovery or repeated mutation was found. Status settling passed in {sum(a['settle_achieved'] is True for a in audits)}/5; complete observation windows: {sum(a['window_complete'] is True and a['window_elapsed']>=90 for a in audits)}/5. All experiment namespaces were removed.", 'The dependency mode is not consumed by the application and no policy writes the ConfigMap. Dependency preservation is therefore trivial; commits under mode v2 are declared-contract violations, not observed application harm. Health alone does not establish successful recovery under the frozen metrics.', 'All 59 original handoff files match their preserved hashes. Effective protocol, implementation, approval, journal, schedule, dependency, image and environment hashes were verified for every supplementary record.', '', '## Stop gate','', 'Stop here for author review. A1 approval does not approve main. No policies were adjusted after observing supplementary outcomes. No main run or manuscript update occurred.','']
(out/'REPORT.md').write_text('\n'.join(lines));paths=[S,R/'A1_APPROVAL.json',R/'AMENDMENTS.md',R/'K8S_PROTOCOL.md',R/'PROTOCOL_DETAILS.md',R/'results/tests-A1.json',R/'results/preflight-A1.json',R/'results/a120261101-session.jsonl',R/'results/smoke-A1-console.log',*out.glob('*'),*[p for p,r in records],*[R/'results/journals'/(r['run_id']+'.jsonl') for p,r in records]]
(out/'MANIFEST.json').write_text(json.dumps(dict(amendment_commit=approval['amendment_commit'],implementation_commit=approval['implementation_commit'],main_authorized=False,main_started=False,files={str(p.relative_to(R)):sha(p) for p in paths}),indent=2)+'\n')
print('\n'.join(lines[:29]));print('Report:',out/'REPORT.md');print('Manifest SHA256:',sha(out/'MANIFEST.json'))
