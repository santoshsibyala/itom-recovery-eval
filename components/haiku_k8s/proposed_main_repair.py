"""PROPOSED, NOT ACTIVE: add main lifecycle dispatch without changing experiment code."""
from common import *
from harness import ExtensionRun,base
from classify import classify
FixtureError=base.FixtureError; ApiError=base.ApiError; exclusive=base.exclusive; time=base.time; CLUSTER=base.CLUSTER
class MainRun(ExtensionRun):
    def execute(self):
        try:
            self.baseline()
            if self.phase in ('smoke','smoke-A1','main'):self.experiment()
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
            if self.phase in ('smoke','smoke-A1','main'):
                try:self.r['metrics']=classify(self.r)
                except Exception as e:self.error('classifier',e)
            self.event('finished',completed=self.r.get('completed'),metrics=self.r.get('metrics'),errors=len(self.r['errors']));self.f.close();self.api.close()
            self.r['journal_sha256']=sha(self.journal);exclusive(ROOT/'results'/self.phase/(self.ns+'.json'),self.r)
            print(json.dumps({'run':self.ns,'policy':self.r['policy'],'condition':self.r['condition'],'completed':self.r.get('completed'),'metrics':self.r.get('metrics'),'errors':len(self.r['errors'])}),flush=True)
        return self.r
