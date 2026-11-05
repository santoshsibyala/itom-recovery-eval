"""Offline verification guard, also loaded by child Python interpreters."""
import os,sys
sys.dont_write_bytecode=True
forbidden=os.environ.get('ITOM_VERIFY_FORBIDDEN_ROOT')
def audit(event,args):
    if event in ('socket.connect','socket.connect_ex','socket.getaddrinfo','socket.bind','urllib.Request','http.client.connect'):
        raise RuntimeError('Network use is disabled during artifact verification')
    if event in ('os.system','os.posix_spawn','os.exec'):
        raise RuntimeError('External commands are disabled during artifact verification')
    if event=='subprocess.Popen' and os.path.realpath(os.fsdecode(args[0]))!=os.path.realpath(sys.executable):
        raise RuntimeError('Only the current Python interpreter may be launched')
    if forbidden and event in ('open','os.listdir','os.scandir') and args and isinstance(args[0],(str,bytes)):
        path=os.path.realpath(os.fsdecode(args[0]))
        if path==forbidden or path.startswith(forbidden+os.sep):
            raise RuntimeError('Verification attempted to access the original workspace')
sys.addaudithook(audit)
