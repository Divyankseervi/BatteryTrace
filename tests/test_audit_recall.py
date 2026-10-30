"""Hash-chain tamper detection and recall correctness against known ground truth."""
import sqlite3, unittest
from harness import DbCase
import audit, recall, services, db
from domain import DomainError
from tools import synthetic


class AuditChainTests(DbCase):
    def test_seed_chain_verifies(self):
        v = audit.verify_chain(self.con)
        self.assertTrue(v['ok']); self.assertEqual(v['checked'], 15); self.assertEqual(len(v['tip_hash']), 64)

    def test_new_events_extend_chain(self):
        services.record_event(self.con, {'asset_code': 'PACK-1001', 'event_type': 'INSPECTED', 'event_at': '2026-10-26', 'location': 'x', 'organization': 'y'}, 'U-SVC')
        v = audit.verify_chain(self.con); self.assertTrue(v['ok']); self.assertEqual(v['checked'], 16)

    def _tamper(self, sql):
        for t in ('trg_event_no_update', 'trg_event_no_delete'):
            self.con.execute(f'DROP TRIGGER IF EXISTS {t}')      # simulates someone editing the .db file directly
        self.con.execute(sql)

    def test_edit_detected_at_exact_row(self):
        self._tamper("UPDATE LifecycleEvent SET notes='quietly changed' WHERE event_id=4")
        v = audit.verify_chain(self.con)
        self.assertFalse(v['ok']); self.assertEqual(v['first_bad_event_id'], 4); self.assertIn('edited', v['reason'])

    def test_delete_from_middle_detected(self):
        self._tamper('DELETE FROM LifecycleEvent WHERE event_id=5')
        v = audit.verify_chain(self.con)
        self.assertFalse(v['ok']); self.assertEqual(v['first_bad_event_id'], 6)

    def test_reorder_detected(self):
        self._tamper("UPDATE LifecycleEvent SET event_id=100 WHERE event_id=3")
        self.con.execute("UPDATE LifecycleEvent SET event_id=3 WHERE event_id=4"); self.con.execute("UPDATE LifecycleEvent SET event_id=4 WHERE event_id=100")
        self.assertFalse(audit.verify_chain(self.con)['ok'])

    def test_known_limitation_tail_truncation_not_detected(self):
        """HONEST LIMIT: deleting the newest rows leaves a valid shorter chain. Anchoring the tip hash elsewhere is needed."""
        tip_before = audit.verify_chain(self.con)['tip_hash']
        self._tamper('DELETE FROM LifecycleEvent WHERE event_id=(SELECT MAX(event_id) FROM LifecycleEvent)')
        v = audit.verify_chain(self.con)
        self.assertTrue(v['ok']); self.assertNotEqual(v['tip_hash'], tip_before)    # only a stored copy of the old tip reveals it

    def test_known_limitation_recomputed_chain_not_detected(self):
        """HONEST LIMIT: someone who edits a row AND recomputes every later hash is undetectable from the DB alone."""
        max_id = self.con.execute('SELECT MAX(event_id) FROM LifecycleEvent').fetchone()[0]
        self._tamper(f"UPDATE LifecycleEvent SET notes='rewritten' WHERE event_id={max_id}")
        r = self.con.execute(f'SELECT * FROM LifecycleEvent WHERE event_id={max_id}').fetchone()
        prev = self.con.execute(f'SELECT event_hash FROM LifecycleEvent WHERE event_id={max_id - 1}').fetchone()[0]
        self.con.execute(f'UPDATE LifecycleEvent SET event_hash=? WHERE event_id={max_id}', (audit.compute_hash(prev, r),))
        self.assertTrue(audit.verify_chain(self.con)['ok'])

    def test_broken_chain_surfaces_as_data_quality_issue(self):
        self._tamper("UPDATE LifecycleEvent SET location='elsewhere' WHERE event_id=2")
        self.assertIn('DQ-005', {i['rule_id'] for i in services.find_issues(self.con)})


class RecallGroundTruthTests(unittest.TestCase):
    """Compare the SQL traversal with the generator's independent expectation. Counts FP/FN explicitly."""

    @classmethod
    def setUpClass(cls):
        cls.con = sqlite3.connect(':memory:'); cls.con.row_factory = sqlite3.Row
        cls.con.execute('PRAGMA foreign_keys=ON'); db.create_schema(cls.con); db.install_triggers(cls.con)   # triggers ON validates the generator too
        cls.gt = synthetic.generate(cls.con, seed=11, vehicles=40)

    def check(self, batch, mode, as_of=None):
        rep = recall.recall_report(self.con, batch=batch, direction='up', mode=mode, as_of=as_of)
        ev = recall.evaluate([a['asset_code'] for a in rep['affected']], self.gt.expected_batch(batch, mode, as_of))
        self.assertEqual((ev['false_positive'], ev['false_negative']), (0, 0), f'{batch} {mode} {as_of}: {ev}')
        self.assertEqual((ev['precision'], ev['recall']), (1.0, 1.0))

    def test_all_batches_all_modes(self):
        for b in self.gt.batch_cells:
            self.check(b, 'CURRENT'); self.check(b, 'ALL')
            for d in ('2023-02-15', '2024-06-01', '2025-01-01', '2026-01-01'):
                self.check(b, 'AS_OF', d)

    def test_modes_differ_when_churn_happened(self):
        sizes = {m: sum(len(self.gt.expected_batch(b, m, '2023-02-15')) for b in self.gt.batch_cells) for m in ('CURRENT', 'ALL')}
        self.assertGreater(sizes['ALL'], sizes['CURRENT'])      # history widens the net (the generator really created churn)

    def test_downward_trace_matches(self):
        pid = next(i for i, c in self.gt.code.items() if c == 'PACK-0003')
        rep = recall.recall_report(self.con, codes=['PACK-0003'], direction='down', mode='CURRENT')
        self.assertEqual({a['asset_code'] for a in rep['affected']}, self.gt.expected_down(pid, 'CURRENT'))

    def test_starts_always_included_at_depth_zero(self):
        rep = recall.recall_report(self.con, batch='SYN-B00', direction='up')
        self.assertEqual({a['asset_code'] for a in rep['affected'] if a['depth'] == 0}, {self.gt.code[c] for c in self.gt.batch_cells['SYN-B00']})


class RecallEdgeCaseTests(DbCase):
    triggers = False   # we need to plant cycles / duplicates / long chains the triggers would forbid

    def link(self, p, c, f='2025-01-01', t=None, typ='CONTAINS'):
        self.con.execute('INSERT INTO AssetRelationship(parent_asset_id,child_asset_id,relationship_type,valid_from,valid_to) VALUES (?,?,?,?,?)', (p, c, typ, f, t))

    def test_cycle_terminates_and_each_asset_once(self):
        self.link('A004', 'A002', typ='CONTAINS')       # cell "contains" its own module: A002 -> A004 -> A002
        rep = recall.recall_report(self.con, codes=['CELL-1001-A1'], direction='up', max_depth=12)
        codes = [a['asset_code'] for a in rep['affected']]
        self.assertEqual(len(codes), len(set(codes)))
        self.assertIn('VEH-2048', codes)
        self.assertFalse(rep['truncated'], 'a cycle must not make the walk run until the depth limit')

    def test_self_reachable_down_cycle(self):
        self.link('A004', 'A001')     # cell -> pack closes a loop
        rep = recall.recall_report(self.con, codes=['PACK-1001'], direction='down', max_depth=12)
        self.assertEqual(len({a['asset_code'] for a in rep['affected']}), len(rep['affected']))

    def test_depth_limit_flags_truncation(self):
        rep = recall.recall_report(self.con, codes=['CELL-1001-A1'], direction='up', max_depth=2)
        self.assertTrue(rep['truncated']); self.assertNotIn('VEH-2048', [a['asset_code'] for a in rep['affected']])
        self.assertIn('DEPTH_LIMIT', [w['code'] for w in rep['warnings']])
        full = recall.recall_report(self.con, codes=['CELL-1001-A1'], direction='up', max_depth=8)
        self.assertFalse(full['truncated'])

    def test_disconnected_asset_warns_instead_of_claiming_complete(self):
        rep = recall.recall_report(self.con, codes=['CELL-4001-A1'], direction='up', mode='ALL')
        rep2 = recall.recall_report(self.con, codes=['STORE-2001'], direction='up')
        self.assertEqual([a['asset_code'] for a in rep2['affected']], ['STORE-2001'])
        self.assertIn('NO_LINKS_FOUND', [w['code'] for w in rep2['warnings']])

    def test_conflicting_parents_included_and_warned(self):
        rep = recall.recall_report(self.con, codes=['CELL-4001-A1'], direction='up')
        codes = {a['asset_code'] for a in rep['affected']}
        self.assertTrue({'MOD-4001-A', 'PACK-4001', 'PACK-5001'} <= codes)     # both branches kept: uncertainty must not hide candidates
        self.assertIn('CONFLICTING_PARENTS', [w['code'] for w in rep['warnings']])

    def test_historical_link_marked(self):
        self.link('A001', 'A013', f='2020-01-01', t='2021-01-01')          # old, closed link
        cur = recall.recall_report(self.con, codes=['CELL-4001-A1'], direction='up', mode='CURRENT')
        allm = recall.recall_report(self.con, codes=['CELL-4001-A1'], direction='up', mode='ALL')
        self.assertNotIn('PACK-1001', [a['asset_code'] for a in cur['affected']])
        hit = [a for a in allm['affected'] if a['asset_code'] == 'PACK-1001'][0]
        self.assertTrue(hit['via_closed_link']); self.assertIn('HISTORICAL_LINK', [w['code'] for w in allm['warnings']])

    def test_as_of_half_open_boundary(self):
        self.link('A001', 'A013', f='2020-01-01', t='2021-01-01')
        on_start = recall.recall_report(self.con, codes=['CELL-4001-A1'], mode='AS_OF', as_of='2020-01-01')
        on_end = recall.recall_report(self.con, codes=['CELL-4001-A1'], mode='AS_OF', as_of='2021-01-01')
        self.assertIn('PACK-1001', [a['asset_code'] for a in on_start['affected']])          # valid_from is inclusive
        self.assertNotIn('PACK-1001', [a['asset_code'] for a in on_end['affected']])         # valid_to is exclusive

    def test_duplicate_paths_counted_not_duplicated(self):
        self.link('A001', 'A004', typ='CONTAINS')       # second path PACK-1001 -> cell, besides via the module
        rep = recall.recall_report(self.con, codes=['CELL-1001-A1'], direction='up')
        pack = [a for a in rep['affected'] if a['asset_code'] == 'PACK-1001']
        self.assertEqual(len(pack), 1); self.assertEqual(pack[0]['path_count'], 2); self.assertEqual(pack[0]['depth'], 1)   # shortest path reported

    def test_input_validation(self):
        for kw, code in ((dict(codes=['NOPE']), 'UNKNOWN_ASSET'), (dict(batch='NOPE'), 'UNKNOWN_BATCH'), (dict(), 'BAD_SCOPE'),
                         (dict(codes=['PACK-1001'], batch='X'), 'BAD_SCOPE'), (dict(codes=['PACK-1001'], direction='sideways'), 'BAD_DIRECTION'),
                         (dict(codes=['PACK-1001'], mode='AS_OF', as_of='nope'), 'BAD_DATE'), (dict(codes=['PACK-1001'], max_depth=0), 'BAD_DEPTH'),
                         (dict(codes=['PACK-1001'], max_depth=999), 'BAD_DEPTH'), (dict(codes=['PACK-1001'], max_depth='x'), 'BAD_DEPTH')):
            with self.assertRaises(DomainError, msg=str(kw)) as cm:
                recall.recall_report(self.con, **kw)
            self.assertEqual(cm.exception.code, code, kw)

    def test_sql_injection_in_batch_is_inert(self):
        with self.assertRaises(DomainError) as cm:
            recall.recall_report(self.con, batch="x' OR '1'='1")
        self.assertEqual(cm.exception.code, 'UNKNOWN_BATCH')

    def test_csv_formula_injection_escaped(self):
        for evil in ('=cmd|calc', '+1', '-1', '@SUM(A1)'):
            self.assertTrue(services.csv_cell(evil).startswith("'"))
        out = services.to_csv(['a'], [{'a': '=HYPERLINK("x")'}]).decode()
        self.assertIn('\'=HYPERLINK', out)

    def test_evaluate_counts_errors(self):
        r = recall.evaluate({'a', 'b', 'x'}, {'a', 'b', 'c'})
        self.assertEqual((r['true_positive'], r['false_positive'], r['false_negative']), (2, 1, 1))


if __name__ == '__main__':
    unittest.main(verbosity=2)
