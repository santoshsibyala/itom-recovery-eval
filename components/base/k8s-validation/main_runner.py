"""Main-only orchestration; imports the exact approved A1 experiment and classifier."""
import argparse,datetime,fcntl,hashlib,json,os,pathlib,subprocess,sys,time,traceback
from run import Run,ApiError,FixtureError,ROOT,KUBECTL,KUBE,CTX,CLUSTER,GOOD,exclusive,sha,git,utc
from classify import classify
POLICIES=['snapshot','field_comp','object_cas','ownership']
CONDITIONS=['clean','disjoint','same_field','dep_race','dep_race_late']
SESSION='m20261101'

def frozen_schedule():
    cells=[]
    for rep in range(1,11):
        row=[dict(policy=p,condition=c,repetition=rep) for p in POLICIES for c in CONDITIONS]
        row.sort(key=lambda x:(hashlib.sha256(f"20261101|main|{rep}|{x['policy']}|{x['condition']}".encode()).hexdigest(),x['policy'],x['condition']))
        cells.extend(row)
    return cells

def approval():return json.loads((ROOT/'MAIN_APPROVAL.json').read_text())
def verify_smoke(a):
    count=0
    for path,h in a['smoke_manifests'].items():
        assert sha(ROOT/path)==h,path
        manifest=json.loads((ROOT/path).read_text())
        for p,expected in manifest['files'].items():
            if p=='AMENDMENTS.md':
                data=subprocess.check_output(['git','show',a['reviewed_execution_commit']+':AMENDMENTS.md'],cwd=ROOT)
                actual=hashlib.sha256(data).hexdigest()
            else:actual=sha(ROOT/p)
            assert actual==expected,(p,'reviewed smoke evidence changed')
            count+=1
    return count

def main_provenance():
    a=approval();assert a['approved_by']=='Santosh Sibyala' and a['main_authorized'] is True
    assert a['session']==SESSION and a['planned_runs']==200 and a['phase']=='main'
    assert not git('status','--porcelain','--untracked-files=no'),'commit all runtime sources before execution'
    for p,h in a['effective_protocol_hashes'].items():assert sha(ROOT/p)==h,p
    for p,h in a['approved_source_hashes'].items():assert sha(ROOT/p)==h,(p,'approved experiment implementation changed')
    verify_smoke(a)
    return dict(original_protocol_commit=a['original_protocol_commit'],protocol_commit=a['amendment_commit'],amendment_id='A1',amendment_commit=a['amendment_commit'],implementation_commit=a['implementation_commit'],reviewed_execution_commit=a['reviewed_execution_commit'],execution_commit=git('rev-parse','HEAD'),protocol_hashes=a['effective_protocol_hashes'],source_hashes={p.name:sha(p) for p in ROOT.glob('*.py')},approved_by=a['approved_by'],approval_recorded_utc=a['approval_recorded_utc'],main_approval_sha256=sha(ROOT/'MAIN_APPROVAL.json'),amendments_sha256=sha(ROOT/'AMENDMENTS.md'),smoke_manifest_hashes=a['smoke_manifests'],environment_sha256=sha(ROOT/'results/env.json'),dependency_lock_sha256=sha(ROOT/'requirements.lock'),image_manifest_sha256=sha(ROOT/'results/images.json'))

class MainRun(Run):
    def __init__(self,session,ordinal,cell,prov):
        super().__init__(session,'main',ordinal,cell['policy'],cell['condition'],prov)
        self.r['repetition']=cell['repetition']
        self.r['completed']=False
        self.event('scheduled_cell',ordinal=ordinal,cell=cell)
    def execute(self):
        try:
            self.baseline()
            if self.phase=='main':self.experiment()
            else:self.r['fixture_valid']=True
            self.stage='final_observation';self.r['final_deployment']=self.get(self.dp);self.r['final_configmap']=self.get(self.cp);self.r['completed']=True
        except Exception as e:
            self.error('fixture' if isinstance(e,FixtureError) or not self.r['fixture_valid'] else 'harness',e);self.r['completed']=False
        finally:
            self.stage='cleanup'
            try:
                obj=self.get('/api/v1/namespaces/'+self.ns)
                if obj['metadata'].get('labels',{}).get('itom-experiment')!=CLUSTER:raise RuntimeError('namespace ownership check failed')
                self.request('DELETE','/api/v1/namespaces/'+self.ns,{'apiVersion':'v1','kind':'DeleteOptions','gracePeriodSeconds':0});start=time.monotonic()
                while True:
                    try:self.get('/api/v1/namespaces/'+self.ns)
                    except ApiError as e:
                        if e.status==404:break
                        raise
                    if time.monotonic()-start>=60:raise TimeoutError('namespace deletion exceeded 60 seconds')
                    time.sleep(2)
                self.r['cleanup_complete']=True
            except Exception as e:self.error('cleanup',e);self.r['cleanup_complete']=False
            self.stage='classification'
            if self.phase=='main':
                try:self.r['metrics']=classify(self.r)
                except Exception as e:self.error('classifier',e)
            self.event('finished',completed=self.r.get('completed'),metrics=self.r.get('metrics'),errors=len(self.r['errors']));self.f.close();self.api.close()
            self.r['journal_sha256']=sha(self.journal);exclusive(ROOT/'results/raw'/(self.ns+'.json'),self.r)
            print(json.dumps({'run':self.ns,'policy':self.r['policy'],'condition':self.r['condition'],'completed':self.r.get('completed'),'metrics':self.r.get('metrics'),'errors':len(self.r['errors'])}),flush=True)
        return self.r

def append_json(path,obj):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('a') as f:f.write(json.dumps(obj)+'\n');f.flush();os.fsync(f.fileno())

def read_journal(path):
    if not path.exists():return [],None
    rows=[];lines=path.read_bytes().splitlines()
    for i,line in enumerate(lines):
        try:rows.append(json.loads(line))
        except (ValueError,UnicodeDecodeError):
            if i!=len(lines)-1:raise ValueError('non-terminal corrupt journal record')
            return rows,dict(terminal_fragment_preserved=True,line=i+1)
    return rows,None

def reconstruct(cell,ordinal,prov,events):
    """Reconstruct only journal-supported evidence; never perform recovery again."""
    ns=f'itom-k8s-{SESSION}-main-{ordinal:03d}'
    r=dict(run_id=ns,namespace=ns,phase='main',ordinal=ordinal,repetition=cell['repetition'],policy=cell['policy'],condition=cell['condition'],good_image=GOOD,fixture_valid=None,completed=False,interrupted=True,window_complete=False,errors=[dict(kind='interruption',stage=events[-1]['stage'] if events else 'before_run_journal',type='InterruptedExecution',message='Mechanically finalized on resume; scheduled cell will not be repeated.')],health_series=[],**prov)
    mutation_request=False
    for e in events:
        stage=e['stage'];kind=e['kind'];b=e.get('body');endpoint=e.get('endpoint','');dep=endpoint.endswith('/deployments/app');cm=endpoint.endswith('/configmaps/app-config')
        if stage in ('predispatch_observation','recovery_dispatch','postdispatch_observation','outcome_window','final_observation'):r['fixture_valid']=True
        if kind=='health_poll':
            if stage=='baseline' and e.get('healthy'):r['baseline_achieved']=True
            if stage=='outcome_window':r['health_series'].append(e)
        if kind=='error':r['errors'].append(e['detail'])
        if kind=='exec_transport_failure':r['errors'].append(dict(kind='api_exec_transport',stage=stage,detail=e.get('detail')))
        if kind=='policy_report':r['report']=e['report'];r['report_monotonic']=e['monotonic']
        if stage=='recovery_dispatch' and kind=='api_request':mutation_request=True;r['mutation_outcome']='unknown';r['recovery_endpoint_is_deployment']=dep
        if kind=='api_response' and 200<=e.get('status',0)<300 and isinstance(b,dict):
            mapping={'baseline':('baseline_deployment','baseline_configmap'),'policy_pre_read':('policy_pre_deployment','policy_pre_configmap'),'predispatch_observation':('predispatch_deployment','predispatch_configmap'),'postdispatch_observation':('post_deployment','post_configmap'),'final_observation':('final_deployment','final_configmap')}
            if stage in mapping:
                if dep:r[mapping[stage][0]]=b
                if cm:r[mapping[stage][1]]=b
            if stage=='bad_change' and e['method']=='PATCH':r['bad_deployment']=b
            if stage=='operator_injection' and e['method']=='PATCH':r['injection_response']=b;r['injection_ack_seq']=e['seq']
            if stage=='recovery_dispatch':r['mutation_outcome']='ack';r['mutation_response']=b;r['mutation_ack_seq']=e['seq']
        if kind=='api_response' and stage=='recovery_dispatch' and e.get('status',0)>=400:
            r['mutation_status']=e['status'];r['mutation_outcome']='rejected' if 400<=e['status']<500 else 'unknown'
        if stage=='final_observation':r['window_complete']=True
    if r.get('predispatch_deployment') and r.get('predispatch_configmap'):
        r['configmap_writer_order_verified']=True;r['injection_verified']=True;r['recovery_endpoint_is_deployment']=True
    if not mutation_request and r.get('report',{}).get('status')=='BLOCKED':r['mutation_outcome']='no_dispatch'
    if any(e.get('kind')=='error' and e.get('detail',{}).get('kind')=='fixture' for e in events):r['fixture_valid']=False
    try:r['metrics']=classify(r)
    except Exception as e:r['errors'].append(dict(kind='classifier',type=type(e).__name__,message=str(e),traceback=traceback.format_exc()))
    return r

def cleanup_interrupted(namespace,log):
    """Only cleanup of this schedule's owned namespace; no recovery writes."""
    assert namespace.startswith(f'itom-k8s-{SESSION}-main-')
    def call(args):
        start=time.monotonic();p=subprocess.run([KUBECTL,'--kubeconfig',str(KUBE),'--context',CTX,*args],capture_output=True,text=True,timeout=10)
        append_json(log,dict(utc=utc(),monotonic=time.monotonic(),argv=args,exit=p.returncode,stdout=p.stdout,stderr=p.stderr,duration=time.monotonic()-start));return p
    p=call(['get','namespace',namespace,'--ignore-not-found=true','-o','json']);assert p.returncode==0,p.stderr
    if not p.stdout.strip():return True
    obj=json.loads(p.stdout);assert obj['metadata'].get('labels',{}).get('itom-experiment')==CLUSTER,'refuse unowned namespace'
    p=call(['delete','namespace',namespace,'--wait=false','--grace-period=0']);assert p.returncode==0,p.stderr
    start=time.monotonic()
    while time.monotonic()-start<60:
        p=call(['get','namespace',namespace,'--ignore-not-found=true','-o','json']);assert p.returncode==0,p.stderr
        if not p.stdout.strip():return True
        time.sleep(2)
    raise TimeoutError('interrupted namespace cleanup exceeded 60 seconds')

def action_for(ordinal,raw_exists,started,journal_exists):
    if raw_exists:return 'skip'
    return 'finalize_interrupted' if ordinal in started or journal_exists else 'execute_once'

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--resume',action='store_true');args=parser.parse_args()
    lock=(ROOT/'results/main.lock').open('a+');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    assert subprocess.check_output([KUBECTL,'--kubeconfig',str(KUBE),'config','current-context'],text=True).strip()==CTX
    prov=main_provenance();tests=json.loads((ROOT/'results/tests-main.json').read_text());pre=json.loads((ROOT/'results/preflight-main.json').read_text())
    assert tests['passed'] and tests['execution_commit']==prov['execution_commit'];assert pre['passed'] and pre['execution_commit']==prov['execution_commit']
    prov.update(tests_sha256=sha(ROOT/'results/tests-main.json'),preflight_sha256=sha(ROOT/'results/preflight-main.json'))
    path=ROOT/f'results/{SESSION}-main-schedule.json';cells=frozen_schedule()
    if path.exists():
        assert args.resume,'existing cohort requires --resume, never restart or replace'
        saved=json.loads(path.read_text());assert saved['cells']==cells
        assert saved['execution_commit']==prov['execution_commit'],'resume only with exact execution code'
        prov={k:v for k,v in saved.items() if k not in ('cells','seed','phase','session')}
    else:
        assert not args.resume,'no schedule to resume'
        assert not list((ROOT/'results/raw').glob('*.json')),'existing main records require audit'
        exclusive(path,dict(seed=20261101,phase='main',session=SESSION,cells=cells,**prov))
    prov['schedule_sha256']=sha(path)
    segments=sorted((ROOT/'results').glob(f'{SESSION}-session*.jsonl'))
    entries=[];fragments=[]
    for segment in segments:
        rows,fragment=read_journal(segment);entries.extend(rows)
        if fragment:fragments.append((segment,fragment))
    started={e['ordinal'] for e in entries if e.get('kind')=='started'}
    recovered={e.get('recovered_from') for e in entries if e.get('recovered_from')}
    if segments:
        index=1
        while (ROOT/f'results/{SESSION}-session-resume-{index:03d}.jsonl').exists():index+=1
        session_log=ROOT/f'results/{SESSION}-session-resume-{index:03d}.jsonl'
    else:session_log=ROOT/f'results/{SESSION}-session.jsonl'
    with session_log.open('x') as f:
        f.write(json.dumps(dict(kind='execution_segment',utc=utc(),resume=args.resume))+'\n');f.flush();os.fsync(f.fileno())
    for segment,fragment in fragments:
        if str(segment.relative_to(ROOT)) in recovered:continue
        # A torn start entry cannot authorize rerunning the next scheduled cell.
        ordinal=next(i for i in range(1,201) if i not in started and not (ROOT/'results/raw'/f'itom-k8s-{SESSION}-main-{i:03d}.json').exists())
        started.add(ordinal)
        append_json(session_log,dict(kind='started',ordinal=ordinal,cell=cells[ordinal-1],utc=utc(),recovered_from=str(segment.relative_to(ROOT)),fragment=fragment,original_segment_sha256=sha(segment)))
    for ordinal,cell in enumerate(cells,1):
        ns=f'itom-k8s-{SESSION}-main-{ordinal:03d}';raw=ROOT/'results/raw'/(ns+'.json');journal=ROOT/'results/journals'/(ns+'.jsonl')
        action=action_for(ordinal,raw.exists(),started,journal.exists())
        if action=='skip':
            prior=json.loads(raw.read_text());assert (prior['policy'],prior['condition'],prior['repetition'])==(cell['policy'],cell['condition'],cell['repetition']);assert prior['schedule_sha256']==sha(path)
            if not prior.get('cleanup_complete'):cleanup_interrupted(ns,ROOT/f'results/{SESSION}-resume-cleanup.jsonl')
            continue
        if action=='finalize_interrupted':
            es,fragment=read_journal(journal);record=reconstruct(cell,ordinal,prov,es);record['partial_journal_tail']=fragment
            try:record['cleanup_complete']=cleanup_interrupted(ns,ROOT/f'results/{SESSION}-resume-cleanup.jsonl')
            except Exception as e:record['cleanup_complete']=False;record['errors'].append(dict(kind='cleanup',type=type(e).__name__,message=str(e),traceback=traceback.format_exc()))
            record['journal_sha256']=sha(journal) if journal.exists() else None
            exclusive(raw,record);append_json(session_log,dict(kind='interrupted_finalized',ordinal=ordinal,utc=utc(),raw_sha256=sha(raw)))
            if not record['cleanup_complete']:raise RuntimeError('cleanup incomplete; do not start another cell')
            continue
        append_json(session_log,dict(kind='started',ordinal=ordinal,cell=cell,utc=utc(),monotonic=time.monotonic()))
        result=MainRun(SESSION,ordinal,cell,prov).execute()
        if not result.get('cleanup_complete'):raise RuntimeError('cleanup incomplete; stop before next cell')
    print('MAIN SCHEDULE FINISHED. Running read-only analysis; no additional experiments.',flush=True)
    subprocess.run([sys.executable,str(ROOT/'analyze.py')],cwd=ROOT,check=True)
    print('STOP: main analysis complete; author review required; manuscript untouched.',flush=True)
if __name__=='__main__':main()
