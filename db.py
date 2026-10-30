"""Database access: connection, schema loading, explicit transactions, synthetic seed data."""
from __future__ import annotations
import sqlite3, contextlib, os
from pathlib import Path
import domain, audit

ROOT = Path(__file__).resolve().parent
SQL_DIR = ROOT / 'sql'
DB_PATH = Path(os.environ.get('BATTERYTRACE_DB', ROOT / 'batterytrace.db'))


def connect(path=None) -> sqlite3.Connection:
    """Autocommit connection; transactions are explicit via tx(). Foreign keys always ON."""
    con = sqlite3.connect(str(path or DB_PATH), timeout=10, isolation_level=None)
    con.row_factory = sqlite3.Row
    con.execute('PRAGMA foreign_keys = ON')
    return con


@contextlib.contextmanager
def tx(con):
    """BEGIN IMMEDIATE takes the write lock up front, so read-check-write is serialized
    (no lost update / race between two clients). Any exception rolls EVERYTHING back."""
    con.execute('BEGIN IMMEDIATE')
    try:
        yield con
    except BaseException:
        con.execute('ROLLBACK')
        raise
    else:
        con.execute('COMMIT')


def read_sql(name: str) -> str:
    return (SQL_DIR / name).read_text(encoding='utf-8')


def create_schema(con):
    con.executescript(read_sql('schema.sql'))
    con.executemany('INSERT OR IGNORE INTO HierarchyRule VALUES (?,?,?)', domain.HIERARCHY)


def install_triggers(con):
    con.executescript(read_sql('triggers.sql'))


USERS = [
    ('U-MFR', 'Demo Manufacturer Operator (synthetic)', 'Aster Mobility', 'MANUFACTURER'),
    ('U-SVC', 'Demo Service Technician (synthetic)', 'Aster Service Centre', 'SERVICE'),
    ('U-REC', 'Demo Recycler Operator (synthetic)', 'CycleLoop Recycling', 'RECYCLER'),
    ('U-AUD', 'Demo Auditor (synthetic, read-only)', 'Independent Audit Desk', 'AUDITOR'),
]

ASSETS = [  # id, code, type, manufacturer, chemistry, kWh, batch, status, created
    ('A001', 'PACK-1001', 'BATTERY_PACK', 'Aster Mobility', 'NMC', 72.0, 'AM-PACK-2024-02', 'ACTIVE', '2024-02-10'),
    ('A002', 'MOD-1001-A', 'MODULE', 'Aster Mobility', 'NMC', 9.0, 'AM-MOD-2024-02', 'ACTIVE', '2024-02-10'),
    ('A003', 'MOD-1001-B', 'MODULE', 'Aster Mobility', 'NMC', 9.0, 'AM-MOD-2024-02', 'ACTIVE', '2024-02-10'),
    ('A004', 'CELL-1001-A1', 'CELL', 'NorthCell Works', 'NMC', 0.75, 'NC-2024-W03', 'ACTIVE', '2024-01-22'),
    ('A005', 'CELL-1001-A2', 'CELL', 'NorthCell Works', 'NMC', 0.75, 'NC-2024-W03', 'ACTIVE', '2024-01-22'),
    ('A006', 'VEH-2048', 'VEHICLE', 'Aster Mobility', '', None, None, 'ACTIVE', '2024-02-15'),
    ('A007', 'PACK-2001', 'BATTERY_PACK', 'Aster Mobility', 'LFP', 48.0, 'AM-PACK-2021-05', 'SECOND_LIFE', '2021-05-17'),
    ('A008', 'STORE-2001', 'STORAGE_SYSTEM', 'GridNest Energy', 'LFP', 48.0, None, 'ACTIVE', '2025-03-01'),
    ('A009', 'PACK-3001', 'BATTERY_PACK', 'Aster Mobility', 'NMC', 64.0, 'AM-PACK-2019-08', 'RECYCLED', '2019-08-14'),
    ('A010', 'MOD-3001-A', 'MODULE', 'Aster Mobility', 'NMC', 8.0, 'AM-MOD-2019-08', 'RECYCLED', '2019-08-14'),
    ('A011', 'PACK-4001', 'BATTERY_PACK', 'VoltPath Motors', 'LFP', 60.0, 'VP-PACK-2023-06', 'IN_REPAIR', '2023-06-05'),
    ('A012', 'MOD-4001-A', 'MODULE', 'VoltPath Motors', 'LFP', 10.0, 'VP-MOD-2023-06', 'ACTIVE', '2023-06-05'),
    ('A013', 'CELL-4001-A1', 'CELL', 'CellForge', 'LFP', 0.8, 'CF-2023-W20', 'ACTIVE', '2023-05-20'),
    ('A014', 'PACK-5001', 'BATTERY_PACK', 'VoltPath Motors', 'NMC', 55.0, 'VP-PACK-2024-11', 'ACTIVE', '2024-11-20'),
    ('A015', 'VEH-NEXON-EV', 'VEHICLE', 'Tata Motors / Aster Fleet', '', None, None, 'ACTIVE', '2024-03-01'),
    ('A016', 'PACK-NEXON-02', 'BATTERY_PACK', 'Aster Mobility', 'LFP', 40.5, 'AM-NEXON-2024-W12', 'ACTIVE', '2024-03-01'),
    ('A017', 'VEH-ATHER-450X', 'VEHICLE', 'Ather Energy', '', None, None, 'ACTIVE', '2024-02-20'),
    ('A018', 'PACK-ATHER-01', 'BATTERY_PACK', 'Aster Mobility', 'NMC', 3.7, 'AE-PACK-2024-W08', 'ACTIVE', '2024-02-20'),
    ('A019', 'VEH-XUV400', 'VEHICLE', 'Mahindra Electric', '', None, None, 'ACTIVE', '2023-10-15'),
    ('A020', 'PACK-XUV-01', 'BATTERY_PACK', 'VoltPath Motors', 'NMC', 39.4, 'VP-PACK-2023-W40', 'ACTIVE', '2023-10-15'),
    ('A021', 'STORE-SOLAR-02', 'STORAGE_SYSTEM', 'GridNest Energy', 'LFP', 50.0, None, 'ACTIVE', '2025-01-10'),
    ('A022', 'PACK-SOLAR-02', 'BATTERY_PACK', 'Aster Mobility', 'LFP', 50.0, 'AM-PACK-2020-W30', 'SECOND_LIFE', '2020-07-20'),
]
PASSPORTS = [
    ('P-1001', 'A001', 1, 'ACTIVE', '2024-02-10', None),
    ('P-2001-V1', 'A007', 1, 'CLOSED', '2021-05-17', None),
    ('P-2001-V2', 'A007', 2, 'ACTIVE', '2025-03-01', 'P-2001-V1'),
    ('P-3001', 'A009', 1, 'ACTIVE', '2019-08-14', None),   # DELIBERATE seeded defect #1
    ('P-4001', 'A011', 1, 'ACTIVE', '2023-06-05', None),
    ('P-5001', 'A014', 1, 'ACTIVE', '2024-11-20', None),
    ('P-NEXON-02', 'A016', 1, 'ACTIVE', '2024-03-01', None),
    ('P-ATHER-01', 'A018', 1, 'ACTIVE', '2024-02-20', None),
    ('P-XUV-01', 'A020', 1, 'ACTIVE', '2023-10-15', None),
    ('P-SOLAR-02', 'A022', 1, 'ACTIVE', '2020-07-20', None),
]
RELS = [
    ('A006', 'A001', 'INSTALLED_IN', '2024-02-15', None),
    ('A001', 'A002', 'CONTAINS', '2024-02-10', None),
    ('A001', 'A003', 'CONTAINS', '2024-02-10', None),
    ('A002', 'A004', 'CONTAINS', '2024-02-10', None),
    ('A002', 'A005', 'CONTAINS', '2024-02-10', None),
    ('A008', 'A007', 'USES', '2025-03-01', None),
    ('A009', 'A010', 'CONTAINS', '2019-08-14', '2025-07-01'),
    ('A011', 'A012', 'CONTAINS', '2023-06-05', None),
    ('A012', 'A013', 'CONTAINS', '2023-06-05', None),
    ('A014', 'A012', 'CONTAINS', '2024-11-20', None),      # DELIBERATE seeded defect #2 (second open parent)
    ('A015', 'A016', 'INSTALLED_IN', '2024-03-05', None),
    ('A017', 'A018', 'INSTALLED_IN', '2024-02-25', None),
    ('A019', 'A020', 'INSTALLED_IN', '2023-10-20', None),
    ('A021', 'A022', 'USES', '2025-01-10', None),
]
EVENTS = [  # asset, type, date, location, org, notes, actor
    ('A001', 'MANUFACTURED', '2024-02-10', 'Chennai, India', 'Aster Mobility', 'Pack assembled and quality checked.', 'U-MFR'),
    ('A001', 'INSTALLED', '2024-02-15', 'Chennai, India', 'Aster Mobility', 'Installed in vehicle VEH-2048.', 'U-MFR'),
    ('A001', 'TESTED', '2025-06-12', 'Bengaluru, India', 'Aster Service Centre', 'Routine capacity and safety inspection.', 'U-SVC'),
    ('A002', 'ASSEMBLED', '2024-02-10', 'Chennai, India', 'Aster Mobility', 'Module assembled into pack PACK-1001.', 'U-MFR'),
    ('A007', 'MANUFACTURED', '2021-05-17', 'Pune, India', 'Aster Mobility', 'Original battery pack created.', 'U-MFR'),
    ('A007', 'REPURPOSED', '2025-03-01', 'Pune, India', 'GridNest Energy', 'Moved to a stationary storage use case.', 'U-SVC'),
    ('A009', 'MANUFACTURED', '2019-08-14', 'Nashik, India', 'Aster Mobility', 'Original pack manufactured.', 'U-MFR'),
    ('A009', 'RECYCLED', '2025-07-01', 'Nashik, India', 'CycleLoop Recycling', 'Recycling event recorded; passport should be closed.', 'U-REC'),
    ('A011', 'MANUFACTURED', '2023-06-05', 'Hyderabad, India', 'VoltPath Motors', 'Pack manufactured.', 'U-MFR'),
    ('A011', 'INSPECTED', '2026-01-18', 'Hyderabad, India', 'VoltPath Service', 'Pack moved to repair after inspection.', 'U-SVC'),
    ('A014', 'MANUFACTURED', '2024-11-20', 'Coimbatore, India', 'VoltPath Motors', 'Pack manufactured; seeded relationship warning for classroom testing.', 'U-MFR'),
    ('A016', 'MANUFACTURED', '2024-03-01', 'Indiranagar Depot, Bengaluru', 'Aster Mobility', 'Installed in Tata Nexon EV (KA-01-EQ-5521).', 'U-MFR'),
    ('A018', 'MANUFACTURED', '2024-02-20', 'Koramangala Hub, Bengaluru', 'Ather Energy', 'Installed in Ather 450X Smart Electric Scooter.', 'U-MFR'),
    ('A020', 'MANUFACTURED', '2023-10-15', 'Bandra-Kurla Depot, Mumbai', 'VoltPath Motors', 'Installed in Mahindra XUV400 Electric SUV.', 'U-MFR'),
    ('A022', 'MANUFACTURED', '2020-07-20', 'Peenya Industrial Microgrid, Bengaluru', 'Aster Mobility', 'Repurposed into Peenya Solar Energy Storage Unit.', 'U-MFR'),
]


TESTS = [  # test_result_id, asset_id, test_time, state_of_health_pct, cycle_count, recorded_by
    ('TR-1001-1', 'A001', '2024-02-10 09:30', 100.0, 0, 'U-MFR'),
    ('TR-1001-2', 'A001', '2025-06-12 14:15', 96.5, 142, 'U-SVC'),
    ('TR-2001-1', 'A007', '2021-05-17 11:00', 100.0, 0, 'U-MFR'),
    ('TR-2001-2', 'A007', '2024-11-10 10:30', 81.5, 840, 'U-SVC'),
    ('TR-2001-3', 'A007', '2025-03-01 15:45', 80.8, 860, 'U-SVC'),
    ('TR-4001-1', 'A011', '2023-06-05 10:00', 100.0, 0, 'U-MFR'),
    ('TR-4001-2', 'A011', '2026-01-18 16:20', 74.2, 1120, 'U-SVC'),
    ('TR-NEXON-1', 'A016', '2024-03-01 10:00', 98.5, 25, 'U-MFR'),
    ('TR-NEXON-2', 'A016', '2025-08-14 11:30', 94.2, 220, 'U-SVC'),
    ('TR-ATHER-1', 'A018', '2024-02-20 09:15', 99.2, 12, 'U-MFR'),
    ('TR-ATHER-2', 'A018', '2025-09-02 14:00', 96.8, 95, 'U-SVC'),
    ('TR-XUV-1', 'A020', '2023-10-15 11:45', 100.0, 0, 'U-MFR'),
    ('TR-XUV-2', 'A020', '2025-05-18 16:30', 91.0, 380, 'U-SVC'),
    ('TR-SOLAR-1', 'A022', '2020-07-20 09:00', 100.0, 0, 'U-MFR'),
    ('TR-SOLAR-2', 'A022', '2025-01-10 14:15', 81.2, 910, 'U-SVC'),
]

CARBON_FOOTPRINTS = [
    # carbon_id, passport_id, raw_material_kg_co2e, manufacturing_kg_co2e, transport_kg_co2e, recycling_offset_kg_co2e, total_kg_co2e_per_kwh, carbon_class, certified_by, declared_at
    ('CF-1001', 'P-1001', 42.5, 28.0, 4.5, -12.0, 63.0, 'B', 'TUV Rheinland / Bureau Veritas', '2024-02-10'),
    ('CF-NEXON-02', 'P-NEXON-02', 32.0, 22.5, 3.0, -9.0, 48.5, 'A', 'ARAI / TUV SUD India', '2024-03-01'),
    ('CF-ATHER-01', 'P-ATHER-01', 36.0, 24.0, 2.5, -10.5, 52.0, 'A', 'ARAI / DNV Sustainability', '2024-02-20'),
    ('CF-XUV-01', 'P-XUV-01', 40.0, 26.0, 3.5, -11.0, 58.5, 'B', 'ARAI / SGS India', '2023-10-15'),
    ('CF-SOLAR-02', 'P-SOLAR-02', 28.0, 12.0, 2.0, -15.0, 27.0, 'A', 'Bureau of Energy Efficiency (BEE)', '2025-01-10'),
]

CRITICAL_MINERALS = [
    # mineral_id, asset_id, lithium_kg, cobalt_kg, nickel_kg, manganese_kg, recycled_cobalt_pct, recycled_lithium_pct, recycled_nickel_pct, epr_certificate_id
    ('MIN-A001', 'A001', 6.5, 8.2, 28.4, 7.1, 16.5, 6.5, 6.0, 'EPR-IN-2024-00142'),
    ('MIN-A016', 'A016', 4.2, 0.0, 0.0, 0.0, 0.0, 8.0, 0.0, 'EPR-IN-2024-00891'),
    ('MIN-A018', 'A018', 0.45, 0.52, 1.85, 0.48, 18.0, 7.5, 6.5, 'EPR-IN-2024-00912'),
    ('MIN-A020', 'A020', 3.8, 4.5, 16.2, 4.1, 16.0, 6.2, 6.0, 'EPR-IN-2023-00560'),
    ('MIN-A009', 'A009', 5.8, 7.4, 25.1, 6.4, 92.5, 88.0, 91.0, 'EPR-CLOSED-2025-00031'),
]


def seed_demo(con):
    """Insert the synthetic demo dataset (only into an empty database)."""
    con.executemany('INSERT INTO AppUser VALUES (?,?,?,?)', USERS)
    con.executemany('INSERT INTO Asset VALUES (?,?,?,?,?,?,?,?,?)', ASSETS)
    con.executemany('INSERT INTO Passport VALUES (?,?,?,?,?,?)', PASSPORTS)
    con.executemany('INSERT INTO AssetRelationship(parent_asset_id,child_asset_id,relationship_type,valid_from,valid_to) VALUES (?,?,?,?,?)', RELS)
    con.executemany('INSERT INTO TestResult(test_result_id,asset_id,test_time,state_of_health_pct,cycle_count,recorded_by) VALUES (?,?,?,?,?,?)', TESTS)
    con.executemany('INSERT INTO CarbonFootprint VALUES (?,?,?,?,?,?,?,?,?,?)', CARBON_FOOTPRINTS)
    con.executemany('INSERT INTO CriticalMinerals VALUES (?,?,?,?,?,?,?,?,?,?)', CRITICAL_MINERALS)
    for asset_id, etype, at, loc, org, notes, actor in EVENTS:
        audit.append_event(con, asset_id=asset_id, event_type=etype, event_at=at, location=loc,
                           organization=org, notes=notes, actor_id=actor,
                           evidence_status='SELF_REPORTED', evidence_ref=None, idempotency_key=None)


def _is_v1_database(path) -> bool:
    """A v1 database has an Asset table without batch_code (and no hash-chain columns)."""
    p = Path(path)
    if not p.exists() or p.stat().st_size == 0:
        return False
    con = sqlite3.connect(str(p))
    try:
        cols = [r[1] for r in con.execute('PRAGMA table_info(Asset)')]
        return bool(cols) and 'batch_code' not in cols
    finally:
        con.close()


def init_db(path=None, seed=True):
    """Create schema, seed (if empty), then install triggers. Safe to call repeatedly.
    An old v1 file is moved aside (data was synthetic) instead of crashing on a missing column."""
    target = Path(path or DB_PATH)
    if _is_v1_database(target):
        backup = target.with_name(target.stem + '.v1-backup' + target.suffix)
        n = 1
        while backup.exists():
            backup = target.with_name(f'{target.stem}.v1-backup{n}{target.suffix}'); n += 1
        target.replace(backup)
        print(f'NOTE: {target.name} used the old v1 schema. Moved to {backup.name}; creating a fresh v2 database.')
    con = connect(path)
    try:
        create_schema(con)
        empty = con.execute('SELECT COUNT(*) FROM Asset').fetchone()[0] == 0
        if empty and seed:
            with tx(con):
                seed_demo(con)
        install_triggers(con)
    finally:
        con.close()
