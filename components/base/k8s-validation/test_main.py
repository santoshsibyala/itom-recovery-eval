import ast,collections,copy,hashlib,json,pathlib,subprocess,unittest
from main_runner import frozen_schedule,action_for,reconstruct,ROOT,MainRun
from analyze import summarize,render,METRICS
class MainTests(unittest.TestCase):
    def test_schedule_full_balanced_and_round_order(self):
        cells=frozen_schedule();self.assertEqual(len(cells),200);self.assertEqual(set(collections.Counter((x['policy'],x['condition']) for x in cells).values()),{10})
        for rep in range(1,11):
            row=cells[(rep-1)*20:rep*20];self.assertTrue(all(c['repetition']==rep for c in row));keys=[hashlib.sha256(f"20261101|main|{rep}|{c['policy']}|{c['condition']}".encode()).hexdigest() for c in row];self.assertEqual(keys,sorted(keys))
    def test_resume_never_replaces_started_or_finalized_cell(self):
        self.assertEqual(action_for(1,True,{1},True),'skip');self.assertEqual(action_for(2,False,{2},False),'finalize_interrupted');self.assertEqual(action_for(3,False,set(),True),'finalize_interrupted');self.assertEqual(action_for(4,False,set(),False),'execute_once')
    def test_interruption_after_request_is_not_assumed_blocked(self):
        es=[dict(stage='recovery_dispatch',kind='api_request',endpoint='/deployments/app')];r=reconstruct(dict(policy='snapshot',condition='clean',repetition=4),61,{},es);self.assertEqual(r['mutation_outcome'],'unknown');self.assertIsNone(r['metrics']['blocked']);self.assertFalse(r['completed']);self.assertEqual(r['repetition'],4)
    def test_interruption_keeps_known_false_predicate_violation(self):
        p=ROOT/'results/journals/itom-k8s-a120261101-smoke-a1-001.jsonl';es=[json.loads(x) for x in p.read_text().splitlines()];es=es[:next(i for i,e in enumerate(es) if e['kind']=='api_response' and e['stage']=='recovery_dispatch')+1];r=reconstruct(dict(policy='snapshot',condition='dep_race_late',repetition=1),1,{},es);self.assertTrue(r['metrics']['committed_under_false_predicate']);self.assertFalse(r['metrics']['safety']);self.assertIsNone(r['metrics']['image_restored'])
    def test_full_journal_reconstruction_preserves_measured_outcomes(self):
        for n in range(1,6):
            raw=json.loads((ROOT/f'results/smoke-A1/itom-k8s-a120261101-smoke-a1-{n:03d}.json').read_text());es=[json.loads(x) for x in (ROOT/'results/journals'/(raw['run_id']+'.jsonl')).read_text().splitlines()];r=reconstruct(dict(policy=raw['policy'],condition=raw['condition'],repetition=1),n,{},es);self.assertEqual(r['metrics'],raw['metrics'])
    def test_fixed_denominator_keeps_missing_failures_unknowns(self):
        cells=frozen_schedule();i=1;cell=cells[0];records={i:dict(completed=False,fixture_valid=False,metrics={},errors=[{'kind':'fixture'}])};rows=summarize(cells,records);r=next(x for x in rows if x['policy']==cell['policy'] and x['condition']==cell['condition']);self.assertEqual(r['planned'],10);self.assertEqual(r['attempted'],1);self.assertEqual(r['fixture_failures'],1);self.assertEqual(r['missing'],9);self.assertEqual(r['safety_unknown'],10);self.assertEqual(r['successful_recovery_true'],0)
    def test_renderer_setup_limit_and_no_invented_success(self):
        rows=summarize(frozen_schedule(),{});table,draft,info=render(rows);self.assertLessEqual(info['setup_word_count'],120);self.assertEqual(info['result_sentences'],[]);self.assertEqual(info['totals']['missing'],200);self.assertNotIn('/50',draft);self.assertIn('A1',draft);self.assertIn('controller status',draft)
    def test_compact_claims_require_uniform_complete_evidence(self):
        import csv
        with (ROOT/'results/main-analysis/summary.csv').open() as f:rows=[{k:v if k in ('policy','condition') else int(v) for k,v in r.items()} for r in csv.DictReader(f)]
        _,draft,info=render(rows,end_health_verified=True)
        self.assertTrue(all(info['computed_checks'].values()));self.assertEqual(len(info['result_sentences']),5);self.assertNotIn('/50',draft);self.assertIn('| disjoint | O | R | B | R |',draft)
        rows[0]['healthy_true']=9;rows[0]['healthy_false']=1
        _,draft,info=render(rows,end_health_verified=True);self.assertFalse(info['computed_checks']['identical_repetitions']);self.assertNotIn('Outcomes were identical',draft)
    def test_ended_health_needs_terminal_evidence(self):
        import csv
        with (ROOT/'results/main-analysis/summary.csv').open() as f:rows=[{k:v if k in ('policy','condition') else int(v) for k,v in r.items()} for r in csv.DictReader(f)]
        _,draft,_=render(rows);self.assertNotIn('ended healthy',draft)
    def test_approved_policy_and_timing_methods_are_inherited(self):
        from run import Run
        for method in ['experiment','baseline','poll','inject','request','command']:self.assertIs(getattr(MainRun,method),getattr(Run,method))
    def test_main_executor_only_changes_phase_and_output_routing(self):
        import inspect,textwrap
        from run import Run
        old=textwrap.dedent(inspect.getsource(Run.execute)).replace("self.phase in ('smoke','smoke-A1')","self.phase=='main'").replace("ROOT/'results'/self.phase/(self.ns+'.json')","ROOT/'results/raw'/(self.ns+'.json')")
        self.assertEqual(ast.dump(ast.parse(old)),ast.dump(ast.parse(textwrap.dedent(inspect.getsource(MainRun.execute)))))
if __name__=='__main__':unittest.main()
