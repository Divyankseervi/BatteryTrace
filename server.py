#!/usr/bin/env python3
"""BatteryTrace HTTP server: Python standard library only (no pip install needed).

All records are synthetic. Educational prototype; not a compliance system.
Binds to 127.0.0.1 only. Demo roles are NOT authentication (see README).
"""
from __future__ import annotations
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs, unquote
from pathlib import Path
import json, os, sqlite3, sys, traceback

import db, services, recall, audit, sqlguard, domain, neo4j_graph
from domain import DomainError

ROOT = Path(__file__).resolve().parent
HOST = os.environ.get('HOST', '127.0.0.1')
PORT = int(os.environ.get('PORT', '8000'))
ALLOW_CORS = os.environ.get('ALLOW_CORS', '0') == '1'
MAX_BODY = 20000
STATIC = {'app.css': 'text/css; charset=utf-8', 'app.js': 'application/javascript; charset=utf-8',
          'lab.js': 'application/javascript; charset=utf-8', 'erd.svg': 'image/svg+xml',
          'config.js': 'application/javascript; charset=utf-8'}
CSP = "default-src 'self'; img-src 'self' data:; style-src 'self' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; script-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"


class Handler(BaseHTTPRequestHandler):
    server_version = 'BatteryTrace/2.0'

    def log_message(self, fmt, *args):
        sys.stderr.write('[%s] %s\n' % (self.log_date_time_string(), fmt % args))

    # ----- plumbing -----
    def _send(self, status, data: bytes, ctype, extra=None):
        self.send_response(status)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Referrer-Policy', 'no-referrer')
        if ALLOW_CORS:
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type, X-Demo-User')
        if ctype.startswith('text/html'):
            self.send_header('Content-Security-Policy', CSP)
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(data)

    def _json(self, status, obj):
        self._send(status, json.dumps(obj, ensure_ascii=False).encode('utf-8'), 'application/json; charset=utf-8')

    def _error(self, status, message, code):
        self._json(status, {'error': message, 'code': code})

    def _host_ok(self):
        if HOST == '0.0.0.0' or os.environ.get('ALLOW_ALL_HOSTS') == '1':
            return True
        host = (self.headers.get('Host') or '').lower()
        return host in (f'127.0.0.1:{PORT}', f'localhost:{PORT}', '127.0.0.1', 'localhost')

    def do_OPTIONS(self):
        self.send_response(204)
        if ALLOW_CORS:
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type, X-Demo-User')
            self.send_header('Access-Control-Max-Age', '86400')
        self.send_header('Content-Length', '0')
        self.end_headers()

    def _dispatch(self, fn):
        try:
            if not self._host_ok():
                return self._error(403, 'Unexpected Host header (local use only).', 'BAD_HOST')
            return fn()
        except DomainError as e:
            return self._error(e.status, str(e), e.code)
        except sqlite3.OperationalError as e:
            if 'locked' in str(e) or 'busy' in str(e):
                return self._error(503, 'Database is busy; please retry.', 'DB_BUSY')
            traceback.print_exc()
            return self._error(500, 'Internal server error.', 'INTERNAL')
        except Exception:
            traceback.print_exc()                      # details stay in the server log, never in the response
            return self._error(500, 'Internal server error.', 'INTERNAL')

    # ----- GET -----
    def do_GET(self):
        self._dispatch(self._get)

    def _get(self):
        u = urlparse(self.path)
        path, params = u.path, parse_qs(u.query)
        if path in ('/', '/index.html'):
            return self._send(200, (ROOT / 'index.html').read_bytes(), 'text/html; charset=utf-8')
        if path.startswith('/static/'):
            name = path[len('/static/'):]
            if name not in STATIC:                     # whitelist: no path traversal possible
                return self._error(404, 'Not found.', 'NOT_FOUND')
            try:
                return self._send(200, (ROOT / 'static' / name).read_bytes(), STATIC[name])
            except FileNotFoundError:
                return self._error(404, 'Not found.', 'NOT_FOUND')
        if not path.startswith('/api/'):
            return self._error(404, 'Not found.', 'NOT_FOUND')
        con = db.connect()
        try:
            g = lambda k, d='': params.get(k, [d])[0]
            if path == '/api/health':
                server_name = os.environ.get('SERVER_NAME') or os.environ.get('HOSTNAME') or 'local-instance'
                return self._json(200, {'ok': True, 'server_name': server_name,
                                        'database': 'SQLite ' + sqlite3.sqlite_version, 'db_file': db.DB_PATH.name,
                                        'synthetic_data': True, 'neo4j': neo4j_graph.status()})
            if path == '/api/meta':
                return self._json(200, {'event_types': list(domain.EVENT_TYPES), 'asset_types': list(domain.ASSET_TYPES), 'statuses': list(domain.ASSET_STATUSES),
                                        'transitions': {k: {'from': sorted(v['from']), 'to': v['to']} for k, v in domain.TRANSITIONS.items()},
                                        'role_events': {k: sorted(v) for k, v in domain.ROLE_EVENTS.items()},
                                        'role_can_relink': domain.ROLE_CAN_RELINK, 'hierarchy': domain.HIERARCHY})
            if path == '/api/users':
                return self._json(200, [dict(r) for r in con.execute('SELECT * FROM AppUser ORDER BY user_id')])
            if path == '/api/summary':
                return self._json(200, services.summary(con))
            if path == '/api/assets':
                return self._json(200, services.list_assets(con, params))
            if path == '/api/assets.csv':
                rows, off = [], 0
                while len(rows) < 5000:                  # bounded export
                    page = services.list_assets(con, {**params, 'limit': ['200'], 'offset': [str(off)]})['items']
                    if not page:
                        break
                    rows += page; off += 200
                cols = ['asset_code', 'asset_type', 'manufacturer', 'chemistry', 'batch_code', 'status', 'passport_id', 'passport_status', 'capacity_kwh', 'last_event_at']
                return self._send(200, services.to_csv(cols, rows[:5000]), 'text/csv; charset=utf-8',
                                  {'Content-Disposition': 'attachment; filename="batterytrace-assets.csv"'})
            if path == '/api/events':
                return self._json(200, services.list_events(con, params))
            if path == '/api/issues':
                return self._json(200, services.find_issues(con))
            if path == '/api/rules':
                return self._json(200, services.rule_catalog())
            if path == '/api/audit/verify':
                return self._json(200, audit.verify_chain(con))
            if path.startswith('/api/lineage/'):
                return self._json(200, services.lineage(con, unquote(path[len('/api/lineage/'):])))
            if path in ('/api/recall', '/api/recall.csv'):
                codes = [c for c in g('codes').split(',') if c.strip()] or None
                rep = recall.recall_report(con, codes=codes, batch=g('batch') or None, direction=g('direction', 'up'), mode=g('mode', 'CURRENT').upper(),
                                           as_of=g('as_of') or None, max_depth=g('max_depth', '8'))
                if path == '/api/recall':
                    return self._json(200, rep)
                rows = [{'asset_code': x['asset_code'], 'asset_type': x['asset_type'], 'status': x['status'], 'batch_code': x['batch_code'] or '',
                         'depth': x['depth'], 'path': ' > '.join(x['path']), 'path_count': x['path_count'], 'via_closed_link': x['via_closed_link']} for x in rep['affected']]
                return self._send(200, services.to_csv(list(rows[0].keys()) if rows else ['asset_code'], rows), 'text/csv; charset=utf-8',
                                  {'Content-Disposition': 'attachment; filename="batterytrace-recall.csv"'})
            if path == '/api/lab-queries':
                return self._json(200, json.loads((ROOT / 'sql' / 'lab_queries.json').read_text(encoding='utf-8')))
            if path == '/api/benchmark':
                f = ROOT / 'research' / 'benchmark_results.json'
                return self._json(200, json.loads(f.read_text(encoding='utf-8')) if f.exists() else {'available': False})
            if path == '/api/schema':
                objs = [dict(r) for r in con.execute("SELECT type, name, tbl_name, sql FROM sqlite_master WHERE sql IS NOT NULL AND name NOT LIKE 'sqlite_%' ORDER BY CASE type WHEN 'table' THEN 0 WHEN 'view' THEN 1 WHEN 'index' THEN 2 ELSE 3 END, name")]
                counts = {r['name']: con.execute(f'SELECT COUNT(*) FROM "{r["name"]}"').fetchone()[0] for r in objs if r['type'] == 'table'}
                return self._json(200, {'objects': objs, 'row_counts': counts})
            if path == '/api/neo4j/status':
                return self._json(200, neo4j_graph.status())
            if path.startswith('/api/neo4j/lineage/'):
                direction = g('direction', 'down')
                depth = g('max_depth', '8')
                return self._json(200, neo4j_graph.lineage(unquote(path[len('/api/neo4j/lineage/'):]), direction, int(depth)))
            return self._error(404, 'API endpoint not found.', 'NOT_FOUND')
        finally:
            con.close()

    # ----- POST -----
    def do_POST(self):
        self._dispatch(self._post)

    def _body(self):
        if 'application/json' not in (self.headers.get('Content-Type') or ''):
            raise DomainError('Content-Type must be application/json.', 'BAD_CONTENT_TYPE', 415)
        origin = self.headers.get('Origin')
        if origin and not ALLOW_CORS and urlparse(origin).netloc.lower() not in (f'127.0.0.1:{PORT}', f'localhost:{PORT}'):
            raise DomainError('Cross-origin request refused.', 'BAD_ORIGIN', 403)
        try:
            length = int(self.headers.get('Content-Length', '0'))
        except ValueError:
            raise DomainError('Bad Content-Length.', 'BAD_JSON')
        if length > MAX_BODY:
            raise DomainError('Request too large.', 'TOO_LARGE', 413)
        try:
            body = json.loads(self.rfile.read(length) or b'{}')
        except (ValueError, UnicodeDecodeError):
            raise DomainError('Request body must be valid JSON.', 'BAD_JSON')
        if not isinstance(body, dict):
            raise DomainError('Request body must be a JSON object.', 'BAD_JSON')
        return body

    def _post(self):
        path = urlparse(self.path).path
        routes = {'/api/events': services.record_event, '/api/transfers': services.transfer_component,
                  '/api/relationships/close': services.close_relationship,
                  '/api/diagnostics': services.record_diagnostic_test}
        if path == '/api/neo4j/sync':
            body = self._body()
            user = self.headers.get('X-Demo-User')
            con = db.connect()
            try:
                if user not in ('U-MFR', 'U-AUD'):
                    raise DomainError('Neo4j sync requires the manufacturer or auditor demo role.', 'FORBIDDEN', 403)
                return self._json(200, neo4j_graph.sync(con))
            finally:
                con.close()
        if path == '/api/sql':
            return self._json(200, sqlguard.run_query(str(self._body().get('sql', ''))))
        if path not in routes:
            return self._error(404, 'Endpoint not found.', 'NOT_FOUND')
        body = self._body()
        con = db.connect()
        try:
            res = routes[path](con, body, self.headers.get('X-Demo-User'))
        finally:
            con.close()
        return self._json(200 if res.get('replayed') else 201, res)


def main():
    db.init_db()
    print(f'BatteryTrace is running at http://{HOST}:{PORT}')
    print(f'SQLite database: {db.DB_PATH}')
    print('All records are synthetic. Demo roles are not authentication. Press Ctrl+C to stop.')
    try:
        ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
    except KeyboardInterrupt:
        print('\nStopped BatteryTrace.')


if __name__ == '__main__':
    main()
