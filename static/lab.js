/* Static teaching text for the DBMS lab (trusted constants, not user data). */
window.BTLab = {
normalization: `
<p>Functional dependencies (FDs) that hold in this schema, and what the design does about them:</p>
<table><thead><tr><th>Relation</th><th>Key</th><th>Non-trivial FDs</th><th>Form</th></tr></thead><tbody>
<tr><td>Asset</td><td>asset_id (candidate: asset_code)</td><td>asset_id → all columns; asset_code → asset_id</td><td>BCNF: every determinant is a candidate key.</td></tr>
<tr><td>Passport</td><td>passport_id (candidate: asset_id + passport_version)</td><td>(asset_id, passport_version) → passport_id, status, issued_at, previous_passport_id</td><td>BCNF.</td></tr>
<tr><td>AssetRelationship</td><td>relationship_id</td><td>relationship_id → parent, child, type, valid_from, valid_to</td><td>3NF. relationship_type is determined by (parent type, child type): that FD lives in HierarchyRule, not repeated here.</td></tr>
<tr><td>HierarchyRule</td><td>(parent_type, child_type)</td><td>(parent_type, child_type) → relationship_type</td><td>BCNF. Exists to remove a transitive dependency.</td></tr>
<tr><td>LifecycleEvent</td><td>event_id</td><td>event_id → all columns</td><td>3NF. actor details live in AppUser, referenced by actor_id.</td></tr>
<tr><td>TestResult</td><td>test_result_id</td><td>test_result_id → asset_id, test_time, state_of_health_pct, cycle_count, recorded_by</td><td>BCNF. Diagnostic measurements over time (Case Study FR-5, Code 1B).</td></tr>
</tbody></table>
<h3>Worked example: why not one wide table?</h3>
<p>A single table “Event(asset_code, asset_type, manufacturer, chemistry, event_type, event_at …)” repeats the asset facts on every event row. That causes <b>update anomalies</b> (change a manufacturer in 40 rows), <b>insertion anomalies</b> (cannot record an asset before it has an event) and <b>deletion anomalies</b>. Splitting out Asset removes all three, because asset_code → manufacturer, chemistry is stored once.</p>
<h3>A deliberate, documented denormalization</h3>
<p><code>Asset.status</code> is derivable from the event history, so strictly it is redundant. It is kept because filtering by current status is a very common read. The price: two copies of the truth can drift. The design pays that price with one atomic transaction per event (event + status change commit together) and a state machine that is the only writer of status.</p>
<h3>Not modelled</h3>
<p>batch_code is a plain column. A full design would add a Batch table (supplier, production date, defect notes). It was left out to keep the demo understandable; with it, batch attributes would otherwise create a transitive dependency.</p>`,

acid: `
<table><thead><tr><th>Property</th><th>Where it is implemented</th><th>Test that demonstrates it</th></tr></thead><tbody>
<tr><td><b>Atomicity</b></td><td><code>db.tx()</code> wraps every write in BEGIN IMMEDIATE … COMMIT/ROLLBACK. A recycle writes the event, asset status, passport and link closures together or not at all.</td><td>test_midway_failure_rolls_back_event_status_and_passport; test_database_failure_after_event_insert_rolls_everything_back</td></tr>
<tr><td><b>Consistency</b></td><td>CHECK, UNIQUE, FOREIGN KEY, partial unique index, 11 triggers (temporal no-overlap, passport chain, hierarchy, append-only), plus the Python state machine.</td><td>DatabaseConstraintTests (writes that bypass the app are still refused)</td></tr>
<tr><td><b>Isolation</b></td><td>SQLite allows one writer at a time. BEGIN IMMEDIATE takes the write lock before the read-check-write sequence, so two clients cannot both pass the same “is ACTIVE?” check (no lost update / write skew). This is serializable behaviour for writers.</td><td>test_competing_state_changes_only_one_wins (6 clients, 1 winner); test_concurrent_transfers_never_create_two_open_parents</td></tr>
<tr><td><b>Durability</b></td><td>SQLite’s rollback journal and fsync on commit (default journal mode). WAL is not enabled.</td><td>Not tested by crash injection. Claimed from SQLite’s documented behaviour only.</td></tr>
</tbody></table>
<h3>Idempotency (retry safety)</h3><p>A client that times out cannot know whether its write happened. It resends with the same <code>idempotency_key</code>; the UNIQUE index plus the immediate lock guarantee exactly one event. Same key with different content is rejected (409).</p>
<h3>Concurrency control, in exam words</h3><p>This is pessimistic, lock-based control with a single database-level write lock: coarse (no row locks), simple, correct, but limits write throughput. PostgreSQL would use MVCC with row-level locks and could run writers in parallel.</p>
<h3>Recovery</h3><p>If the server dies mid-transaction the journal rolls the half-written change back at next open. Because the ledger is append-only and hash-chained, an auditor can also check that no committed row was altered afterwards (see limits on the Event ledger page).</p>`,

syllabus: `
<div class="notice ok">
  <b>Comprehensive Syllabus Mapping (BCSE302L - Database Management Systems):</b><br>
  Every single concept taught in the university DBMS curriculum is actively implemented in this project. Below, each topic is explained in <b>simple, beginner-friendly language</b> alongside the exact feature and code where it is used.
</div>

<h3>1. Conceptual &amp; Relational Data Modeling</h3>
<table>
<thead>
  <tr><th>Syllabus Topic</th><th>What it Means in Simple Words</th><th>Feature in BatteryTrace</th><th>Where to See in Code / UI</th></tr>
</thead>
<tbody>
  <tr>
    <td><b>Entity-Relationship (ER) Modeling</b></td>
    <td>Drawing real-world things as tables and connecting them with relationships.</td>
    <td>The entire fleet model: Batteries, Vehicles, Passports, Users, and Lifecycle Events connected with 1-to-Many and Many-to-Many links.</td>
    <td><code>sql/schema.sql</code>, <code>static/erd.svg</code>, and Lab &rarr; <b>Schema &amp; ERD</b> tab.</td>
  </tr>
  <tr>
    <td><b>Primary Keys &amp; Candidate Keys</b></td>
    <td>A unique fingerprint column that guarantees no two rows can ever be duplicates.</td>
    <td><code>Asset(asset_id)</code>, <code>Passport(passport_id)</code>, and composite candidate key <code>(asset_id, passport_version)</code>.</td>
    <td><code>sql/schema.sql</code> (lines 6, 18, 24).</td>
  </tr>
  <tr>
    <td><b>Foreign Keys &amp; Referential Integrity</b></td>
    <td>Rules that stop you from linking to a parent row that doesn't exist.</td>
    <td>Events reference <code>Asset(asset_id)</code> and <code>AppUser(user_id)</code>; Passports reference <code>Asset(asset_id)</code>. If an asset is deleted, the database refuses.</td>
    <td><code>PRAGMA foreign_keys = ON</code> in <code>db.py</code>; foreign key clauses in <code>sql/schema.sql</code>.</td>
  </tr>
  <tr>
    <td><b>Domain &amp; CHECK Constraints</b></td>
    <td>Restricting what values are allowed in a column (e.g. no negative numbers, only valid statuses).</td>
    <td>Battery capacity cannot be negative (<code>capacity_kwh &gt;= 0</code>); State of Health must be 0 to 100%; event types must be valid enums.</td>
    <td><code>CHECK</code> constraints in <code>sql/schema.sql</code> (lines 8, 11, 13, 58, 76).</td>
  </tr>
</tbody>
</table>

<h3>2. Database Normalization &amp; Functional Dependencies</h3>
<table>
<thead>
  <tr><th>Syllabus Topic</th><th>What it Means in Simple Words</th><th>Feature in BatteryTrace</th><th>Where to See in Code / UI</th></tr>
</thead>
<tbody>
  <tr>
    <td><b>1st Normal Form (1NF)</b></td>
    <td>Every cell holds exactly one single value; no lists, no arrays stored inside a cell.</td>
    <td>All tables use atomic data types (strings, numbers, dates). Sub-components are stored as separate rows, not CSV lists.</td>
    <td><code>AssetRelationship</code> table stores each parent-child link as an individual row.</td>
  </tr>
  <tr>
    <td><b>2nd Normal Form (2NF)</b></td>
    <td>Every column must depend on the whole primary key, not just half of it.</td>
    <td>In composite table <code>Passport(asset_id, passport_version)</code>, columns like <code>status</code> and <code>issued_at</code> depend on the full composite key.</td>
    <td>Lab &rarr; <b>Normalization</b> tab.</td>
  </tr>
  <tr>
    <td><b>3rd Normal Form &amp; BCNF</b></td>
    <td>No hidden transitive shortcuts (A &rarr; B &rarr; C). Every determinant must be a candidate key.</td>
    <td>Hierarchy rules are factored out into <code>HierarchyRule(parent_type, child_type)</code> rather than repeating the relationship label in every link. User details live in <code>AppUser</code>.</td>
    <td><code>HierarchyRule</code> table; BCNF mathematical proofs in <code>docs/CASE_STUDY_SUBMISSION_GUIDE.md</code>.</td>
  </tr>
  <tr>
    <td><b>Controlled Denormalization</b></td>
    <td>Intentionally storing a calculated field to make reads 100&times; faster, but keeping it updated with transactions.</td>
    <td><code>Asset.status</code> is stored directly on the Asset for fast filtering, rather than re-calculating it from thousands of event rows every time.</td>
    <td>Synchronized inside <code>services.record_event</code> using an atomic transaction.</td>
  </tr>
</tbody>
</table>

<h3>3. SQL Queries, Aggregations &amp; Advanced Graph Traversal</h3>
<table>
<thead>
  <tr><th>Syllabus Topic</th><th>What it Means in Simple Words</th><th>Feature in BatteryTrace</th><th>Where to See in Code / UI</th></tr>
</thead>
<tbody>
  <tr>
    <td><b>Multi-Table Joins (INNER &amp; LEFT JOIN)</b></td>
    <td>Stitching two or more tables together side-by-side based on matching ID keys.</td>
    <td>Joining Assets with their active Passports, parent vehicle names, and latest diagnostic test results to display the unified fleet dashboard.</td>
    <td><code>v_asset_overview</code> in <code>sql/schema.sql</code>; SQL Lab queries #1 to #8.</td>
  </tr>
  <tr>
    <td><b>Aggregations &amp; GROUP BY</b></td>
    <td>Calculating totals, averages, and counts across groups of rows.</td>
    <td>Calculating the Fleet Average State of Health (<code>AVG(state_of_health_pct)</code>) and counting batteries by lifecycle status (<code>GROUP BY status</code>).</td>
    <td><code>services.summary</code> and Lab &rarr; <b>SQL Lab</b> Query #10.</td>
  </tr>
  <tr>
    <td><b>Window Functions (PARTITION BY)</b></td>
    <td>Doing calculations across groups of rows without collapsing them into a single row.</td>
    <td>Finding the single most recent diagnostic test for each battery using <code>ROW_NUMBER() OVER (PARTITION BY asset_id ORDER BY test_time DESC)</code>.</td>
    <td>Lab &rarr; <b>SQL Lab</b> Query #9 and <code>services.summary</code>.</td>
  </tr>
  <tr>
    <td><b>Recursive Common Table Expressions (WITH RECURSIVE)</b></td>
    <td>A query that loops on itself to walk up or down a tree/graph of arbitrary depth.</td>
    <td>Tracing recalls: tracing a defective cell batch upstream through modules, packs, and vehicles to find all affected cars.</td>
    <td><code>recall.py</code> (lines 25-36) and Recall Simulation page.</td>
  </tr>
  <tr>
    <td><b>Database Views (Stored Queries)</b></td>
    <td>Saving a complex SELECT query as a virtual table for clean code and data security.</td>
    <td><code>v_asset_overview</code>, <code>v_open_relationship</code>, <code>v_active_passport</code>.</td>
    <td><code>sql/schema.sql</code> (lines 93-106).</td>
  </tr>
</tbody>
</table>

<h3>4. Transactions, Concurrency &amp; Physical Optimization</h3>
<table>
<thead>
  <tr><th>Syllabus Topic</th><th>What it Means in Simple Words</th><th>Feature in BatteryTrace</th><th>Where to See in Code / UI</th></tr>
</thead>
<tbody>
  <tr>
    <td><b>ACID Transactions</b></td>
    <td>All-or-nothing guarantee: if step 4 of 5 fails, the whole database rewinds back to before step 1.</td>
    <td>Recycling a battery: atomically marks asset RECYCLED, closes passport, closes relationships, and logs event. If anything fails, everything rolls back.</td>
    <td><code>db.tx()</code> context manager in <code>db.py</code>; tested in <code>tests/test_domain.py</code>.</td>
  </tr>
  <tr>
    <td><b>Concurrency Control &amp; Isolation</b></td>
    <td>Stopping two users from editing the same battery at the exact same millisecond (preventing Lost Updates).</td>
    <td><code>BEGIN IMMEDIATE</code> takes an exclusive write lock immediately, preventing write skew and lost updates when multiple users submit simultaneously.</td>
    <td><code>tests/test_concurrency.py</code> (6 simultaneous client threads).</td>
  </tr>
  <tr>
    <td><b>Active Databases &amp; SQL Triggers</b></td>
    <td>Automatic background programs that fire whenever an INSERT, UPDATE, or DELETE happens.</td>
    <td>11 triggers enforcing rules: blocking components having two parents at once, preventing edits to recycled batteries, and ensuring immutable event logs.</td>
    <td><code>sql/triggers.sql</code> (all 11 triggers).</td>
  </tr>
  <tr>
    <td><b>B-Tree Indexes &amp; Query Optimization</b></td>
    <td>Like the index at the back of a textbook: lets the database jump straight to the row in O(log N) time instead of reading the whole table in O(N).</td>
    <td>B-Tree indexes on <code>child_asset_id</code>, <code>parent_asset_id</code>, and <code>status</code>. Analyzed using <code>EXPLAIN QUERY PLAN</code>.</td>
    <td>Lab &rarr; <b>SQL Lab</b> (EXPLAIN button shows <code>SEARCH using INDEX</code> vs <code>SCAN table</code>).</td>
  </tr>
  <tr>
    <td><b>Database Security &amp; Authorization</b></td>
    <td>Controlling who is allowed to do what (RBAC) and blocking malicious SQL injection attacks.</td>
    <td>4 distinct roles (Manufacturer, Service, Recycler, Auditor); 100% parameterized queries; 5-layer SQL sandbox preventing DROP or DELETE commands.</td>
    <td><code>sqlguard.py</code> and <code>tests/test_api.py</code>.</td>
  </tr>
  <tr>
    <td><b>Audit Trails &amp; Tamper Detection</b></td>
    <td>An unchangeable ledger where any unauthorized edit immediately sounds an alarm.</td>
    <td>Cryptographic SHA-256 hash chaining: every event contains the hash of the previous event. Editing any past row breaks the entire chain.</td>
    <td><code>audit.py</code> and Event Ledger &rarr; <b>Verify Ledger Chain</b> button.</td>
  </tr>
</tbody>
</table>

<h3>5. Architecture, Subqueries &amp; Relational Algebra Services</h3>
<table>
<thead>
  <tr><th>Syllabus Topic</th><th>What it Means in Simple Words</th><th>Feature in BatteryTrace</th><th>Where to See in Code / UI</th></tr>
</thead>
<tbody>
  <tr>
    <td><b>3-Schema ANSI/SPARC Architecture</b></td>
    <td>Dividing the database into 3 independent layers so physical disk changes don't break frontend views.</td>
    <td>1. Internal level: SQLite B-tree pages on disk.<br>2. Conceptual level: Normalized BCNF tables (Asset, Passport, TestResult).<br>3. External level: User-specific Views (v_asset_overview, v_active_passport) and role dashboards.</td>
    <td><code>sql/schema.sql</code>, <code>v_asset_overview</code>, and Frontend personas.</td>
  </tr>
  <tr>
    <td><b>Physical &amp; Logical Data Independence</b></td>
    <td>Ability to change physical disk indexes without modifying queries, and modifying table columns without breaking existing user views.</td>
    <td>Adding B-tree indexes (<code>idx_test_asset_time</code>) speeds up the app without changing frontend code. Adding <code>TestResult</code> didn't break existing <code>Asset</code> queries.</td>
    <td><code>sql/schema.sql</code> (indexes) and <code>v_asset_overview</code>.</td>
  </tr>
  <tr>
    <td><b>Correlated Subqueries</b></td>
    <td>A query inside a SELECT list that runs row-by-row to compute a value based on the outer table's current row.</td>
    <td>Looking up each battery's current location, host vehicle name, and latest SoH % directly in <code>v_asset_overview</code> without mutating base tables.</td>
    <td><code>v_asset_overview</code> in <code>sql/schema.sql</code> (lines 103-107).</td>
  </tr>
  <tr>
    <td><b>Relational Algebra Operations</b></td>
    <td>The mathematical building blocks of all SQL queries (&sigma; Selection, &pi; Projection, &bowtie; Join, &minus; Difference).</td>
    <td>1. Selection: Filtering active batteries.<br>2. Projection: Selecting only code, capacity, and chemistry.<br>3. Natural Join: Combining Asset with Passport.<br>4. Difference: Finding batteries with missing passports (DQ-003).</td>
    <td>SQL Lab Queries #1 to #8 and Data Quality rules (<code>services.RULES</code>).</td>
  </tr>
  <tr>
    <td><b>TCL (Transaction Control Language)</b></td>
    <td>Commands that manage transaction boundaries: COMMIT, ROLLBACK, SAVEPOINT.</td>
    <td>If writing an event succeeds but updating the passport fails, <code>con.rollback()</code> undoes all intermediate writes cleanly.</td>
    <td><code>db.tx()</code> in <code>db.py</code> and <code>services.py</code>.</td>
  </tr>
  <tr>
    <td><b>DCL (Data Control Language) &amp; RBAC</b></td>
    <td>Controlling access permissions so unauthorized users cannot alter or view sensitive records.</td>
    <td>4 distinct roles (Manufacturer, Service, Recycler, Auditor). Recyclers cannot issue new packs; Auditors cannot alter ledger records.</td>
    <td><code>domain.ROLE_CAN_RELINK</code>, <code>services.py</code>, and header role switcher.</td>
  </tr>
</tbody>
</table>

<h3>6. Quick Viva Voce Revision (Explain in 30 Seconds)</h3>
<div class="grid2">
  <div class="circ-item" style="padding:16px;">
    <b>Q: Why is SQLite ACID compliant in your project?</b>
    <p class="small muted" style="margin-top:6px;">We use <code>BEGIN IMMEDIATE</code> transactions with a rollback journal. It takes an exclusive write lock upfront so no other thread can cause lost updates or write skew (Atomicity &amp; Isolation). Foreign keys and 11 triggers ensure Consistency, and disk flush guarantees Durability.</p>
  </div>
  <div class="circ-item" style="padding:16px;">
    <b>Q: What is the Bill of Materials (BOM) problem?</b>
    <p class="small muted" style="margin-top:6px;">Batteries have multi-tier hierarchies: Vehicles contain Packs, Packs contain Modules, Modules contain Cells. Relational tables cannot traverse unknown depths with plain JOINs. We solve this using <code>WITH RECURSIVE</code> (CTE) in SQL and bounded BFS in Python.</p>
  </div>
  <div class="circ-item" style="padding:16px;">
    <b>Q: How do you prevent components being in two vehicles at once?</b>
    <p class="small muted" style="margin-top:6px;">We store temporal intervals <code>[valid_from, valid_to)</code>. Two database triggers (<code>trg_rel_overlap_ins</code> and <code>trg_rel_overlap_upd</code>) check that no child asset can have overlapping active time windows.</p>
  </div>
  <div class="circ-item" style="padding:16px;">
    <b>Q: Why not store battery status in the LifecycleEvent table?</b>
    <p class="small muted" style="margin-top:6px;">Repeating manufacturer and capacity in every event creates update and insertion anomalies (violating 2NF and 3NF). We normalize into BCNF by separating Asset from LifecycleEvent, with <code>Asset.status</code> synchronized via atomic transaction.</p>
  </div>
</div>
`,

policy: `
<p>Modern electric vehicle (EV) battery passport systems operate under fast-evolving international statutory mandates and open-source industry standards. This matrix maps global legislation (2024–2027) directly to relational database design choices in BatteryTrace:</p>

<h3>1. Global regulatory comparison (EU vs. US vs. India)</h3>
<table>
<thead>
  <tr><th>Jurisdiction &amp; Regulation</th><th>Enforcement Timeline</th><th>Core Legal Mandate</th><th>DBMS Architecture Requirement</th></tr>
</thead>
<tbody>
  <tr>
    <td><b>European Union</b><br>Regulation (EU) 2023/1542<br>(Articles 7, 8, 14, 77)</td>
    <td>Mandatory <b>18 Feb 2027</b> for EV &amp; industrial batteries &gt; 2 kWh</td>
    <td>Mandatory digital battery passport, carbon footprint declaration, recycled material minimums (Co, Li, Ni), second-life passport succession (Art. 77(7)), and recycling closure (Art. 77(8)).</td>
    <td>Composite key versioning, atomic passport succession, triggers blocking post-recycle edits (<code>trg_asset_terminal</code>), and dynamic SoH diagnostic time series (<code>TestResult</code>).</td>
  </tr>
  <tr>
    <td><b>United States</b><br>Inflation Reduction Act (IRA § 30D) &amp; FEOC Guidance</td>
    <td>Phase-in 2024–2025; stringent supplier exclusions active</td>
    <td>To qualify for the $7,500 tax credit, critical minerals must originate from US/FTA partners; strict exclusion of Foreign Entities of Concern (FEOC) across multi-tier extraction and refining.</td>
    <td>Deep multi-tier supply chain genealogy tracing from finished pack down to cell batch codes via cycle-safe recursive CTEs (<code>WITH RECURSIVE</code>).</td>
  </tr>
  <tr>
    <td><b>India</b><br>Battery Waste Management Rules (BWMR 2022) &amp; NITI Aayog</td>
    <td>Mandatory Extended Producer Responsibility (EPR) reporting active; 2025–2028 targets</td>
    <td>Extended Producer Responsibility (EPR) credits on the CPCB portal, mandatory recovery targets (70% &rarr; 90%), Unique Identification Numbers (UIN), and swap station telemetry.</td>
    <td>Strict temporal custody tracking (<code>[valid_from, valid_to)</code> non-overlapping intervals), component transfers between owners/operators, and immutable event ledger.</td>
  </tr>
</tbody>
</table>

<h3>2. Open-source reference architectures &amp; industrial standards</h3>
<table>
<thead>
  <tr><th>Project / Standard</th><th>Lead Organization / Repository</th><th>Architectural Pattern Borrowed</th></tr>
</thead>
<tbody>
  <tr>
    <td><b>Eclipse Tractus-X DPP</b></td>
    <td>Catena-X Automotive Network / Eclipse Foundation<br><code>eclipse-tractusx/digital-product-pass</code></td>
    <td>Separation of physical asset identifier (QR / digital link) from sovereign versioned passport payload; decentralized trust layer.</td>
  </tr>
  <tr>
    <td><b>Eclipse Tractus-X IRS</b></td>
    <td>Item Relationship Service<br><code>eclipse-tractusx/item-relationship-service</code></td>
    <td>Recursive directed acyclic graph (DAG) traversal across multi-level Bills of Materials (BOM) with depth limiting and cycle prevention.</td>
  </tr>
  <tr>
    <td><b>Battery Pass Consortium</b></td>
    <td>German BMWK / Fraunhofer / Systemiq<br><code>thebatterypass.eu</code></td>
    <td>90+ attribute taxonomy across composition, electrochemical durability, recycled content, and carbon footprint lifecycle stages.</td>
  </tr>
  <tr>
    <td><b>GS1 EPCIS 2.0 / OpenEPCIS</b></td>
    <td>GS1 Standard / OpenEPCIS Consortium<br><code>openepcis/epcis-repository-ce</code></td>
    <td>Event-driven state transitions (Object, Aggregation, and Transformation events) linked by parent-child containment semantics.</td>
  </tr>
</tbody>
</table>

<h3>3. Technical mapping: Policy mandates to relational database constraints</h3>
<table>
<thead>
  <tr><th>Real-World Policy Requirement</th><th>DBMS Technical Challenge</th><th>How BatteryTrace Enforces It</th></tr>
</thead>
<tbody>
  <tr>
    <td><b>EU Art. 77(7) Passport Succession</b></td>
    <td>Successor passport must reference exactly one predecessor for the same physical battery, with strictly higher version number.</td>
    <td>Trigger <code>trg_passport_chain</code> enforces <code>previous.asset_id = NEW.asset_id</code> and <code>previous.passport_version &lt; NEW.passport_version</code>. Partial index enforces max 1 <code>ACTIVE</code> passport.</td>
  </tr>
  <tr>
    <td><b>EU Art. 77(8) Recycling Termination</b></td>
    <td>When an asset is recycled, all containment links must close and no further lifecycle events or status mutations can occur.</td>
    <td>Atomic transaction in <code>services.record_event</code> closes passport and relationships; trigger <code>trg_asset_terminal</code> aborts any subsequent status changes.</td>
  </tr>
  <tr>
    <td><b>US IRA / FEOC Batch Verification</b></td>
    <td>Auditing whether any sub-component in an assembled pack originated from a restricted mineral batch code across arbitrary tiers.</td>
    <td>Recursive CTE (<code>recall.py</code>) traces the entire sub-assembly hierarchy downstream and upstream, checking all constituent batch codes.</td>
  </tr>
  <tr>
    <td><b>India BWMR EPR Custody Transfers</b></td>
    <td>Tracking physical handover of packs, modules, and cells across owners, repairers, and recyclers without temporal gaps or overlaps.</td>
    <td>Half-open temporal intervals <code>[valid_from, valid_to)</code> with trigger-enforced mutual exclusion (<code>trg_rel_overlap_ins</code>, <code>trg_rel_overlap_upd</code>).</td>
  </tr>
  <tr>
    <td><b>EU Art. 14 Health Diagnostics</b></td>
    <td>Recording continuous degradation (SoH %, cycle counts) over time without overwriting historical test milestones.</td>
    <td>Normalized <code>TestResult</code> table (1-to-N with <code>Asset</code>) indexed on <code>(asset_id, test_time)</code> for fast chronological range scans.</td>
  </tr>
  <tr>
    <td><b>Audit Ledger Tamper-Evidence</b></td>
    <td>Preventing retroactive alteration, deletion, or back-dating of regulatory event evidence.</td>
    <td>Cryptographic SHA-256 hash chaining (<code>prev_hash &rarr; event_hash</code>), plus database triggers <code>trg_event_no_update</code> and <code>trg_event_no_delete</code>.</td>
  </tr>
</tbody>
</table>

<div class="notice">
  <b>Academic &amp; Engineering Scope:</b> BatteryTrace is a pedagogical B.Tech DBMS semester project designed to demonstrate core database theory (BCNF, ACID, triggers, recursive CTEs, temporal intervals, hash chaining). It does not claim formal legal compliance with EU 2023/1542, US IRA, or India BWMR, and does not replace a production enterprise dataspace connector. All operational data is synthetically generated for demonstration and testing.
</div>`
};
