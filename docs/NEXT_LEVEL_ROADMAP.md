# BatteryTrace — next-level engineering roadmap

This is an ambitious but staged roadmap. The goal is a defensible final-year engineering project, not a large number of unintegrated technologies. Work top to bottom; don't jump to optional infrastructure before lifecycle correctness is solid.

## Product thesis
An EV battery's components can be assembled, removed, repaired, moved to a second-life system, or recycled. A useful database must preserve identity and dated lineage, reject impossible transitions, explain how a conclusion was derived, and support targeted recall queries. The project evaluates design trade-offs rather than assuming one technology is best.

## Phase 0 — establish the baseline (mandatory)
- Re-run existing tests and inspect the app manually.
- Document every route, table, lifecycle type, state transition, known invariant and UI screen.
- Capture the current test result and don't change seed data silently.
- Add tests before changing fragile paths.

**Exit gate:** all existing tests pass; key behaviour and limitations are documented.

## Phase 1 — domain correctness and schema quality (highest priority)
- Define allowed asset types, statuses and lifecycle event types in one domain module.
- Formalize state transitions as a state machine. Invalid transitions return a useful validation error and leave all tables unchanged.
- Define component membership as a temporal relationship with clear rules for valid intervals, overlapping assignments, transfers and re-installation.
- Validate passport version numbers, one-active-passport invariant, valid previous-version link, same-asset lineage, no passport cycles, and terminal recycling state.
- Use explicit transactions for compound lifecycle operations.
- Add idempotency keys or another documented retry-safe write strategy for event submission.
- Add database constraints where possible and application-level tests for constraints that need cross-row checks.
- Add negative tests and rollback tests for every transition.

**Exit gate:** seeded legitimate flows pass; every deliberately invalid transition is rejected without partial writes; lineage and passport chains have tests.

## Phase 2 — secure, maintainable application architecture

### Recommended target (not mandatory rewrite for its own sake)
- Backend: FastAPI with Pydantic request/response validation and SQLAlchemy 2.x; Alembic migrations.
- Relational source of truth: PostgreSQL for multi-user/deployment use; SQLite remains a low-friction demo/test option if the repository can keep both configurations tested.
- Frontend: a typed component system only if it clearly improves consistency/testability. A small Vite + React + TypeScript app is reasonable, but avoid migrating just for fashion; retain an accessible, responsive operations UI.
- Configuration via environment variables and `.env.example`; secrets must never be committed.
- Structured logging, stable API error format, health endpoint, API docs and bounded pagination.
- Auth: secure password hashing and server-side role checks if persistent users are implemented. Never ship a production default admin password.
- Export controls and CSV formula-injection mitigation.

**Exit gate:** fresh checkout setup works; migrations create a new database; API tests cover errors and permissions; no secrets or permissive production settings.

## Phase 3 — evidence and auditability
- Keep lifecycle events append-only for normal users; corrections should be compensating events with actor, timestamp, reason and reference to the corrected event.
- Add `actor_id`, organization scope, request/correlation ID, source/evidence metadata, and event schema version where justified.
- Optional tamper-evident audit chain: canonicalize event fields and calculate a hash referencing the previous event hash. Test reordering, edit and removal detection. Explain that a hash chain is only tamper-evident if an attacker cannot rewrite the whole chain and anchor; it does not certify the truth of inputs.
- Make provenance visible in UI (who recorded, when, what evidence, whether evidence is verified or self-reported).
- Distinguish `unknown`, `not provided`, `verified`, `self-reported`, and `invalid` rather than treating missing data as zero or false.

**Exit gate:** an auditor can review event history, corrections and evidence provenance; tampering tests behave as expected; UI doesn't overstate evidence.

## Phase 4 — recall and lineage engine
- Build deterministic seed generation with a stored random seed and known expected downstream set for each test recall.
- Support forward trace (component -> packs/products) and backward trace (pack -> origin/batches) with cycle-safe traversal and bounds.
- Provide a recall report containing query scope, timestamp, matching assets, paths, unknown links, warnings, and a downloadable CSV/JSON.
- Test deep chains, branching, duplicate links, closed historical links, cycles and missing nodes.
- Report recall completeness against the seeded ground truth; do not infer perfect real-world completeness from synthetic test success.

**Exit gate:** exact expected paths and recall sets match for a fixed fixture suite; invalid/cyclic input is handled predictably.

## Phase 5 — real relational-versus-graph experiment (main research contribution)
- Keep a canonical generated dataset and import the same node/edge/event IDs into both systems.
- Suggested comparison: PostgreSQL recursive CTE/closure strategy versus Neo4j path queries. Document what is equivalent and where semantics differ.
- Workloads: direct child lookup, full ancestors, downstream recall from a defective batch, lifecycle timeline, and component transfer history.
- Scales: choose realistic levels such as 1k, 10k and 100k events only if hardware/runtime allows; adapt and document rather than fabricate data or results.
- For each database, first assert result equivalence against known ground truth. Then run warm-up iterations and repeated timed samples, recording p50, p95, throughput, errors, and resource notes.
- Record OS, CPU, memory, versions, indexes, configuration, seed, data-generation time, query text, run count and raw samples.
- Do not compare one tuned database with one untuned database. Include an explicit fairness section.

**Exit gate:** one command regenerates data and benchmark outputs; raw measurements and summary are committed; conclusions follow actual output and mention limitations.

## Phase 6 — operational dashboard, designed not decorated
- Information architecture: Overview, Assets, Lineage, Recall Simulation, Event Ledger, Data Quality, Benchmarks, Administration, DBMS Lab.
- Overview should explain KPIs and “as of” timestamp; don't create meaningless charts. Give operators an actionable “attention required” list.
- Asset register: real filters, sorting, pagination, status, passport version, last event, source/evidence status and quick actions.
- Lineage: readable path/tree with keyboard alternative and a textual path/export fallback. Show valid-from/valid-to intervals rather than implying every historical relationship is current.
- Event ledger: filters, detail drawer, event IDs, actor/time/evidence and corrections as separate events.
- Data quality: severity, rule ID, evidence/path, confidence/limitations, suggested next action and resolved/ignored state with reason.
- Show useful loading, error, no-results and form-validation states. Confirm irreversible or terminal actions.
- No fake live feed, decorative charts, gradients, AI-generated marketing copy, or “AI-powered” labels without an implemented and evaluated feature.

**Exit gate:** manually checked at desktop, tablet and mobile widths; basic keyboard/accessibility checks; end-to-end tests cover primary tasks.

## Phase 7 — final-year packaging
- ER diagram + data dictionary + API contract + migration notes + deployment architecture.
- A 5-minute demo script with synthetic data warnings.
- Syllabus map for ER model, normalization, keys/integrity constraints, indexes/query plans, ACID, concurrency, recovery, NoSQL and CAP-related discussion only where implemented.
- Limitations and future work; no unsupported novelty statement.
- Optional Docker Compose only after local setup remains easy and instructions are tested.

**Exit gate:** a classmate can install and run the project from the README without undocumented steps; a teacher can reproduce the experiment and follow the design rationale.

## Priority order if time is constrained
1. Lifecycle and data integrity.
2. Repeatable tests and clean setup.
3. Recall completeness and lineage correctness.
4. Light dashboard polish.
5. Reproducible performance comparison.
6. Optional deployment/auth/graph extras.

Do not trade correctness for additional features.
