"""Versioned development cases; no held-out or production claims."""
from copy import deepcopy
from .common import require


def make_scenario(name='single_clean', history='complete'):
    require(history in ('complete', 'truncated', 'redacted'), 'Unknown history mode')
    initial = {'service': {'timeout': 30, 'tls': 'strict'}, 'dependency': {'requires_forward': False}}
    effects = [dict(id='target-service', resource='service', forward={'timeout': 60}, before={'timeout': 30})]
    external = []
    failures = []
    order = []
    stale = False
    capability = 'atomic'
    timing = 'before_read'
    if name in ('single_disjoint', 'multi_disjoint'):
        external = [dict(resource='service', patch={'tls': 'pinned'})]
    elif name in ('single_superseded', 'multi_conflict'):
        external = [dict(resource='service', patch={'timeout': 45})]
    elif name == 'same_value_hidden':
        external = [dict(resource='service', patch={'timeout': 60})]
    elif name == 'dependency_conflict':
        external = [dict(resource='dependency', patch={'requires_forward': True})]
    elif name == 'dependency_race':
        external = [dict(resource='dependency', patch={'requires_forward': True})]
        timing = 'before_write'
    elif name == 'stale_disjoint':
        external = [dict(resource='service', patch={'tls': 'pinned'})]
        stale = True
    elif name not in ('single_clean', 'multi_clean', 'multi_failure', 'lingering_health'):
        raise ValueError('Unknown scenario')
    if name.startswith('multi'):
        initial['worker'] = {'batch': 10, 'region': 'us'}
        effects.append(dict(id='target-worker', resource='worker', forward={'batch': 20}, before={'batch': 10}))
        order = [['target-service', 'target-worker']]
    if name == 'multi_failure':
        failures = ['worker']
    for i, e in enumerate(external):
        e.update(id=f'operator-{i+1}', authorization='approved-external-change')
    return dict(version='itom-v02', id=f'{name}-{history}', name=name, split='development',
                initial=initial, effects=effects, external=external, order=order,
                failures=failures, history=history, stale=stale, timing=timing,
                capability=capability, lingering_health=name == 'lingering_health',
                max_tools=25, horizon=20, tail=5)


def development_suite():
    names = ('single_clean', 'single_disjoint', 'single_superseded', 'same_value_hidden',
             'dependency_conflict', 'dependency_race', 'stale_disjoint', 'multi_clean',
             'multi_disjoint', 'multi_conflict', 'multi_failure', 'lingering_health')
    return [make_scenario(n, h) for n in names for h in ('complete', 'truncated', 'redacted')]


def pilot_cases():
    # Frozen subset before any model call; all development cases, not main-study data.
    return [make_scenario(n, h) for n, h in (
        ('single_clean','complete'), ('single_disjoint','complete'),
        ('same_value_hidden','redacted'), ('single_disjoint','truncated'),
        ('multi_clean','complete'), ('multi_disjoint','complete'),
        ('multi_failure','complete'), ('dependency_race','complete'))]
