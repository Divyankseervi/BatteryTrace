"""Shared test helpers. Every test uses a throw-away database; the demo database is never touched."""
from __future__ import annotations
import json, os, socket, subprocess, sys, tempfile, time, unittest
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import db  # noqa: E402


def fresh_db(seed=True, triggers=True):
    """Create a temp SQLite file with schema (+ demo seed + triggers). Returns (TemporaryDirectory, path)."""
    tmp = tempfile.TemporaryDirectory(prefix='bt-db-')
    path = Path(tmp.name) / 'test.db'
    if triggers:
        db.init_db(path, seed=seed)
    else:
        con = db.connect(path)
        db.create_schema(con)
        if seed:
            with db.tx(con):
                db.seed_demo(con)
        con.close()
    return tmp, path


class DbCase(unittest.TestCase):
    """Per-test fresh seeded database, direct service-layer access."""
    triggers = True

    def setUp(self):
        self.tmp, self.path = fresh_db(triggers=self.triggers)
        self.con = db.connect(self.path)

    def tearDown(self):
        self.con.close()
        self.tmp.cleanup()

    def q(self, sql, *a):
        return self.con.execute(sql, a).fetchall()

    def one(self, sql, *a):
        return self.con.execute(sql, a).fetchone()[0]

    def snapshot(self):
        """Everything a rejected operation must NOT change."""
        return {t: [tuple(r) for r in self.con.execute(f'SELECT * FROM {t} ORDER BY 1')] for t in
                ('Asset', 'Passport', 'AssetRelationship', 'LifecycleEvent')}


class ServerCase(unittest.TestCase):
    """One real HTTP server process per test class with its own temp database."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix='bt-srv-')
        with socket.socket() as s:
            s.bind(('127.0.0.1', 0)); cls.port = s.getsockname()[1]
        env = os.environ.copy()
        env.update(PORT=str(cls.port), BATTERYTRACE_DB=str(Path(cls.tmp.name) / 'srv.db'), PYTHONUNBUFFERED='1')
        cls.proc = subprocess.Popen([sys.executable, 'server.py'], cwd=ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        cls.base = f'http://127.0.0.1:{cls.port}'
        for _ in range(80):
            try:
                with urlopen(cls.base + '/api/health', timeout=1):
                    break
            except (URLError, TimeoutError, ConnectionError):
                time.sleep(.15)
        else:
            cls.proc.kill(); raise RuntimeError('BatteryTrace server did not start')

    @classmethod
    def tearDownClass(cls):
        cls.proc.terminate()
        try:
            cls.proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            cls.proc.kill()
        cls.tmp.cleanup()

    def get(self, path, headers=None):
        try:
            with urlopen(Request(self.base + path, headers=headers or {}), timeout=5) as r:
                raw = r.read()
                ct = r.headers.get('Content-Type', '')
                return r.status, (json.loads(raw) if 'json' in ct else raw.decode()), r.headers
        except HTTPError as e:
            raw = e.read(); ct = e.headers.get('Content-Type', '')
            return e.code, (json.loads(raw) if 'json' in ct else raw.decode()), e.headers

    def post(self, path, payload, user='U-SVC', headers=None, raw=None):
        h = {'Content-Type': 'application/json'}
        if user:
            h['X-Demo-User'] = user
        h.update(headers or {})
        data = raw if raw is not None else json.dumps(payload).encode()
        try:
            with urlopen(Request(self.base + path, data=data, headers=h, method='POST'), timeout=8) as r:
                return r.status, json.loads(r.read().decode())
        except HTTPError as e:
            return e.code, json.loads(e.read().decode())

    def event(self, code, etype, date='2026-10-26', user='U-SVC', **extra):
        p = {'asset_code': code, 'event_type': etype, 'event_at': date, 'location': 'Test site', 'organization': 'Test Org', 'notes': 'automated test'}
        p.update(extra)
        return self.post('/api/events', p, user=user)
