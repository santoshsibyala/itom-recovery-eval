"""Offline reference policies; not simulated model observations."""
POLICIES=('snapshot','field_guard','public_runbook')


def run_policy(api,policy='field_guard'):
    if policy not in POLICIES:raise ValueError('Unknown policy')
    evidence=[];done=[];remaining=[e['id'] for e in api.task['effects']]
    def call(tool,**args):
        o=api.call(tool,**args);evidence.append(o['evidence_id'])
        if not o['reply']['ok']:raise ValueError(o['reply']['message'])
        return o['reply']['result']
    def report(status):
        return dict(status=status,resolved_effect_ids=done[:],remaining_effect_ids=remaining[:],evidence_ids=evidence[:])
    def stop(reason):
        call('escalate',reason=reason)
        return report('PARTIAL' if done else 'ESCALATED')
    for index,e in enumerate(api.task['effects']):
        view=call('read_resource',resource_id=e['resource'])
        history=call('read_changes',resource_id=e['resource'])
        if policy!='snapshot':
            if not history['complete'] or any(x is None for x in view['provenance'].values()):return stop('Cannot establish complete authorized history')
            if view['version']!=history['current_version']:
                view=call('read_resource',resource_id=e['resource'])
                if view['version']!=history['current_version']:return stop('Cannot establish current state')
            if any(view['provenance'][k]!=e['id'] for k in e['forward']):return stop('Target fields superseded')
            dep=call('read_resource',resource_id='dependency')
            if dep['values']['requires_forward']:return stop('Dependency forbids inverse')
        patch=dict(e['before'])
        if policy=='snapshot':
            # Include unrelated defaults only for this documented negative control.
            if e['resource']=='service':patch['tls']='strict'
        result=call('apply_patch',resource_id=e['resource'],patch=patch,expected_version=None if policy=='snapshot' else view['version'],
                    operation_id=f'recovery-{index+1}',target_effect_id=e['id'])
        if not result.get('committed'):return stop('Conditional write conflicted or compensation unavailable')
        readback=call('read_resource',resource_id=e['resource'])
        call('record_recovery_audit',effect_ids=[f'recovery-{index+1}'],evidence_ids=evidence[:])
        if not all(readback['values'][k]==x for k,x in e['before'].items()):return stop('Recovery not verified')
        done.append(e['id']);remaining.remove(e['id'])
    return report('RECOVERED')
