-- BatteryTrace schema (SQLite). CANONICAL: db.py loads this file; there is no copy in Python.
-- Tables and indexes only. Business rules enforced inside the database live in triggers.sql.
-- All data is synthetic.

CREATE TABLE IF NOT EXISTS Asset (
  asset_id     TEXT PRIMARY KEY,
  asset_code   TEXT NOT NULL UNIQUE,
  asset_type   TEXT NOT NULL CHECK (asset_type IN ('CELL','MODULE','BATTERY_PACK','VEHICLE','STORAGE_SYSTEM')),
  manufacturer TEXT NOT NULL,
  chemistry    TEXT,
  capacity_kwh REAL CHECK (capacity_kwh IS NULL OR capacity_kwh >= 0),
  batch_code   TEXT,                       -- production batch, used for recall scoping
  status       TEXT NOT NULL CHECK (status IN ('ACTIVE','IN_REPAIR','SECOND_LIFE','RECYCLED','RETIRED')),
  created_at   TEXT NOT NULL CHECK (created_at GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]')
);

CREATE TABLE IF NOT EXISTS Passport (
  passport_id          TEXT PRIMARY KEY,
  asset_id             TEXT NOT NULL REFERENCES Asset(asset_id),
  passport_version     INTEGER NOT NULL DEFAULT 1 CHECK (passport_version > 0),
  status               TEXT NOT NULL CHECK (status IN ('ACTIVE','SUPERSEDED','CLOSED')),
  issued_at            TEXT NOT NULL,
  previous_passport_id TEXT REFERENCES Passport(passport_id),
  UNIQUE (asset_id, passport_version)
);

-- Lookup table: which parent type may hold which child type, with which relationship label.
-- Data-driven rule used by a trigger. Because every rule goes one level DOWN, the
-- relationship graph is a DAG by construction (no cycles are possible).
CREATE TABLE IF NOT EXISTS HierarchyRule (
  parent_type       TEXT NOT NULL,
  child_type        TEXT NOT NULL,
  relationship_type TEXT NOT NULL,
  PRIMARY KEY (parent_type, child_type)
);

CREATE TABLE IF NOT EXISTS AssetRelationship (
  relationship_id   INTEGER PRIMARY KEY AUTOINCREMENT,
  parent_asset_id   TEXT NOT NULL REFERENCES Asset(asset_id),
  child_asset_id    TEXT NOT NULL REFERENCES Asset(asset_id),
  relationship_type TEXT NOT NULL,
  valid_from        TEXT NOT NULL,
  valid_to          TEXT,                  -- NULL = still open. Interval is [valid_from, valid_to)
  CHECK (parent_asset_id <> child_asset_id),
  CHECK (valid_to IS NULL OR valid_to > valid_from)
);

CREATE TABLE IF NOT EXISTS AppUser (
  user_id      TEXT PRIMARY KEY,
  display_name TEXT NOT NULL,
  organization TEXT NOT NULL,
  role         TEXT NOT NULL CHECK (role IN ('MANUFACTURER','SERVICE','RECYCLER','AUDITOR'))
);

CREATE TABLE IF NOT EXISTS LifecycleEvent (
  event_id        INTEGER PRIMARY KEY AUTOINCREMENT,
  asset_id        TEXT NOT NULL REFERENCES Asset(asset_id),
  event_type      TEXT NOT NULL CHECK (event_type IN ('MANUFACTURED','ASSEMBLED','INSTALLED','TESTED','REPAIR_STARTED','REPAIRED','REPURPOSED','TRANSFERRED','RECYCLED','INSPECTED')),
  event_at        TEXT NOT NULL CHECK (event_at GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'),
  location        TEXT NOT NULL,
  organization    TEXT NOT NULL,
  notes           TEXT NOT NULL DEFAULT '',
  actor_id        TEXT REFERENCES AppUser(user_id),
  evidence_status TEXT NOT NULL DEFAULT 'SELF_REPORTED' CHECK (evidence_status IN ('UNKNOWN','SELF_REPORTED','VERIFIED')),
  evidence_ref    TEXT,
  idempotency_key TEXT UNIQUE,             -- retry safety; NULLs do not collide
  prev_hash       TEXT NOT NULL,           -- tamper-evident chain (see services.py)
  event_hash      TEXT NOT NULL
);

-- Diagnostic measurements (Case Study FR-5, Code 1B): SoH %, cycles, and electrochemical telemetry
CREATE TABLE IF NOT EXISTS TestResult (
  test_result_id           TEXT PRIMARY KEY,
  asset_id                 TEXT NOT NULL REFERENCES Asset(asset_id),
  test_time                TEXT NOT NULL CHECK (test_time GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]*'),
  state_of_health_pct      REAL CHECK (state_of_health_pct IS NULL OR (state_of_health_pct >= 0 AND state_of_health_pct <= 100)),
  cycle_count              INTEGER CHECK (cycle_count IS NULL OR cycle_count >= 0),
  internal_resistance_mohm REAL CHECK (internal_resistance_mohm IS NULL OR internal_resistance_mohm >= 0),
  cell_temp_celsius        REAL CHECK (cell_temp_celsius IS NULL OR (cell_temp_celsius >= -40 AND cell_temp_celsius <= 120)),
  voltage_delta_mv         REAL CHECK (voltage_delta_mv IS NULL OR voltage_delta_mv >= 0),
  remaining_useful_life_cycles INTEGER CHECK (remaining_useful_life_cycles IS NULL OR remaining_useful_life_cycles >= 0),
  recorded_by              TEXT REFERENCES AppUser(user_id)
);

-- Statutory Carbon Footprint Declaration (EU Regulation 2023/1542 Article 7)
CREATE TABLE IF NOT EXISTS CarbonFootprint (
  carbon_id                TEXT PRIMARY KEY,
  passport_id              TEXT NOT NULL REFERENCES Passport(passport_id),
  raw_material_kg_co2e     REAL NOT NULL CHECK (raw_material_kg_co2e >= 0),
  manufacturing_kg_co2e    REAL NOT NULL CHECK (manufacturing_kg_co2e >= 0),
  transport_kg_co2e         REAL NOT NULL CHECK (transport_kg_co2e >= 0),
  recycling_offset_kg_co2e REAL NOT NULL CHECK (recycling_offset_kg_co2e <= 0),
  total_kg_co2e_per_kwh    REAL NOT NULL CHECK (total_kg_co2e_per_kwh >= 0),
  carbon_class             TEXT NOT NULL CHECK (carbon_class IN ('A','B','C','D','E')),
  certified_by             TEXT NOT NULL,
  declared_at              TEXT NOT NULL CHECK (declared_at GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]')
);

-- Critical Raw Materials & Recycled Content Declaration (EU Article 8 & India BWMR 2022)
CREATE TABLE IF NOT EXISTS CriticalMinerals (
  mineral_id           TEXT PRIMARY KEY,
  asset_id             TEXT NOT NULL REFERENCES Asset(asset_id),
  lithium_kg           REAL NOT NULL CHECK (lithium_kg >= 0),
  cobalt_kg            REAL NOT NULL CHECK (cobalt_kg >= 0),
  nickel_kg            REAL NOT NULL CHECK (nickel_kg >= 0),
  manganese_kg         REAL NOT NULL CHECK (manganese_kg >= 0),
  recycled_cobalt_pct  REAL NOT NULL CHECK (recycled_cobalt_pct >= 0 AND recycled_cobalt_pct <= 100),
  recycled_lithium_pct REAL NOT NULL CHECK (recycled_lithium_pct >= 0 AND recycled_lithium_pct <= 100),
  recycled_nickel_pct  REAL NOT NULL CHECK (recycled_nickel_pct >= 0 AND recycled_nickel_pct <= 100),
  epr_certificate_id   TEXT
);

CREATE INDEX IF NOT EXISTS idx_asset_status       ON Asset(status);
CREATE INDEX IF NOT EXISTS idx_asset_type         ON Asset(asset_type);
CREATE INDEX IF NOT EXISTS idx_asset_batch        ON Asset(batch_code);
CREATE INDEX IF NOT EXISTS idx_passport_status    ON Passport(status);
CREATE UNIQUE INDEX IF NOT EXISTS idx_passport_one_active_per_asset ON Passport(asset_id) WHERE status = 'ACTIVE';
CREATE INDEX IF NOT EXISTS idx_relationship_parent ON AssetRelationship(parent_asset_id);
CREATE INDEX IF NOT EXISTS idx_relationship_child  ON AssetRelationship(child_asset_id);
CREATE INDEX IF NOT EXISTS idx_event_asset_time    ON LifecycleEvent(asset_id, event_at DESC);
CREATE INDEX IF NOT EXISTS idx_event_type          ON LifecycleEvent(event_type);
CREATE INDEX IF NOT EXISTS idx_test_asset_time     ON TestResult(asset_id, test_time DESC);
CREATE INDEX IF NOT EXISTS idx_carbon_passport     ON CarbonFootprint(passport_id);
CREATE INDEX IF NOT EXISTS idx_mineral_asset       ON CriticalMinerals(asset_id);

-- Views (stored queries) used by the API and the SQL lab.
CREATE VIEW IF NOT EXISTS v_open_relationship AS
  SELECT * FROM AssetRelationship WHERE valid_to IS NULL;

CREATE VIEW IF NOT EXISTS v_active_passport AS
  SELECT * FROM Passport WHERE status = 'ACTIVE';

CREATE VIEW IF NOT EXISTS v_asset_overview AS
  SELECT a.asset_id, a.asset_code, a.asset_type, a.manufacturer, a.chemistry, a.capacity_kwh,
         a.batch_code, a.status, a.created_at,
         p.passport_id, p.passport_version, p.status AS passport_status,
         (SELECT MAX(e.event_at) FROM LifecycleEvent e WHERE e.asset_id = a.asset_id) AS last_event_at,
         (SELECT e.location FROM LifecycleEvent e WHERE e.asset_id = a.asset_id ORDER BY e.event_at DESC, e.event_id DESC LIMIT 1) AS current_location,
         (SELECT pr.asset_code FROM AssetRelationship r JOIN Asset pr ON pr.asset_id = r.parent_asset_id WHERE r.child_asset_id = a.asset_id AND r.valid_to IS NULL LIMIT 1) AS host_product,
         (SELECT t.state_of_health_pct FROM TestResult t WHERE t.asset_id = a.asset_id ORDER BY t.test_time DESC LIMIT 1) AS latest_soh,
         (SELECT t.cycle_count FROM TestResult t WHERE t.asset_id = a.asset_id ORDER BY t.test_time DESC LIMIT 1) AS latest_cycles,
         (SELECT COUNT(*) FROM v_open_relationship r WHERE r.child_asset_id = a.asset_id) AS open_parents
  FROM Asset a LEFT JOIN v_active_passport p ON p.asset_id = a.asset_id;
