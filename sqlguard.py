"""Read-only SQL lab. Lets a student run SELECT / EXPLAIN against the demo database safely.

Defence in depth: (1) separate connection opened with mode=ro, (2) PRAGMA query_only,
(3) sqlite3 authorizer that only permits SELECT/READ/FUNCTION/RECURSIVE, (4) single statement,
(5) row cap, (6) time cap via progress handler. Local teaching use only (server binds 127.0.0.1).
"""
from __future__ import annotations
import re, sqlite3, time
from pathlib import Path
from domain import DomainError
import db

MAX_ROWS, MAX_SECONDS, MAX_LEN = 200, 2.0, 4000
_ALLOWED = {sqlite3.SQLITE_SELECT, sqlite3.SQLITE_READ, sqlite3.SQLITE_FUNCTION}
if hasattr(sqlite3, 'SQLITE_RECURSIVE'):
    _ALLOWED.add(sqlite3.SQLITE_RECURSIVE)


def _authorizer(action, a1, a2, dbname, source):
    if action in _ALLOWED:
        return sqlite3.SQLITE_OK
    return sqlite3.SQLITE_DENY


def run_query(sql: str, path=None):
    sql = (sql or '').strip().rstrip(';').strip()
    if not sql:
        raise DomainError('Enter a SELECT query.', 'EMPTY_SQL')
    if len(sql) > MAX_LEN:
        raise DomainError(f'Query too long (max {MAX_LEN} characters).', 'SQL_TOO_LONG')
    if ';' in sql:
        raise DomainError('Only one statement is allowed.', 'MULTI_STATEMENT')
    if not re.match(r'^(select|with|explain\s+query\s+plan)\b', sql, re.I):
        raise DomainError('Only SELECT, WITH ... SELECT and EXPLAIN QUERY PLAN are allowed.', 'READ_ONLY')
    uri = Path(path or db.DB_PATH).resolve().as_uri() + '?mode=ro'
    con = sqlite3.connect(uri, uri=True, timeout=3)
    try:
        con.row_factory = sqlite3.Row
        con.execute('PRAGMA query_only = ON')
        con.set_authorizer(_authorizer)
        deadline = time.monotonic() + MAX_SECONDS
        con.set_progress_handler(lambda: 1 if time.monotonic() > deadline else 0, 10000)
        t0 = time.perf_counter()
        try:
            cur = con.execute(sql)
            rows = cur.fetchmany(MAX_ROWS + 1)
            cols = [d[0] for d in cur.description or []]
        except sqlite3.OperationalError as exc:
            msg = str(exc)
            if 'interrupted' in msg:
                raise DomainError(f'Query stopped: exceeded {MAX_SECONDS:.0f}s.', 'SQL_TIMEOUT')
            if 'not authorized' in msg:
                raise DomainError('That statement is not permitted in the read-only lab.', 'READ_ONLY')
            raise DomainError(f'SQL error: {msg}', 'SQL_ERROR')
        except sqlite3.DatabaseError as exc:
            raise DomainError(f'SQL error: {exc}', 'SQL_ERROR')
        ms = (time.perf_counter() - t0) * 1000
        truncated = len(rows) > MAX_ROWS
        return {'columns': cols, 'rows': [list(r) for r in rows[:MAX_ROWS]], 'truncated': truncated, 'row_cap': MAX_ROWS, 'elapsed_ms': round(ms, 2)}
    finally:
        con.close()
