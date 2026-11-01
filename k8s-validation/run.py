"""Frozen-protocol setup baseline and smoke runner. Main intentionally disabled."""
import argparse,copy,datetime,hashlib,json,os,pathlib,platform,subprocess,sys,time,traceback
from kubernetes import client,config
from classify import classify,owners,image,replicas,note,mode
ROOT=pathlib.Path(__file__).resolve().parent
CLUSTER='itom-k8s-validation'; CTX='kind-'+CLUSTER
GOOD='hashicorp/http-echo:1.0.0'; PROBE='curlimages/curl:8.16.0'; BAD='hashicorp/http-echo:itom-k8s-absent-20261101'
FREEZE='caa6966197d7733fc69b0374155dd053262f076f'
HASHES={'K8S_PROTOCOL.md': '08fd3e7f6f40361b8a7da4a6dec67d5152698bb1d35fcb2e7da13cc5ded11aa2', 'PROTOCOL_DETAILS.md': '345300a594b0c8a295623f677b4170ed00760b5a4c0220fcb5aa0be5e094821c'}
KUBE=ROOT/'.kubeconfig'; KUBECTL=str(ROOT/'.tools/kubectl')
def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def exclusive(p,data):
    p=pathlib.Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('x') as f:json.dump(data,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT,text=True).strip()
def provenance():
    approval_path=ROOT/'A1_APPROVAL.json'
    approval=json.loads(approval_path.read_text())
    assert approval['approved_by']=='Santosh Sibyala' and approval['authorized_phase']=='smoke-A1'
    assert approval['main_authorized'] is False
    for p,h in HASHES.items():assert sha(ROOT/p)==h,(p,'effective protocol changed')
    assert approval['effective_protocol_hashes']==HASHES
    assert git('rev-parse',FREEZE)==FREEZE
    assert not git('status','--porcelain','--untracked-files=no'),'tracked implementation changes must be committed'
    implementation=approval['implementation_commit']
    for p in ROOT.glob('*.py'):
        committed=subprocess.check_output(['git','show',implementation+':'+p.name],cwd=ROOT)
        assert hashlib.sha256(committed).hexdigest()==sha(p),(p,'implementation mismatch')
    return dict(protocol_commit=approval['amendment_commit'],original_protocol_commit=FREEZE,amendment_id='A1',amendment_commit=approval['amendment_commit'],approved_by=approval['approved_by'],approval_recorded_utc=approval['approval_recorded_utc'],approval_sha256=sha(approval_path),amendments_sha256=sha(ROOT/'AMENDMENTS.md'),protocol_hashes=HASHES,implementation_commit=implementation,execution_commit=git('rev-parse','HEAD'),source_hashes={p.name:sha(p) for p in ROOT.glob('*.py')},environment_sha256=sha(ROOT/'results/env.json'),dependency_lock_sha256=sha(ROOT/'requirements.lock'),image_manifest_sha256=sha(ROOT/'results/images.json'))

class FixtureError(Exception):pass
class ApiError(Exception):
    def __init__(self,status,body):self.status=status;self.body=body;super().__init__(f'API {status}: {body}')
class Run:
    def __init__(self,session,phase,ordinal,policy,condition,prov):
        self.ns=f'itom-k8s-{session}-{phase.lower()}-{ordinal:03d}';self.phase=phase;self.stage='initialization';self.seq=0
        self.journal=ROOT/'results/journals'/f'{self.ns}.jsonl';self.journal.parent.mkdir(parents=True,exist_ok=True)
        self.f=self.journal.open('x');self.r=dict(run_id=self.ns,namespace=self.ns,phase=phase,policy=policy,condition=condition,repetition=1,ordinal=ordinal,good_image=GOOD,fixture_valid=False,errors=[],health_series=[],**prov)
        cfg=client.Configuration();config.load_kube_config(str(KUBE),context=CTX,client_configuration=cfg);cfg.retries=0;self.api=client.ApiClient(cfg)
        self.dp=f'/apis/apps/v1/namespaces/{self.ns}/deployments/app';self.cp=f'/api/v1/namespaces/{self.ns}/configmaps/app-config'
        self.event('started',phase=phase,policy=policy,condition=condition,provenance=prov)
    def event(self,kind,**data):
        self.seq+=1;e=dict(seq=self.seq,utc=utc(),monotonic=time.monotonic(),stage=self.stage,kind=kind);e.update(data);self.f.write(json.dumps(e)+'\n');self.f.flush();os.fsync(self.f.fileno());return e
    def error(self,kind,e):
        d=dict(kind=kind,stage=self.stage,type=type(e).__name__,message=str(e),traceback=traceback.format_exc());self.r['errors'].append(d);self.event('error',detail=d)
    def request(self,method,path,body=None,ctype='application/json',manager=None,force=None,visibility='observer_only'):
        query=[]
        if manager:query.append(('fieldManager',manager))
        if force is not None:query.append(('force',str(force).lower()))
        start=time.monotonic();self.event('api_request',method=method,endpoint=path,body=body,content_type=ctype,query=query,visibility=visibility)
        try:
            resp=self.api.call_api(path,method,path_params={},query_params=query,header_params={'Accept':'application/json','Content-Type':ctype},body=body,response_type=None,auth_settings=['BearerToken'],_return_http_data_only=True,_preload_content=False,_request_timeout=10)
            raw=resp.data.decode();status=resp.status
        except client.exceptions.ApiException as e:
            if not e.status:self.event('api_transport_error',message=str(e),duration=time.monotonic()-start);raise
            status=e.status;raw=e.body
        except Exception as e:self.event('api_transport_error',message=str(e),duration=time.monotonic()-start);raise
        try:parsed=json.loads(raw)
        except (TypeError,ValueError):parsed=raw
        self.event('api_response',method=method,endpoint=path,status=status,body=parsed,duration=time.monotonic()-start,visibility=visibility)
        if not 200<=status<300:raise ApiError(status,parsed)
        return parsed
    def get(self,path,visibility='observer_only'):return self.request('GET',path,visibility=visibility)
    def apply(self,path,body,manager,force=False):return self.request('PATCH',path,body,'application/apply-patch+yaml',manager,force)
    def command(self,args,timeout=5):
        start=time.monotonic();self.event('subprocess_request',argv=args,timeout=timeout)
        try:
            p=subprocess.run(args,text=True,capture_output=True,timeout=timeout);d=dict(argv=args,exit=p.returncode,stdout=p.stdout,stderr=p.stderr,duration=time.monotonic()-start)
        except subprocess.TimeoutExpired as e:
            d=dict(argv=args,exit=None,stdout=(e.stdout or b'').decode() if isinstance(e.stdout,bytes) else e.stdout,stderr=(e.stderr or b'').decode() if isinstance(e.stderr,bytes) else e.stderr,duration=time.monotonic()-start,timeout=True)
        self.event('subprocess_response',**d);return d
    def poll(self):
        d=self.get(self.dp);p=self.command([KUBECTL,'--kubeconfig',str(KUBE),'--context',CTX,'-n',self.ns,'exec','probe','--','curl','--silent','--show-error','--connect-timeout','2','--max-time','3','--write-out','\n%{http_code}','http://app/'])
        out=p.get('stdout') or '';body,_,status=out.rpartition('\n');code=int(status) if status.isdigit() else None
        transport=p['exit'] is None or (p['exit']!=0 and 'command terminated with exit code' not in (p.get('stderr') or ''))
        if transport:
            self.r['errors'].append(dict(kind='api_exec_transport',stage=self.stage,detail=p));self.event('exec_transport_failure',detail=p)
        s=d.get('status',{});current=s.get('observedGeneration',0)>=d['metadata']['generation'];avail=s.get('availableReplicas',0);available=any(c.get('type')=='Available' and c.get('status')=='True' for c in s.get('conditions',[]))
        row=dict(monotonic=time.monotonic(),utc=utc(),http_code=code,body=body,exec_transport_failure=transport,generation=d['metadata']['generation'],observed_generation=s.get('observedGeneration'),available_replicas=avail,desired_replicas=d['spec']['replicas'],healthy=current and available and avail>=d['spec']['replicas'] and code==200,current_available_replicas=avail if current else 0)
        self.event('health_poll',**row);return row
    def identity(self,kind,name='app',api='apps/v1'):return dict(apiVersion=api,kind=kind,metadata={'name':name,'namespace':self.ns})
    def baseline(self):
        self.stage='baseline'
        self.request('POST','/api/v1/namespaces',dict(apiVersion='v1',kind='Namespace',metadata={'name':self.ns,'labels':{'itom-experiment':CLUSTER}}))
        cm=self.identity('ConfigMap','app-config','v1');cm['data']={'mode':'v1'};self.apply(self.cp,cm,'bootstrap')
        d=self.identity('Deployment');d['spec']={'replicas':2,'strategy':{'type':'Recreate'},'selector':{'matchLabels':{'app':'itom-app'}},'template':{'metadata':{'labels':{'app':'itom-app'}},'spec':{'terminationGracePeriodSeconds':0,'containers':[{'name':'app','image':GOOD,'imagePullPolicy':'Never','args':['-listen=:5678','-text=itom-k8s-ok'],'ports':[{'containerPort':5678}],'env':[{'name':'APP_MODE','valueFrom':{'configMapKeyRef':{'name':'app-config','key':'mode'}}}],'resources':{'requests':{'cpu':'10m','memory':'16Mi'},'limits':{'cpu':'100m','memory':'64Mi'}},'readinessProbe':{'httpGet':{'path':'/','port':5678},'periodSeconds':1,'timeoutSeconds':1,'successThreshold':1,'failureThreshold':1}}]}}};self.apply(self.dp,d,'bootstrap')
        svc=self.identity('Service','app','v1');svc['spec']={'selector':{'app':'itom-app'},'ports':[{'port':80,'targetPort':5678}]};self.apply(f'/api/v1/namespaces/{self.ns}/services/app',svc,'bootstrap')
        p=self.identity('Pod','probe','v1');p['spec']={'terminationGracePeriodSeconds':0,'containers':[{'name':'probe','image':PROBE,'imagePullPolicy':'Never','command':['/bin/sh','-c','while true; do sleep 3600; done']}]};self.apply(f'/api/v1/namespaces/{self.ns}/pods/probe',p,'bootstrap')
        start=time.monotonic();ok=False
        while time.monotonic()-start<180:
            pod=self.get(f'/api/v1/namespaces/{self.ns}/pods/probe')
            if pod.get('status',{}).get('phase')=='Running' and self.poll()['healthy']:ok=True;break
            time.sleep(2)
        self.r['baseline_achieved']=ok;self.r['baseline_elapsed']=time.monotonic()-start
        if not ok:raise FixtureError('baseline failed within 180 seconds')
        self.r['baseline_deployment']=self.get(self.dp);self.r['baseline_configmap']=self.get(self.cp)
    def inject(self):
        cond=self.r['condition']
        if cond=='clean':self.r['injection_verified']=True;return
        self.stage='operator_injection';d=self.identity('Deployment')
        if cond=='disjoint':d['spec']={'template':{'spec':{'containers':[{'name':'app','env':[{'name':'OPERATOR_NOTE','value':'preserve-me'}]}]}}};resp=self.apply(self.dp,d,'operator');ok=note(resp)=='preserve-me' and 'operator' in owners(resp,'note')
        elif cond=='same_field':d['spec']={'replicas':4};resp=self.apply(self.dp,d,'operator',True);ok=replicas(resp)==4 and owners(resp,'replicas')==['operator']
        else:
            d=self.identity('ConfigMap','app-config','v1');d['data']={'mode':'v2'};resp=self.apply(self.cp,d,'operator',True);ok=mode(resp)=='v2' and owners(resp,'mode')==['operator']
        self.r['injection_response']=resp;self.r['injection_verified']=ok;self.r['injection_ack_seq']=self.seq
        if not ok:raise FixtureError('injection value/ownership verification failed')
    def experiment(self):
        self.stage='bad_change';d=self.identity('Deployment');d['spec']={'replicas':3,'template':{'spec':{'containers':[{'name':'app','image':BAD}]}}};bad=self.apply(self.dp,d,'agent',True);self.r['bad_deployment']=bad
        if owners(bad,'image')!=['agent'] or owners(bad,'replicas')!=['agent']:raise FixtureError('bad fixture ownership not exclusive agent')
        start=time.monotonic();consecutive=0
        while time.monotonic()-start<60:
            row=self.poll();consecutive=consecutive+1 if row['http_code']!=200 and row['current_available_replicas']==0 else 0
            if consecutive>=2:break
            time.sleep(2)
        self.r['bad_unhealthy_confirmed']=consecutive>=2;self.r['bad_elapsed']=time.monotonic()-start
        self.stage='status_settle';start=time.monotonic();last=None;settled=False
        while time.monotonic()-start<30:
            cur=self.get(self.dp);rv=cur['metadata']['resourceVersion'];match=cur.get('status',{}).get('observedGeneration')==cur['metadata']['generation']
            if match and last==rv:settled=True;break
            last=rv if match else None;time.sleep(2)
        self.r.update(settle_achieved=settled,settle_elapsed=time.monotonic()-start)
        self.stage='policy_pre_read';pre=self.get(self.dp,'policy_visible');cm=self.get(self.cp,'policy_visible');self.r.update(policy_pre_deployment=pre,policy_pre_configmap=cm)
        if mode(cm) is None:raise ValueError('missing initial mode')
        allow=mode(cm)=='v1';policy=self.r['policy'];cond=self.r['condition']
        if cond!='dep_race_late':self.inject()
        self.stage='policy_prepare';fields={};body=None;method='PATCH';ctype='application/strategic-merge-patch+json';manager='recovery-field';force=None
        if allow and policy in ('object_cas','ownership'):
            fresh=self.get(self.cp,'policy_visible')
            if mode(fresh) is None:raise ValueError('missing recheck mode')
            allow=mode(fresh)=='v1'
        if allow:
            fields={'image':GOOD,'replicas':2}
            if policy=='snapshot':
                live=self.get(self.dp,'policy_metadata_only');meta=copy.deepcopy(live['metadata']);meta.pop('managedFields',None);meta.pop('resourceVersion',None)
                body={'apiVersion':'apps/v1','kind':'Deployment','metadata':meta,'spec':copy.deepcopy(self.r['baseline_deployment']['spec'])};method='PUT';ctype='application/json';manager='recovery-snapshot'
            elif policy=='field_comp':body={'spec':{'replicas':2,'template':{'spec':{'containers':[{'name':'app','image':GOOD}]}}}}
            elif policy=='object_cas':
                cs=pre['spec']['template']['spec']['containers']
                if len(cs)!=1 or cs[0]['name']!='app':raise ValueError('CAS fixture container identity mismatch')
                body=[{'op':'test','path':'/metadata/resourceVersion','value':pre['metadata']['resourceVersion']},{'op':'replace','path':'/spec/replicas','value':2},{'op':'replace','path':'/spec/template/spec/containers/0/image','value':GOOD}];ctype='application/json-patch+json';manager='recovery-cas'
            else:
                current=self.get(self.dp,'policy_visible');self.r['policy_ownership_deployment']=current;fields={k:v for k,v in fields.items() if owners(current,k)==['agent']};body=self.identity('Deployment');body['spec']={}
                if 'replicas' in fields:body['spec']['replicas']=2
                if 'image' in fields:body['spec']['template']={'spec':{'containers':[{'name':'app','image':GOOD}]}}
                allow=bool(fields);ctype='application/apply-patch+yaml';manager='agent';force=False
        self.event('prepared_intent',allow=allow,fields=fields,body=body,visibility='policy_visible')
        if cond=='dep_race_late':self.inject()
        self.r['fixture_valid']=True;self.stage='predispatch_observation'
        self.r['predispatch_deployment']=self.get(self.dp);self.r['predispatch_configmap']=self.get(self.cp);self.r['configmap_writer_order_verified']=True;self.r['recovery_endpoint_is_deployment']=True
        self.stage='recovery_dispatch'
        if not allow:outcome='no_dispatch'
        else:
            try:
                response=self.request(method,self.dp,body,ctype,manager,force,'policy_visible');outcome='ack';self.r['mutation_response']=response;self.r['mutation_ack_seq']=self.seq
            except ApiError as e:
                # HTTP client-side rejection is explicit noncommit; server failures are ambiguous.
                if 400<=e.status<500:outcome='rejected'
                else:outcome='unknown';self.error('api_server_ambiguous',e)
                self.r['mutation_status']=e.status
            except Exception as e:outcome='unknown';self.error('api_transport',e)
        self.r['mutation_outcome']=outcome
        self.stage='postdispatch_observation';self.r['post_deployment']=self.get(self.dp);self.r['post_configmap']=self.get(self.cp)
        report={'status':('RECOVERED' if len(fields)==2 else 'PARTIAL'),'claims':fields} if outcome=='ack' else {'status':'BLOCKED','claims':{}} if outcome in ('no_dispatch','rejected') else {'status':'PARTIAL','claims':{},'commit_unknown':True}
        self.r['report']=report;self.event('policy_report',report=report);start=time.monotonic();self.r['report_monotonic']=start;self.stage='outcome_window'
        while time.monotonic()-start<90:
            row=self.poll();row['elapsed']=time.monotonic()-start;self.r['health_series'].append(row)
            if row['healthy'] and 'first_healthy_elapsed' not in self.r:self.r['first_healthy_elapsed']=row['elapsed']
            remaining=90-(time.monotonic()-start)
            if remaining>0:time.sleep(min(2,remaining))
        self.r['window_complete']=True;self.r['window_elapsed']=time.monotonic()-start
    def execute(self):
        try:
            self.baseline()
            if self.phase in ('smoke','smoke-A1'):self.experiment()
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
            if self.phase in ('smoke','smoke-A1'):
                try:self.r['metrics']=classify(self.r)
                except Exception as e:self.error('classifier',e)
            self.event('finished',completed=self.r.get('completed'),metrics=self.r.get('metrics'),errors=len(self.r['errors']));self.f.close();self.api.close()
            self.r['journal_sha256']=sha(self.journal);exclusive(ROOT/'results'/self.phase/(self.ns+'.json'),self.r)
            print(json.dumps({'run':self.ns,'policy':self.r['policy'],'condition':self.r['condition'],'completed':self.r.get('completed'),'metrics':self.r.get('metrics'),'errors':len(self.r['errors'])}),flush=True)
        return self.r

def main():
    p=argparse.ArgumentParser();p.add_argument('phase',choices=['smoke-A1']);p.add_argument('--session',required=True);a=p.parse_args()
    if not a.session.isalnum() or len(a.session)>16:raise ValueError('session must be short alphanumeric')
    ctx=subprocess.check_output([KUBECTL,'--kubeconfig',str(KUBE),'config','current-context'],text=True).strip();assert ctx==CTX
    prov=provenance();approval=json.loads((ROOT/'A1_APPROVAL.json').read_text())
    baseline=ROOT/approval['baseline_record'];assert sha(baseline)==approval['baseline_sha256']
    assert json.loads(baseline.read_text()).get('baseline_achieved'),'original setup baseline must pass'
    tests_path=ROOT/'results/tests-A1.json';tests=json.loads(tests_path.read_text())
    assert tests['passed'] and tests['implementation_commit']==prov['implementation_commit'],'tests must pass for current implementation'
    preflight=ROOT/'results/preflight-A1.json';pre=json.loads(preflight.read_text());assert pre['passed'] and pre['implementation_commit']==prov['implementation_commit']
    prov.update(tests_sha256=sha(tests_path),preflight_sha256=sha(preflight),baseline_sha256=sha(baseline))
    cells=[dict(policy='snapshot',condition=c,repetition=1) for c in ['clean','disjoint','same_field','dep_race','dep_race_late']]
    cells.sort(key=lambda x:(hashlib.sha256(f"20261101|{a.phase}|1|{x['policy']}|{x['condition']}".encode()).hexdigest(),x['policy'],x['condition']))
    schedule=ROOT/'results'/f'{a.session}-{a.phase}-schedule.json';exclusive(schedule,dict(seed=20261101,phase=a.phase,cells=cells,**prov));prov['schedule_sha256']=sha(schedule)
    journal=ROOT/'results'/f'{a.session}-session.jsonl'
    for i,cell in enumerate(cells,1):
        with journal.open('a') as f:f.write(json.dumps(dict(utc=utc(),kind='started',phase=a.phase,ordinal=i,cell=cell))+'\n');f.flush();os.fsync(f.fileno())
        result=Run(a.session,a.phase,i,cell['policy'],cell['condition'],prov).execute()
        if not result.get('cleanup_complete'):raise RuntimeError('cleanup incomplete; stop before creating another namespace')
    print('STOP: smoke-A1 review required; main runner is not enabled.',flush=True)
if __name__=='__main__':main()
