"""Tamper-evident event ledger.

Each LifecycleEvent stores prev_hash and event_hash = SHA-256(prev_hash | canonical fields).
Editing, deleting from the middle, or re-ordering rows breaks the chain at a detectable place.

HONEST LIMITS (also in README): this detects some after-the-fact changes by someone who
cannot also recompute the whole chain. It does NOT show the original input was true, it does
not detect truncation of the newest rows unless the latest hash was stored elsewhere, and a
database administrator can rebuild the chain. It is not a blockchain and does not need to be.
"""
from __future__ import annotations
import hashlib, json

GENESIS = '0' * 64
FIELDS = ('asset_id', 'event_type', 'event_at', 'location', 'organization', 'notes',
          'actor_id', 'evidence_status', 'evidence_ref')


def canonical(row) -> str:
    return json.dumps([row[f] for f in FIELDS], separators=(',', ':'), ensure_ascii=False)


def compute_hash(prev_hash: str, row) -> str:
    return hashlib.sha256((prev_hash + '|' + canonical(row)).encode('utf-8')).hexdigest()


def append_event(con, **f) -> int:
    """Insert one event linked to the current chain tip. Must run inside an open transaction."""
    tip = con.execute('SELECT event_hash FROM LifecycleEvent ORDER BY event_id DESC LIMIT 1').fetchone()
    prev = tip['event_hash'] if tip else GENESIS
    h = compute_hash(prev, f)
    cur = con.execute(
        'INSERT INTO LifecycleEvent(asset_id,event_type,event_at,location,organization,notes,actor_id,'
        'evidence_status,evidence_ref,idempotency_key,prev_hash,event_hash) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',
        (f['asset_id'], f['event_type'], f['event_at'], f['location'], f['organization'], f['notes'],
         f['actor_id'], f['evidence_status'], f['evidence_ref'], f['idempotency_key'], prev, h))
    return cur.lastrowid


def verify_chain(con) -> dict:
    """Recompute the chain. Returns {ok, checked, first_bad_event_id, reason, tip_hash}."""
    prev, n = GENESIS, 0
    for r in con.execute('SELECT * FROM LifecycleEvent ORDER BY event_id'):
        n += 1
        if r['prev_hash'] != prev:
            return {'ok': False, 'checked': n, 'first_bad_event_id': r['event_id'],
                    'reason': 'prev_hash does not match the previous row (row removed, inserted or re-ordered)', 'tip_hash': None}
        if compute_hash(prev, r) != r['event_hash']:
            return {'ok': False, 'checked': n, 'first_bad_event_id': r['event_id'],
                    'reason': 'event content does not match its stored hash (row edited)', 'tip_hash': None}
        prev = r['event_hash']
    return {'ok': True, 'checked': n, 'first_bad_event_id': None, 'reason': None, 'tip_hash': prev if n else None}
