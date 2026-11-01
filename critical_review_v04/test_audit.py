import copy
import sys
import unittest
from pathlib import Path
from audit import fresh_history, sensitivities, load, ROOT

sys.path.insert(0, str(ROOT))
from recovery.environment import Environment
from recovery.scenarios import suite
from recovery.policies import run
from recovery.scoring import grade

class AuditTests(unittest.TestCase):
    def make_trace(self, post_history=False):
        spec=next(s for s in suite() if s['name']=='route_failover' and s['variant']=='clean')
        env=Environment(spec)
        report=run(env.task,env.invoke,'field_compensator')
        if post_history:
            o=env.invoke('read_changes',resource_id='route')
            report['evidence_ids'].append(o['evidence_id'])
        return env.finish(report)

    def test_frozen_endpoint_accepts_prewrite_history(self):
        t=self.make_trace()
        self.assertTrue(grade(t)['strict_reported_recovery'])
        self.assertFalse(fresh_history(t))

    def test_postwrite_history_is_accepted(self):
        t=self.make_trace(True)
        self.assertTrue(grade(t)['strict_reported_recovery'])
        self.assertTrue(fresh_history(t))

    def test_uncited_history_rejected(self):
        t=self.make_trace(True)
        t['report']['evidence_ids'].remove(t['public'][-1]['evidence_id'])
        self.assertFalse(fresh_history(t))

    def test_version_disagreement_rejected(self):
        t=self.make_trace(True)
        t['public'][-1]['reply']['result']['current_version']+=1
        self.assertFalse(fresh_history(t))

    def test_exact_bootstrap_preserves_mean(self):
        for r in sensitivities(load(ROOT/'analysis_final/results.json')['heldout']['rows']):
            self.assertEqual(len(r['exact_bootstrap_64_draws']),64)
            self.assertAlmostEqual(sum(r['exact_bootstrap_64_draws'])/64,r['mean'])

if __name__ == '__main__':
    unittest.main()
