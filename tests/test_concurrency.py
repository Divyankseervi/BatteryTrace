"""Concurrent writers against the real HTTP server (separate connections, real SQLite locking)."""
import threading
from harness import ServerCase


class ConcurrencyTests(ServerCase):
    def run_threads(self, fns):
        out, lock = [], threading.Lock()
        def wrap(f):
            r = f()
            with lock: out.append(r)
        ts = [threading.Thread(target=wrap, args=(f,)) for f in fns]
        [t.start() for t in ts]; [t.join(30) for t in ts]
        return out

    def test_same_idempotency_key_from_many_clients_creates_one_event(self):
        res = self.run_threads([lambda: self.event('PACK-1001', 'INSPECTED', idempotency_key='race-1') for _ in range(10)])
        self.assertEqual(len(res), 10)
        self.assertTrue(all(st in (200, 201) for st, _ in res), res)
        self.assertEqual(sum(1 for st, _ in res if st == 201), 1)             # exactly one real write
        self.assertEqual(len({b['event_id'] for _, b in res}), 1)             # everyone got the same event
        _, p, _ = self.get('/api/events?asset=PACK-1001&type=INSPECTED'); self.assertEqual(p['total'], 1)

    def test_competing_state_changes_only_one_wins(self):
        """Two clients try to REPURPOSE the same ACTIVE pack. Without serialization both could pass the 'is ACTIVE' check."""
        res = self.run_threads([lambda: self.event('PACK-5001', 'REPURPOSED') for _ in range(6)])
        codes = sorted(st for st, _ in res)
        self.assertEqual(codes.count(201), 1, res); self.assertEqual(codes.count(409), 5, res)
        _, d, _ = self.get('/api/lineage/PACK-5001')
        self.assertEqual(sum(1 for p in d['passport_history'] if p['status'] == 'ACTIVE'), 1); self.assertEqual(len(d['passport_history']), 2)

    def test_parallel_distinct_writes_keep_hash_chain_valid(self):
        n0 = self.get('/api/summary')[1]['events']
        res = self.run_threads([lambda i=i: self.event('PACK-2001', 'INSPECTED', notes=f'parallel {i}') for i in range(12)])
        self.assertTrue(all(st == 201 for st, _ in res), res)
        _, v, _ = self.get('/api/audit/verify')
        self.assertTrue(v['ok'], v); self.assertEqual(v['checked'], n0 + 12)

    def test_concurrent_transfers_never_create_two_open_parents(self):
        mk = lambda p: (lambda: self.post('/api/transfers', {'child_code': 'MOD-1001-B', 'new_parent_code': p, 'effective_date': '2026-10-20', 'reason': 'race'}))
        res = self.run_threads([mk('PACK-5001'), mk('PACK-4001'), mk('PACK-5001'), mk('PACK-4001')])
        self.assertEqual(sum(1 for st, _ in res if st == 201), 1, res)
        _, r, _ = self.get('/api/recall?codes=MOD-1001-B&direction=up')
        self.assertNotIn('CONFLICTING_PARENTS', [w['code'] for w in r['warnings']])


if __name__ == '__main__':
    import unittest; unittest.main(verbosity=2)
