"""Application services: every write is one atomic transaction; every rule violation raises DomainError."""
from __future__ import annotations
import csv, io, sqlite3, datetime
import domain, audit
from db import tx
from domain import DomainError

MAX_NOTES, MAX_FIELD = 1000, 200


# ---------- helpers ----------
def get_user(con, user_id):
    if not user_id:
        raise DomainError('Demo user required: send header X-Demo-User (e.g. U-SVC). This is demo mode, not authentication.', 'NO_USER', 401)
    u = con.execute('SELECT * FROM AppUser WHERE user_id=?', (str(user_id).strip(),)).fetchone()
    if not u:
        raise DomainError(f'Unknown demo user: {user_id}', 'UNKNOWN_USER', 401)
    return u


def _asset(con, code):
    a = con.execute('SELECT * FROM Asset WHERE asset_code=?', (str(code or '').strip().upper(),)).fetchone()
    if not a:
        raise DomainError(f'Unknown asset code: {str(code or "").strip().upper()}', 'UNKNOWN_ASSET', 404)
    return a


def _text(p, key, required=True, limit=MAX_FIELD):
    v = str(p.get(key) if p.get(key) is not None else '').strip()
    if required and not v:
        raise DomainError(f'{key} is required.', 'MISSING_FIELD')
    if len(v) > limit:
        raise DomainError(f'{key} is too long (max {limit} characters).', 'TOO_LONG')
    return v


def _date_window(con, asset, date, *, label='Event date'):
    if date > domain.today():
        raise DomainError(f'{label} {date} is in the future.', 'FUTURE_DATE')
    if date < asset['created_at']:
        raise DomainError(f'{label} {date} is before the asset was created ({asset["created_at"]}).', 'BEFORE_CREATION')
    last = con.execute('SELECT MAX(event_at) FROM LifecycleEvent WHERE asset_id=?', (asset['asset_id'],)).fetchone()[0]
    if last and date < last:
        raise DomainError(f'{label} {date} is earlier than the latest recorded event ({last}). The ledger is append-only and chronological; record a dated correction instead.', 'OUT_OF_ORDER', 409)


def _guard(fn):
    """Translate trigger/constraint aborts into a clear 409 instead of a 500."""
    try:
        return fn()
    except sqlite3.IntegrityError as exc:
        raise DomainError(f'Database integrity rule rejected the change: {exc}', 'DB_CONSTRAINT', 409)


# ---------- lifecycle events ----------
def record_event(con, payload: dict, user_id):
    """Validate -> check state machine -> write event + status + passport + links in ONE transaction."""
    user = get_user(con, user_id)
    etype = str(payload.get('event_type', '')).strip().upper()
    code = _text(payload, 'asset_code')
    date = domain.parse_date(payload.get('event_at'), 'event_at')
    location = _text(payload, 'location')
    org = _text(payload, 'organization', required=False) or user['organization']
    notes = _text(payload, 'notes', required=False, limit=MAX_NOTES)
    evidence = str(payload.get('evidence_status') or 'SELF_REPORTED').strip().upper()
    if evidence not in domain.EVIDENCE_STATUSES:
        raise DomainError('evidence_status must be UNKNOWN, SELF_REPORTED or VERIFIED.', 'BAD_EVIDENCE')
    if evidence == 'VERIFIED':
        raise DomainError('VERIFIED evidence needs an external attestation, which this demo does not implement. Use SELF_REPORTED or UNKNOWN.', 'EVIDENCE_NOT_SUPPORTED')
    ref = _text(payload, 'evidence_ref', required=False) or None
    key = _text(payload, 'idempotency_key', required=False, limit=100) or None
    if etype not in domain.EVENT_TYPES:
        raise DomainError(f'event_type must be one of: {", ".join(domain.EVENT_TYPES)}', 'BAD_EVENT_TYPE')

    def work():
        with tx(con):
            asset = _asset(con, code)
            if key:  # retry safety: same key + same content -> replay; same key + different content -> conflict
                old = con.execute('SELECT * FROM LifecycleEvent WHERE idempotency_key=?', (key,)).fetchone()
                if old:
                    same = (old['asset_id'], old['event_type'], old['event_at'], old['location'], old['notes']) == \
                           (asset['asset_id'], etype, date, location, notes)
                    if same:
                        return {'ok': True, 'replayed': True, 'event_id': old['event_id'], 'message': 'Duplicate submission ignored; original event returned.'}
                    raise DomainError('idempotency_key was already used for a different event.', 'IDEMPOTENCY_CONFLICT', 409)
            has_mf = con.execute("SELECT 1 FROM LifecycleEvent WHERE asset_id=? AND event_type='MANUFACTURED'", (asset['asset_id'],)).fetchone() is not None
            has_pp = con.execute("SELECT 1 FROM Passport WHERE asset_id=? AND status='ACTIVE'", (asset['asset_id'],)).fetchone() is not None
            rule = domain.check_transition(etype, asset['asset_type'], asset['status'], user['role'],
                                           already_manufactured=has_mf, has_active_passport=has_pp)
            _date_window(con, asset, date)
            event_id = audit.append_event(con, asset_id=asset['asset_id'], event_type=etype, event_at=date, location=location,
                                          organization=org, notes=notes, actor_id=user['user_id'], evidence_status=evidence,
                                          evidence_ref=ref, idempotency_key=key)
            new_status, new_passport = asset['status'], None
            to = rule['to']
            if to == 'RETURN':
                rep = con.execute("SELECT 1 FROM LifecycleEvent WHERE asset_id=? AND event_type='REPURPOSED'", (asset['asset_id'],)).fetchone()
                to = domain.return_status(rep is not None)
            if to:
                new_status = to
                con.execute('UPDATE Asset SET status=? WHERE asset_id=?', (to, asset['asset_id']))
            if etype == 'REPURPOSED':
                cur = con.execute("SELECT * FROM Passport WHERE asset_id=? AND status='ACTIVE'", (asset['asset_id'],)).fetchone()
                con.execute("UPDATE Passport SET status='SUPERSEDED' WHERE passport_id=?", (cur['passport_id'],))
                nv = con.execute('SELECT COALESCE(MAX(passport_version),0)+1 FROM Passport WHERE asset_id=?', (asset['asset_id'],)).fetchone()[0]
                new_passport = f"{asset['asset_code']}-V{nv}"
                con.execute('INSERT INTO Passport(passport_id,asset_id,passport_version,status,issued_at,previous_passport_id) VALUES (?,?,?,?,?,?)',
                            (new_passport, asset['asset_id'], nv, 'ACTIVE', date, cur['passport_id']))
            if etype == 'RECYCLED':
                con.execute("UPDATE Passport SET status='CLOSED' WHERE asset_id=? AND status='ACTIVE'", (asset['asset_id'],))
                for r in con.execute('SELECT relationship_id, valid_from FROM AssetRelationship WHERE valid_to IS NULL AND (parent_asset_id=? OR child_asset_id=?)',
                                     (asset['asset_id'], asset['asset_id'])).fetchall():
                    if date <= r['valid_from']:
                        raise DomainError(f'Cannot close link #{r["relationship_id"]}: it starts on {r["valid_from"]}, not before the recycling date {date}.', 'BAD_INTERVAL', 409)
                    con.execute('UPDATE AssetRelationship SET valid_to=? WHERE relationship_id=?', (date, r['relationship_id']))
            return {'ok': True, 'replayed': False, 'event_id': event_id, 'asset_code': asset['asset_code'],
                    'new_status': new_status, 'new_passport_id': new_passport, 'message': 'Lifecycle event saved.'}
    return _guard(work)


# ---------- component transfer / link correction ----------
def transfer_component(con, payload: dict, user_id):
    """Move a component to a new parent: close the old link and open the new one, atomically."""
    user = get_user(con, user_id)
    if not domain.ROLE_CAN_RELINK.get(user['role']):
        raise DomainError(f'Role {user["role"]} may not change component links.', 'FORBIDDEN', 403)
    date = domain.parse_date(payload.get('effective_date'), 'effective_date')
    reason = _text(payload, 'reason', limit=MAX_NOTES)
    location = _text(payload, 'location', required=False) or 'Not recorded'
    key = _text(payload, 'idempotency_key', required=False, limit=100) or None

    def work():
        with tx(con):
            child = _asset(con, payload.get('child_code'))
            parent = _asset(con, payload.get('new_parent_code'))
            label = domain.relationship_label(parent['asset_type'], child['asset_type'])
            for a in (child, parent):
                if a['status'] in domain.TERMINAL_STATUSES:
                    raise DomainError(f'{a["asset_code"]} is {a["status"]} (terminal) and cannot be re-linked.', 'TERMINAL_STATE', 409)
            if key:
                old = con.execute('SELECT * FROM LifecycleEvent WHERE idempotency_key=?', (key,)).fetchone()
                if old:
                    return {'ok': True, 'replayed': True, 'event_id': old['event_id'], 'message': 'Duplicate submission ignored.'}
            opens = con.execute('SELECT * FROM v_open_relationship WHERE child_asset_id=?', (child['asset_id'],)).fetchall()
            if len(opens) > 1:
                raise DomainError(f'{child["asset_code"]} has {len(opens)} open parents (data conflict). Close the wrong link first with /api/relationships/close.', 'CONFLICTING_PARENTS', 409)
            if opens and opens[0]['parent_asset_id'] == parent['asset_id']:
                raise DomainError(f'{child["asset_code"]} is already linked to {parent["asset_code"]}.', 'NO_CHANGE', 409)
            _date_window(con, child, date, label='effective_date')
            old_parent = None
            if opens:
                o = opens[0]
                if date <= o['valid_from']:
                    raise DomainError(f'effective_date must be after the current link started ({o["valid_from"]}).', 'BAD_INTERVAL', 409)
                con.execute('UPDATE AssetRelationship SET valid_to=? WHERE relationship_id=?', (date, o['relationship_id']))
                old_parent = con.execute('SELECT asset_code FROM Asset WHERE asset_id=?', (o['parent_asset_id'],)).fetchone()[0]
            if date < parent['created_at']:
                raise DomainError(f'effective_date {date} is before the new parent was created ({parent["created_at"]}).', 'BEFORE_CREATION')
            cur = con.execute('INSERT INTO AssetRelationship(parent_asset_id,child_asset_id,relationship_type,valid_from,valid_to) VALUES (?,?,?,?,NULL)',
                              (parent['asset_id'], child['asset_id'], label, date))
            note = f'Moved from {old_parent or "no recorded parent"} to {parent["asset_code"]}. Reason: {reason}'
            ev = audit.append_event(con, asset_id=child['asset_id'], event_type='TRANSFERRED', event_at=date, location=location,
                                    organization=user['organization'], notes=note[:MAX_NOTES], actor_id=user['user_id'],
                                    evidence_status='SELF_REPORTED', evidence_ref=None, idempotency_key=key)
            return {'ok': True, 'replayed': False, 'relationship_id': cur.lastrowid, 'event_id': ev,
                    'closed_parent': old_parent, 'message': 'Component transferred.'}
    return _guard(work)


def close_relationship(con, payload: dict, user_id):
    """Corrective action: end an open link (e.g. to resolve a 'multiple open parents' warning)."""
    user = get_user(con, user_id)
    if not domain.ROLE_CAN_RELINK.get(user['role']):
        raise DomainError(f'Role {user["role"]} may not change component links.', 'FORBIDDEN', 403)
    date = domain.parse_date(payload.get('valid_to'), 'valid_to')
    reason = _text(payload, 'reason', limit=MAX_NOTES)
    try:
        rid = int(payload.get('relationship_id'))
    except (TypeError, ValueError):
        raise DomainError('relationship_id must be an integer.', 'MISSING_FIELD')

    def work():
        with tx(con):
            r = con.execute('SELECT * FROM AssetRelationship WHERE relationship_id=?', (rid,)).fetchone()
            if not r:
                raise DomainError(f'Unknown relationship #{rid}.', 'UNKNOWN_RELATIONSHIP', 404)
            if r['valid_to'] is not None:
                raise DomainError(f'Relationship #{rid} is already closed ({r["valid_to"]}).', 'ALREADY_CLOSED', 409)
            if date <= r['valid_from']:
                raise DomainError(f'valid_to must be after valid_from ({r["valid_from"]}).', 'BAD_INTERVAL', 409)
            child = con.execute('SELECT * FROM Asset WHERE asset_id=?', (r['child_asset_id'],)).fetchone()
            parent = con.execute('SELECT asset_code FROM Asset WHERE asset_id=?', (r['parent_asset_id'],)).fetchone()
            _date_window(con, child, date, label='valid_to')
            domain.check_transition('TRANSFERRED', child['asset_type'], child['status'], user['role'])
            con.execute('UPDATE AssetRelationship SET valid_to=? WHERE relationship_id=?', (date, rid))
            ev = audit.append_event(con, asset_id=child['asset_id'], event_type='TRANSFERRED', event_at=date, location='Not recorded',
                                    organization=user['organization'], notes=f'CORRECTION: closed link {parent["asset_code"]} → {child["asset_code"]}. Reason: {reason}'[:MAX_NOTES],
                                    actor_id=user['user_id'], evidence_status='SELF_REPORTED', evidence_ref=None, idempotency_key=None)
            return {'ok': True, 'event_id': ev, 'message': 'Relationship closed.'}
    return _guard(work)


# ---------- diagnostic measurements (Case Study FR-5, Code 1B, Code 3) ----------
def record_diagnostic_test(con, payload: dict, user_id):
    """Record a State of Health (SoH %) and cycle count measurement in TestResult table.
    Atomically records a linked TESTED lifecycle event in the SHA-256 hash-chained ledger."""
    user = get_user(con, user_id)
    if user['role'] not in ('MANUFACTURER', 'SERVICE'):
        raise DomainError(f"Role {user['role']} may not record diagnostic tests. Only MANUFACTURER or SERVICE roles are permitted.", 'FORBIDDEN', 403)
    code = _text(payload, 'asset_code')
    raw_time = payload.get('test_time') or payload.get('test_at')
    if not raw_time:
        raise DomainError('test_time is required.', 'BAD_DATE')
    test_time = str(raw_time).strip()
    date_part = test_time.split(' ')[0]
    domain.parse_date(date_part, 'test_time')

    soh = payload.get('state_of_health_pct')
    if soh is None:
        raise DomainError('state_of_health_pct is required.', 'BAD_VALUE')
    try:
        soh_val = float(soh)
        if not (0.0 <= soh_val <= 100.0):
            raise ValueError()
    except (ValueError, TypeError):
        raise DomainError('state_of_health_pct must be a number between 0 and 100.', 'BAD_VALUE')

    cycles = payload.get('cycle_count')
    cycle_val = None
    if cycles is not None and str(cycles).strip() != '':
        try:
            cycle_val = int(cycles)
            if cycle_val < 0:
                raise ValueError()
        except (ValueError, TypeError):
            raise DomainError('cycle_count must be a non-negative integer.', 'BAD_VALUE')

    notes = _text(payload, 'notes', required=False, limit=MAX_NOTES)
    loc = _text(payload, 'location', required=False) or 'Service Facility'
    key = _text(payload, 'idempotency_key', required=False, limit=100) or None

    def work():
        with tx(con):
            asset = _asset(con, code)
            if asset['status'] in domain.TERMINAL_STATUSES:
                raise DomainError(f"{asset['asset_code']} is {asset['status']} (terminal) and cannot receive diagnostic tests.", 'TERMINAL_STATE', 409)
            _date_window(con, asset, date_part, label='test_time')

            cnt = con.execute('SELECT COUNT(*) FROM TestResult WHERE asset_id=?', (asset['asset_id'],)).fetchone()[0]
            tid = f"TR-{asset['asset_code']}-{cnt + 1}"

            ir = payload.get('internal_resistance_mohm')
            temp = payload.get('cell_temp_celsius')
            vdelta = payload.get('voltage_delta_mv')
            rul = payload.get('remaining_useful_life_cycles')

            has_adv = False
            try:
                has_adv = bool([r[1] for r in con.execute('PRAGMA table_info(TestResult)') if r[1] == 'internal_resistance_mohm'])
            except Exception:
                pass

            if has_adv:
                con.execute('''INSERT INTO TestResult(test_result_id, asset_id, test_time, state_of_health_pct, cycle_count,
                                                      internal_resistance_mohm, cell_temp_celsius, voltage_delta_mv, remaining_useful_life_cycles, recorded_by)
                               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                            (tid, asset['asset_id'], test_time, round(soh_val, 2), cycle_val,
                             float(ir) if ir is not None and str(ir).strip() != '' else None,
                             float(temp) if temp is not None and str(temp).strip() != '' else None,
                             float(vdelta) if vdelta is not None and str(vdelta).strip() != '' else None,
                             int(rul) if rul is not None and str(rul).strip() != '' else None,
                             user['user_id']))
            else:
                con.execute('''INSERT INTO TestResult(test_result_id, asset_id, test_time, state_of_health_pct, cycle_count, recorded_by)
                               VALUES (?, ?, ?, ?, ?, ?)''',
                            (tid, asset['asset_id'], test_time, round(soh_val, 2), cycle_val, user['user_id']))

            ev_notes = f"Diagnostic test {tid}: {round(soh_val, 1)}% SoH" + (f", {cycle_val} cycles" if cycle_val is not None else "")
            if temp is not None and str(temp).strip() != '':
                ev_notes += f", {temp}°C"
            if notes:
                ev_notes += f". {notes}"
            ev_id = audit.append_event(con, asset_id=asset['asset_id'], event_type='TESTED', event_at=date_part,
                                       location=loc, organization=user['organization'], notes=ev_notes[:MAX_NOTES],
                                       actor_id=user['user_id'], evidence_status='SELF_REPORTED',
                                       evidence_ref=tid, idempotency_key=key)
            return {
                'ok': True,
                'test_result_id': tid,
                'event_id': ev_id,
                'asset_code': asset['asset_code'],
                'test_time': test_time,
                'state_of_health_pct': round(soh_val, 2),
                'cycle_count': cycle_val,
                'internal_resistance_mohm': float(ir) if ir is not None and str(ir).strip() != '' else None,
                'cell_temp_celsius': float(temp) if temp is not None and str(temp).strip() != '' else None,
                'voltage_delta_mv': float(vdelta) if vdelta is not None and str(vdelta).strip() != '' else None,
                'recorded_by': user['user_id'],
                'message': f"Diagnostic test {tid} recorded ({round(soh_val, 1)}% SoH)."
            }
    return _guard(work)



# ---------- read models ----------
def _page(params, default=50, maximum=200):
    try:
        limit = max(1, min(int(params.get('limit', [default])[0]), maximum))
        offset = max(0, int(params.get('offset', [0])[0]))
    except ValueError:
        raise DomainError('limit and offset must be integers.', 'BAD_PAGING')
    return limit, offset


def list_assets(con, params):
    q = params.get('q', [''])[0].strip()
    status = params.get('status', [''])[0].strip().upper()
    kind = params.get('type', [''])[0].strip().upper()
    batch = params.get('batch', [''])[0].strip()
    where, args = ['1=1'], []
    if q:
        where.append('(asset_code LIKE ? OR manufacturer LIKE ? OR chemistry LIKE ? OR batch_code LIKE ?)')
        args += [f'%{q}%'] * 4
    if status in domain.ASSET_STATUSES:
        where.append('status=?'); args.append(status)
    if kind in domain.ASSET_TYPES:
        where.append('asset_type=?'); args.append(kind)
    if batch:
        where.append('batch_code=?'); args.append(batch)
    sorts = {'code': 'asset_code', 'status': 'status, asset_code', 'last_event': 'last_event_at DESC, asset_code',
             'type': "CASE asset_type WHEN 'BATTERY_PACK' THEN 0 WHEN 'STORAGE_SYSTEM' THEN 1 WHEN 'VEHICLE' THEN 2 WHEN 'MODULE' THEN 3 ELSE 4 END, asset_code"}
    order = sorts.get(params.get('sort', ['type'])[0], sorts['type'])
    limit, offset = _page(params)
    w = ' AND '.join(where)
    total = con.execute(f'SELECT COUNT(*) FROM v_asset_overview WHERE {w}', args).fetchone()[0]
    rows = con.execute(f'SELECT * FROM v_asset_overview WHERE {w} ORDER BY {order} LIMIT ? OFFSET ?', args + [limit, offset]).fetchall()
    return {'items': [dict(r) for r in rows], 'total': total, 'limit': limit, 'offset': offset}


def list_events(con, params):
    q = params.get('q', [''])[0].strip()
    etype = params.get('type', [''])[0].strip().upper()
    code = params.get('asset', [''])[0].strip().upper()
    where, args = ['1=1'], []
    if q:
        where.append('(e.notes LIKE ? OR e.organization LIKE ? OR e.location LIKE ? OR a.asset_code LIKE ?)'); args += [f'%{q}%'] * 4
    if etype in domain.EVENT_TYPES:
        where.append('e.event_type=?'); args.append(etype)
    if code:
        where.append('a.asset_code=?'); args.append(code)
    limit, offset = _page(params, 50, 200)
    w = ' AND '.join(where)
    base = f'FROM LifecycleEvent e JOIN Asset a ON a.asset_id=e.asset_id LEFT JOIN AppUser u ON u.user_id=e.actor_id WHERE {w}'
    total = con.execute(f'SELECT COUNT(*) {base}', args).fetchone()[0]
    rows = con.execute(f'SELECT e.event_id,e.event_type,e.event_at,e.location,e.organization,e.notes,e.evidence_status,e.evidence_ref,'
                       f'e.actor_id,u.role AS actor_role,e.prev_hash,e.event_hash,a.asset_code,a.asset_type {base} '
                       f'ORDER BY e.event_at DESC, e.event_id DESC LIMIT ? OFFSET ?', args + [limit, offset]).fetchall()
    return {'items': [dict(r) for r in rows], 'total': total, 'limit': limit, 'offset': offset}


def summary(con):
    one = lambda sql: con.execute(sql).fetchone()[0]
    issues = find_issues(con)
    by_status = {r[0]: r[1] for r in con.execute('SELECT status, COUNT(*) FROM Asset GROUP BY status')}
    
    # Circular economy & diagnostics summary (EU 2023/1542 & India BWMR)
    has_test_tbl = con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='TestResult'").fetchone() is not None
    avg_soh = None
    if has_test_tbl:
        row = con.execute('''
            WITH latest AS (
                SELECT state_of_health_pct,
                       ROW_NUMBER() OVER (PARTITION BY asset_id ORDER BY test_time DESC) as rn
                FROM TestResult
            )
            SELECT ROUND(AVG(state_of_health_pct), 1) FROM latest WHERE rn = 1
        ''').fetchone()
        if row and row[0] is not None:
            avg_soh = row[0]

    has_carbon = con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='CarbonFootprint'").fetchone() is not None
    avg_carbon = None
    if has_carbon:
        crow = con.execute('SELECT ROUND(AVG(total_kg_co2e_per_kwh), 1) FROM CarbonFootprint').fetchone()
        if crow and crow[0] is not None:
            avg_carbon = crow[0]

    has_minerals = con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='CriticalMinerals'").fetchone() is not None
    minerals_summary = None
    if has_minerals:
        mrow = con.execute('''
            SELECT ROUND(SUM(lithium_kg), 1), ROUND(SUM(cobalt_kg), 1), ROUND(SUM(nickel_kg), 1)
            FROM CriticalMinerals
        ''').fetchone()
        if mrow and mrow[0] is not None:
            minerals_summary = {'lithium_kg': mrow[0], 'cobalt_kg': mrow[1], 'nickel_kg': mrow[2]}

    circularity = {
        'active_mobility': one("SELECT COUNT(*) FROM Asset WHERE asset_type='BATTERY_PACK' AND status='ACTIVE'"),
        'second_life_storage': one("SELECT COUNT(*) FROM Asset WHERE asset_type='BATTERY_PACK' AND status='SECOND_LIFE'"),
        'in_repair': one("SELECT COUNT(*) FROM Asset WHERE asset_type='BATTERY_PACK' AND status='IN_REPAIR'"),
        'recycled': one("SELECT COUNT(*) FROM Asset WHERE asset_type='BATTERY_PACK' AND status='RECYCLED'"),
        'avg_fleet_soh': avg_soh,
        'avg_carbon_intensity': avg_carbon,
        'minerals_tracked': minerals_summary
    }

    return {
        'as_of': datetime.datetime.now().isoformat(timespec='seconds'),
        'assets': one('SELECT COUNT(*) FROM Asset'),
        'battery_packs': one("SELECT COUNT(*) FROM Asset WHERE asset_type='BATTERY_PACK'"),
        'active_passports': one("SELECT COUNT(*) FROM Passport WHERE status='ACTIVE'"),
        'events': one('SELECT COUNT(*) FROM LifecycleEvent'),
        'by_status': by_status,
        'circularity': circularity,
        'open_links': one('SELECT COUNT(*) FROM v_open_relationship'),
        'issues': len(issues),
        'issues_high': sum(1 for i in issues if i['severity'] == 'HIGH'),
        'audit': audit.verify_chain(con),
        'definitions': {
            'assets': 'Rows in Asset (all types, all statuses).',
            'active_passports': "Rows in Passport with status 'ACTIVE'.",
            'issues': 'Rows returned by the data-quality rules (see Data quality page). Rule matches, not proof of fraud.',
            'open_links': 'AssetRelationship rows with valid_to IS NULL.'},
        'attention': [i for i in issues if i['severity'] == 'HIGH'][:5]}


def lineage(con, code):
    """Neighbourhood view for the Asset detail page (bounded BFS, both directions, cycle-safe)."""
    asset = _asset(con, code)
    seen, frontier, nodes, links = {asset['asset_id']}, [(asset['asset_id'], 0)], {asset['asset_id']: dict(asset)}, {}
    while frontier:
        cur, depth = frontier.pop(0)
        if depth >= 4:
            continue
        for rr in con.execute('''SELECT r.*, p.asset_code AS p_code, p.asset_type AS p_type, p.status AS p_status,
                                        c.asset_code AS c_code, c.asset_type AS c_type, c.status AS c_status
                                 FROM AssetRelationship r JOIN Asset p ON p.asset_id=r.parent_asset_id
                                 JOIN Asset c ON c.asset_id=r.child_asset_id
                                 WHERE r.parent_asset_id=? OR r.child_asset_id=?''', (cur, cur)):
            d = dict(rr); links[d['relationship_id']] = d
            for nid, ncode, ntype, nst in ((d['parent_asset_id'], d['p_code'], d['p_type'], d['p_status']),
                                           (d['child_asset_id'], d['c_code'], d['c_type'], d['c_status'])):
                nodes.setdefault(nid, {'asset_id': nid, 'asset_code': ncode, 'asset_type': ntype, 'status': nst})
                if nid not in seen:
                    seen.add(nid); frontier.append((nid, depth + 1))
    ev = [dict(r) for r in con.execute('''SELECT e.event_id,e.event_type,e.event_at,e.location,e.organization,e.notes,e.evidence_status,e.actor_id
                                          FROM LifecycleEvent e WHERE asset_id=? ORDER BY event_at,event_id''', (asset['asset_id'],))]
    hist = [dict(r) for r in con.execute('SELECT * FROM Passport WHERE asset_id=? ORDER BY passport_version DESC', (asset['asset_id'],))]
    tests = [dict(r) for r in con.execute('SELECT * FROM TestResult WHERE asset_id=? ORDER BY test_time DESC', (asset['asset_id'],))] if con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='TestResult'").fetchone() else []
    
    carbon = None
    if hist and con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='CarbonFootprint'").fetchone():
        crow = con.execute('SELECT * FROM CarbonFootprint WHERE passport_id=?', (hist[0]['passport_id'],)).fetchone()
        carbon = dict(crow) if crow else None

    minerals = None
    if con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='CriticalMinerals'").fetchone():
        mrow = con.execute('SELECT * FROM CriticalMinerals WHERE asset_id=?', (asset['asset_id'],)).fetchone()
        minerals = dict(mrow) if mrow else None

    return {'asset': dict(asset), 'passport': hist[0] if hist else None, 'passport_history': hist,
            'carbon': carbon, 'minerals': minerals,
            'nodes': list(nodes.values()), 'relationships': sorted(links.values(), key=lambda x: x['relationship_id']), 'events': ev, 'tests': tests,
            'note': 'Neighbourhood view (max 4 hops, all link types, past and present). Use the Recall page for directed, date-aware tracing.'}


# ---------- data quality ----------
RULES = [
 {'rule_id': 'DQ-001', 'code': 'RECYCLED_PASSPORT_ACTIVE', 'severity': 'HIGH', 'title': 'Recycled asset has an active passport',
  'suggestion': 'Check the recycling record, then close the passport only if authoritative evidence supports it.',
  'limits': 'Detects a contradiction between two columns; cannot tell which one is wrong.',
  'sql': """SELECT a.asset_code, p.passport_id || ' is ACTIVE while ' || a.asset_code || ' is RECYCLED' AS detail, p.passport_id AS evidence
FROM Asset a JOIN Passport p ON p.asset_id = a.asset_id
WHERE a.status = 'RECYCLED' AND p.status = 'ACTIVE'"""},
 {'rule_id': 'DQ-002', 'code': 'MULTIPLE_OPEN_PARENTS', 'severity': 'HIGH', 'title': 'Component has multiple open parents',
  'suggestion': 'Confirm where the component physically is, then close the outdated link with a dated correction.',
  'limits': 'A component cannot be in two packs at once, but the data cannot say which record is right.',
  'sql': """SELECT c.asset_code, c.asset_code || ' has ' || COUNT(*) || ' open parents: ' || GROUP_CONCAT(p.asset_code, ', ') AS detail,
       GROUP_CONCAT('link#' || r.relationship_id, ', ') AS evidence
FROM v_open_relationship r
JOIN Asset c ON c.asset_id = r.child_asset_id JOIN Asset p ON p.asset_id = r.parent_asset_id
GROUP BY r.child_asset_id HAVING COUNT(*) > 1"""},
 {'rule_id': 'DQ-003', 'code': 'BATTERY_NO_ACTIVE_PASSPORT', 'severity': 'MEDIUM', 'title': 'Battery pack has no active passport',
  'suggestion': 'Check whether a passport should exist and verify any previous-passport link before issuing one.',
  'limits': 'Only checks existence, not whether passport content is correct.',
  'sql': """SELECT a.asset_code, a.asset_code || ' is ' || a.status || ' but has no ACTIVE passport' AS detail, a.asset_id AS evidence
FROM Asset a LEFT JOIN v_active_passport p ON p.asset_id = a.asset_id
WHERE a.asset_type = 'BATTERY_PACK' AND a.status IN ('ACTIVE','IN_REPAIR','SECOND_LIFE') AND p.passport_id IS NULL"""},
 {'rule_id': 'DQ-004', 'code': 'PASSPORT_CHAIN_INVALID', 'severity': 'HIGH', 'title': 'Passport version chain is invalid',
  'suggestion': 'Passport versions must chain to an earlier version of the same asset.',
  'limits': 'New writes are blocked by a trigger; this finds legacy or imported rows.',
  'sql': """SELECT a.asset_code, p.passport_id || ' points to ' || p.previous_passport_id || ', which is not an earlier version of the same asset' AS detail, p.passport_id AS evidence
FROM Passport p JOIN Asset a ON a.asset_id = p.asset_id
LEFT JOIN Passport q ON q.passport_id = p.previous_passport_id
WHERE p.previous_passport_id IS NOT NULL
  AND (q.passport_id IS NULL OR q.asset_id <> p.asset_id OR q.passport_version >= p.passport_version)"""},
 {'rule_id': 'DQ-005', 'code': 'AUDIT_CHAIN_BROKEN', 'severity': 'HIGH', 'title': 'Event hash chain does not verify', 'suggestion': 'Compare against a stored copy of the chain tip; investigate who changed the database file.',
  'limits': 'Detects edits made without recomputing the chain; says nothing about whether recorded facts were true.', 'sql': '-- computed in audit.verify_chain() (Python, SHA-256 over canonical event fields)'},
 {'rule_id': 'DQ-006', 'code': 'OVERLAPPING_PARENT_HISTORY', 'severity': 'HIGH', 'title': 'Historical parent intervals overlap',
  'suggestion': 'Adjust the dates with a documented correction. New overlaps are blocked by a trigger.',
  'limits': 'Open-vs-open overlaps are reported by DQ-002 instead.',
  'sql': """SELECT c.asset_code, c.asset_code || ' was linked to two parents at once: link#' || r1.relationship_id || ' and link#' || r2.relationship_id AS detail,
       'link#' || r1.relationship_id || ', link#' || r2.relationship_id AS evidence
FROM AssetRelationship r1
JOIN AssetRelationship r2 ON r1.child_asset_id = r2.child_asset_id AND r1.relationship_id < r2.relationship_id
 AND r1.valid_from < COALESCE(r2.valid_to, '9999-12-31') AND r2.valid_from < COALESCE(r1.valid_to, '9999-12-31')
JOIN Asset c ON c.asset_id = r1.child_asset_id
WHERE NOT (r1.valid_to IS NULL AND r2.valid_to IS NULL)"""},
 {'rule_id': 'DQ-007', 'code': 'EVENT_BEFORE_CREATION', 'severity': 'MEDIUM', 'title': 'Event dated before the asset existed',
  'suggestion': 'Check the event date or the asset creation date.', 'limits': 'Dates are self-reported.',
  'sql': """SELECT a.asset_code, 'event#' || e.event_id || ' (' || e.event_type || ') is dated ' || e.event_at || ' before creation ' || a.created_at AS detail, 'event#' || e.event_id AS evidence
FROM LifecycleEvent e JOIN Asset a ON a.asset_id = e.asset_id WHERE e.event_at < a.created_at"""},
]


def rule_catalog():
    return [{k: r[k] for k in ('rule_id', 'code', 'severity', 'title', 'suggestion', 'limits', 'sql')} for r in RULES]


def find_issues(con):
    out = []
    for r in RULES:
        if r['rule_id'] == 'DQ-005':
            v = audit.verify_chain(con)
            if not v['ok']:
                out.append({'rule_id': r['rule_id'], 'code': r['code'], 'severity': r['severity'], 'asset_code': '—', 'title': r['title'],
                            'detail': f'Chain breaks at event #{v["first_bad_event_id"]}: {v["reason"]}.', 'evidence': f'event#{v["first_bad_event_id"]}',
                            'suggestion': r['suggestion'], 'limits': r['limits']})
            continue
        for row in con.execute(r['sql']).fetchall():
            out.append({'rule_id': r['rule_id'], 'code': r['code'], 'severity': r['severity'], 'asset_code': row['asset_code'], 'title': r['title'],
                        'detail': row['detail'], 'evidence': row['evidence'], 'suggestion': r['suggestion'], 'limits': r['limits']})
    return out


# ---------- CSV (bounded, formula-injection safe) ----------
def csv_cell(v):
    s = '' if v is None else str(v)
    if s[:1] in ('=', '+', '-', '@', '\t', '\r'):
        s = "'" + s
    return s


def to_csv(columns, rows) -> bytes:
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator='\r\n', quoting=csv.QUOTE_ALL)
    w.writerow(columns)
    for r in rows:
        w.writerow([csv_cell(r[c]) for c in columns])
    return ('\ufeff' + buf.getvalue()).encode('utf-8')
