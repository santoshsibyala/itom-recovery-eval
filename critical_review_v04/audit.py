"""Read-only, post-hoc diagnostics. No provider clients; frozen scores are not edited."""
import hashlib
import itertools
import json
import os
from pathlib import Path
from collections import Counter

HERE = Path(__file__).resolve().parent
ITOM = HERE.parent
ROOT = ITOM / 'heldout_v03'

def load(path):
    return json.loads(path.read_text())

def fresh_history(t):
    """Additional cited complete history AFTER last write attempt, matching final read version.

    This is an observation-order diagnostic, not a freshness guarantee or new frozen score.
    Only target resources are covered, just as in the original endpoint.
    """
    report = t['report']
    if not isinstance(report, dict) or not isinstance(report.get('evidence_ids'), list):
        return False
    cites = report['evidence_ids']
    for r in {e['resource'] for e in t['spec']['effects']}:
        obs = [(i, o) for i, o in enumerate(t['public']) if o['arguments'].get('resource_id') == r]
        writes = [i for i, o in obs if o['tool'] == 'apply_patch']
        cutoff = max(writes, default=-1)
        reads = [(i, o) for i, o in obs if o['tool'] == 'read_resource' and o['reply']['ok']]
        histories = [(i, o) for i, o in obs if o['tool'] == 'read_changes' and o['reply']['ok']]
        if not reads or not histories:
            return False
        ri, read = reads[-1]
        hi, hist = histories[-1]
        if not (ri > cutoff and hi > cutoff and read['evidence_id'] in cites and hist['evidence_id'] in cites):
            return False
        if not hist['reply']['result']['complete'] or hist['reply']['result']['current_version'] != read['reply']['result']['version']:
            return False
    return True

def sensitivities(rows):
    result = []
    for model in sorted({r['model'] for r in rows}):
        rr = [r for r in rows if r['model'] == model]
        for metric, subset in [('unsupported_completion', None), ('configuration_recovery', {'clean', 'disjoint'})]:
            selected = [r for r in rr if subset is None or r['variant'] in subset]
            templates = sorted({r['template'] for r in selected})
            means = {}
            family = {}
            for t in templates:
                cells = [r for r in selected if r['template'] == t]
                arms = {a: [r[metric] for r in cells if r['arm'] == a] for a in ('ordinary', 'verify')}
                assert len(arms['ordinary']) == len(arms['verify'])
                means[t] = (sum(arms['verify']) - sum(arms['ordinary'])) / len(arms['ordinary'])
                family[t] = cells[0]['family']
            fams = sorted(set(family.values()))
            draws_by_family = [list(itertools.product([t for t in templates if family[t] == f], repeat=2)) for f in fams]
            exact = sorted(sum(means[t] for pair in draw for t in pair) / 6 for draw in itertools.product(*draws_by_family))
            assert len(exact) == 64
            loo_t = {t: sum(v for k,v in means.items() if k != t)/5 for t in templates}
            loo_f = {f: sum(v for k,v in means.items() if family[k] != f)/4 for f in fams}
            result.append(dict(model=model,metric=metric,template_differences=means,
                mean=sum(means.values())/6,leave_one_template_out=loo_t,leave_one_family_out=loo_f,
                exact_bootstrap_64_draws=exact,exact_percentile_interval=[exact[1],exact[62]],
                note='Post-hoc exact enumeration; percentile quantiles use inverse empirical CDF. Not a randomization test or significance test.'))
    return result

def main():
    existing = load(ROOT/'analysis_final/results.json')
    traces = [load(p) for p in sorted((ROOT/'study/heldout').glob('*.trace.json'))]
    service = [load(p) for p in sorted((ROOT/'service_study/models').glob('*.trace.json'))]
    evidence = []
    for cohort, ts in [('heldout',traces),('service',service)]:
        strict = [t for t in ts if t['grade']['strict_reported_recovery']]
        passing = [t for t in strict if fresh_history(t)]
        evidence.append(dict(cohort=cohort,n=len(ts),frozen_strict=len(strict),fresh_history_strict=len(passing),
            removed_ids=[t['cell']['id'] for t in strict if not fresh_history(t)]))
    errors = []
    for model in sorted({t['cell']['model'] for t in traces}):
        for arm in ('ordinary','verify'):
            ts = [t for t in traces if (t['cell']['model'],t['cell']['arm']) == (model,arm)]
            unsupported = sum(t['grade']['unsupported_completion'] for t in ts)
            invalid = sum(not t['grade']['status_format_valid'] for t in ts)
            union = sum(t['grade']['unsupported_completion'] or not t['grade']['status_format_valid'] for t in ts)
            errors.append(dict(model=model,arm=arm,n=len(ts),unsupported=unsupported,invalid_report=invalid,
                unsupported_or_invalid=union,report_categories=dict(Counter(str(t['report'].get('status','NO_STATUS')) for t in ts))))
    violations = Counter(v['kind'] for t in traces for v in t['grade']['violations'])
    violating_traces = {k:sum(any(v['kind']==k for v in t['grade']['violations']) for t in traces) for k in violations}
    partial_bad = []
    # Use the frozen independent predicates without importing any provider code.
    import sys
    sys.path.insert(0,str(ROOT))
    from recovery.scoring import constraints
    for t in traces:
        if t['grade']['partial_recovery'] and not constraints(t['spec']['name'], {r:v['values'] for r,v in t['final'].items()}):
            partial_bad.append(t['cell']['id'])
    health_thresholds = []
    for threshold in (18,19,20):
        healthy = [t for t in service if all(w['correct'] >= threshold for w in t['service']['terminal_windows'])]
        health_thresholds.append(dict(required_per_20=threshold,healthy=len(healthy),operational=sum(t['grade']['configuration_recovery'] for t in healthy)))
    cross = Counter((bool(t['grade']['configuration_recovery']),bool(t['service']['health_pass'])) for t in service)
    iam = load(ITOM/'IAM_RELOCATION_MANIFEST.json')['files']
    iamroot = ITOM.parent/'IAM'
    changed=[]
    for rel, info in iam.items():
        p=iamroot/rel
        if 'symlink' in info:
            good=p.is_symlink() and os.readlink(p)==info['symlink']
        else:
            good=p.is_file() and hashlib.sha256(p.read_bytes()).hexdigest()==info['sha256']
        if not good: changed.append(rel)
    actual={str(p.relative_to(iamroot)) for p in iamroot.rglob('*') if p.is_file() or p.is_symlink()}
    manifest=load(ITOM/'ITOM_v03_RELEASE_MANIFEST.json')['files']
    altered=[name for name,d in manifest.items() if not (ITOM/name).is_file() or hashlib.sha256((ITOM/name).read_bytes()).hexdigest()!=d]
    import sqlite3
    with sqlite3.connect('file:'+str(ITOM/'prototype_v02/live_state/budget.sqlite3')+'?mode=ro',uri=True) as db:
        n,settled,pending=db.execute('select count(*), sum(coalesce(settled,0)), sum(case when settled is null then reserved else 0 end) from calls').fetchone()
        cap=db.execute('select cap from config').fetchone()[0]
    budget=dict(attempts=n,settled_upper_usd=settled/1e9,pending_reserved_usd=pending/1e9,total_bound_usd=(settled+pending)/1e9,cap_usd=cap/1e9,new_calls=0)
    assert n==existing['budget']['attempts'] and settled+pending<=cap
    result=dict(status='Post-hoc diagnostics; original endpoints and trials unchanged',evidence_sensitivity=evidence,
        paired_sensitivity=sensitivities(existing['heldout']['rows']),report_sensitivity=errors,
        historical_violation_trace_counts=violating_traces,partial_recoveries_with_false_terminal_predicate=partial_bad,
        service_threshold_sensitivity=health_thresholds,service_cross_tab={f'C={c},V={v}':count for (c,v),count in cross.items()},
        budget=budget,preservation=dict(iam_verified=len(iam),iam_changed_or_missing=changed,iam_extra=sorted(actual-set(iam)),
        historical_release_verified=len(manifest),historical_release_changed=altered))
    assert not changed and not actual-set(iam) and not altered
    (HERE/'audit_results.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('paired_sensitivity',)},indent=2))

if __name__ == '__main__':
    main()
