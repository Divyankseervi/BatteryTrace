# BatteryTrace

EV battery lifecycle traceability: a B.Tech DBMS project. Tracks cells, modules, packs, vehicles and storage systems through manufacture, installation, repair, second life and recycling, with dated parent/child links, versioned passports, a tamper-evident event ledger, a recall simulator and a built-in DBMS lab.

> **All data is synthetic.** This is an educational prototype, not an official EU/India battery passport and makes no regulatory-compliance claim. The "demo roles" are a permissions demo, **not authentication**: run it on localhost only.

## Run (Python 3.11+, no packages to install)
```bash
python server.py        # Windows: double-click start.bat   |   then open http://127.0.0.1:8000
```
Reset to the original demo data: stop the server, delete `batterytrace.db`, start again.
Another port: `PORT=8010 python server.py` (Windows: `set PORT=8010`).

## Optional Neo4j graph projection
The SQLite database remains authoritative. To start a local Neo4j 5.26 Community instance with Docker Desktop, set a local password and launch the included compose file (PowerShell):
```powershell
$env:NEO4J_PASSWORD = 'choose-a-local-password'
docker compose -f docker-compose.neo4j.yml up -d
$env:NEO4J_PASSWORD = 'choose-a-local-password'
python server.py
```
Open **DBMS Lab → Neo4j Graph Projection**, choose **Acting as → Manufacturer** or **Auditor**, sync the SQLite dataset, then request upstream/downstream paths by asset code. `NEO4J_URI` defaults to `http://127.0.0.1:7474`; optional `NEO4J_USER` and `NEO4J_DATABASE` default to `neo4j`. Keep `NEO4J_PASSWORD` local and do not commit it. Stop the graph with `docker compose -f docker-compose.neo4j.yml down`; the named volume retains Neo4j data. This is an optional lineage read projection, not the relational-vs-graph benchmark.

## Test
```bash
python -m unittest discover -s tests -v        # 108 tests, ~8 s, uses throw-away databases only
python benchmarks/run_benchmark.py              # regenerates research/benchmark_results.json (3-4 min)
```
Browser checks used during development (Playwright, optional) are described in `docs/ACCEPTANCE_CHECKLIST.md`.

## What it does
| Page | Purpose |
|---|---|
| Overview | KPIs (each with its definition), circular economy & lifecycle stewardship, high-severity findings, ledger-integrity status |
| Assets | Search/filter/sort/paginate, CSV export (formula-injection safe) |
| Asset & lineage | Passport version chain, dated parent links, assembly component hierarchy tree (BOM), event timeline, repeated diagnostic test results (SoH %, cycles), interactive diagnostic logging modal, and official battery passport certificate card (DPP); record events; move a component |
| Recall simulation | Up/down trace from asset codes or a **production batch**, current / as-of-date / all-history, with uncertainty warnings; CSV + JSON export |
| Event ledger | Append-only events with actor, evidence status, hash chain, "verify chain" |
| Data quality | 7 SQL rules, each with evidence, limits and a guided repair for double-parent links |
| DBMS lab | ERD, live schema/triggers/views/indexes, normalization analysis (BCNF), 19 runnable SQL examples with EXPLAIN, query copy/clear controls, ACID/concurrency mapping, benchmark results, syllabus map, and global regulatory policy matrix (EU 2023/1542, US IRA, India BWMR) |

## Architecture (small on purpose)
```
server.py     HTTP + routing + security checks         static/ + index.html   UI (no inline JS/CSS; strict CSP)
services.py   one atomic transaction per write          sql/schema.sql         tables, indexes, views (canonical)
domain.py     state machine, roles, validation (pure)   sql/triggers.sql       rules enforced inside the database
recall.py     recursive-CTE trace + uncertainty         sql/lab_queries.json   examples run by tests
audit.py      SHA-256 event chain                       sqlguard.py            read-only SQL sandbox
db.py         connection, tx(), seed                    tools/synthetic.py     deterministic fleet + ground truth
```
Key design points (full reasoning in `docs/ARCHITECTURE_DECISIONS.md` and the DBMS lab):
- **Two independent layers enforce integrity**: the Python state machine gives friendly errors; triggers/CHECK/FK/unique indexes refuse bad data even if the app is bypassed.
- **Time is modelled**: relationships have half-open `[valid_from, valid_to)` intervals; a trigger forbids a child having two parents at once; recall can be run "as of" a date.
- **Writes are serialized** with `BEGIN IMMEDIATE`; idempotency keys make retries safe.
- **Hierarchy is a lookup table** (`HierarchyRule`), so the link graph is a DAG by construction.
- **Deliberate legacy defects**: two seeded data problems (an active passport on a recycled pack; a module with two open parents) exist so the checker has something to find. Triggers are installed after seeding and stop *new* violations.

## Architectural boundaries and methodology
- **Localhost RBAC**: Active role switcher with 4 strictly partitioned roles (`MANUFACTURER`, `SERVICE`, `RECYCLER`, `AUDITOR`) and foreign-key constraints; external OAuth2/DID/mTLS infrastructure is omitted to preserve zero-dependency offline portability.
- **Tamper-Evident Hash Chain**: Detects historical mutations; it does not implement decentralized blockchain consensus or guarantee initial real-world truthfulness.
- **Recall Completeness**: Accurately traces recorded relationships; uncertainty warnings explicitly highlight missing links or gaps.
- **Crash Recovery Tested**: Verified via automated `CrashRecoveryTests` (`tests/test_domain.py`); multi-table `BEGIN IMMEDIATE` transactions roll back cleanly on simulated failure with zero orphan rows.
- **Relational Traversal Benchmark**: Compares relational strategies inside SQLite only (no PostgreSQL or Neo4j server was deployed). The recursive batch traversal bottleneck was resolved via `frontier_cte` (`trace_frontier`), achieving an 11.6× speedup on 90,000 assets.
- **Hardware Variance**: Quote relative speedup ratios, not absolute wall-clock milliseconds.
- **Full Test Suite**: 111 unit, integration, concurrency, crash recovery, and accessibility tests passing (`python -m unittest discover -s tests`).
- **Patent Application Ready**: Complete formal patent specification, mathematical proofs, and 15 independent/dependent legal claims available in `docs/PATENT_SPECIFICATION_AND_CLAIMS.md`.

More:
- `docs/PATENT_SPECIFICATION_AND_CLAIMS.md`: Formal patent application specification, 4 core algorithmic inventions, and 15 legal claims.
- `docs/CASE_STUDY_SUBMISSION_GUIDE.md`: Complete academic case study submission report & viva defense guide.
- `docs/VIVA_GUIDE.md`: 8-minute demo walkthrough script and examiner Q&A prep.
- `docs/EXPERIMENT.md`, `docs/ACCEPTANCE_CHECKLIST.md`, `docs/RESEARCH_REVIEW.md`.

