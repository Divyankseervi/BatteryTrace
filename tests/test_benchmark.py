"""Keeps the benchmark honest and runnable: tiny scale, must stay correct against ground truth."""
import sys, unittest
from harness import ROOT
sys.path.insert(0, str(ROOT / 'benchmarks'))
import run_benchmark as rb


class BenchmarkSmoke(unittest.TestCase):
    def test_tiny_scale_all_strategies_correct(self):
        r = rb.run_scale(vehicles=15, seed=3, warmup=0, samples=2)
        self.assertTrue(r['correct'])
        self.assertEqual({x['strategy'] for x in r['results']}, {'recursive_cte', 'frontier_cte', 'app_bfs_n_plus_1', 'closure_table', 'recursive_cte_noidx'})
        self.assertTrue(any('SEARCH' in p and 'idx_relationship_child' in p for p in r['plan_with_index']))
        self.assertTrue(any(p.startswith('SCAN') for p in r['plan_without_index']))


if __name__ == '__main__':
    unittest.main()
