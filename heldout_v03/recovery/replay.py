from .environment import Environment
from .scoring import grade
from .common import require

def verify(t):
 require(grade(t)==t['grade'],'Independent grade mismatch')
 env=Environment(t['spec']);require(env.task==t['task'],'Task mismatch')
 for o in t['public']:require(env.invoke(o['tool'],**o['arguments'])==o,'Public replay mismatch')
 rebuilt=env.finish(t['report'])
 for k,v in rebuilt.items():require(v==t[k],'Replay mismatch '+k)
 return True
