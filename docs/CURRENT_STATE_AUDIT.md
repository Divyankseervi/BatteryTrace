# Current-state engineering audit (handoff baseline)

Audit date: 26 October 2026. This file records the current source as packaged, not an assertion that the project is production-ready.

## Current architecture
- `server.py`: Python standard-library `ThreadingHTTPServer` API and SQLite persistence in one file.
- `index.html`: single-page frontend with embedded CSS and JavaScript.
- `sql/schema.sql`: documented SQLite schema that mirrors the schema string inside `server.py`; this duplication can drift unless tested.
- `sql/demo_queries.sql`: teaching queries.
- `tests/test_smoke.py`: isolated end-to-end smoke suite that copies the project into a temporary directory and runs a server with a temporary database.
- `docs/RESEARCH_REVIEW.md`: selected published papers, public repositories and a proposed benchmark direction.

## Current API surface
- `GET /` and `GET /index.html`: serve the dashboard.
- `GET /api/health`: basic health response with database type and database filename.
- `GET /api/summary`: KPI counts and recent events.
- `GET /api/assets`: search/filter assets with a bounded result set.
- `GET /api/events`: most recent lifecycle events, bounded to 100.
- `GET /api/issues`: runs the current rule-based integrity checks.
- `GET /api/lineage/{asset_code}`: bounded traversal of connected parent/child relationships, with an event and passport history for the selected asset.
- `POST /api/events`: records a lifecycle event and performs selected state/passport updates.

## Current data tables
- `Asset`: identity, type, manufacturer, chemistry, capacity, current status and creation date.
- `Passport`: passport versions, status and previous-passport pointer.
- `AssetRelationship`: parent-child membership with `valid_from` / `valid_to` dates.
- `LifecycleEvent`: event type/date/location/organization/notes.

## Existing strengths
- Parameterized SQL in the visible search queries and writes.
- Foreign keys enabled per connection and database checks for types/statuses/basic value ranges.
- Unique passport version number by asset and partial unique index for at most one active passport per asset.
- Compound event/state/passport writes are wrapped in a SQLite transaction.
- Seed data is explicitly synthetic, including intentional integrity warnings.
- The six baseline tests cover page/health response, summary/assets/events/lineage, intentional warnings, unknown asset validation, repurposing and recycling.

## Material gaps / risks to address
1. **Lifecycle transition model is incomplete.** The endpoint permits several event types on almost any asset/state, with only targeted checks for repurposing/recycling. Centralize and test the full transition policy.
2. **Idempotency is not implemented.** Repeating a successful POST can create duplicate events. Add an idempotency strategy only after defining request identity and conflict semantics.
3. **Temporal relationship correctness is incomplete.** The schema checks interval ordering but does not prevent overlapping assignments across rows. There is no dedicated atomic transfer workflow yet.
4. **Passport chain validation is incomplete.** The foreign key ensures a previous record exists, but same-asset ownership, valid version succession and cycle prevention are not enforced comprehensively.
5. **API security is prototype-level.** There is no authentication or role authorization. The server returns raw exception messages for some errors and sets permissive CORS headers. Keep it bound to localhost for local teaching use; do not deploy publicly without remediation.
6. **No anti-forgery trust model.** There is no signed evidence, user/organization identity, append-only correction workflow or cryptographic audit chain.
7. **Lineage traversal semantics are broad.** It traverses all relationship types in both directions, treats temporal relationships as connected without fully distinguishing current vs historical edges, and uses a fixed maximum depth of four. This is useful for a demo but can be misleading for recall calculations.
8. **Schema source duplication.** The schema exists both as a Python string and SQL file. Make one source canonical or add a test that ensures both stay aligned.
9. **No reproducible benchmark yet.** There is no live PostgreSQL/Neo4j comparison or validated timing dataset. Do not claim performance conclusions.
10. **Frontend manual QA gap.** The README notes that the earlier headless screenshot attempt timed out. Recheck responsive and accessible interaction states with an available browser/tool before making claims.
11. **Pagination and data scale are limited.** Assets are capped at 250 and event history at 100 without pagination controls or total counts.
12. **Event editing/correction semantics are missing.** Lifecycle events are not formally append-only and no correction/audit trail exists.

## Exact baseline test command
```bash
python -m unittest discover -s tests -v
```
The handoff baseline was run during packaging; the six tests passed. Re-run before relying on this statement after making any changes.

## Recommended first fixes
1. Expand tests around invalid transition, rollback, repeated submission, passport chain and component assignment interval cases.
2. Implement lifecycle transitions and transfer semantics.
3. Improve API input/error handling and restrict CORS to the intended local origin until authentication exists.
4. Build recall correctness against known synthetic ground truth.
5. Only then conduct UI redesign, framework migration or database benchmarking.


---
## Resolution of the 12 gaps (v2, 27 Oct 2026)
| # | Gap | Status |
|---|---|---|
| 1 | Transition model | Done: `domain.TRANSITIONS`, tested incl. rollback |
| 2 | Idempotency | Done: `idempotency_key` UNIQUE + immediate lock; replay vs conflict semantics |
| 3 | Temporal overlaps / transfer | Done: trigger + `transfer_component` + `close_relationship` |
| 4 | Passport chain | Done: trigger (same asset, earlier version, immutable) + DQ-004 |
| 5 | API security | Mostly: CORS removed, Host/Origin/CSP, no leaks. **Authentication still absent** (demo roles only) |
| 6 | Anti-forgery / audit | Partial: hash chain, actor, evidence status. No signatures; limits documented and tested |
| 7 | Lineage semantics | Done: directed, CURRENT/AS_OF/ALL, shortest path + path count, warnings |
| 8 | Schema duplication | Done: single `sql/schema.sql` |
| 9 | Benchmark | Partial: SQLite strategies measured; PostgreSQL/Neo4j NOT run |
| 10 | Frontend QA | Done with Playwright at 3 widths + 19 flows; screen-reader pass not done |
| 11 | Pagination | Done: limit/offset/total, 200 max |
| 12 | Event correction | Done by design: append-only (triggers) + corrective events |
