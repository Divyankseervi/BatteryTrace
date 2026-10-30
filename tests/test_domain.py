"""Lifecycle state machine, roles, dates, rollback, idempotency, transfers (service layer, temp DB)."""
import sqlite3
from harness import DbCase
import services, recall
from domain import DomainError


def ev(code, etype, date='2026-10-26', **kw):
    p = {'asset_code': code, 'event_type': etype, 'event_at': date, 'location': 'Lab', 'organization': 'Org', 'notes': 'n'}
    p.update(kw); return p


class TransitionTests(DbCase):
    def rec(self, *a, user='U-SVC', **k):
        return services.record_event(self.con, ev(*a, **k), user)

    def assertRejectedUnchanged(self, code, status, fn):
        before = self.snapshot()
        with self.assertRaises(DomainError) as cm:
            fn()
        self.assertEqual(cm.exception.code, code)
        self.assertEqual(cm.exception.status, status)
        self.assertEqual(self.snapshot(), before, 'rejected operation must not change ANY table')

    def test_repaired_requires_in_repair(self):
        self.assertRejectedUnchanged('ILLEGAL_TRANSITION', 409, lambda: self.rec('PACK-1001', 'REPAIRED'))

    def test_repair_cycle_returns_to_active(self):
        self.rec('PACK-1001', 'REPAIR_STARTED', '2026-10-01')
        self.assertEqual(self.one("SELECT status FROM Asset WHERE asset_code='PACK-1001'"), 'IN_REPAIR')
        r = self.rec('PACK-1001', 'REPAIRED', '2026-10-10')
        self.assertEqual(r['new_status'], 'ACTIVE')

    def test_repair_of_second_life_pack_returns_to_second_life(self):
        self.rec('PACK-1001', 'REPURPOSED', '2026-09-01')
        self.rec('PACK-1001', 'REPAIR_STARTED', '2026-09-05')
        self.assertEqual(self.rec('PACK-1001', 'REPAIRED', '2026-09-09')['new_status'], 'SECOND_LIFE')

    def test_seeded_in_repair_pack_can_be_repaired(self):
        self.assertEqual(self.rec('PACK-4001', 'REPAIRED')['new_status'], 'ACTIVE')

    def test_repurpose_twice_rejected(self):
        self.rec('PACK-1001', 'REPURPOSED', '2026-09-01')
        self.assertRejectedUnchanged('ILLEGAL_TRANSITION', 409, lambda: self.rec('PACK-1001', 'REPURPOSED', '2026-09-02'))

    def test_repurpose_only_battery_pack(self):
        self.assertRejectedUnchanged('WRONG_ASSET_TYPE', 409, lambda: self.rec('MOD-1001-A', 'REPURPOSED'))

    def test_repurpose_needs_active_passport(self):
        with self.con:
            self.con.execute("INSERT INTO Asset VALUES ('X1','PACK-X1','BATTERY_PACK','M','NMC',1,NULL,'ACTIVE','2025-01-01')")
        self.assertRejectedUnchanged('NO_ACTIVE_PASSPORT', 409, lambda: self.rec('PACK-X1', 'REPURPOSED'))

    def test_manufactured_once(self):
        self.assertRejectedUnchanged('DUPLICATE_EVENT', 409, lambda: self.rec('PACK-1001', 'MANUFACTURED', user='U-MFR'))

    def test_terminal_state_blocks_everything(self):
        self.rec('PACK-5001', 'RECYCLED', user='U-REC')
        for t, u in (('INSPECTED', 'U-SVC'), ('TESTED', 'U-REC'), ('RECYCLED', 'U-REC')):
            self.assertRejectedUnchanged('TERMINAL_STATE', 409, lambda t=t, u=u: self.rec('PACK-5001', t, user=u))

    def test_roles(self):
        self.assertRejectedUnchanged('FORBIDDEN', 403, lambda: self.rec('PACK-1001', 'INSPECTED', user='U-AUD'))
        self.assertRejectedUnchanged('FORBIDDEN', 403, lambda: self.rec('PACK-1001', 'RECYCLED', user='U-SVC'))
        self.assertRejectedUnchanged('FORBIDDEN', 403, lambda: self.rec('PACK-1001', 'REPAIR_STARTED', user='U-REC'))
        self.rec('PACK-5001', 'RECYCLED', user='U-REC')   # recycler may recycle

    def test_missing_or_unknown_user(self):
        for u, code in ((None, 'NO_USER'), ('U-NOPE', 'UNKNOWN_USER')):
            with self.assertRaises(DomainError) as cm:
                services.record_event(self.con, ev('PACK-1001', 'INSPECTED'), u)
            self.assertEqual(cm.exception.code, code); self.assertEqual(cm.exception.status, 401)

    def test_verified_evidence_not_selfservice(self):
        self.assertRejectedUnchanged('EVIDENCE_NOT_SUPPORTED', 400, lambda: self.rec('PACK-1001', 'INSPECTED', evidence_status='VERIFIED'))

    def test_input_validation(self):
        bad = [(dict(event_at='2026-13-01'), 'BAD_DATE'), (dict(event_at='26-10-2026'), 'BAD_DATE'), (dict(event_at='2026-02-30'), 'BAD_DATE'),
               (dict(event_at='2999-01-01'), 'FUTURE_DATE'), (dict(event_at='2024-02-01'), 'BEFORE_CREATION'),
               (dict(event_at='2025-01-01'), 'OUT_OF_ORDER'), (dict(location=''), 'MISSING_FIELD'), (dict(notes='x' * 1001), 'TOO_LONG'),
               (dict(event_type='EXPLODED'), 'BAD_EVENT_TYPE')]
        for patch, code in bad:
            p = ev('PACK-1001', 'INSPECTED'); p.update(patch)
            before = self.snapshot()
            with self.assertRaises(DomainError, msg=str(patch)) as cm:
                services.record_event(self.con, p, 'U-SVC')
            self.assertEqual(cm.exception.code, code, patch)
            self.assertEqual(self.snapshot(), before)

    def test_same_day_events_allowed_boundary(self):
        self.rec('PACK-1001', 'INSPECTED', '2026-10-26'); self.rec('PACK-1001', 'TESTED', '2026-10-26')

    def test_boundary_event_on_creation_date(self):
        self.rec('PACK-5001', 'INSPECTED', '2024-11-20')


class RollbackAndRecyclingTests(DbCase):
    def test_recycle_closes_passport_and_links_atomically(self):
        services.record_event(self.con, ev('PACK-5001', 'RECYCLED'), 'U-REC')
        self.assertEqual(self.one("SELECT status FROM Passport WHERE asset_id='A014'"), 'CLOSED')
        self.assertEqual(self.one("SELECT COUNT(*) FROM AssetRelationship WHERE parent_asset_id='A014' AND valid_to IS NULL"), 0)
        self.assertEqual(self.one("SELECT valid_to FROM AssetRelationship WHERE parent_asset_id='A014'"), '2026-10-26')

    def test_midway_failure_rolls_back_event_status_and_passport(self):
        """RECYCLED on the day a link starts: event+status+passport are written first, then the link close
        fails -> the WHOLE transaction must roll back."""
        before = self.snapshot()
        with self.assertRaises(DomainError) as cm:
            services.record_event(self.con, ev('PACK-5001', 'RECYCLED', '2024-11-20'), 'U-REC')
        self.assertEqual(cm.exception.code, 'BAD_INTERVAL')
        self.assertEqual(self.snapshot(), before)
        self.assertTrue(self.con.in_transaction is False)

    def test_database_failure_after_event_insert_rolls_everything_back(self):
        """Inject a trigger that aborts the passport update (3rd write of REPURPOSED). The event row and the
        asset status change that were already written in the same transaction must disappear."""
        self.con.execute("CREATE TRIGGER t_boom BEFORE UPDATE OF status ON Passport BEGIN SELECT RAISE(ABORT,'injected failure'); END")
        before = self.snapshot()
        with self.assertRaises(DomainError) as cm:
            services.record_event(self.con, ev('PACK-1001', 'REPURPOSED'), 'U-SVC')
        self.assertEqual(cm.exception.code, 'DB_CONSTRAINT')
        self.assertEqual(self.snapshot(), before)

    def test_next_passport_version_skips_existing_versions(self):
        with self.con:
            self.con.execute("INSERT INTO Passport VALUES ('P-1001-V2','A001',2,'SUPERSEDED','2024-03-01','P-1001')")
        r = services.record_event(self.con, ev('PACK-1001', 'REPURPOSED'), 'U-SVC')
        self.assertEqual(r['new_passport_id'], 'PACK-1001-V3')

    def test_repurpose_passport_chain_is_valid(self):
        services.record_event(self.con, ev('PACK-1001', 'REPURPOSED'), 'U-SVC')
        rows = self.q("SELECT passport_id, previous_passport_id, passport_version, status FROM Passport WHERE asset_id='A001' ORDER BY passport_version")
        self.assertEqual([(r[0], r[1], r[2], r[3]) for r in rows], [('P-1001', None, 1, 'SUPERSEDED'), ('PACK-1001-V2', 'P-1001', 2, 'ACTIVE')])
        self.assertEqual(self.one("SELECT COUNT(*) FROM Passport WHERE asset_id='A001' AND status='ACTIVE'"), 1)


class IdempotencyTests(DbCase):
    def test_same_key_same_payload_is_replayed_not_duplicated(self):
        a = services.record_event(self.con, ev('PACK-1001', 'INSPECTED', idempotency_key='k1'), 'U-SVC')
        n = self.one('SELECT COUNT(*) FROM LifecycleEvent')
        b = services.record_event(self.con, ev('PACK-1001', 'INSPECTED', idempotency_key='k1'), 'U-SVC')
        self.assertTrue(b['replayed']); self.assertEqual(a['event_id'], b['event_id']); self.assertEqual(self.one('SELECT COUNT(*) FROM LifecycleEvent'), n)

    def test_replay_of_terminal_event_still_succeeds(self):
        a = services.record_event(self.con, ev('PACK-5001', 'RECYCLED', idempotency_key='r1'), 'U-REC')
        b = services.record_event(self.con, ev('PACK-5001', 'RECYCLED', idempotency_key='r1'), 'U-REC')   # would be TERMINAL_STATE without idempotency
        self.assertTrue(b['replayed']); self.assertEqual(a['event_id'], b['event_id'])

    def test_same_key_different_payload_conflicts(self):
        services.record_event(self.con, ev('PACK-1001', 'INSPECTED', idempotency_key='k2'), 'U-SVC')
        with self.assertRaises(DomainError) as cm:
            services.record_event(self.con, ev('PACK-1001', 'TESTED', idempotency_key='k2'), 'U-SVC')
        self.assertEqual(cm.exception.code, 'IDEMPOTENCY_CONFLICT')

    def test_without_key_duplicates_are_allowed_as_distinct_events(self):
        services.record_event(self.con, ev('PACK-1001', 'INSPECTED'), 'U-SVC'); services.record_event(self.con, ev('PACK-1001', 'INSPECTED'), 'U-SVC')


class DatabaseConstraintTests(DbCase):
    """These hit SQLite directly: the database must refuse bad data even if the app is bypassed."""

    def bad(self, sql, *a):
        with self.assertRaises(sqlite3.IntegrityError):
            self.con.execute(sql, a)

    def test_event_ledger_is_append_only(self):
        self.bad("UPDATE LifecycleEvent SET notes='edited' WHERE event_id=1")
        self.bad('DELETE FROM LifecycleEvent WHERE event_id=1')

    def test_passport_chain_rules(self):
        self.bad("INSERT INTO Passport VALUES ('PX','A002',2,'ACTIVE','2025-01-01','P-1001')")          # previous belongs to another asset
        self.bad("INSERT INTO Passport VALUES ('PY','A001',1,'SUPERSEDED','2025-01-01','P-1001')")     # same version, not earlier
        self.bad("UPDATE Passport SET previous_passport_id='P-2001-V2' WHERE passport_id='P-2001-V1'")  # cycle attempt: identity fields immutable
        self.bad("INSERT INTO Passport VALUES ('PZ','A001',2,'ACTIVE','2025-01-01','P-1001')")         # second ACTIVE passport (partial unique index)

    def test_one_active_passport_index(self):
        self.bad("INSERT INTO Passport VALUES ('P-1001-B','A001',3,'ACTIVE','2025-01-01','P-1001')")

    def test_hierarchy_rule(self):
        self.bad("INSERT INTO AssetRelationship(parent_asset_id,child_asset_id,relationship_type,valid_from) VALUES ('A004','A001','CONTAINS','2026-01-01')")  # CELL contains PACK
        self.bad("INSERT INTO AssetRelationship(parent_asset_id,child_asset_id,relationship_type,valid_from) VALUES ('A001','A004','CONTAINS','2026-01-01')")  # PACK contains CELL directly

    def test_overlap_blocked_but_touching_allowed(self):
        self.bad("INSERT INTO AssetRelationship(parent_asset_id,child_asset_id,relationship_type,valid_from) VALUES ('A014','A003','CONTAINS','2025-01-01')")   # A003 already has an open parent
        with self.con:
            self.con.execute("UPDATE AssetRelationship SET valid_to='2026-01-01' WHERE child_asset_id='A003'")
            self.con.execute("INSERT INTO AssetRelationship(parent_asset_id,child_asset_id,relationship_type,valid_from) VALUES ('A014','A003','CONTAINS','2026-01-01')")   # hand-over on the same date

    def test_cannot_rewrite_link_identity(self):
        self.bad("UPDATE AssetRelationship SET parent_asset_id='A014' WHERE relationship_id=2")
        self.bad("UPDATE AssetRelationship SET valid_from='2020-01-01' WHERE relationship_id=2")

    def test_interval_and_self_link_checks(self):
        self.bad("INSERT INTO AssetRelationship(parent_asset_id,child_asset_id,relationship_type,valid_from,valid_to) VALUES ('A014','A003','CONTAINS','2026-05-01','2026-04-01')")
        self.bad("INSERT INTO AssetRelationship(parent_asset_id,child_asset_id,relationship_type,valid_from) VALUES ('A001','A001','CONTAINS','2026-01-01')")

    def test_terminal_asset_irreversible_and_no_events(self):
        self.bad("UPDATE Asset SET status='ACTIVE' WHERE asset_id='A009'")
        self.con.execute("INSERT INTO Asset VALUES ('A-RET','PACK-RET','BATTERY_PACK','m','NMC',50,NULL,'RETIRED','2024-01-01')")
        self.bad("UPDATE Asset SET status='ACTIVE' WHERE asset_id='A-RET'")
        self.bad("INSERT INTO LifecycleEvent(asset_id,event_type,event_at,location,organization,prev_hash,event_hash) VALUES ('A009','INSPECTED','2026-01-01','x','y','a','b')")
        self.bad("INSERT INTO LifecycleEvent(asset_id,event_type,event_at,location,organization,prev_hash,event_hash) VALUES ('A-RET','INSPECTED','2026-01-01','x','y','a','b')")

    def test_value_checks(self):
        self.bad("INSERT INTO Asset VALUES ('Z','Z1','BATTERY_PACK','m','NMC',-1,NULL,'ACTIVE','2025-01-01')")      # negative capacity
        self.bad("INSERT INTO Asset VALUES ('Z','Z1','TRUCK','m','NMC',1,NULL,'ACTIVE','2025-01-01')")             # bad type
        self.bad("INSERT INTO Asset VALUES ('Z','Z1','CELL','m','NMC',1,NULL,'ACTIVE','01/01/2025')")              # bad date format
        self.bad("INSERT INTO Asset VALUES ('Z','PACK-1001','CELL','m','NMC',1,NULL,'ACTIVE','2025-01-01')")       # duplicate code
        self.bad("INSERT INTO Passport VALUES ('PQ','NOPE',1,'ACTIVE','2025-01-01',NULL)")                          # FK violation


class TransferTests(DbCase):
    def xfer(self, child, parent, date='2026-01-01', user='U-SVC', **k):
        p = {'child_code': child, 'new_parent_code': parent, 'effective_date': date, 'reason': 'rebuild', 'location': 'Bay 2'}; p.update(k)
        return services.transfer_component(self.con, p, user)

    def test_transfer_closes_old_and_opens_new_with_event(self):
        r = self.xfer('MOD-1001-B', 'PACK-5001')
        self.assertEqual(r['closed_parent'], 'PACK-1001')
        links = self.q("SELECT parent_asset_id, valid_from, valid_to FROM AssetRelationship WHERE child_asset_id='A003' ORDER BY relationship_id")
        self.assertEqual([tuple(x) for x in links], [('A001', '2024-02-10', '2026-01-01'), ('A014', '2026-01-01', None)])
        e = self.q("SELECT event_type, notes FROM LifecycleEvent WHERE event_id=?", r['event_id'])[0]
        self.assertEqual(e[0], 'TRANSFERRED'); self.assertIn('PACK-1001', e[1]); self.assertIn('PACK-5001', e[1])

    def test_transfer_is_visible_in_time_travel_recall(self):
        self.xfer('MOD-1001-B', 'PACK-5001', '2026-01-01')
        before = recall.recall_report(self.con, codes=['MOD-1001-B'], mode='AS_OF', as_of='2025-06-01')
        after = recall.recall_report(self.con, codes=['MOD-1001-B'], mode='AS_OF', as_of='2026-06-01')
        self.assertIn('PACK-1001', [a['asset_code'] for a in before['affected']]); self.assertNotIn('PACK-5001', [a['asset_code'] for a in before['affected']])
        self.assertIn('PACK-5001', [a['asset_code'] for a in after['affected']]); self.assertNotIn('PACK-1001', [a['asset_code'] for a in after['affected']])

    def test_rejections_leave_database_unchanged(self):
        cases = [(('MOD-1001-B', 'PACK-1001'), 'NO_CHANGE'), (('MOD-1001-B', 'CELL-1001-A1'), 'BAD_HIERARCHY'), (('PACK-1001', 'MOD-1001-A'), 'BAD_HIERARCHY'),
                 (('MOD-1001-B', 'PACK-3001'), 'TERMINAL_STATE'), (('MOD-3001-A', 'PACK-5001'), 'TERMINAL_STATE'), (('MOD-1001-B', 'NOPE'), 'UNKNOWN_ASSET'),
                 (('MOD-4001-A', 'PACK-1001'), 'CONFLICTING_PARENTS')]
        for (c, p), code in cases:
            before = self.snapshot()
            with self.assertRaises(DomainError, msg=f'{c}->{p}') as cm:
                self.xfer(c, p)
            self.assertEqual(cm.exception.code, code, f'{c}->{p}'); self.assertEqual(self.snapshot(), before)

    def test_date_boundaries(self):
        for d, code in (('2024-02-10', 'BAD_INTERVAL'), ('2999-01-01', 'FUTURE_DATE'), ('bad', 'BAD_DATE')):
            with self.assertRaises(DomainError) as cm:
                self.xfer('MOD-1001-B', 'PACK-5001', d)
            self.assertEqual(cm.exception.code, code)

    def test_auditor_and_recycler_cannot_relink(self):
        for u in ('U-AUD', 'U-REC'):
            with self.assertRaises(DomainError) as cm:
                self.xfer('MOD-1001-B', 'PACK-5001', user=u)
            self.assertEqual(cm.exception.status, 403)

    def test_transfer_is_idempotent_with_key(self):
        a = self.xfer('MOD-1001-B', 'PACK-5001', idempotency_key='t1'); b = self.xfer('MOD-1001-B', 'PACK-5001', idempotency_key='t1')
        self.assertTrue(b['replayed']); self.assertEqual(self.one("SELECT COUNT(*) FROM AssetRelationship WHERE child_asset_id='A003'"), 2)

    def test_close_relationship_repairs_seeded_double_parent(self):
        before = {i['code'] for i in services.find_issues(self.con)}
        self.assertIn('MULTIPLE_OPEN_PARENTS', before)
        rid = self.one("SELECT relationship_id FROM AssetRelationship WHERE parent_asset_id='A011' AND child_asset_id='A012'")
        services.close_relationship(self.con, {'relationship_id': rid, 'valid_to': '2024-11-20', 'reason': 'module physically moved to PACK-5001'}, 'U-SVC')
        after = {i['code'] for i in services.find_issues(self.con)}
        self.assertNotIn('MULTIPLE_OPEN_PARENTS', after); self.assertNotIn('OVERLAPPING_PARENT_HISTORY', after)
        with self.assertRaises(DomainError) as cm:
            services.close_relationship(self.con, {'relationship_id': rid, 'valid_to': '2025-01-01', 'reason': 'again'}, 'U-SVC')
        self.assertEqual(cm.exception.code, 'ALREADY_CLOSED')

    def test_closing_wrong_overlap_leaves_historical_overlap_flagged(self):
        """Closing the NEWER link at a later date leaves two intervals that overlap in the past -> DQ-006 must say so."""
        rid = self.one("SELECT relationship_id FROM AssetRelationship WHERE parent_asset_id='A014' AND child_asset_id='A012'")
        services.close_relationship(self.con, {'relationship_id': rid, 'valid_to': '2026-01-01', 'reason': 'test'}, 'U-SVC')
        codes = {i['code'] for i in services.find_issues(self.con)}
        self.assertIn('OVERLAPPING_PARENT_HISTORY', codes); self.assertNotIn('MULTIPLE_OPEN_PARENTS', codes)


class DataQualityTests(DbCase):
    triggers = False   # we need to be able to plant bad rows

    def test_rule_catalog_matches_checks(self):
        ids = {r['rule_id'] for r in services.rule_catalog()}
        self.assertEqual(ids, {f'DQ-00{i}' for i in range(1, 8)})

    def test_invalid_passport_chain_detected(self):
        self.con.execute("INSERT INTO Passport VALUES ('PX','A002',1,'ACTIVE','2025-01-01','P-1001')")   # chains to ANOTHER asset's passport
        hits = [i for i in services.find_issues(self.con) if i['rule_id'] == 'DQ-004']
        self.assertEqual([h['evidence'] for h in hits], ['PX'])

    def test_event_before_creation_detected(self):
        import audit
        audit.append_event(self.con, asset_id='A014', event_type='INSPECTED', event_at='2020-01-01', location='x', organization='y', notes='', actor_id='U-SVC',
                           evidence_status='SELF_REPORTED', evidence_ref=None, idempotency_key=None)
        self.assertIn('DQ-007', {i['rule_id'] for i in services.find_issues(self.con)})

    def test_every_issue_has_evidence_and_limits(self):
        for i in services.find_issues(self.con):
            self.assertTrue(i['evidence'] and i['limits'] and i['suggestion'])


class DiagnosticTests(DbCase):
    def test_record_diagnostic_service_success(self):
        res = services.record_diagnostic_test(self.con, {
            'asset_code': 'PACK-1001',
            'test_time': '2026-05-15 11:30',
            'state_of_health_pct': 94.2,
            'cycle_count': 210,
            'notes': 'Scheduled annual capacity verification',
            'location': 'Bengaluru Service Center'
        }, user_id='U-SVC')
        self.assertTrue(res['ok'])
        self.assertEqual(res['asset_code'], 'PACK-1001')
        self.assertEqual(res['state_of_health_pct'], 94.2)
        self.assertEqual(res['cycle_count'], 210)
        
        # Verify TestResult row exists
        row = self.con.execute('SELECT * FROM TestResult WHERE test_result_id=?', (res['test_result_id'],)).fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row['state_of_health_pct'], 94.2)
        self.assertEqual(row['cycle_count'], 210)
        
        # Verify linked TESTED event in LifecycleEvent exists with matching evidence_ref
        ev = self.con.execute('SELECT * FROM LifecycleEvent WHERE event_id=?', (res['event_id'],)).fetchone()
        self.assertIsNotNone(ev)
        self.assertEqual(ev['event_type'], 'TESTED')
        self.assertEqual(ev['evidence_ref'], res['test_result_id'])

    def test_record_diagnostic_unauthorized_role(self):
        with self.assertRaises(DomainError) as cm:
            services.record_diagnostic_test(self.con, {
                'asset_code': 'PACK-1001',
                'test_time': '2026-05-15',
                'state_of_health_pct': 90.0,
                'cycle_count': 100
            }, user_id='U-REC')
        self.assertEqual(cm.exception.code, 'FORBIDDEN')
        self.assertEqual(cm.exception.status, 403)

    def test_record_diagnostic_invalid_soh(self):
        for bad_soh in (105.0, -5.0, 'not-a-number'):
            with self.assertRaises(DomainError) as cm:
                services.record_diagnostic_test(self.con, {
                    'asset_code': 'PACK-1001',
                    'test_time': '2026-05-15',
                    'state_of_health_pct': bad_soh
                }, user_id='U-SVC')
            self.assertEqual(cm.exception.code, 'BAD_VALUE')

    def test_record_diagnostic_terminal_asset(self):
        with self.assertRaises(DomainError) as cm:
            services.record_diagnostic_test(self.con, {
                'asset_code': 'PACK-3001',  # Already RECYCLED
                'test_time': '2026-05-15',
                'state_of_health_pct': 85.0
            }, user_id='U-SVC')
        self.assertEqual(cm.exception.code, 'TERMINAL_STATE')
        self.assertEqual(cm.exception.status, 409)


if __name__ == '__main__':
    import unittest; unittest.main(verbosity=2)



class StartupTests(__import__('unittest').TestCase):
    def test_restart_is_idempotent_and_keeps_data(self):
        from harness import fresh_db
        tmp, path = fresh_db()
        try:
            import db
            db.init_db(path); db.init_db(path)
            con = db.connect(path)
            self.assertEqual(con.execute('SELECT COUNT(*) FROM Asset').fetchone()[0], 22)
            self.assertEqual(con.execute('SELECT COUNT(*) FROM LifecycleEvent').fetchone()[0], 15)
            con.close()
        finally:
            tmp.cleanup()

    def test_old_v1_database_is_moved_aside_not_crashed_on(self):
        import sqlite3, tempfile, db
        from pathlib import Path
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'old.db'
            c = sqlite3.connect(p); c.execute('CREATE TABLE Asset(asset_id TEXT PRIMARY KEY, asset_code TEXT)'); c.execute("INSERT INTO Asset VALUES ('x','OLD')"); c.commit(); c.close()
            db.init_db(p)
            con = db.connect(p)
            self.assertEqual(con.execute('SELECT COUNT(*) FROM Asset').fetchone()[0], 22)
            con.close()
            self.assertTrue(any('v1-backup' in f.name for f in Path(d).iterdir()))


class CrashRecoveryTests(__import__('unittest').TestCase):
    def test_crash_midway_diagnostic_insert_rolls_back_atomically(self):
        from harness import fresh_db
        tmp, path = fresh_db()
        try:
            import db, audit, services
            db.init_db(path)
            con = db.connect(path)
            tip_before = audit.verify_chain(con)['tip_hash']
            events_before = con.execute('SELECT COUNT(*) FROM LifecycleEvent').fetchone()[0]
            # Inject a mid-transaction crash during diagnostic event insert
            con.execute("CREATE TRIGGER crash_trigger AFTER INSERT ON TestResult BEGIN SELECT RAISE(FAIL, 'SIMULATED_POWER_FAILURE'); END")
            with self.assertRaises(Exception):
                services.record_diagnostic_test(con, {
                    'asset_code': 'PACK-1001',
                    'test_time': '2026-10-27 12:00',
                    'state_of_health_pct': 92.0,
                    'cycle_count': 100
                }, user_id='U-SVC')
            # Verify atomic rollback: no orphan TestResult or half-committed event
            self.assertEqual(con.execute("SELECT COUNT(*) FROM TestResult WHERE state_of_health_pct=92.0").fetchone()[0], 0)
            self.assertEqual(con.execute('SELECT COUNT(*) FROM LifecycleEvent').fetchone()[0], events_before)
            self.assertEqual(con.execute('PRAGMA integrity_check').fetchone()[0], 'ok')
            audit_res = audit.verify_chain(con)
            self.assertTrue(audit_res['ok'])
            self.assertEqual(audit_res['tip_hash'], tip_before)
            con.close()
        finally:
            tmp.cleanup()

    def test_uncommitted_connection_kill_rollback(self):
        from harness import fresh_db
        tmp, path = fresh_db()
        try:
            import db, audit
            db.init_db(path)
            con1 = db.connect(path)
            con1.execute('BEGIN IMMEDIATE')
            con1.execute("INSERT INTO Asset VALUES ('A999','CRASH-ASSET','CELL','Aster Mobility','NMC',0.5,'B1','ACTIVE','2026-01-01')")
            con1.close()  # abrupt uncommitted termination
            con2 = db.connect(path)
            self.assertIsNone(con2.execute("SELECT asset_id FROM Asset WHERE asset_id='A999'").fetchone())
            self.assertEqual(con2.execute('PRAGMA integrity_check').fetchone()[0], 'ok')
            self.assertTrue(audit.verify_chain(con2)['ok'])
            con2.close()
        finally:
            tmp.cleanup()


class ScreenReaderAccessibilityTests(__import__('unittest').TestCase):
    def test_html_and_js_aria_semantics(self):
        from pathlib import Path
        root = Path(__file__).resolve().parents[1]
        html = (root / 'index.html').read_text(encoding='utf-8')
        js = (root / 'static' / 'app.js').read_text(encoding='utf-8')
        # Core document semantics
        self.assertIn('lang="en"', html)
        self.assertIn('role="status"', html)
        self.assertIn('aria-live="polite"', html)
        self.assertIn('role="note"', html)
        # Tree hierarchy ARIA semantics
        self.assertIn('role="tree"', js)
        self.assertIn('role="treeitem"', js)
        self.assertIn('aria-expanded=', js)
        self.assertIn('aria-current=', js)
        # Table accessibility
        self.assertIn('scope="col"', js)
        # Passcard modal semantics
        self.assertIn('role="region"', js)
        self.assertIn('aria-label=', js)
