import json
from pathlib import Path
from .environment import Environment,PublicAPI
from .reference import grade
from .evidence import assess
from .controllers import run_policy,POLICIES
from .scenarios import development_suite
from .common import require,digest


def run_episode(spec,policy):
    env=Environment(spec);report=run_policy(PublicAPI(env),policy);t=env.finish(report)
    t['policy']=policy;t['grade']=grade(t);t['assessment']=assess(t['task'],t['public'],report)
    return t


def replay(t):
    require(grade(t)==t['grade'],'Grade mismatch')
    env=Environment(t['scenario'])
    for o in t['public']:require(env.invoke(o['tool'],**o['arguments'])==o,'Public replay mismatch')
    rebuilt=env.finish(t['report'])
    for k,v in rebuilt.items():require(v==t[k],'Replay mismatch '+k)
    require(assess(t['task'],t['public'],t['report'])==t['assessment'],'Assessment mismatch')
    return True


def write_suite(output):
    out=Path(output);out.mkdir(parents=True,exist_ok=False);files={};rows=[]
    for s in development_suite():
        for p in POLICIES:
            t=run_episode(s,p);replay(t);name=s['id']+'--'+p+'.json'
            (out/name).write_text(json.dumps(t,indent=2)+'\n');files[name]=digest(t)
            rows.append(dict(scenario=s['id'],policy=p,**t['grade']))
    summary=dict(kind='deterministic development suite',scenarios=36,episodes=len(rows),model_calls=0,rows=rows)
    (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');files['summary.json']=digest(summary)
    (out/'manifest.json').write_text(json.dumps(dict(files=files),indent=2)+'\n')
    return dict(episodes=len(rows),model_calls=0)


def verify_suite(output):
    out=Path(output);m=json.loads((out/'manifest.json').read_text());count=0
    for name,h in m['files'].items():
        require(Path(name).name==name,'Bad path');v=json.loads((out/name).read_text());require(digest(v)==h,'File digest mismatch')
        if name!='summary.json':replay(v);count+=1
    require(count==json.loads((out/'summary.json').read_text())['episodes'],'Episode count mismatch')
    return dict(verified_episodes=count)
