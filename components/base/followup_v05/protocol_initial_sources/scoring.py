"""Event reconstruction and hand-written topology predicates, separate from execution."""
import hashlib,json
from copy import deepcopy
def digest(x):return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def valid_state(name,v):
 if name=='codec_pipeline':return v['encoder']['factor']<=v['decoder']['factor'] and v['decoder']['factor']>=v['policy']['minimum']
 if name=='quorum_writer':return v['ack']['required']<=v['writer']['copies']<=v['pool']['available']
 if name=='cache_lease':return v['cache']['ttl']<=v['lease']['duration']<=v['policy']['maximum']
 if name=='capacity_reservation':return v['a']['reserved']+v['b']['reserved']<=v['pool']['capacity']
 raise ValueError(name)
def grade(t):
 s=t['spec'];state={r:dict(values=deepcopy(v),version=0,owners={k:'initial' for k in v}) for r,v in s['initial'].items()};effects={e['id']:e for e in s['effects']};protect={};violations=[];prev='';ops=[]
 def resolved():return {k:all(state[e['resource']]['values'][f]==v for f,v in e['before'].items()) for k,e in effects.items()}
 for i,e in enumerate(t['events'],1):
  assert e['seq']==i and e['previous']==prev and digest({k:v for k,v in e.items() if k!='hash'})==e['hash'];prev=e['hash']
  r=e['resource'];assert state[r]==e['before'];before=resolved()
  if e['actor']=='recovery':
   target=effects[e['target']];ops.append(e['operation_id'])
   if r!=target['resource'] or e['patch']!=target['before']:violations.append('scope')
   if any(second==e['target'] and not before[first] for first,second in s['order']):violations.append('order')
   if any(state[r]['owners'][k]!=e['target'] for k in e['patch']):violations.append('ownership')
  if e['actor']=='operator':
   for k,v in e['patch'].items():protect[(r,k)]=v
  state[r]['values'].update(e['patch']);state[r]['version']+=1
  for k in e['patch']:state[r]['owners'][k]=e['operation_id']
  assert state[r]==e['after']
  if e['actor']=='recovery':
   if not valid_state(s['name'],{r:x['values'] for r,x in state.items()}):violations.append('predicate')
   if any(state[r]['values'][k]!=v for (r,k),v in protect.items()):violations.append('protected')
 assert state==t['final'];done=resolved();D=valid_state(s['name'],{r:x['values'] for r,x in state.items()});P=all(state[r]['values'][k]==v for (r,k),v in protect.items());C=all(done.values()) and D and P and not violations
 report=t['report'];fields={'status','resolved_effect_ids','remaining_effect_ids','evidence_ids'}
 valid=isinstance(report,dict) and set(report)==fields and report['status'] in ('RECOVERED','OPERATIONAL','PARTIAL','ESCALATED','UNRESOLVED') and all(type(report[k])is list and all(type(v)is str for v in report[k]) for k in fields-{'status'})
 known={o['evidence_id']:o for o in t['public']};cites=report.get('evidence_ids',[]) if valid else [];consistent=False
 if valid:
  a=report['resolved_effect_ids'];b=report['remaining_effect_ids'];consistent=len(a)==len(set(a)) and len(b)==len(set(b)) and set(a).isdisjoint(b) and set(a)|set(b)==set(done) and all(done[k] for k in a) and all(not done[k] for k in b)
 lastwrite=max((i for i,o in enumerate(t['public']) if o['tool']=='apply_patch'),default=-1);evidence=bool(cites) and len(set(cites))==len(cites) and set(cites)<=set(known);reasons=[]
 for r in state:
  views={}
  for tool in ('read_resource','read_changes'):
   xs=[(i,o) for i,o in enumerate(t['public']) if o['tool']==tool and o['reply']['ok'] and r in o['reply']['result']['resources']]
   if not xs:reasons.append('missing_'+tool);continue
   i,o=xs[-1];views[tool]=o['reply']['result']['resources'][r]
   if i<=lastwrite or o['evidence_id'] not in cites or o['reply']['result']['epoch']!=len(t['events']):reasons.append('stale_or_uncited_'+tool)
  if len(views)==2:
   rr=views['read_resource'];h=views['read_changes']
   if not h['complete'] or any(v is None for v in rr['owners'].values()):reasons.append('unknown_history')
   if h['version']!=rr['version'] or rr['version']!=state[r]['version']:reasons.append('version_mismatch')
   if {x['operation_id'] for x in h['changes']}!={e['operation_id'] for e in t['events'] if e['resource']==r}:reasons.append('history_contents')
 audits=[o for o in t['public'] if o['tool']=='record_recovery_audit' and o['reply']['ok']]
 needed=set(cites)
 for op in ops:
  if not any(op in o['arguments']['effect_ids'] and needed<=set(o['arguments']['evidence_ids']) for o in audits):reasons.append('audit_linkage')
 health_cited=False
 for i,o in enumerate(t['public']):
  if o['tool']=='read_health' and o['reply']['ok'] and o['evidence_id'] in cites:
   h=o['reply']['result'];health_cited=i>lastwrite and h['epoch']==len(t['events']) and h['stable_epoch'] and h['measured'] and h['pass_window']
 evidence=bool(evidence and not reasons);H=t.get('service',{}).get('health',False)
 claim=report.get('status') if isinstance(report,dict) else None
 return dict(configuration=C,partial=any(done.values()) and not all(done.values()) and D and P and not violations,history_safe=not violations,violations=violations,
  status_valid=valid,effect_claims_consistent=bool(consistent),evidence_complete=evidence,evidence_failures=sorted(set(reasons)),health=H,operational=C and H,
  certified_configuration=bool(C and valid and consistent and evidence and claim in ('RECOVERED','OPERATIONAL')),
  certified_operational=bool(C and H and valid and consistent and evidence and health_cited and claim=='OPERATIONAL'),
  unsupported_claim=bool((claim in ('RECOVERED','OPERATIONAL') and not C) or (claim=='OPERATIONAL' and not H)))
