"""HTTP layer: security headers, validation, error format, SQL lab sandbox, exports, pagination."""
import json, socket
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from harness import ServerCase


class ApiSecurityTests(ServerCase):
    def test_security_headers_and_no_cors(self):
        st, _, h = self.get('/')
        self.assertIn("script-src 'self'", h['Content-Security-Policy']); self.assertEqual(h['X-Content-Type-Options'], 'nosniff')
        st, _, h = self.get('/api/health')
        self.assertIsNone(h.get('Access-Control-Allow-Origin'))

    def test_bad_host_header_refused(self):
        s = socket.create_connection(('127.0.0.1', self.port)); s.sendall(b'GET /api/health HTTP/1.1\r\nHost: evil.example\r\nConnection: close\r\n\r\n')
        data = s.recv(4096).decode(); s.close()
        self.assertIn('403', data.split('\r\n')[0])

    def test_writes_need_json_and_same_origin(self):
        st, b = self.post('/api/events', {}, headers={'Content-Type': 'text/plain'}, raw=b'{}')
        self.assertEqual((st, b['code']), (415, 'BAD_CONTENT_TYPE'))
        st, b = self.post('/api/events', {}, headers={'Origin': 'http://evil.example'})
        self.assertEqual((st, b['code']), (403, 'BAD_ORIGIN'))

    def test_malformed_and_oversized_bodies(self):
        self.assertEqual(self.post('/api/events', None, raw=b'{not json')[1]['code'], 'BAD_JSON')
        self.assertEqual(self.post('/api/events', None, raw=b'[1,2]')[1]['code'], 'BAD_JSON')
        st, b = self.post('/api/events', None, raw=b'{"notes":"' + b'x' * 30000 + b'"}')
        self.assertEqual((st, b['code']), (413, 'TOO_LARGE'))

    def test_write_requires_demo_user(self):
        st, b = self.event('PACK-1001', 'INSPECTED', user=None)
        self.assertEqual((st, b['code']), (401, 'NO_USER'))
        st, b = self.event('PACK-1001', 'INSPECTED', user='U-NOPE')
        self.assertEqual((st, b['code']), (401, 'UNKNOWN_USER'))

    def test_errors_never_leak_internals(self):
        for path in ('/api/lineage/%27%3Bdrop', '/api/nothing', '/static/../server.py', '/static/server.py', '/etc/passwd'):
            st, body, _ = self.get(path)
            text = json.dumps(body)
            self.assertGreaterEqual(st, 400); self.assertNotIn('Traceback', text); self.assertNotIn('/home/', text)
        st, body, _ = self.get('/api/recall?codes=NOPE'); self.assertEqual((st, body['code']), (404, 'UNKNOWN_ASSET'))

    def test_sql_injection_in_search_is_inert(self):
        st, body, _ = self.get("/api/assets?q=%27%20OR%201%3D1--")
        self.assertEqual(st, 200); self.assertEqual(body['total'], 0)
        st, body, _ = self.get('/api/assets?status=ACTIVE%27%3B%20DROP%20TABLE%20Asset')
        self.assertEqual(body['total'], 22)     # unknown status value is ignored, not executed
        st, s, _ = self.get('/api/summary'); self.assertEqual(s['assets'], 22)


class ApiReadTests(ServerCase):
    def test_pagination_bounds(self):
        _, p, _ = self.get('/api/assets?limit=5&offset=10'); self.assertEqual((len(p['items']), p['total'], p['limit'], p['offset']), (5, 22, 5, 10))
        _, p, _ = self.get('/api/assets?limit=99999'); self.assertEqual(p['limit'], 200)
        st, b, _ = self.get('/api/assets?limit=abc'); self.assertEqual((st, b['code']), (400, 'BAD_PAGING'))

    def test_filters_and_sorting(self):
        _, p, _ = self.get('/api/assets?type=CELL'); self.assertEqual({i['asset_type'] for i in p['items']}, {'CELL'})
        _, p, _ = self.get('/api/assets?batch=NC-2024-W03'); self.assertEqual(p['total'], 2)
        _, p, _ = self.get('/api/events?type=RECYCLED'); self.assertEqual(p['total'], 1)
        _, p, _ = self.get('/api/events?asset=PACK-1001'); self.assertEqual(p['total'], 3)

    def test_assets_csv_export(self):
        st, text, h = self.get('/api/assets.csv?type=BATTERY_PACK')
        self.assertIn('text/csv', h['Content-Type']); self.assertIn('attachment', h['Content-Disposition'])
        lines = text.lstrip('\ufeff').strip().split('\r\n'); self.assertEqual(len(lines), 1 + 9); self.assertIn('"asset_code"', lines[0])

    def test_recall_endpoint_and_csv(self):
        _, r, _ = self.get('/api/recall?batch=NC-2024-W03&direction=up')
        self.assertEqual({a['asset_code'] for a in r['affected']}, {'CELL-1001-A1', 'CELL-1001-A2', 'MOD-1001-A', 'PACK-1001', 'VEH-2048'})
        self.assertIn('disclaimer', r); self.assertEqual(r['scope']['batch_code'], 'NC-2024-W03')
        st, text, h = self.get('/api/recall.csv?batch=NC-2024-W03'); self.assertIn('recall', h['Content-Disposition']); self.assertEqual(len(text.strip().split('\r\n')), 6)

    def test_meta_rules_schema_users(self):
        _, m, _ = self.get('/api/meta'); self.assertIn('REPAIRED', m['transitions']); self.assertEqual(m['transitions']['REPAIRED']['from'], ['IN_REPAIR'])
        _, r, _ = self.get('/api/rules'); self.assertEqual(len(r), 7); self.assertTrue(all('sql' in x for x in r))
        _, s, _ = self.get('/api/schema'); names = {o['name'] for o in s['objects']}
        self.assertTrue({'Asset', 'v_asset_overview', 'trg_event_no_update', 'idx_relationship_child'} <= names); self.assertEqual(s['row_counts']['Asset'], 22)
        self.assertEqual(sum(1 for o in s['objects'] if o['type'] == 'trigger'), 11)   # the lab/README say 11
        _, u, _ = self.get('/api/users'); self.assertEqual({x['role'] for x in u}, {'MANUFACTURER', 'SERVICE', 'RECYCLER', 'AUDITOR'})
        _, v, _ = self.get('/api/audit/verify'); self.assertTrue(v['ok'])


class SqlLabTests(ServerCase):
    def sql(self, q):
        return self.post('/api/sql', {'sql': q}, user=None)

    def test_select_and_explain_work(self):
        st, b = self.sql("SELECT asset_code, status FROM Asset WHERE asset_type='BATTERY_PACK' ORDER BY 1")
        self.assertEqual(st, 200); self.assertEqual(b['columns'], ['asset_code', 'status']); self.assertEqual(len(b['rows']), 9)
        st, b = self.sql('EXPLAIN QUERY PLAN SELECT * FROM LifecycleEvent WHERE asset_id=\'A001\' ORDER BY event_at DESC')
        self.assertEqual(st, 200); self.assertIn('idx_event_asset_time', json.dumps(b['rows']))      # the planner really uses the index
        st, b = self.sql('WITH RECURSIVE n(x) AS (SELECT 1 UNION ALL SELECT x+1 FROM n WHERE x<5) SELECT x FROM n')
        self.assertEqual([r[0] for r in b['rows']], [1, 2, 3, 4, 5])

    def test_views_usable(self):
        st, b = self.sql('SELECT asset_code, open_parents FROM v_asset_overview WHERE open_parents > 1'); self.assertEqual(b['rows'], [['MOD-4001-A', 2]])

    def test_writes_and_ddl_refused_and_data_intact(self):
        for q in ("DELETE FROM Asset", "DROP TABLE Asset", "UPDATE Asset SET status='ACTIVE'", "INSERT INTO AppUser VALUES ('x','x','x','AUDITOR')",
                  "PRAGMA writable_schema=1", "ATTACH DATABASE 'x.db' AS x", "CREATE TABLE t(a)", "WITH x AS (SELECT 1) DELETE FROM Asset",
                  "SELECT 1; DROP TABLE Asset", "", "   ;  ", "VACUUM"):
            st, b = self.sql(q); self.assertEqual(st, 400, q); self.assertIn(b['code'], ('READ_ONLY', 'MULTI_STATEMENT', 'EMPTY_SQL', 'SQL_ERROR'), q)
        _, s, _ = self.get('/api/summary'); self.assertEqual(s['assets'], 22)

    def test_load_extension_and_dangerous_functions_refused(self):
        st, b = self.sql("SELECT load_extension('x')"); self.assertEqual(st, 400)

    def test_row_cap_and_timeout(self):
        st, b = self.sql('WITH RECURSIVE n(x) AS (SELECT 1 UNION ALL SELECT x+1 FROM n WHERE x<5000) SELECT x FROM n')
        self.assertEqual((len(b['rows']), b['truncated']), (200, True))
        st, b = self.sql('WITH RECURSIVE n(x) AS (SELECT 1 UNION ALL SELECT x+1 FROM n) SELECT COUNT(*) FROM n')
        self.assertEqual((st, b['code']), (400, 'SQL_TIMEOUT'))

    def test_sql_syntax_error_is_friendly(self):
        st, b = self.sql('SELECT FROM WHERE'); self.assertEqual((st, b['code']), (400, 'SQL_ERROR'))


if __name__ == '__main__':
    import unittest; unittest.main(verbosity=2)


class LabQueryTests(ServerCase):
    def test_every_canned_lab_query_runs_and_has_content(self):
        st, qs, _ = self.get('/api/lab-queries')
        self.assertGreaterEqual(len(qs), 15); self.assertEqual(len({q['id'] for q in qs}), len(qs))
        for q in qs:
            st, b = self.post('/api/sql', {'sql': q['sql']}, user=None)
            self.assertEqual(st, 200, (q['id'], b)); self.assertTrue(b['columns'], q['id'])
            if not q['id'] in ('outer-join',):     # all others must return rows on the pristine seed
                self.assertGreater(len(b['rows']), 0, q['id'])

    def test_lab_answers_are_correct_not_just_non_empty(self):
        run = lambda i: self.post('/api/sql', {'sql': next(q['sql'] for q in self.get('/api/lab-queries')[1] if q['id'] == i)}, user=None)[1]['rows']
        self.assertEqual(run('recursive'), [[0, 'CELL-1001-A1', 'CELL'], [1, 'MOD-1001-A', 'MODULE'], [2, 'PACK-1001', 'BATTERY_PACK'], [3, 'VEH-2048', 'VEHICLE']])
        self.assertEqual(run('integrity'), [['MOD-4001-A', 2, 'PACK-4001, PACK-5001']])
        self.assertEqual({r[0] for r in run('time-travel')}, {'PACK-4001', 'PACK-5001'})
        self.assertIn('USING INDEX idx_event_asset_time', ' '.join(r[-1] for r in run('explain-index')))
        self.assertIn('SCAN', ' '.join(r[-1] for r in run('explain-scan')))


class SqlGuardLayerTests(__import__('unittest').TestCase):
    """Each defensive layer is tested on its own, because the layers overlap and would otherwise hide each other's failures."""

    def test_authorizer_layer_alone(self):
        import sqlite3, sqlguard
        ok, deny = sqlite3.SQLITE_OK, sqlite3.SQLITE_DENY
        for a in (sqlite3.SQLITE_SELECT, sqlite3.SQLITE_READ, sqlite3.SQLITE_FUNCTION):
            self.assertEqual(sqlguard._authorizer(a, None, None, None, None), ok)
        for name in ('SQLITE_INSERT', 'SQLITE_UPDATE', 'SQLITE_DELETE', 'SQLITE_PRAGMA', 'SQLITE_ATTACH', 'SQLITE_CREATE_TABLE', 'SQLITE_DROP_TABLE', 'SQLITE_TRANSACTION'):
            self.assertEqual(sqlguard._authorizer(getattr(sqlite3, name), None, None, None, None), deny, name)

    def test_readonly_connection_layer_alone(self):
        import sqlite3, db
        from pathlib import Path
        from harness import fresh_db
        tmp, path = fresh_db()
        try:
            con = sqlite3.connect(Path(path).resolve().as_uri() + '?mode=ro', uri=True)
            with self.assertRaises(sqlite3.OperationalError):
                con.execute('DELETE FROM Asset')
            con.close()
        finally:
            tmp.cleanup()
