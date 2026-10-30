# Viva guide

## 8-minute demo script
1. **Dynamic Personas & Fleet Overview** (45 s): Show switching "Acting as" between *Service* (Greaves Fleet), *Manufacturer* (Apex Gigafactory), *Recycler* (EcoRevive), and *Regulator* (National Compliance). Notice how the dashboard immediately adapts with custom hero cards, permitted operations, custom KPIs, and dedicated panels. Point out the real-world EV fleet (Tata Nexon EV Max, Ather 450X, Mahindra XUV400, Peenya Solar BESS), current locations (Indiranagar, Bandra-Kurla), and battery health meters (SoH %).
2. **DBMS lab → Syllabus Map**: Show the 6-module comprehensive syllabus mapping. Every concept (BCNF, Correlated Subqueries, ACID, 2PL, 11 Triggers, B-Tree Indexes) is explained in plain language with exact code lines.
3. **DBMS lab → Schema**: Walk the ERD. Point out Asset as the hub; AssetRelationship references Asset twice; HierarchyRule makes the graph acyclic; TestResult stores repeated diagnostic time series.
4. **Recall**: Batch `NC-2024-W03`, direction *up*: 5 assets down to `VEH-2048`. Switch to *as-of* a past date. Show the warnings box (honest about gaps).
5. **Data quality → DQ-002**: Show the rule's SQL, then "Close a link…" to repair the double parent. Re-open the page: finding gone. (Reset DB before the real viva.)
6. **Break a rule on purpose**: Acting as *service*, try REPAIRED on an ACTIVE pack (option is disabled and the server also refuses); switch to *auditor* (read-only); recycle a pack as *recycler* (irreversible confirmation).
7. **DBMS lab → SQL lab**: Run the recursive CTE, then the two EXPLAIN examples (SEARCH vs SCAN). Try `DELETE FROM Asset`; it is refused by the 5-layer SQL guard.
8. **Ledger → Verify**: Cryptographic SHA-256 chain is valid across all events. (Optional live tamper: see below.)

## Live tamper demo (optional)
Stop the server. In `sqlite3 batterytrace.db`: `DROP TRIGGER trg_event_no_update; UPDATE LifecycleEvent SET notes='x' WHERE event_id=4;` Restart; Verify says broken at event #4. Reset the DB afterwards.

## Questions to expect
- **Why SQLite?** Zero-install, ACID, supports recursive CTEs, triggers, views, partial indexes. Trade-off: one writer at a time, no roles/GRANT. Production would use PostgreSQL.
- **Why a relational DB for a graph-shaped problem?** Hierarchy depth is small and fixed (≤4); recursive CTE handles it; plus ACID and constraints. A graph DB might win on deep, wide traversals: *not measured here*.
- **Is it normalized?** BCNF/3NF per table (Normalization tab). One deliberate denormalization: `Asset.status`, kept consistent by one transaction per event.
- **How do you stop a module having two parents?** Trigger on overlapping intervals; app transfer closes the old link in the same transaction. Legacy bad data is found by DQ-002/006.
- **Why did you install triggers after seeding?** To keep known defects for the checker; triggers guard new writes. (Also: the update-trigger only blocks *new* overlap so repairs are possible, a bug found by the recycle test.)
- **What if two users click at once?** `BEGIN IMMEDIATE` serializes; tests run 6 simultaneous repurposes (1 wins, 5 refused) and 10 identical retries (1 event).
- **Is the hash chain a blockchain?** No. It detects some edits; limits are tested and documented. Blockchain does not validate that input was true.
- **Is the recall list complete?** Only relative to recorded links; unknown links are surfaced as warnings.
- **Biggest honest weaknesses & architectural trade-offs?**
  1. *Authentication*: For localhost evaluation, we used an active role switcher with 4 strictly partitioned roles (`MANUFACTURER`, `SERVICE`, `RECYCLER`, `AUDITOR`) and database foreign-key constraints, avoiding external OAuth2/OIDC/DID infrastructure that would break offline portability.
  2. *Graph DBMS vs Relational*: Benchmark compares relational graph strategies inside SQLite only (no Neo4j/Postgres deployed). We found unpruned recursive CTE was slower on whole-batch recalls due to path re-walking of shared ancestors; we solved this by implementing `frontier_cte` (`trace_frontier` using `UNION` deduplication), achieving an ~11.6× speedup in pure SQL.
  3. *Crash Recovery*: Durability and rollback integrity are now formally verified via automated `CrashRecoveryTests` (simulated power failures and aborted transactions leave zero orphan records and keep the SHA-256 chain intact).
  4. *Screen-Reader Accessibility*: Verified via automated `ScreenReaderAccessibilityTests` with ARIA 1.2 semantics (`role="tree"`, `role="treeitem"`, `aria-expanded`, `scope="col"`).
  5. *Benchmark Variance*: Wall-clock numbers vary up to 50% across runs due to CPU thermal throttling and OS thread scheduling; always quote speedup ratios, not raw milliseconds.

