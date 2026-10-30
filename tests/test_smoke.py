"""End-to-end smoke tests (the original six, adapted to the v2 API: demo user header + paged responses)."""
from harness import ServerCase


class BatteryTraceSmokeTest(ServerCase):
    def test_health_and_frontend(self):
        st, health, _ = self.get('/api/health')
        self.assertEqual(st, 200); self.assertTrue(health['ok']); self.assertTrue(health['synthetic_data'])
        st, html, _ = self.get('/')
        self.assertIn('BatteryTrace', html); self.assertIn('Synthetic', html)
        for f in ('app.css', 'app.js', 'lab.js'):
            st, body, h = self.get('/static/' + f)
            self.assertEqual(st, 200, f)

    def test_summary_assets_events_and_lineage(self):
        _, s, _ = self.get('/api/summary')
        self.assertEqual(s['assets'], 22); self.assertGreaterEqual(s['events'], 15); self.assertTrue(s['audit']['ok'])
        _, a, _ = self.get('/api/assets?q=PACK-1001')
        self.assertEqual(a['total'], 1); self.assertEqual(a['items'][0]['asset_code'], 'PACK-1001')
        _, ev, _ = self.get('/api/events')
        self.assertGreater(ev['total'], 0)
        _, lin, _ = self.get('/api/lineage/PACK-1001')
        self.assertGreaterEqual(len(lin['nodes']), 3); self.assertGreaterEqual(len(lin['passport_history']), 1)

    def test_seeded_integrity_warnings(self):
        _, issues, _ = self.get('/api/issues')
        codes = {i['code'] for i in issues}
        self.assertEqual(codes, {'RECYCLED_PASSPORT_ACTIVE', 'MULTIPLE_OPEN_PARENTS'})   # exactly the two seeded defects
        self.assertTrue(all(i['rule_id'] and i['evidence'] for i in issues))

    def test_validation_rejects_unknown_asset(self):
        st, body = self.event('NOT-A-REAL-ASSET', 'TESTED')
        self.assertEqual(st, 404); self.assertIn('Unknown asset', body['error']); self.assertEqual(body['code'], 'UNKNOWN_ASSET')


class BatteryTraceWorkflowSmokeTest(ServerCase):
    """Mutating workflows: separate server so read-only tests above see pristine seed data."""

    def test_repurpose_creates_linked_passport_version(self):
        st, body = self.event('PACK-1001', 'REPURPOSED')
        self.assertEqual(st, 201, body)
        _, d, _ = self.get('/api/lineage/PACK-1001')
        self.assertEqual(d['asset']['status'], 'SECOND_LIFE')
        self.assertEqual([p['status'] for p in d['passport_history']], ['ACTIVE', 'SUPERSEDED'])
        self.assertEqual(d['passport_history'][0]['previous_passport_id'], d['passport_history'][1]['passport_id'])

    def test_recycling_closes_active_passport(self):
        st, body = self.event('PACK-5001', 'RECYCLED', user='U-REC')
        self.assertEqual(st, 201, body)
        _, d, _ = self.get('/api/lineage/PACK-5001')
        self.assertEqual(d['asset']['status'], 'RECYCLED'); self.assertEqual(d['passport_history'][0]['status'], 'CLOSED')
        self.assertTrue(all(r['valid_to'] for r in d['relationships'] if 'PACK-5001' in (r['p_code'], r['c_code'])))


if __name__ == '__main__':
    import unittest; unittest.main(verbosity=2)
