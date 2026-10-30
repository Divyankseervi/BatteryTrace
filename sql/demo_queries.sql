-- BatteryTrace teaching queries (SQLite)

-- 1. Battery packs with their current active passport, if one exists.
SELECT a.asset_code, a.status AS asset_status,
       p.passport_id, p.status AS passport_status
FROM Asset AS a
LEFT JOIN Passport AS p
  ON p.asset_id = a.asset_id AND p.status = 'ACTIVE'
WHERE a.asset_type = 'BATTERY_PACK'
ORDER BY a.asset_code;

-- 2. Integrity warning: a recycled asset still has an active passport.
SELECT a.asset_code, p.passport_id
FROM Asset AS a
JOIN Passport AS p ON p.asset_id = a.asset_id
WHERE a.status = 'RECYCLED' AND p.status = 'ACTIVE';

-- 3. Integrity warning: child component has multiple open parent links.
SELECT child.asset_code AS child_asset,
       COUNT(*) AS open_parent_count
FROM AssetRelationship AS r
JOIN Asset AS child ON child.asset_id = r.child_asset_id
WHERE r.valid_to IS NULL
GROUP BY r.child_asset_id
HAVING COUNT(*) > 1;

-- 4. Event history for a particular asset code.
SELECT a.asset_code, e.event_type, e.event_at,
       e.organization, e.location, e.notes
FROM LifecycleEvent AS e
JOIN Asset AS a ON a.asset_id = e.asset_id
WHERE a.asset_code = 'PACK-1001'
ORDER BY e.event_at, e.event_id;

-- 5. Indexes declared in the project support common filters and joins.
-- Use EXPLAIN QUERY PLAN before making performance claims.
EXPLAIN QUERY PLAN
SELECT event_type, event_at
FROM LifecycleEvent
WHERE asset_id = 'A001'
ORDER BY event_at DESC;
