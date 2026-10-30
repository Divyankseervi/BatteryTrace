"""Lineage tracing and recall simulation using a recursive CTE (relational graph traversal).

Direction 'up'   : from components to the packs/vehicles that contain them (who is affected?).
Direction 'down' : from a pack/vehicle to everything inside it (what is in it?).

Temporal modes for which links count:
  CURRENT  - links open today (valid_to IS NULL)
  AS_OF    - links valid on a given date: valid_from <= d < valid_to
  ALL      - every recorded link, past and present (widest net; may over-include)

The query is cycle-safe (a path may not revisit an asset) and depth-bounded.
"""
from __future__ import annotations
import datetime
import domain
from domain import DomainError

MAX_DEPTH_LIMIT = 12
FAR = '9999-12-31'

# Column names are chosen from this fixed whitelist, never from user text.
_DIRS = {'up': ('child_asset_id', 'parent_asset_id'), 'down': ('parent_asset_id', 'child_asset_id')}

_SQL = """
WITH RECURSIVE walk(asset_id, depth, path, rels) AS (
  SELECT asset_id, 0, '>' || asset_id || '>', '' FROM Asset WHERE asset_id IN ({starts})
  UNION ALL
  SELECT r.{nxt}, w.depth + 1, w.path || r.{nxt} || '>', w.rels || r.relationship_id || ','
  FROM walk w
  JOIN AssetRelationship r ON r.{cur} = w.asset_id
  WHERE w.depth < :maxd
    AND instr(w.path, '>' || r.{nxt} || '>') = 0                      -- cycle guard
    AND (:mode = 'ALL' OR (r.valid_from <= :d AND (r.valid_to IS NULL OR r.valid_to > :d)))
)
SELECT asset_id, depth, path, rels FROM walk ORDER BY depth, path
"""


_SQL_FRONTIER = """
WITH RECURSIVE frontier(asset_id, depth) AS (
  SELECT asset_id, 0 FROM Asset WHERE asset_id IN ({starts})
  UNION
  SELECT r.{nxt}, f.depth + 1
  FROM frontier f
  JOIN AssetRelationship r ON r.{cur} = f.asset_id
  WHERE f.depth < :maxd
    AND (:mode = 'ALL' OR (r.valid_from <= :d AND (r.valid_to IS NULL OR r.valid_to > :d)))
)
SELECT asset_id, MIN(depth) AS depth FROM frontier GROUP BY asset_id ORDER BY depth;
"""


def resolve_starts(con, *, codes=None, batch=None):
    if bool(codes) == bool(batch):
        raise DomainError('Provide exactly one of: asset code(s) or batch_code.', 'BAD_SCOPE')
    if batch:
        rows = con.execute('SELECT asset_id, asset_code FROM Asset WHERE batch_code=? ORDER BY asset_code', (batch,)).fetchall()
        if not rows:
            raise DomainError(f'No assets have batch_code {batch!r}.', 'UNKNOWN_BATCH', 404)
        return [(r['asset_id'], r['asset_code']) for r in rows]
    out, seen = [], set()
    for c in codes:
        clean = c.strip().upper()
        if not clean or clean in seen:
            continue
        seen.add(clean)
        r = con.execute('SELECT asset_id, asset_code FROM Asset WHERE asset_code=?', (clean,)).fetchone()
        if not r:
            raise DomainError(f'Unknown asset code: {clean}', 'UNKNOWN_ASSET', 404)
        out.append((r['asset_id'], r['asset_code']))
    return out


def trace(con, starts, direction='up', mode='CURRENT', as_of=None, max_depth=8):
    """Return the raw traversal rows: (asset_id, depth, path, rels). `starts` = list of asset_ids."""
    if direction not in _DIRS:
        raise DomainError("direction must be 'up' or 'down'.", 'BAD_DIRECTION')
    if mode not in ('CURRENT', 'AS_OF', 'ALL'):
        raise DomainError('mode must be CURRENT, AS_OF or ALL.', 'BAD_MODE')
    d = domain.parse_date(as_of, 'as_of') if mode == 'AS_OF' else domain.today()
    cur, nxt = _DIRS[direction]
    names = [f's{i}' for i in range(len(starts))]
    ph = ','.join(':' + n for n in names) or "''"
    sql = _SQL.format(starts=ph, cur=cur, nxt=nxt)          # cur/nxt come from the fixed whitelist above
    args = {n: v for n, v in zip(names, starts)}
    args.update(maxd=max_depth, mode=mode, d=d)
    return con.execute(sql, args).fetchall()


def trace_frontier(con, starts, direction='up', mode='CURRENT', as_of=None, max_depth=8):
    """Optimized frontier-deduplicated CTE: eliminates redundant path traversals for multi-asset batch recalls."""
    if direction not in _DIRS:
        raise DomainError("direction must be 'up' or 'down'.", 'BAD_DIRECTION')
    if mode not in ('CURRENT', 'AS_OF', 'ALL'):
        raise DomainError('mode must be CURRENT, AS_OF or ALL.', 'BAD_MODE')
    d = domain.parse_date(as_of, 'as_of') if mode == 'AS_OF' else domain.today()
    cur, nxt = _DIRS[direction]
    names = [f's{i}' for i in range(len(starts))]
    ph = ','.join(':' + n for n in names) or "''"
    sql = _SQL_FRONTIER.format(starts=ph, cur=cur, nxt=nxt)
    args = {n: v for n, v in zip(names, starts)}
    args.update(maxd=max_depth, mode=mode, d=d)
    return con.execute(sql, args).fetchall()


def recall_report(con, *, codes=None, batch=None, direction='up', mode='CURRENT', as_of=None, max_depth=8):
    try:
        max_depth = int(max_depth)
    except (TypeError, ValueError):
        raise DomainError('max_depth must be an integer.', 'BAD_DEPTH')
    if not 1 <= max_depth <= MAX_DEPTH_LIMIT:
        raise DomainError(f'max_depth must be between 1 and {MAX_DEPTH_LIMIT}.', 'BAD_DEPTH')
    starts = resolve_starts(con, codes=codes, batch=batch)
    ids = [s[0] for s in starts]
    rows = trace(con, ids, direction, mode, as_of, max_depth + 1)   # one extra level to detect truncation
    cache = {}
    def asset(aid):
        if aid not in cache:
            cache[aid] = dict(con.execute('SELECT asset_id,asset_code,asset_type,status,batch_code,manufacturer FROM Asset WHERE asset_id=?', (aid,)).fetchone())
        return cache[aid]
    rel_status = {r['relationship_id']: r['valid_to'] for r in con.execute('SELECT relationship_id, valid_to FROM AssetRelationship')}

    best, count, truncated = {}, {}, False
    for r in rows:
        if r['depth'] > max_depth:
            truncated = True
            continue
        a = r['asset_id']
        count[a] = count.get(a, 0) + 1
        if a not in best:                       # rows are ordered by depth: the first is a shortest path
            best[a] = r
    affected = []
    for a, r in best.items():
        meta = asset(a)
        path_ids = [p for p in r['path'].split('>') if p]
        codes_path = [asset(p)['asset_code'] if p != a else meta['asset_code'] for p in path_ids]
        rels = [int(x) for x in r['rels'].split(',') if x]
        affected.append({**meta, 'depth': r['depth'], 'path': codes_path, 'path_count': count[a],
                         'via_closed_link': any(rel_status.get(x) is not None for x in rels),
                         'is_start': r['depth'] == 0})
    affected.sort(key=lambda x: (x['depth'], x['asset_code']))

    # ---- uncertainty warnings: make gaps visible instead of implying completeness ----
    warnings = []
    ids_aff = [x['asset_id'] for x in affected]
    for x in affected:
        opens = con.execute('SELECT COUNT(*) FROM v_open_relationship WHERE child_asset_id=?', (x['asset_id'],)).fetchone()[0]
        if opens > 1:
            warnings.append({'code': 'CONFLICTING_PARENTS', 'asset_code': x['asset_code'], 'message': f'{x["asset_code"]} has {opens} open parents; the true location is uncertain, so every branch is included.'})
        if direction == 'up' and mode == 'CURRENT':
            if x['asset_type'] in ('CELL', 'MODULE') and not con.execute('SELECT 1 FROM v_open_relationship WHERE child_asset_id=?', (x['asset_id'],)).fetchone():
                warnings.append({'code': 'NO_PARENT_RECORDED', 'asset_code': x['asset_code'], 'message': f'{x["asset_code"]} has no recorded current parent; where it is installed is unknown.'})
            if x['asset_type'] == 'BATTERY_PACK' and x['status'] in ('ACTIVE', 'IN_REPAIR', 'SECOND_LIFE') and \
               not con.execute('SELECT 1 FROM v_open_relationship WHERE child_asset_id=?', (x['asset_id'],)).fetchone():
                warnings.append({'code': 'NO_HOST_RECORDED', 'asset_code': x['asset_code'], 'message': f'{x["asset_code"]} is in use but has no recorded vehicle/storage host.'})
        if x['via_closed_link']:
            warnings.append({'code': 'HISTORICAL_LINK', 'asset_code': x['asset_code'], 'message': f'{x["asset_code"]} is reached only through a closed (past) link.'})
        if x['status'] == 'RECYCLED' and not x['is_start']:
            warnings.append({'code': 'ALREADY_RECYCLED', 'asset_code': x['asset_code'], 'message': f'{x["asset_code"]} is already recycled; likely no field action possible.'})
    if truncated:
        warnings.append({'code': 'DEPTH_LIMIT', 'asset_code': '—', 'message': f'More links exist beyond depth {max_depth}; the result may be incomplete.'})
    if not any(x['depth'] > 0 for x in affected):
        warnings.append({'code': 'NO_LINKS_FOUND', 'asset_code': '—', 'message': 'No qualifying links were found. This can mean "nothing is connected" or "the connection was never recorded".'})

    return {
        'scope': {'starts': [s[1] for s in starts], 'batch_code': batch, 'direction': direction, 'mode': mode,
                  'as_of': as_of if mode == 'AS_OF' else None, 'max_depth': max_depth,
                  'generated_at': datetime.datetime.now().isoformat(timespec='seconds')},
        'counts': {'affected_total': len(affected), 'start_assets': len(starts),
                   'by_type': {t: sum(1 for x in affected if x['asset_type'] == t) for t in domain.ASSET_TYPES if any(x['asset_type'] == t for x in affected)}},
        'affected': affected, 'warnings': warnings, 'truncated': truncated,
        'method': 'WITH RECURSIVE over AssetRelationship (cycle-safe path check, depth-bounded). Completeness is relative to RECORDED links only.',
        'disclaimer': 'Synthetic data. A recall list is only as complete as the recorded relationships; it is not a regulatory recall notice.'}


def evaluate(found_codes, expected_codes):
    """Compare a result with a known ground-truth set (used on synthetic fixtures only)."""
    f, e = set(found_codes), set(expected_codes)
    tp, fp, fn = len(f & e), len(f - e), len(e - f)
    return {'true_positive': tp, 'false_positive': fp, 'false_negative': fn,
            'precision': 1.0 if not f else tp / len(f), 'recall': 1.0 if not e else tp / len(e)}
