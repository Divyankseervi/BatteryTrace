# Changelog

## Automated Feature Screenshot Suite & Final Academic Case Study Report — 30 October 2026

- **Automated Feature Screenshot Suite**: Added `tools/capture_case_study_screenshots.py` using Playwright Chromium to run the live application and systematically capture 20 high-resolution, pixel-perfect desktop screenshots across all system views, interactive modals, and DBMS lab modules.
- **Captured Feature Set (20 Screenshots)**:
  1. `01_overview_dashboard.png`: Executive fleet dashboard, active vehicle KPIs, circular economy mass balance, and ledger integrity.
  2. `02_actor_persona_mfg.png`: Gigafactory Manufacturer persona view with role-tailored actions.
  3. `03_assets_catalog.png`: Complete vehicle and battery catalog (Tata Nexon EV Max, Ather 450X, Mahindra XUV400, Indiranagar BESS).
  4. `04_asset_lineage_pack.png`: Battery pack detail view with multi-tier Bill of Materials (BOM) hierarchy tree.
  5. `05_dpp_passport_certificate.png`: Official statutory Digital Battery Passport (EU 2023/1542 Article 77) card with QR code and carbon footprint.
  6. `06_diagnostic_health_modal.png`: Interactive diagnostic health test logger dialog (SoH %, cycles, internal resistance).
  7. `07_component_transfer_modal.png`: Component swap/transfer modal enforcing temporal validity intervals and hierarchy taxonomy.
  8. `08_cell_ancestry_lineage.png`: Single cell (`CELL-1001-A1`) upward multi-level ancestry lineage traversal.
  9. `09_recall_simulation_batch.png`: Safety recall simulation tracing defective production batch `NC-2024-W03` across vehicles.
  10. `10_event_ledger_hash_chain.png`: Append-only event ledger protected by cryptographic SHA-256 hash chaining.
  11. `11_event_ledger_verified.png`: Interactive cryptographic verification audit mathematically proving ledger integrity.
  12. `12_data_quality_rules.png`: 7 automated SQL business rules with evidence inspector and seeded educational anomalies.
  13. `13_guided_repair_dialog.png`: Guided repair dialog resolving conflicting component parent intervals.
  14. `14_dbms_lab_schema_erd.png`: Interactive DBMS Lab schema browser and vector Entity-Relationship diagram.
  15. `15_dbms_lab_normalization.png`: Normalization analysis with mathematical 1NF, 2NF, 3NF, BCNF proofs.
  16. `16_dbms_lab_sql_runner.png`: Interactive SQL runner executing recursive CTE queries with `EXPLAIN QUERY PLAN`.
  17. `17_dbms_lab_acid_concurrency.png`: ACID transaction isolation and concurrency locking proof matrix.
  18. `18_dbms_lab_benchmarks.png`: Traversal benchmark curves showing 11.6× speedup on 90,000 synthetic records.
  19. `19_dbms_lab_syllabus_map.png`: BCSE302L comprehensive syllabus guide directly mapped to project features.
  20. `20_dbms_lab_policy_matrix.png`: Global battery passport regulatory matrix (EU 2023/1542, US IRA, India BWMR 2022).
- **Final Case Study Document**: Created `docs/FINAL_CASE_STUDY_REPORT.md` (and corresponding interactive chat artifact) with complete 14-section academic structure, embedding all 20 screenshots with detailed captions, syllabus mapping, BCNF mathematical proofs, ACID concurrency analysis, and examiner Q&A viva defense guide.
- **Neo4j Graph Database Integration & Live Projection**: Configured and verified the Neo4j 5.26 graph projection module (`neo4j_graph.py`). Connected to local Neo4j on port 7474, successfully synchronized 22 assets and 14 containment relationships from SQLite via HTTP transactional commit API, executed Cypher path-matching queries (`MATCH p=(start:Asset {asset_code: $code})-[:RELATED*1..8]->(node:Asset)`), and captured live verification screenshot `docs/screenshots/21_dbms_lab_neo4j_projection.png`.
- **Human-Formatted Microsoft Word (.docx) Report Generated**: Created `tools/generate_human_docx.py` producing `docs/BatteryTrace_Case_Study_24BCE0793_Updated.docx` (4.97 MB) for Divyank Seervi (24BCE0793), submitted to Prof. Sivakumar V for BCSE302L Database Systems at VIT. Formatted cleanly with Times New Roman, all-black font, 1-inch margins, no running headers/footers, and all 21 embedded screenshots.
- **Publication-Quality Academic PDF Generated**: Created `tools/build_case_study_pdf.py` producing `docs/BatteryTrace_DBMS_Case_Study.pdf` (36 pages, 5.50 MB) featuring VIT academic header styling, the official GitHub repository link (`https://github.com/Divyankseervi/BatteryTrace`), all 20 embedded screenshots, running page headers, and page-numbered footers.
- **Verification**: Verified 111 out of 111 unit, integration, concurrency, crash recovery, and security tests continue to pass.

## AWS Cloud Architecture Dual-Mode Deployment (BCSE355L) — 30 October 2026

- **Dual-Mode Cloud Compatibility**: Added support for remote hosting environments via environment variables `HOST` (binds to `0.0.0.0` or custom interface), `ALLOW_CORS=1` (enables cross-origin headers and preflight handling), and `SERVER_NAME` for instance identification.
- **Frontend Runtime Endpoint Configuration**: Added `static/config.js` and updated `api(...)` client in `static/app.js` to dynamically prefix requests with the AWS Application Load Balancer endpoint when static files are hosted in Amazon S3.
- **CORS & Preflight Support**: Implemented HTTP `OPTIONS` handling in `server.py` with `Access-Control-Allow-Origin`, `Access-Control-Allow-Methods`, and `Access-Control-Allow-Headers` headers.
- **Load Balancer Health & Server Differentiation**: Enhanced `/api/health` to return `server_name` (`Server1` vs `Server2`), enabling round-robin load distribution proof during examiner evaluation.
- **Cloud Architecture Documentation**: Added `docs/AWS_CLOUD_ARCHITECTURE.md` mapping the VIT BCSE355L Cloud Architecture Design case study requirements (S3 static frontend, two EC2 backend instances, Application Load Balancer, and shared database tier) with deployment blueprints, test scripts, and viva defense answers.
- Zero local regressions: All 111 unit, integration, and security tests continue to pass.

- Added a reproducible Docker Compose setup for optional Neo4j 5.26 Community and Windows PowerShell configuration steps.
- Added controls in DBMS Lab to sync the current SQLite projection and inspect upstream/downstream Neo4j lineage paths.
- Neo4j remains optional; SQLite remains the source of truth. No graph benchmark results are claimed.

## DBMS Lab loading fix — 30 October 2026

- Fixed the `static/lab.js` template-literal boundary between the syllabus and policy content. The DBMS Lab now loads its `BTLab` content instead of failing with `BTLab is not defined`.

## Final submission & regulatory refinement — 27 October 2026

**Case study alignment, interactive diagnostics and frontend features**
- Added `record_diagnostic_test` service and endpoint `POST /api/diagnostics` for Case Study FR-5 and EU Art. 14, atomically logging the test measurement in `TestResult` and appending a linked `TESTED` event to the SHA-256 hash-chained ledger.
- Added interactive **Record Diagnostic Test** modal (`openDiagnostic`) to the Lineage page with live validation of SoH %, cycle count, and role authorization.
- Added official **Digital Battery Passport (DPP) Certificate Card** modal (`openPassportCard`), rendering QR matrix code, battery chemistry, rated capacity, passport version succession chain, and circularity status.
- Added **Assembly Component Hierarchy Tree** (`renderAssemblyTree`) in `PAGES.lineage`, visually rendering multi-tier parent-child containment with clickable nodes and status badges.
- Added **Circular Economy & Lifecycle Stewardship** KPI widget in `PAGES.overview`, breaking down active mobility, second life storage, repair, recycling, and fleet average SoH %.
- Added **Copy SQL** and **Clear Output** controls to the read-only SQL lab.

**Resolution of previously documented gaps**
- **Batch Recursive Traversal Optimization (The 7× Gap Resolved)**: Implemented `trace_frontier` (`_SQL_FRONTIER` in `recall.py`) using `UNION` deduplication across intermediate graph frontiers. Slashed batch traversal time from 1,171 ms to 100 ms (an **11.6× speedup**) on 90,000 assets, achieving performance parity with procedural Python BFS in pure SQL. Integrated into `benchmarks/run_benchmark.py`.
- **Crash Recovery & Durability Testing**: Added automated `CrashRecoveryTests` (`test_domain.py`) verifying that mid-transaction power failures or crashed uncommitted writes roll back cleanly via `BEGIN IMMEDIATE`, passing `PRAGMA integrity_check` and preserving the SHA-256 hash chain tip.
- **Screen-Reader & ARIA Accessibility**: Added full ARIA 1.2 semantics across the UI (`role="tree"`, `role="treeitem"`, `aria-expanded`, `aria-current`, `scope="col"`, `role="region"`). Added automated `ScreenReaderAccessibilityTests` (`test_domain.py`).
- **Benchmark Hardware Variance**: Documented the "Quote ratios, not milliseconds" scientific evaluation standard in the submission guide and benchmark notes.
- **Academic Boundaries**: Added Section 11 to `docs/CASE_STUDY_SUBMISSION_GUIDE.md` and updated `docs/VIVA_GUIDE.md`.
- Test suite expanded from 104 to **111 tests**, 100% passing.

**Model integrity fixes**
- `sql/triggers.sql`: Updated trigger `trg_asset_terminal` to block status mutations on both `RECYCLED` and `RETIRED` statuses (`WHEN OLD.status IN ('RECYCLED','RETIRED') AND NEW.status <> OLD.status`).
- `domain.py`: Updated `TRANSITIONS['TRANSFERRED']` to permit transfers from `ALL_LIVE` (`{'ACTIVE', 'IN_REPAIR', 'SECOND_LIFE'}`), fixing an issue where closing relationships on components in repair was rejected.
- `services.py`: Added parent creation date validation in `transfer_component` (`if date < parent['created_at']: raise DomainError(..., 'BEFORE_CREATION')`), strictly following interval boundary precedence.
- `recall.py`: Added deduplication of input asset codes in `resolve_starts` to avoid duplicate graph traversals and duplicate path counts in recursive CTEs.

**Global policies, standards & open-source architectures**
- Added **Global policies & standards** tab to the DBMS lab (`static/lab.js`, `static/app.js`), mapping EU 2023/1542, US IRA § 30D / FEOC, and India BWMR 2022 / NITI Aayog to relational database constraints.
- Analyzed industrial open-source repositories in `docs/RESEARCH_REVIEW.md`: Eclipse Tractus-X (Digital Product Pass, Item Relationship Service, SLDT Semantic Models), Battery Pass Consortium, OpenEPCIS, and Global Battery Alliance.
- Expanded SQL Lab from 15 to 19 runnable queries (`sql/lab_queries.json`): added EU Art. 77(7) passport succession history, circular economy SoH decision matrix, and US IRA multi-tier recursive mineral provenance trace.
- Added comprehensive academic submission document `docs/CASE_STUDY_SUBMISSION_GUIDE.md` with complete relational theory, BCNF proofs, ACID concurrency analysis, and 8 viva defense answers.
- Test suite: 108 tests, all passing.

## v2 engineering iteration — 27 October 2026

**Correctness and integrity**
- Canonical `sql/schema.sql` (loaded by `db.py`; the duplicate Python schema string is gone) plus `sql/triggers.sql` (11 triggers), views, `HierarchyRule` lookup, `batch_code`.
- Central lifecycle state machine (`domain.py`) incl. new `REPAIR_STARTED`; terminal states; chronological dates; no future dates.
- Atomic transactions with `BEGIN IMMEDIATE`; idempotency keys; atomic component transfer; link-correction workflow.
- Append-only SHA-256 hash-chained ledger with verification and documented limits.
- Demo roles (permission matrix; explicitly not authentication).
- Seven data-quality rules with evidence, limits and exposed SQL.

**Recall and DBMS features**: recursive-CTE trace (cycle-safe, depth-bounded, current / as-of / all-history), batch scoping, uncertainty warnings, CSV/JSON export; read-only SQL lab with EXPLAIN; 15 tested example queries; deterministic synthetic fleet generator with independent ground truth.

**Security**: Host/Origin checks, JSON-only writes, no CORS, strict CSP, body limits, no traceback leakage, formula-safe CSV, pagination limits.

**UI**: rebuilt as `index.html` + `static/` (no inline JS/CSS). New pages: lineage, recall, ledger, data quality, DBMS lab. Responsive at 1280/1024/390 px.

**Experiment**: SQLite strategy benchmark with ground-truth checks, index ablation, raw JSON and honest write-up.

**Tests**: 6 → 102 (+19 browser flows run during development). 7/7 deliberate code mutations are caught by the suite.

**Bugs found by testing during this iteration** (all fixed): overlap trigger blocked legitimate link repairs on legacy data; event form checked permissions with user id instead of role; router race let a slow page overwrite a newer one; grid `1fr` caused mobile overflow; benchmark recorded a stale EXPLAIN plan because of Python's statement cache; an authorizer layer was untested because other layers masked it.

**Changed seed data**: added `batch_code` values and `actor_id`s to seed rows; no records were added or removed. Seed events are now hash-chained.

**Known gaps**: no authentication; no PostgreSQL/Neo4j comparison; recursive CTE enumerates paths (slower than BFS on large batch recalls; improvement noted, not implemented); no crash-injection durability test; no screen-reader pass.

## Research-informed refinement — 26 October 2026

- Reworked visual styling to a restrained light theme: white navigation rail, muted neutral surfaces, flat controls, less decorative gradients and reduced card rounding.
- Added CSV export for the currently filtered asset register.
- Added `docs/RESEARCH_REVIEW.md` with related peer-reviewed papers, public GitHub repositories and a carefully qualified possible student research contribution.
- Added `docs/ARCHITECTURE_DECISIONS.md` documenting why the project uses SQLite and what it does not claim to do.
- Added six end-to-end smoke tests using a temporary copy and throwaway database.
- Added keyboard focus visibility and reduced-motion support.

## Validation performed

- Python bytecode compilation for server and test script.
- JavaScript syntax check with Node.js.
- Six automated HTTP/API workflow tests pass: health/frontend, summary/assets/events/lineage, seeded integrity warnings, unknown-asset validation, repurposing passport versioning, and recycling passport closure.
- Headless Chromium screenshot attempt timed out in this environment; therefore no screenshot-based visual test is claimed.

## Claude engineering handoff pack — 26 October 2026

- Added root-level `CLAUDE.md` with project context, visual constraints, engineering standards and verification rules.
- Added `HANDOFF_TO_CLAUDE.md` and a ready-to-paste Claude Code first prompt.
- Added a factual current-state audit, staged next-level roadmap, acceptance checklist and sprint plan.
- Added reusable Claude Code command prompts for audit, testing and visual review.
- Expanded `.gitignore` for local environments, secrets, generated databases and future frontend test/build output.
- Kept the application baseline unchanged; the existing six end-to-end smoke tests should be rerun before and after Claude's changes.
