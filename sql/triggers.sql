-- Integrity rules enforced INSIDE the database (cannot be bypassed by a buggy client).
-- Installed AFTER the demo seed so that the two deliberately seeded legacy defects exist
-- for the integrity checker to find; the triggers stop NEW violations.

-- 1. Append-only ledger: events cannot be edited or deleted.
CREATE TRIGGER IF NOT EXISTS trg_event_no_update BEFORE UPDATE ON LifecycleEvent
BEGIN SELECT RAISE(ABORT, 'LifecycleEvent is append-only: record a corrective event instead'); END;

CREATE TRIGGER IF NOT EXISTS trg_event_no_delete BEFORE DELETE ON LifecycleEvent
BEGIN SELECT RAISE(ABORT, 'LifecycleEvent is append-only: rows cannot be deleted'); END;

-- 2. No new events against a terminal asset.
CREATE TRIGGER IF NOT EXISTS trg_event_terminal BEFORE INSERT ON LifecycleEvent
WHEN (SELECT status FROM Asset WHERE asset_id = NEW.asset_id) IN ('RECYCLED','RETIRED')
BEGIN SELECT RAISE(ABORT, 'Asset is in a terminal state (RECYCLED/RETIRED): no further events allowed'); END;

-- 3. Terminal status is irreversible.
CREATE TRIGGER IF NOT EXISTS trg_asset_terminal BEFORE UPDATE OF status ON Asset
WHEN OLD.status IN ('RECYCLED','RETIRED') AND NEW.status <> OLD.status
BEGIN SELECT RAISE(ABORT, 'A terminal asset (RECYCLED/RETIRED) cannot change status'); END;

-- 4. Passport chain: previous passport must be the same asset and an earlier version.
--    Strictly increasing versions on the same asset make a cycle impossible.
CREATE TRIGGER IF NOT EXISTS trg_passport_chain BEFORE INSERT ON Passport
WHEN NEW.previous_passport_id IS NOT NULL AND NOT EXISTS (
  SELECT 1 FROM Passport p WHERE p.passport_id = NEW.previous_passport_id
    AND p.asset_id = NEW.asset_id AND p.passport_version < NEW.passport_version)
BEGIN SELECT RAISE(ABORT, 'previous_passport_id must reference an earlier version of the SAME asset'); END;

CREATE TRIGGER IF NOT EXISTS trg_passport_immutable BEFORE UPDATE OF asset_id, passport_version, previous_passport_id, issued_at ON Passport
BEGIN SELECT RAISE(ABORT, 'Passport identity and chain fields are immutable; only status may change'); END;

CREATE TRIGGER IF NOT EXISTS trg_passport_terminal BEFORE INSERT ON Passport
WHEN (SELECT status FROM Asset WHERE asset_id = NEW.asset_id) IN ('RECYCLED','RETIRED')
BEGIN SELECT RAISE(ABORT, 'Cannot issue a passport for a terminal asset'); END;

-- 5. Relationship must follow the HierarchyRule table (e.g. MODULE contains CELL).
CREATE TRIGGER IF NOT EXISTS trg_rel_hierarchy BEFORE INSERT ON AssetRelationship
WHEN NOT EXISTS (
  SELECT 1 FROM Asset p, Asset c, HierarchyRule h
  WHERE p.asset_id = NEW.parent_asset_id AND c.asset_id = NEW.child_asset_id
    AND h.parent_type = p.asset_type AND h.child_type = c.asset_type
    AND h.relationship_type = NEW.relationship_type)
BEGIN SELECT RAISE(ABORT, 'Relationship violates HierarchyRule (parent/child type or label not allowed)'); END;

-- 6. Temporal exclusion: a child may not have two overlapping parent intervals.
--    Half-open intervals [valid_from, valid_to): touching at one date is allowed (a hand-over).
CREATE TRIGGER IF NOT EXISTS trg_rel_overlap_ins BEFORE INSERT ON AssetRelationship
WHEN EXISTS (
  SELECT 1 FROM AssetRelationship r
  WHERE r.child_asset_id = NEW.child_asset_id
    AND r.valid_from < COALESCE(NEW.valid_to, '9999-12-31')
    AND NEW.valid_from < COALESCE(r.valid_to, '9999-12-31'))
BEGIN SELECT RAISE(ABORT, 'Overlapping parent assignment: the child already has a parent during this interval'); END;

-- An UPDATE is blocked only if it INTRODUCES an overlap that the old row did not already have.
-- This lets operators repair legacy double-parent data (closing a link shrinks the interval and can
-- never create a new overlap) while still blocking any change that makes things worse.
CREATE TRIGGER IF NOT EXISTS trg_rel_overlap_upd BEFORE UPDATE OF valid_from, valid_to, child_asset_id ON AssetRelationship
WHEN EXISTS (
  SELECT 1 FROM AssetRelationship r
  WHERE r.child_asset_id = NEW.child_asset_id AND r.relationship_id <> NEW.relationship_id
    AND r.valid_from < COALESCE(NEW.valid_to, '9999-12-31')
    AND NEW.valid_from < COALESCE(r.valid_to, '9999-12-31')
    AND NOT (r.valid_from < COALESCE(OLD.valid_to, '9999-12-31')
             AND OLD.valid_from < COALESCE(r.valid_to, '9999-12-31')))
BEGIN SELECT RAISE(ABORT, 'Overlapping parent assignment: update would create a NEW double-parent interval'); END;

-- 7. Relationship history is not rewritten: only valid_to may be set (closing a link).
CREATE TRIGGER IF NOT EXISTS trg_rel_identity BEFORE UPDATE OF parent_asset_id, child_asset_id, relationship_type, valid_from ON AssetRelationship
BEGIN SELECT RAISE(ABORT, 'Relationship identity and start date are immutable; close it with valid_to instead'); END;
