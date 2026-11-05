import io,unittest
from common import *
suite=unittest.defaultTestLoader.loadTestsFromNames(['test_classify','test_extension'])
s=io.StringIO();r=unittest.TextTestRunner(stream=s,verbosity=2).run(suite)
save(ROOT/'results/tests.json',dict(passed=r.wasSuccessful(),tests_run=r.testsRun,failures=len(r.failures),errors=len(r.errors),utc=utc(),implementation_commit=git('rev-parse','HEAD'),output=s.getvalue(),source_hashes={p.name:sha(p) for p in ROOT.glob('*.py')}))
print(s.getvalue());raise SystemExit(0 if r.wasSuccessful() else 1)
