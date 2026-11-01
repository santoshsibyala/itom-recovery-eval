import json,os,sys
from .server import http
status,result=http(int(sys.argv[1]),'/operator',{})
print(json.dumps(dict(operator_pid=os.getpid(),http_status=status,result=result)),flush=True)
if status!=200:raise SystemExit(1)
