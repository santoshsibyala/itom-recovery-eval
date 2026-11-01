"""Offline tests exercise the actual experiment request path, without API calls."""
import copy,itertools,unittest
from unittest.mock import patch
from run import Run,ApiError,GOOD,BAD

def deployment(rv='100',image=BAD):
    return {'apiVersion':'apps/v1','kind':'Deployment','metadata':{'name':'app','namespace':'test','uid':'uid','resourceVersion':rv,'generation':2,'labels':{'keep':'label'},'annotations':{'keep':'annotation'},'managedFields':[{'manager':'agent','fieldsType':'FieldsV1','fieldsV1':{'f:spec':{'f:replicas':{},'f:template':{'f:spec':{'f:containers':{'k:{"name":"app"}':{'f:image':{}}}}}}}}]},'spec':{'replicas':3,'strategy':{'type':'Recreate'},'template':{'spec':{'containers':[{'name':'app','image':image,'env':[{'name':'APP_MODE','valueFrom':{'configMapKeyRef':{'name':'app-config','key':'mode'}}}]}]}}},'status':{'observedGeneration':2}}

class RequestTests(unittest.TestCase):
    def exercise(self,policy='snapshot',condition='disjoint',failure=None,initial_mode='v1'):
        obj=Run.__new__(Run);obj.ns='test';obj.dp='/deployment';obj.cp='/configmap';obj.seq=0;obj.stage='init';calls=[];events=[]
        baseline=deployment('baseline',GOOD);baseline['spec']['replicas']=2;original=copy.deepcopy(baseline)
        obj.r={'policy':policy,'condition':condition,'baseline_deployment':baseline,'health_series':[],'errors':[]}
        live=deployment('100');prepared_live=[]
        def event(kind,**kw):obj.seq+=1;events.append((kind,obj.stage,copy.deepcopy(kw)));return {}
        obj.event=event;obj.apply=lambda *a,**kw:deployment()
        def get(path,visibility='observer_only'):
            events.append(('GET',obj.stage,{'path':path,'visibility':visibility}))
            if path==obj.cp:
                val=initial_mode
                if condition in ('dep_race','dep_race_late') and obj.r.get('injection_verified'):val='v2'
                return {'data':{'mode':val}}
            d=copy.deepcopy(live)
            if obj.stage=='policy_prepare':d['metadata']['resourceVersion']='fresh-200';prepared_live.append(copy.deepcopy(d))
            if obj.stage=='predispatch_observation':d['metadata']['resourceVersion']='observer-300'
            return d
        obj.get=get
        def inject():
            obj.stage='operator_injection';event('injection_ack');obj.r['injection_verified']=True
            if condition=='same_field':live['spec']['replicas']=4
            if condition=='disjoint':live['spec']['template']['spec']['containers'][0]['env'].append({'name':'OPERATOR_NOTE','value':'preserve-me'})
        obj.inject=inject
        def request(*args):
            calls.append(copy.deepcopy(args));event('mutation')
            if failure:raise failure
            return copy.deepcopy(live)
        obj.request=request
        obj.poll=lambda:{'http_code':0,'current_available_replicas':0,'healthy':False}
        obj.error=lambda kind,e:obj.r['errors'].append({'kind':kind,'type':type(e).__name__})
        with patch('run.time.monotonic',side_effect=itertools.count()),patch('run.time.sleep'):
            obj.experiment()
        self.assertEqual(original,baseline,'request preparation must not mutate baseline evidence')
        return obj,calls,events,prepared_live
    def test_snapshot_full_baseline_spec_without_rv_status_or_managed_fields(self):
        o,c,e,live=self.exercise();self.assertEqual(len(c),1);method,path,body,ctype,manager,force,visibility=c[0]
        self.assertEqual((method,ctype,manager,force),('PUT','application/json','recovery-snapshot',None));self.assertNotIn('resourceVersion',body['metadata']);self.assertNotIn('managedFields',body['metadata']);self.assertNotIn('status',body)
        self.assertEqual(body['spec'],o.r['baseline_deployment']['spec']);self.assertEqual(body['metadata'],{k:v for k,v in live[0]['metadata'].items() if k not in ('resourceVersion','managedFields')});self.assertIn('resourceVersion',live[0]['metadata'])
    def test_snapshot_fresh_get_after_early_injection(self):
        o,c,events,_=self.exercise();inj=next(i for i,x in enumerate(events) if x[0]=='injection_ack');fresh=next(i for i,x in enumerate(events) if x[0]=='GET' and x[2].get('visibility')=='policy_metadata_only');mut=next(i for i,x in enumerate(events) if x[0]=='mutation');self.assertLess(inj,fresh);self.assertLess(fresh,mut)
        self.assertEqual(sum(x[0]=='GET' and x[2].get('path')==o.cp and x[2].get('visibility')=='policy_visible' for x in events),1)
    def test_late_injection_after_prepared_intent_and_before_put(self):
        o,c,events,_=self.exercise(condition='dep_race_late');idx=lambda k:next(i for i,x in enumerate(events) if x[0]==k)
        self.assertLess(idx('prepared_intent'),idx('injection_ack'));self.assertLess(idx('injection_ack'),idx('mutation'));self.assertEqual(len(c),1)
    def test_snapshot_explicit_rejection_has_no_retry_or_force(self):
        o,c,_,_=self.exercise(failure=ApiError(409,{'reason':'Conflict'}));self.assertEqual(len(c),1);self.assertIsNone(c[0][5]);self.assertEqual(o.r['mutation_outcome'],'rejected');self.assertEqual(o.r['report'],{'status':'BLOCKED','claims':{}})
    def test_snapshot_timeout_has_no_retry_and_unknown_commit(self):
        o,c,_,_=self.exercise(failure=TimeoutError('synthetic transport timeout'));self.assertEqual(len(c),1);self.assertIsNone(c[0][5]);self.assertEqual(o.r['mutation_outcome'],'unknown');self.assertEqual(o.r['report'],{'status':'PARTIAL','claims':{},'commit_unknown':True})
    def test_initial_false_predicate_still_blocks(self):
        o,c,_,_=self.exercise(initial_mode='v2');self.assertEqual(c,[]);self.assertEqual(o.r['report'],{'status':'BLOCKED','claims':{}})
    def test_cas_keeps_original_rv_test_and_predicate_recheck(self):
        o,c,events,_=self.exercise(policy='object_cas');self.assertEqual(len(c),1);self.assertEqual(c[0][0],'PATCH');self.assertEqual(c[0][3],'application/json-patch+json');self.assertEqual(c[0][2],[{'op':'test','path':'/metadata/resourceVersion','value':'100'},{'op':'replace','path':'/spec/replicas','value':2},{'op':'replace','path':'/spec/template/spec/containers/0/image','value':GOOD}]);self.assertIsNone(c[0][5]);self.assertEqual(sum(x[0]=='GET' and x[2].get('path')==o.cp and x[2].get('visibility')=='policy_visible' for x in events),2)
    def test_cas_rejection_still_has_one_request_no_retry(self):
        o,c,_,_=self.exercise(policy='object_cas',failure=ApiError(422,{}));self.assertEqual(len(c),1);self.assertEqual(o.r['mutation_outcome'],'rejected');self.assertIsNone(c[0][5])
    def test_field_comp_request_unchanged(self):
        o,c,_,_=self.exercise(policy='field_comp');self.assertEqual(c[0][0],'PATCH');self.assertEqual(c[0][3],'application/strategic-merge-patch+json');self.assertEqual(c[0][4],'recovery-field');self.assertIsNone(c[0][5]);self.assertEqual(c[0][2],{'spec':{'replicas':2,'template':{'spec':{'containers':[{'name':'app','image':GOOD}]}}}})
if __name__=='__main__':unittest.main()
