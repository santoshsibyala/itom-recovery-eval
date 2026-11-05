"""Read-only refresh of the approved environment checks for main."""
from common import *
from main_execution import main_gate,verify_frozen
import preflight
# Reuse exactly the smoke environment checks; only write a new receipt.
main_gate();verify_frozen()
preflight.gate=main_gate
original_save=preflight.save
def main_save(path,value):
 assert path==ROOT/'results/preflight.json'
 value['bound_implementation_commit']=json.loads((ROOT/'MAIN_APPROVAL.json').read_text())['implementation_commit']
 original_save(ROOT/'results/main-preflight.json',value)
preflight.save=main_save
preflight.check()
