"""Synthetic resource APIs with explicit incomplete history and partial recovery."""
from copy import deepcopy
from .common import digest, require


class Environment:
    def __init__(self, spec):
        self.spec = deepcopy(spec)
        self.state = {r: dict(values=deepcopy(v), version=0, provenance={k:'initial' for k in v})
                      for r,v in spec['initial'].items()}
        self.events=[]; self.public=[]; self.operations={}; self.calls=0; self.finished=False
        self.external_done=False; self.stale={}; self.last_write=0
        for e in spec['effects']:
            self._commit(e['resource'],e['forward'],e['id'],'remediator',None)
        self.task=dict(effects=deepcopy(spec['effects']),order=deepcopy(spec['order']),
                      dependency_rule={'resource':'dependency','field':'requires_forward','target':'service'},
                      capability=spec['capability'],resource_ids=list(spec['initial']),
                      recovery_goal='Restore all target before values, preserve approved external changes. Do not undo superseding writes. Escalate if these conflict. Follow declared recovery order.',
                      history_contract='History can be incomplete; unknown provenance is null, not initial ownership.',
                      health_contract='RECOVERED asserts configuration recovery; operational health is measured separately.')
        if spec['timing']=='before_read': self._external()

    def _event(self, kind, **data):
        e=dict(seq=len(self.events)+1,kind=kind,previous=self.events[-1]['hash'] if self.events else '',**deepcopy(data))
        e['hash']=digest(e); self.events.append(e)
        return e['seq']

    def _commit(self,r,patch,op,actor,target):
        before=deepcopy(self.state[r]); after=deepcopy(before)
        after['values'].update(patch); after['version']+=1
        for k in patch: after['provenance'][k]=op
        self.state[r]=after
        self.last_write=self._event('effect',resource=r,patch=patch,operation_id=op,actor=actor,target=target,
                                   authorization='approved-external-change' if actor=='operator' else 'task-contract',
                                   before=before,after=after)
        result=dict(committed=True,operation_id=op,resource=r,version=after['version'])
        self.operations[op]=dict(result=result,patch=deepcopy(patch),target=target)
        return result

    def _external(self):
        if self.external_done:return
        self.external_done=True
        for e in self.spec['external']:
            if self.spec['stale']:self.stale[e['resource']]=deepcopy(self.state[e['resource']])
            self._commit(e['resource'],e['patch'],e['id'],'operator',None)

    def _resolved(self):
        return {e['id']:all(self.state[e['resource']]['values'][k]==v for k,v in e['before'].items())
                for e in self.spec['effects']}

    def _health(self,elapsed=0):
        dependency=not self.state['dependency']['values']['requires_forward'] or all(
            self.state['service']['values'][k]==v for k,v in self.spec['effects'][0]['forward'].items())
        return dict(service=all(self._resolved().values()) and dependency and not self.spec['lingering_health']
                    and elapsed>=3,dependency=dependency)

    def invoke(self,tool,**args):
        require(not self.finished and self.calls<self.spec['max_tools'],'Episode ended or tool cap reached')
        self.calls+=1
        dispatch=self._event('dispatch',tool=tool,arguments=args)
        try:reply={'ok':True,'result':self._dispatch(tool,args)}
        except (ValueError,KeyError,TypeError) as ex:reply={'ok':False,'error':type(ex).__name__,'message':str(ex)}
        obs=dict(evidence_id=f'obs-{self.calls}',tool=tool,arguments=deepcopy(args),reply=reply)
        self._event('observation',dispatch=dispatch,observation=obs)
        self.public.append(deepcopy(obs))
        return deepcopy(obs)

    def _dispatch(self,tool,a):
        allowed={'read_resource':{'resource_id'},'read_changes':{'resource_id'},'read_health':set(),
                 'get_operation':{'operation_id'},'apply_patch':{'resource_id','patch','expected_version','operation_id','target_effect_id'},
                 'record_recovery_audit':{'effect_ids','evidence_ids'},'escalate':{'reason'}}
        require(tool in allowed and set(a)==allowed[tool],'Unknown tool or incorrect argument fields')
        if tool in ('read_resource','read_changes'):
            r=a['resource_id']; require(r in self.state,'Unknown resource')
            if tool=='read_resource':
                view=deepcopy(self.stale.pop(r,self.state[r]))
                if self.spec['history']=='redacted':view['provenance']={k:None for k in view['provenance']}
                return dict(resource_id=r,**view)
            events=[e for e in self.events if e['kind']=='effect' and e['resource']==r]
            complete=self.spec['history']=='complete'
            if not complete:events=[e for e in events if e['actor']!='operator']
            # No before/after snapshots that would silently bypass provenance redaction.
            changes=[{k:deepcopy(e[k]) for k in ('operation_id','actor','authorization','patch','target')} for e in events]
            if self.spec['history']=='redacted': changes=[]
            return dict(complete=complete,current_version=self.state[r]['version'],changes=changes,
                        gap=None if complete else 'History unavailable for part of the resource lifecycle')
        if tool=='read_health':return dict(current=self._health(len(self.events)-self.last_write),window_coverage=1)
        if tool=='get_operation':return deepcopy(self.operations.get(a['operation_id'],{}).get('result',{'committed':False}))
        if tool=='apply_patch':return self._apply(a)
        if tool=='record_recovery_audit':
            require(all(type(a[k]) is list and all(type(x) is str for x in a[k]) for k in a),'Invalid audit lists')
            known={x['evidence_id'] for x in self.public}
            require(all(x in known for x in a['evidence_ids']),'Unknown audit evidence')
            require(all(x in self.operations and self.operations[x]['target'] for x in a['effect_ids']),'Unknown compensation in audit')
            self._event('audit',**a);return {'recorded':True}
        if tool=='escalate':
            require(type(a['reason']) is str and bool(a['reason']),'Reason required')
            self._event('escalation',**a);return {'recorded':True}

    def _apply(self,a):
        r,patch,op=a['resource_id'],a['patch'],a['operation_id']
        require(r in self.state and type(patch) is dict and bool(patch),'Invalid resource/patch')
        require(type(op) is str and op.startswith('recovery-'),'Invalid operation ID')
        require(a['target_effect_id'] in {e['id'] for e in self.spec['effects']},'Unknown target')
        require(a['expected_version'] is None or type(a['expected_version']) is int,'Invalid version')
        require(all(k in self.state[r]['values'] and type(v) is type(self.state[r]['values'][k]) for k,v in patch.items()),'Invalid patch fields/types')
        if op in self.operations:
            old=self.operations[op]
            require(old['result']['resource']==r and old['patch']==patch and old['target']==a['target_effect_id'],'Operation ID intent mismatch')
            return dict(old['result'],replayed=True)
        self._external()
        if a['expected_version'] is not None and a['expected_version']!=self.state[r]['version']:
            return dict(committed=False,conflict=True)
        if r in self.spec['failures']:
            return dict(committed=False,error='PermanentUnavailable',retryable=False)
        return self._commit(r,patch,op,'recovery',a['target_effect_id'])

    def finish(self,report):
        require(not self.finished,'Already finished')
        self._event('terminal',report=report)
        for tick in range(self.spec['horizon']):self._event('health',tick=tick,health=self._health(tick))
        self.finished=True
        return dict(version='itom-trace-v02',scenario=deepcopy(self.spec),task=deepcopy(self.task),
                    events=deepcopy(self.events),public=deepcopy(self.public),report=deepcopy(report),
                    final=deepcopy(self.state),external_occurred=self.external_done and bool(self.spec['external']))


class PublicAPI:
    def __init__(self,env):self.task=deepcopy(env.task);self.__invoke=env.invoke
    def call(self,tool,**args):return self.__invoke(tool,**args)
